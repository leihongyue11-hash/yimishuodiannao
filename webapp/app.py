from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading
import uuid
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


class TaskView(BaseModel):
    id: str
    filename: str
    status: Status
    progress: int
    error_message: str = ""
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime


app = FastAPI(title="DWG to PDF")
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")

TASKS: dict[str, Task] = {}
JOB_QUEUE: queue.Queue[str] = queue.Queue()


def _now(task: Task) -> None:
    task.updated_at = datetime.utcnow()


def _render_fallback_pdf(task: Task) -> str:
    output = OUTPUT_DIR / f"{task.id}.pdf"
    with output.open("wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
        f.write(b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n")
        text = f"DWG file uploaded: {task.filename}.\\nConfigure DWG_CONVERTER_CMD for real conversion.".encode("latin-1", "replace")
        stream = b"BT /F1 14 Tf 50 750 Td (" + text.replace(b"(", b"[").replace(b")", b"]") + b") Tj ET"
        f.write(b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n")
        f.write(b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n")
        f.write(f"5 0 obj<</Length {len(stream)}>>stream\n".encode())
        f.write(stream + b"\nendstream endobj\n")
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        offsets = [9, 56, 113, 239, 309]
        for off in offsets:
            f.write(f"{off:010d} 00000 n \n".encode())
        f.write(b"trailer<</Root 1 0 R/Size 6>>\nstartxref\n390\n%%EOF")
    return str(output)


def _run_conversion(task: Task) -> str:
    cmd_template = os.getenv("DWG_CONVERTER_CMD", "").strip()
    if not cmd_template:
        return _render_fallback_pdf(task)

    output = OUTPUT_DIR / f"{task.id}.pdf"
    cmd = cmd_template.format(input=task.input_path, output=str(output))
    subprocess.run(cmd, shell=True, check=True)
    if not output.exists():
        raise RuntimeError("converter finished but output PDF not found")
    return str(output)


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
            task.output_path = _run_conversion(task)
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


@app.post("/api/v1/convert", response_model=TaskView)
async def create_convert_task(
    file: UploadFile = File(...),
    paper_size: str = Form("A4"),
    orientation: str = Form("portrait"),
    scale: str = Form("fit"),
    line_style: str = Form("default"),
) -> TaskView:
    ext = Path(file.filename).suffix.lower()
    if ext != ".dwg":
        raise HTTPException(status_code=400, detail="Only .dwg files are accepted")

    task_id = str(uuid.uuid4())
    input_path = UPLOAD_DIR / f"{task_id}.dwg"
    with input_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    task = Task(
        id=task_id,
        filename=file.filename,
        input_path=str(input_path),
        error_message=f"options: paper_size={paper_size}, orientation={orientation}, scale={scale}, line_style={line_style}",
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
    return FileResponse(task.output_path, filename=f"{Path(task.filename).stem}.pdf", media_type="application/pdf")


def _to_view(task: Task) -> TaskView:
    return TaskView(
        id=task.id,
        filename=task.filename,
        status=task.status,
        progress=task.progress,
        error_message=task.error_message,
        download_url=f"/api/v1/download/{task.id}" if task.status == "success" else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
