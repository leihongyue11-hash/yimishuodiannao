from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
for p in (UPLOAD_DIR, OUTPUT_DIR):
    p.mkdir(parents=True, exist_ok=True)

Status = Literal["queued", "running", "success", "failed"]


@dataclass
class Task:
    id: str
    filename: str
    status: Status = "queued"
    progress: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    input_path: str = ""
    output_path: str = ""
    error_message: str = ""
    detail: str = ""
    task_type: Literal["single", "batch"] = "single"


class TaskView(BaseModel):
    id: str
    filename: str
    task_type: Literal["single", "batch"]
    status: Status
    progress: int
    error_message: str = ""
    detail: str = ""
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime


app = FastAPI(title="DWG to PDF")
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")

TASKS: dict[str, Task] = {}
JOB_QUEUE: queue.Queue[str] = queue.Queue()


def _now(task: Task) -> None:
    task.updated_at = datetime.utcnow()


def _converter_template() -> str:
    template = os.getenv("DWG_CONVERTER_CMD", "").strip()
    if not template:
        raise RuntimeError(
            "DWG_CONVERTER_CMD is not configured. Example: "
            "DWG_CONVERTER_CMD='ODAFileConverter \"{input_dir}\" \"{output_dir}\" ACAD2018 PDF 0 1'"
        )
    return template


def _run_converter(input_path: Path, output_pdf: Path) -> None:
    template = _converter_template()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = template.format(
        input=str(input_path),
        input_dir=str(input_path.parent),
        input_name=input_path.name,
        input_stem=input_path.stem,
        output=str(output_pdf),
        output_dir=str(output_pdf.parent),
        output_name=output_pdf.name,
        output_stem=output_pdf.stem,
    )
    proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"convert failed({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip() or cmd}")
    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
        raise RuntimeError(f"convert finished but output not found: {output_pdf}")


def _convert_single(task: Task) -> str:
    output = OUTPUT_DIR / f"{task.id}.pdf"
    _run_converter(Path(task.input_path), output)
    task.detail = "single conversion completed"
    return str(output)


def _extract_dwg_from_zip(zip_path: Path, dest: Path) -> list[Path]:
    dwg_files: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename)
            if name.suffix.lower() != ".dwg":
                continue
            safe_name = "_".join(name.parts)
            target = dest / safe_name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            dwg_files.append(target)
    return dwg_files


def _convert_batch(task: Task) -> str:
    working = OUTPUT_DIR / task.id
    working.mkdir(parents=True, exist_ok=True)
    extract_dir = working / "extracted"
    extract_dir.mkdir(exist_ok=True)
    pdf_dir = working / "pdfs"
    pdf_dir.mkdir(exist_ok=True)

    dwg_files = _extract_dwg_from_zip(Path(task.input_path), extract_dir)
    if not dwg_files:
        raise RuntimeError("ZIP contains no .dwg files")

    total = len(dwg_files)
    for idx, dwg in enumerate(dwg_files, start=1):
        output_pdf = pdf_dir / f"{dwg.stem}.pdf"
        _run_converter(dwg, output_pdf)
        task.progress = 10 + int((idx / total) * 85)
        task.detail = f"converted {idx}/{total}: {dwg.name}"
        _now(task)

    output_zip = OUTPUT_DIR / f"{task.id}.zip"
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for pdf in sorted(pdf_dir.glob("*.pdf")):
            zf.write(pdf, arcname=pdf.name)
    task.detail = f"batch conversion completed: {total} files"
    return str(output_zip)


def _worker() -> None:
    while True:
        task_id = JOB_QUEUE.get()
        task = TASKS.get(task_id)
        if task is None:
            JOB_QUEUE.task_done()
            continue
        try:
            task.status = "running"
            task.progress = 10
            _now(task)
            if task.task_type == "single":
                task.output_path = _convert_single(task)
            else:
                task.output_path = _convert_batch(task)
            task.status = "success"
            task.progress = 100
            _now(task)
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.progress = 100
            task.error_message = str(exc)
            _now(task)
        finally:
            JOB_QUEUE.task_done()


threading.Thread(target=_worker, daemon=True).start()


def _save_upload(file: UploadFile, suffix: str, task_id: str) -> Path:
    path = UPLOAD_DIR / f"{task_id}{suffix}"
    with path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return path


@app.post("/api/v1/convert", response_model=TaskView)
async def create_convert_task(
    file: UploadFile = File(...),
    paper_size: str = Form("A4"),
    orientation: str = Form("portrait"),
    scale: str = Form("fit"),
    line_style: str = Form("default"),
) -> TaskView:
    ext = Path(file.filename).suffix.lower()
    if ext not in {".dwg", ".zip"}:
        raise HTTPException(status_code=400, detail="Only .dwg or .zip files are accepted")

    task_id = str(uuid.uuid4())
    task_type: Literal["single", "batch"] = "single" if ext == ".dwg" else "batch"
    input_path = _save_upload(file, ext, task_id)
    task = Task(
        id=task_id,
        filename=file.filename,
        input_path=str(input_path),
        task_type=task_type,
        detail=f"options: paper_size={paper_size}, orientation={orientation}, scale={scale}, line_style={line_style}",
    )
    TASKS[task_id] = task
    JOB_QUEUE.put(task_id)
    return _to_view(task)


@app.get("/api/v1/tasks/{task_id}", response_model=TaskView)
def get_task(task_id: str) -> TaskView:
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _to_view(task)


@app.get("/api/v1/download/{task_id}")
def download(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "success" or not task.output_path:
        raise HTTPException(status_code=400, detail="Task is not ready")
    name_stem = Path(task.filename).stem
    filename = f"{name_stem}.pdf" if task.task_type == "single" else f"{name_stem}_pdfs.zip"
    media = "application/pdf" if task.task_type == "single" else "application/zip"
    return FileResponse(task.output_path, filename=filename, media_type=media)


def _to_view(task: Task) -> TaskView:
    return TaskView(
        id=task.id,
        filename=task.filename,
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        error_message=task.error_message,
        detail=task.detail,
        download_url=f"/api/v1/download/{task.id}" if task.status == "success" else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
