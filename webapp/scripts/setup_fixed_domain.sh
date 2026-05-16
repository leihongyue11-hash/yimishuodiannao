#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "用法: $0 <domain> <email>"
  echo "示例: $0 dwg.example.com admin@example.com"
  exit 1
fi

DOMAIN="$1"
EMAIL="$2"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_PATH="/etc/systemd/system/dwg-webapp.service"
NGINX_SITE="/etc/nginx/sites-available/dwg-webapp"

if [[ -z "${DWG_CONVERTER_CMD:-}" ]]; then
  echo "[ERROR] 请先设置 DWG_CONVERTER_CMD"
  exit 1
fi

echo "[1/6] 安装依赖..."
sudo apt update
sudo apt install -y python3 python3-venv nginx certbot python3-certbot-nginx

echo "[2/6] 准备 Python 环境..."
cd "$APP_DIR"
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

echo "[3/6] 写入 systemd 服务..."
sudo tee "$SERVICE_PATH" >/dev/null <<SERVICE
[Unit]
Description=DWG WebApp FastAPI
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=DWG_CONVERTER_CMD=$DWG_CONVERTER_CMD
ExecStart=$APP_DIR/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

sudo chown -R www-data:www-data "$APP_DIR"
sudo systemctl daemon-reload
sudo systemctl enable --now dwg-webapp

echo "[4/6] 写入 Nginx 配置..."
sudo tee "$NGINX_SITE" >/dev/null <<NGINX
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

sudo ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/dwg-webapp
sudo nginx -t
sudo systemctl reload nginx

echo "[5/6] 申请 HTTPS 证书..."
sudo certbot --nginx -d "$DOMAIN" --redirect -m "$EMAIL" --agree-tos -n

echo "[6/6] 完成"
echo "固定访问地址: https://$DOMAIN"
