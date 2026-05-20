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

echo "Docker Compose 狀態："
"${COMPOSE[@]}" ps

echo
echo "健康檢查："
if curl -fsS http://localhost:3002/health; then
  echo
  echo "[OK] 服務正常。"
else
  echo
  echo "[提醒] 服務尚未正常回應。請查看：${COMPOSE[*]} logs -f"
  exit 1
fi
