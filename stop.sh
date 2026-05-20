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

"${COMPOSE[@]}" down

echo "LINE 行政小秘書已停止。"
