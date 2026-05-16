#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

if [[ -z "${DWG_CONVERTER_CMD:-}" ]]; then
  echo "[WARN] DWG_CONVERTER_CMD 未设置，转换任务会失败。"
fi

cd "$(dirname "$0")/.."

python -m uvicorn app:app --host "$HOST" --port "$PORT" > /tmp/dwg_webapp.log 2>&1 &
APP_PID=$!

cleanup() {
  kill "$APP_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1
if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
  echo "[ERROR] uvicorn 启动失败，请检查 /tmp/dwg_webapp.log"
  exit 1
fi

echo "[INFO] 本地服务已启动：http://127.0.0.1:${PORT}"
echo "[INFO] 正在创建公网地址（localhost.run）..."
echo "[INFO] 按 Ctrl+C 可关闭服务和公网通道。"

ssh -o StrictHostKeyChecking=no -R 80:localhost:${PORT} nokey@localhost.run
