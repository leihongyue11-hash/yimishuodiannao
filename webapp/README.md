# DWG 转 PDF 网页

## 启动
```bash
cd webapp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DWG_CONVERTER_CMD='ODAFileConverter "{input_dir}" "{output_dir}" ACAD2018 PDF 0 1'
uvicorn app:app --host 0.0.0.0 --port 8000
```

打开 `http://<你的IP>:8000`，其他用户即可访问。

## 输入与输出
- 上传 `.dwg`：输出单个 `.pdf`
- 上传 `.zip`（内含多个 `.dwg`）：输出打包后的 `*_pdfs.zip`

## DWG_CONVERTER_CMD 模板变量
可用模板变量：
- `{input}` / `{input_dir}` / `{input_name}` / `{input_stem}`
- `{output}` / `{output_dir}` / `{output_name}` / `{output_stem}`

示例（单文件工具）：
```bash
export DWG_CONVERTER_CMD='my_dwg_tool --in "{input}" --out "{output}"'
```

示例（ODA 批处理思路，按目录生成）：
```bash
export DWG_CONVERTER_CMD='ODAFileConverter "{input_dir}" "{output_dir}" ACAD2018 PDF 0 1'
```

## API
- `POST /api/v1/convert`：上传 `.dwg` 或 `.zip` 创建任务
- `GET /api/v1/tasks/{task_id}`：查看状态/进度/错误
- `GET /api/v1/download/{task_id}`：下载结果


## 一键生成可分享地址（公网临时地址）
在服务器上执行：
```bash
cd webapp
bash scripts/start_public.sh
```
运行后终端会显示一个 `https://xxxx.localhost.run` 地址，把这个地址发给其他用户即可访问。

> 说明：这是临时公网通道，终端关闭后地址失效。生产环境建议使用 Nginx + 域名 + HTTPS。


## 升级为固定域名（推荐）
1. 先确保 DNS 已把你的域名（如 `dwg.example.com`）解析到服务器公网 IP。  
2. 设置真实转换命令：
```bash
export DWG_CONVERTER_CMD='my_dwg_tool --in "{input}" --out "{output}"'
```
3. 一键部署固定域名：
```bash
cd webapp
bash scripts/setup_fixed_domain.sh dwg.example.com admin@example.com
```
成功后会输出固定地址：
- `https://dwg.example.com`
