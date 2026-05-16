# DWG 转 PDF 程序/网页设计方案

## 1. 目标
- 支持用户上传 `.dwg` 文件并生成可下载的 `.pdf`。
- 支持批量转换、纸张尺寸（A4/A3）、横竖版、线宽样式（CTB/STB）设置。
- 网页端支持进度反馈，后端异步任务处理。

## 2. 两种实现路径

### 路径 A：桌面程序（本地离线）
- 技术栈：`Python + PySide6 + ODA File Converter/LibreDWG + ReportLab/Ghostscript`
- 适合：企业内网、数据敏感场景。
- 优点：文件不出本机，部署简单。
- 缺点：多平台打包与依赖管理略复杂。

### 路径 B：网页应用（推荐）
- 前端：`Vue3` 或 `React`。
- 后端：`FastAPI`（Python）或 `Node.js`。
- 转换引擎：
  - 商业方案：AutoCAD Forge/ODA SDK（精度高）。
  - 开源链路：先 `DWG -> DXF` 再 `DXF -> PDF`（成本低，但复杂图纸可能有偏差）。
- 存储：本地磁盘/MinIO/S3。
- 队列：Redis + RQ/Celery（异步任务）。

## 3. 网页版系统架构
1. 前端上传 DWG（单文件或 ZIP）。
2. 后端创建任务并返回 `task_id`。
3. Worker 消费任务，调用转换引擎生成 PDF。
4. 回写任务状态（排队中/处理中/完成/失败）。
5. 前端轮询或 WebSocket 订阅进度并下载结果。

## 4. 核心接口设计（REST）
- `POST /api/v1/convert`
  - 入参：文件、paper_size、orientation、scale、line_style
  - 出参：`task_id`
- `GET /api/v1/tasks/{task_id}`
  - 出参：状态、进度、错误信息、下载地址
- `GET /api/v1/download/{task_id}`
  - 出参：PDF 文件流

## 5. 数据表（最小可用）
`convert_tasks`
- `id` (uuid)
- `filename`
- `status` (`queued|running|success|failed`)
- `progress` (0-100)
- `error_message`
- `input_path`
- `output_path`
- `created_at`
- `updated_at`

## 6. 后端伪代码
```python
# FastAPI 示例（伪代码）
@app.post('/api/v1/convert')
async def convert(file: UploadFile, options: ConvertOptions):
    task_id = create_task_record(file.filename, options)
    save_upload(file, task_id)
    enqueue_convert_job(task_id)
    return {"task_id": task_id}

@worker.task
def run_convert(task_id):
    update_status(task_id, 'running', 10)
    # 示例链路：dwg -> dxf -> pdf
    dxf_file = run_cmd(['oda_converter', input_dwg, output_dir])
    pdf_file = run_cmd(['dxf2pdf', dxf_file, output_pdf])
    update_status(task_id, 'success', 100, output_path=pdf_file)
```

## 7. 前端页面设计
- 上传区：拖拽上传、文件列表。
- 参数区：纸张、方向、比例、线宽、黑白/彩色。
- 任务区：状态徽标、进度条、失败重试。
- 结果区：预览按钮、下载按钮。

## 8. 关键非功能要求
- 安全：
  - 限制上传大小（如 50MB/文件）
  - 文件类型白名单校验（magic number + 扩展名）
  - 临时文件定时清理（如 24 小时）
- 性能：
  - 多 worker 并发
  - 批量任务限流
- 可观测：
  - 日志（task_id 串联）
  - 失败重试与告警

## 9. MVP 里程碑（2 周）
- 第 1-2 天：接口与任务模型
- 第 3-5 天：集成转换引擎 + 本地跑通
- 第 6-8 天：前端上传、进度、下载
- 第 9-10 天：批量、失败重试、清理策略
- 第 11-14 天：压测、部署、文档

## 10. 给你的落地建议
- 若你更重视“效果稳定、商业可用”，优先选 **商业转换 SDK**。
- 若你重视“低成本试错”，先做 **开源链路 MVP**，跑出真实样本再升级。

---

如果你愿意，我下一步可以直接给你：
1) 可运行的 `FastAPI + Vue` 项目骨架；
2) 上传/轮询/下载完整代码；
3) Docker 一键部署文件。
