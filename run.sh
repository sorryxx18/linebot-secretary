#!/bin/zsh
set -euo pipefail
cd /Users/leifhuang/sec2-linebot
exec /Users/leifhuang/sec2-linebot/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 3002
