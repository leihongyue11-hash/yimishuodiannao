# 固定域名部署（Nginx + HTTPS）

> 目标：把临时 `localhost.run` 地址升级为固定域名，例如 `https://dwg.yourdomain.com`。

## 1) 前置条件
- 你有一台公网 Linux 服务器（Ubuntu/Debian）
- 你有域名（如 `yourdomain.com`）
- DNS 已添加：`dwg.yourdomain.com -> 服务器公网 IP`

## 2) 服务器安装依赖
```bash
sudo apt update
sudo apt install -y python3 python3-venv nginx certbot python3-certbot-nginx
```

## 3) 启动应用（systemd）
```bash
cd /opt
sudo mkdir -p dwg-webapp
sudo chown -R $USER:$USER dwg-webapp
# 将当前仓库 webapp/ 内容上传到 /opt/dwg-webapp

cd /opt/dwg-webapp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 真实转换命令（请按你的环境修改）
export DWG_CONVERTER_CMD='my_dwg_tool --in "{input}" --out "{output}"'

# 验证本地启动
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

创建 systemd 文件：
```bash
sudo tee /etc/systemd/system/dwg-webapp.service >/dev/null <<'SERVICE'
[Unit]
Description=DWG WebApp FastAPI
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/dwg-webapp
Environment="DWG_CONVERTER_CMD=my_dwg_tool --in {input} --out {output}"
ExecStart=/opt/dwg-webapp/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

sudo chown -R www-data:www-data /opt/dwg-webapp
sudo systemctl daemon-reload
sudo systemctl enable --now dwg-webapp
sudo systemctl status dwg-webapp
```

## 4) Nginx 反向代理
```bash
sudo tee /etc/nginx/sites-available/dwg-webapp >/dev/null <<'NGINX'
server {
    listen 80;
    server_name dwg.yourdomain.com;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/dwg-webapp /etc/nginx/sites-enabled/dwg-webapp
sudo nginx -t
sudo systemctl reload nginx
```

## 5) 申请 HTTPS 证书
```bash
sudo certbot --nginx -d dwg.yourdomain.com --redirect -m you@example.com --agree-tos -n
```

完成后，你的固定地址就是：
- `https://dwg.yourdomain.com`
