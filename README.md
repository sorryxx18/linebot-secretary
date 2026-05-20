# LINE 行政小秘書

本專案是「二大隊行政小秘書」的 Docker 一鍵安裝驗證版，目標是讓現行本地 LINE Bot 的使用效果可以被穩定重建、啟動與維護。待二大隊版本運行穩定後，再整理為其他單位推廣版。

預設效果包含：

- LINE Messaging API webhook reply-only 回覆
- Codex-first 深度回答模式
- Gemini RAG fallback
- Google Drive 知識庫同步與來源引用
- 正式公務報告格式
- Flex 卡片摘要
- 敏感資料保守處理
- `/同步`、`/重建索引`、`/文件清單`、`/狀態` 等管理指令

> 注意：本專案不使用 LINE push message。所有 LINE 回覆均透過 webhook reply token 完成。

---

## 一鍵安裝

### macOS / Linux

```bash
git clone https://github.com/sorryxx18/linebot-secretary.git
cd linebot-secretary
./install.sh
```

### Windows

> **前置需求**：Docker Desktop + WSL2（見下方說明）

1. 以系統管理員身份開啟 PowerShell，啟用 WSL2：
   ```powershell
   wsl --install
   ```
   完成後重新開機。

2. 開啟 Docker Desktop → Settings → Resources → WSL Integration，啟用 WSL2 backend。

3. 下載或 `git clone` 本專案到任意資料夾。

4. 在專案資料夾中，**雙擊 `setup.bat`** 即可一鍵安裝。
   - 程式會自動檢查 Docker Desktop 與 WSL2 是否就緒
   - 確認後自動在 WSL2 中執行 `install.sh`
   - 請依畫面提示輸入 LINE / Google / OpenAI 等憑證

安裝程式會引導您填入必要資料、產生 `.env`、複製 Google Service Account JSON、建立資料夾，並使用 Docker Compose 啟動服務。

---

## 安裝前請先準備

### 必要工具

1. Git
2. Docker Desktop
3. Node.js / npm
4. Codex CLI

Codex CLI 安裝方式：

```bash
npm install -g @openai/codex
codex --version
```

本版本先將 Codex CLI 列為必要工具，主要用於二大隊運行驗證、維護與除錯。之後對外推廣版可再降級為開發者選用。

### 必要資料

安裝精靈會請您填入：

1. 單位完整名稱，預設：`第二救災救護大隊`
2. 單位簡稱，預設：`二大隊`
3. Bot 名稱，預設：`二大隊行政小秘書`
4. LINE Channel Secret
5. LINE Channel Access Token
6. OpenAI API Key，供 Codex-first 回答使用；也可使用主機 `codex login` OAuth
7. Gemini API Key，供 fallback RAG 回答使用
8. Google Service Account JSON 檔案路徑
9. Google Drive 知識庫資料夾 ID 或資料夾網址
10. 公開 HTTPS 網址，可先留空，稍後再設定 Cloudflare Tunnel 或正式網域

---

## 常用指令

**macOS / Linux（WSL2 終端機）：**

```bash
./start.sh    # 建置並啟動 Docker 服務
./stop.sh     # 停止服務
./status.sh   # 查看容器與健康檢查
```

**Windows（在 WSL2 終端機執行，或直接用 Docker Desktop 介面）：**

```powershell
# 啟動
wsl bash -c "cd /path/to/linebot-secretary && ./start.sh"

# 或直接用 docker compose（在 CMD / PowerShell 均可）
docker compose up -d --build
docker compose down
docker compose logs -f
```

查看 log：

```bash
docker compose logs -f
```

---

## LINE Developers 設定

服務預設監聽本機：

```text
http://localhost:3002
```

Webhook path 固定為：

```text
/webhook
```

若您的公開網址是：

```text
https://linebot.example.com
```

請在 LINE Developers 後台填入：

```text
https://linebot.example.com/webhook
```

建議設定：

- Use webhook：Enabled
- Auto-reply messages：Disabled
- Greeting messages：Optional

---

## Google Drive 權限提醒

安裝精靈會讀取 Service Account JSON 裡的 `client_email` 並提醒您將 Drive 知識庫資料夾分享給該帳號。

請確認：

1. Google Drive 知識庫資料夾已分享給 service account email
2. 權限至少為 Viewer
3. `.env` 的 `DRIVE_FOLDER_ID` 為正確資料夾 ID
4. LINE 傳送 `/同步` 後，資料會下載到 `data/raw/` 並重建索引

---

## 安全注意事項

請勿提交下列資料到 GitHub：

- `.env`
- `.env.backup.*`
- `credentials/`
- `service-account.json`
- LINE Channel Secret
- LINE Channel Access Token
- OpenAI / Gemini API Key
- 真實議員備詢資料
- 實際問答紀錄
- `data/raw/`、`data/extracted/`、`data/index.sqlite3`
- `logs/`

本 repo 僅保留 `.env.example` 與程式碼；實際機密資料由 `./install.sh` 在本機產生。

---

## Docker 結構

主要檔案：

```text
Dockerfile
docker-compose.yml
install.sh
start.sh
stop.sh
status.sh
.env.example
main.py
rag.py
drive_sync.py
```

Docker Compose 會掛載：

```text
./credentials -> /app/credentials:ro
./data        -> /app/data
./logs        -> /app/logs
~/.codex      -> /root/.codex:ro
```

若 `.env` 已填 `OPENAI_API_KEY`，Codex 可直接使用 API key；若留空，容器會嘗試使用主機掛載的 `~/.codex` OAuth 狀態。

---

## LINE 指令

在 LINE 對 Bot 傳送：

```text
/狀態
```

查看資料庫狀態。

```text
/同步
```

從 Google Drive 下載最新文件並重建索引。

```text
/重建索引
```

重新掃描 `data/raw/` 建立索引。

```text
/文件清單
```

查看已索引文件。

---

## 目前版本定位

目前版本先以「二大隊行政小秘書」運行穩定為優先，因此：

- 採 Docker-only 安裝
- 採 Codex-first 回答模式
- 預設二大隊正式公務回覆格式
- 其他單位可透過安裝精靈替換單位名稱、LINE 憑證與 Drive 知識庫

後續推廣版可再移除 Codex 必要性、增加更多安裝模式與更完整的客製化設定。
