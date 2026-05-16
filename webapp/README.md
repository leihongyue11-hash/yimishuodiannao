# DWG 转 PDF 网页

## 启动
```bash
cd webapp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

打开 `http://<你的IP>:8000`，其他用户即可访问。

## 真实转换配置（可选）
默认会生成占位 PDF，确认链路可用。若要真实转换，请设置环境变量：

```bash
export DWG_CONVERTER_CMD='oda_converter "{input}" "{output}"'
```

程序会把 `{input}` 和 `{output}` 替换为实际文件路径并执行命令。
