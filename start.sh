#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "[錯誤] 未偵測到 Docker Compose。請安裝 Docker Desktop 或 docker-compose。" >&2
  exit 1
fi

"${COMPOSE[@]}" up -d --build

echo "LINE 行政小秘書已啟動。"
echo "健康檢查：http://localhost:3002/health"
echo "查看狀態：./status.sh"
