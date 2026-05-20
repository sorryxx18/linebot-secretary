#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
NC="\033[0m"

say() { printf "%b\n" "$*"; }
fail() { say "${RED}[錯誤]${NC} $*"; exit 1; }
ok() { say "${GREEN}[OK]${NC} $*"; }
warn() { say "${YELLOW}[提醒]${NC} $*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "缺少必要工具：$1"
}

prompt_default() {
  local var_name="$1" label="$2" default_value="$3" value
  read -r -p "$label [$default_value]: " value
  printf -v "$var_name" '%s' "${value:-$default_value}"
}

prompt_required() {
  local var_name="$1" label="$2" value=""
  while [[ -z "$value" ]]; do
    read -r -p "$label: " value
    [[ -z "$value" ]] && warn "此欄位必填。"
  done
  printf -v "$var_name" '%s' "$value"
}

prompt_secret_required() {
  local var_name="$1" label="$2" value=""
  while [[ -z "$value" ]]; do
    read -r -s -p "$label: " value
    printf "\n"
    [[ -z "$value" ]] && warn "此欄位必填。"
  done
  printf -v "$var_name" '%s' "$value"
}

extract_drive_id() {
  local input="$1"
  if [[ "$input" =~ /folders/([A-Za-z0-9_-]+) ]]; then
    printf "%s" "${BASH_REMATCH[1]}"
  else
    printf "%s" "$input"
  fi
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    fail "未偵測到 Docker Compose。請安裝 Docker Desktop 或 docker-compose。"
  fi
}

say "${BOLD}============================================================${NC}"
say "${BOLD} LINE 行政小秘書 Docker 一鍵安裝程式${NC}"
say "${BOLD} 目前版本：二大隊行政小秘書運行驗證版${NC}"
say "${BOLD}============================================================${NC}"
say ""
say "本程式會協助您："
say "1. 檢查 Docker / Codex 必要工具"
say "2. 建立 .env 與必要資料夾"
say "3. 複製 Google Service Account JSON"
say "4. 使用 Docker Compose 啟動服務"
say "5. 顯示 LINE Developers Webhook 設定指引"
say ""

need_cmd git
need_cmd python3
need_cmd curl
need_cmd docker

if ! docker info >/dev/null 2>&1; then
  fail "Docker 尚未啟動。請先開啟 Docker Desktop 後重新執行 ./install.sh。"
fi
ok "Docker 可用"

if docker compose version >/dev/null 2>&1; then
  ok "Docker Compose plugin 可用"
elif command -v docker-compose >/dev/null 2>&1; then
  ok "docker-compose 可用"
else
  fail "未偵測到 Docker Compose。請安裝 Docker Desktop 或 docker-compose。"
fi

if ! command -v codex >/dev/null 2>&1; then
  warn "未偵測到 Codex CLI。"
  say "本版本先將 Codex CLI 列為必要工具，主要用於二大隊運行驗證、維護與除錯。"
  if command -v npm >/dev/null 2>&1; then
    read -r -p "是否現在自動安裝 Codex CLI？(Y/n): " install_codex
    install_codex="${install_codex:-Y}"
    if [[ "$install_codex" =~ ^[Yy]$ ]]; then
      npm install -g @openai/codex
    else
      fail "請先安裝 Codex CLI：npm install -g @openai/codex"
    fi
  else
    fail "缺少 npm，無法自動安裝 Codex。請先安裝 Node.js 後執行：npm install -g @openai/codex"
  fi
fi
ok "Codex CLI：$(codex --version 2>/dev/null || echo installed)"

say ""
say "${BOLD}請依序填入必要資料。直接按 Enter 會使用預設值。${NC}"
say ""

prompt_default UNIT_NAME "單位完整名稱" "第二救災救護大隊"
prompt_default UNIT_SHORT_NAME "單位簡稱" "二大隊"
prompt_default BOT_DISPLAY_NAME "Bot 名稱" "二大隊行政小秘書"

say ""
prompt_secret_required LINE_CHANNEL_SECRET "LINE Channel Secret"
prompt_secret_required LINE_CHANNEL_ACCESS_TOKEN "LINE Channel Access Token"

say ""
say "Codex-first 回答模式需要 OpenAI API Key，或主機已完成 codex login。"
read -r -s -p "OpenAI API Key（可留空，改用主機 ~/.codex OAuth）: " OPENAI_API_KEY
printf "\n"
if [[ -z "$OPENAI_API_KEY" && ! -d "$HOME/.codex" ]]; then
  warn "未填 OPENAI_API_KEY，且找不到 $HOME/.codex。Codex 回答可能失敗並 fallback 到 Gemini。"
fi

prompt_secret_required GOOGLE_API_KEY "Gemini API Key（Codex 失敗時 fallback 使用）"

say ""
SERVICE_ACCOUNT_SOURCE=""
while [[ -z "$SERVICE_ACCOUNT_SOURCE" || ! -f "$SERVICE_ACCOUNT_SOURCE" ]]; do
  read -r -p "Google Service Account JSON 檔案路徑: " SERVICE_ACCOUNT_SOURCE
  [[ ! -f "$SERVICE_ACCOUNT_SOURCE" ]] && warn "找不到檔案：$SERVICE_ACCOUNT_SOURCE"
done

SERVICE_ACCOUNT_EMAIL=$(python3 - "$SERVICE_ACCOUNT_SOURCE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        print(json.load(f).get('client_email', ''))
except Exception:
    print('')
PY
)
if [[ -n "$SERVICE_ACCOUNT_EMAIL" ]]; then
  warn "請確認 Google Drive 知識庫資料夾已分享給：$SERVICE_ACCOUNT_EMAIL"
fi

prompt_required DRIVE_FOLDER_INPUT "Google Drive 知識庫資料夾 ID 或資料夾網址"
DRIVE_FOLDER_ID="$(extract_drive_id "$DRIVE_FOLDER_INPUT")"

read -r -p "公開網址（例如 https://linebot.example.com，可先留空稍後設定）: " PUBLIC_BASE_URL
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-http://localhost:3002}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL%/}"
DRIVE_FOLDER_URL="https://drive.google.com/drive/folders/${DRIVE_FOLDER_ID}"

ADMIN_TOKEN=$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)

say ""
if [[ -f .env ]]; then
  BACKUP=".env.backup.$(date +%Y%m%d%H%M%S)"
  cp .env "$BACKUP"
  warn "已備份既有 .env → $BACKUP"
fi

mkdir -p credentials data/raw data/extracted logs
cp "$SERVICE_ACCOUNT_SOURCE" credentials/service-account.json
chmod 600 credentials/service-account.json 2>/dev/null || true

cat > .env <<EOF
UNIT_NAME=${UNIT_NAME}
UNIT_SHORT_NAME=${UNIT_SHORT_NAME}
BOT_DISPLAY_NAME=${BOT_DISPLAY_NAME}

LINE_CHANNEL_SECRET=${LINE_CHANNEL_SECRET}
LINE_CHANNEL_ACCESS_TOKEN=${LINE_CHANNEL_ACCESS_TOKEN}

OPENAI_API_KEY=${OPENAI_API_KEY}
CODEX_MODEL=gpt-5.4
CODEX_TIMEOUT=150

GOOGLE_API_KEY=${GOOGLE_API_KEY}
GEMINI_MODEL=gemini-2.5-flash

GOOGLE_SA_KEY=/app/credentials/service-account.json
DRIVE_FOLDER_ID=${DRIVE_FOLDER_ID}
DRIVE_MANIFEST_PATH=/app/data/drive_manifest.json

PUBLIC_BASE_URL=${PUBLIC_BASE_URL}
DRIVE_FOLDER_URL=${DRIVE_FOLDER_URL}
DATA_DIR=/app/data

ADMIN_TOKEN=${ADMIN_TOKEN}
EOF
chmod 600 .env 2>/dev/null || true
ok "已產生 .env、credentials/、data/、logs/"

cat > INSTALL_SUMMARY.txt <<EOF
LINE 行政小秘書安裝摘要
========================
單位：${UNIT_NAME}
單位簡稱：${UNIT_SHORT_NAME}
Bot：${BOT_DISPLAY_NAME}
本機服務：http://localhost:3002
Webhook path：/webhook
目前公開網址：${PUBLIC_BASE_URL}
LINE Webhook URL：${PUBLIC_BASE_URL}/webhook
Drive Folder ID：${DRIVE_FOLDER_ID}
Service Account Email：${SERVICE_ACCOUNT_EMAIL:-未讀取到}

常用指令：
- 啟動：./start.sh
- 停止：./stop.sh
- 狀態：./status.sh
- 查看 log：docker compose logs -f

注意：本摘要不包含 LINE / Google / OpenAI token。
EOF

say ""
read -r -p "是否立即建置並啟動 Docker 服務？(Y/n): " START_NOW
START_NOW="${START_NOW:-Y}"
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
  compose up -d --build
  say ""
  say "等待健康檢查..."
  for i in {1..30}; do
    if curl -fsS http://localhost:3002/health >/dev/null 2>&1; then
      ok "服務已啟動：http://localhost:3002/health"
      break
    fi
    sleep 2
    if [[ "$i" == "30" ]]; then
      warn "服務尚未通過健康檢查，請執行：docker compose logs -f"
    fi
  done
fi

say ""
say "${BOLD}安裝完成。${NC}"
say ""
say "下一步："
say "1. 若 PUBLIC_BASE_URL 仍是 http://localhost:3002，請先建立公開 HTTPS 網址（例如 Cloudflare Tunnel）。"
say "2. 到 LINE Developers 後台設定 Webhook URL："
say "   ${PUBLIC_BASE_URL}/webhook"
say "3. LINE Developers 建議設定："
say "   - Use webhook: Enabled"
say "   - Auto-reply messages: Disabled"
say "4. 在 LINE 傳送「/狀態」測試。"
say ""
say "常用指令：./start.sh、./stop.sh、./status.sh"
say "安裝摘要：INSTALL_SUMMARY.txt"
