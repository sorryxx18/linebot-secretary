# LINE 行政小秘書

**第二救災救護大隊行政小秘書** — 協助依據 Google Drive 知識庫回覆議會備詢問題的 LINE Bot。

功能包含：
- 議員備詢文件 RAG 查詢（Codex 深度回答 + Gemini 備援）
- Google Drive 知識庫自動同步
- 正式公務報告格式回覆
- Flex 卡片摘要
- 圖片文字辨識查詢
- 白名單密語機制（防未授權使用）
- 管理員 API

> 本專案**僅支援 Windows（Docker Desktop + WSL2）**。

---

## 安裝前準備

安裝前請先備妥以下帳號與資料，安裝精靈會逐項引導填入。

### 一、申請 LINE Bot

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)，登入後點 **Create a new provider**。
2. 建立 Provider 後，點 **Create a new channel** → 選 **Messaging API**。
3. 填入 Bot 名稱、類別，完成後進入 Channel 頁面。
4. 在 **Basic settings** 頁籤，複製 **Channel secret**。
5. 在 **Messaging API** 頁籤，點 **Issue** 產生 **Channel access token**，複製備用。
6. 同頁面，**Auto-reply messages** 設為 **Disabled**。

> Webhook URL 在安裝完成後再設定（需要公開 HTTPS 網址）。

---

### 二、建立 Google Service Account

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)，建立或選擇一個專案。
2. 左側選單 → **IAM 與管理** → **服務帳戶** → **建立服務帳戶**。
3. 填入名稱（如 `linebot-drive-reader`），點 **完成**，不需指派角色。
4. 點進建立好的服務帳戶 → **金鑰** 頁籤 → **新增金鑰** → **JSON**。
5. 下載的 `.json` 檔妥善保存，安裝時會要求輸入此檔案路徑。
6. 啟用 **Google Drive API**：左側 → **API 和服務** → **已啟用的 API 和服務** → **啟用 API** → 搜尋「Google Drive API」並啟用。

---

### 三、準備 Google Drive 知識庫資料夾

1. 在 Google Drive 建立一個資料夾，專門放議員備詢文件（.docx、.xlsx、.pdf 等）。
2. 在資料夾上按右鍵 → **共用** → 輸入服務帳戶的 email（格式如 `xxx@your-project.iam.gserviceaccount.com`）→ 權限設為 **檢視者**。
3. 複製資料夾的網址備用（格式如 `https://drive.google.com/drive/folders/xxxxxxxxxx`）。

---

### 四、取得 OpenAI API Key

1. 前往 [platform.openai.com](https://platform.openai.com/api-keys)，登入後點 **Create new secret key**。
2. 複製 API Key 備用（`sk-...`）。

> 若無 OpenAI API Key，也可在安裝時留空，改用 `codex login` OAuth 方式。

---

### 五、取得 Gemini API Key

1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)。
2. 點 **Create API key**，選擇 Google Cloud 專案後複製 Key。

---

### 六、設定公開 HTTPS 網址（Cloudflare Tunnel）

LINE Webhook 必須使用 HTTPS 網址。建議使用 **Cloudflare Tunnel** 免費建立，不需申請網域或開放防火牆入向 port。

1. 前往 [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)，登入後點 **Networks → Tunnels → Create a tunnel**。
2. 選 **Cloudflared**，輸入 Tunnel 名稱後下載 Windows 版 `cloudflared.exe`（或 Docker 版）。
3. 依指示執行 `cloudflared.exe service install <token>` 完成安裝。
4. 在 **Public Hostname** 設定：
   - Subdomain：自訂（如 `linebot-sec2`）
   - Domain：你的 Cloudflare 網域（或申請免費 `*.trycloudflare.com`）
   - Service：`http://localhost:3002`
5. 建立後取得公開網址，格式如 `https://linebot-sec2.example.com`，備用。

> 若暫時沒有網址，安裝時可先留空，稍後再到 LINE Developers 設定 Webhook URL。

---

## 安裝步驟（Windows）

### Step 1：安裝 Git for Windows

前往 [git-scm.com](https://git-scm.com/download/win) 下載安裝，全部保持預設值即可。

安裝完成後開啟 **命令提示字元（CMD）** 確認：
```cmd
git --version
```

---

### Step 2：安裝 Docker Desktop

1. 前往 [docker.com](https://www.docker.com/products/docker-desktop) 下載 Docker Desktop for Windows。
2. 安裝時勾選 **Use WSL 2 instead of Hyper-V**（預設已勾選）。
3. 安裝後重新開機，啟動 Docker Desktop，等待系統匣出現鯨魚圖示且狀態為 **Running**。

---

### Step 3：啟用 WSL2

開啟 **Docker Desktop** → Settings → Resources → **WSL Integration** → 確認 WSL2 已啟用。

若尚未安裝 WSL2，以**系統管理員**身份開啟 PowerShell 執行：
```powershell
wsl --install
```
完成後重新開機。

---

### Step 4：下載本專案

開啟 CMD，切換到要放置專案的資料夾後執行：
```cmd
git clone https://github.com/sorryxx18/linebot-secretary.git
cd linebot-secretary
```

---

### Step 5：執行 setup.bat

在專案資料夾中，**雙擊 `setup.bat`**（或在 CMD 輸入 `setup.bat`）。

安裝精靈會依序引導您填入：

| 項目 | 說明 |
|------|------|
| 單位完整名稱 | 預設：第二救災救護大隊 |
| 單位簡稱 | 預設：二大隊 |
| Bot 名稱 | 預設：二大隊行政小秘書 |
| LINE Channel Secret | 見「申請 LINE Bot」步驟 4 |
| LINE Channel Access Token | 見「申請 LINE Bot」步驟 5 |
| OpenAI API Key | 見「取得 OpenAI API Key」，可留空 |
| Gemini API Key | 見「取得 Gemini API Key」|
| Google Service Account JSON 路徑 | 下載的 .json 檔案完整路徑 |
| Google Drive 資料夾 ID 或網址 | 見「準備 Drive 知識庫資料夾」步驟 3 |
| 公開 HTTPS 網址 | 見「設定 Cloudflare Tunnel」步驟 5，可先留空 |

填寫完成後，安裝精靈會自動建置並啟動 Docker 服務。

---

### Step 6：設定 LINE Webhook URL

1. 回到 [LINE Developers Console](https://developers.line.biz/console/)，進入你的 Channel。
2. **Messaging API** 頁籤 → **Webhook URL** 填入：
   ```
   https://你的公開網址/webhook
   ```
3. 點 **Verify** 確認連線正常，再開啟 **Use webhook**。

---

### Step 7：上傳知識庫並啟用 Bot

1. 將議員備詢文件（.docx、.xlsx、.pdf 等）上傳到 Google Drive 知識庫資料夾。
2. 在 LINE 對 Bot 傳送：
   ```
   /同步
   ```
   Bot 會自動下載並建立索引。
3. 傳送啟用密語加入白名單：
   ```
   /tfdfire7236/
   ```
4. 直接輸入問題測試，例如：
   ```
   有什麼水源匱乏地區嗎
   ```

---

## 常用指令

在 CMD 或 PowerShell 執行：

```powershell
docker compose up -d --build   # 啟動（重建後啟動）
docker compose down            # 停止
docker compose logs -f         # 查看即時 log
```

---

## LINE 指令

### 啟用服務（首次必須）

```
/tfdfire7236/
```

加入白名單，啟用後方可使用所有功能。群組與個人均需各自啟用。

---

### 一般指令

| 指令 | 功能 |
|------|------|
| `/同步` | 從 Google Drive 下載最新文件並重建索引 |
| `/重建索引` | 重新掃描 data/raw/ 建立索引（不重新下載）|
| `/文件清單` | 查看已索引文件列表 |
| `/狀態` | 查看資料庫狀態與 Webhook 網址 |
| `/說明` | 顯示使用說明 |
| 直接輸入問題 | AI 查詢議員備詢資料庫 |
| 傳送圖片 | 自動辨識文字並查詢 |

---

## 使用者白名單

本服務採用密語啟用機制，防止未授權人員使用。

- 用戶傳送 `/tfdfire7236/` → 加入白名單，回覆啟用成功
- 未啟用者所有訊息均只收到提示，不觸發查詢

### 管理白名單（Admin API）

```bash
# 查看白名單（在 WSL2 或 CMD 執行）
curl -H "X-Admin-Token: <ADMIN_TOKEN>" http://localhost:3002/admin/allowlist

# 移除某用戶
curl -X DELETE -H "X-Admin-Token: <ADMIN_TOKEN>" http://localhost:3002/admin/allowlist/<user_id>
```

`ADMIN_TOKEN` 在安裝時自動產生，儲存於 `.env`。

---

## 防火牆設定

### 出向連線需求（全部為 HTTPS port 443）

| 目的地 | 用途 |
|--------|------|
| `api.line.me` | LINE Messaging API |
| `oauth2.googleapis.com` | Google 認證 |
| `www.googleapis.com` / `drive.googleapis.com` | Google Drive 同步 |
| `generativelanguage.googleapis.com` | Gemini API |
| `api.openai.com` | Codex 深度回答 |
| `hub.docker.com` / `registry-1.docker.io` | Docker image（安裝時）|
| `*.cloudflare.com` | Cloudflare Tunnel |

### 不需開放任何入向 port

使用 Cloudflare Tunnel 時，所有連線由主機主動對外建立，**防火牆不需新增任何入向規則**。

---

## 安全注意事項

請勿將下列資料提交到 GitHub 或傳送給他人：

- `.env`（含所有 API Key 和 Token）
- `credentials/`（Service Account JSON）
- `data/raw/`（議員備詢原始文件）

以上均已在 `.gitignore` 中排除，安裝時由本機產生，不會上傳。

### 資安設計說明

| 項目 | 說明 |
|------|------|
| LINE Webhook 簽名驗證 | 每筆請求驗證 X-Line-Signature，防偽造 |
| 白名單機制 | 未啟用密語的用戶不觸發任何查詢 |
| Admin 端點驗證 | 所有 `/admin/*` 必須附帶 X-Admin-Token |
| 檔案上傳限制 | 最大 50 MB，僅允許指定格式 |
| SQL Injection 防護 | 所有 SQLite 查詢使用參數化語句 |

---

## 問題排除

**Bot 沒有回應**
- 確認 Docker 容器正在執行：`docker compose ps`
- 確認 LINE Webhook URL 正確且 Verify 通過
- 查看 log：`docker compose logs -f`

**/同步 失敗**
- 確認 Drive 資料夾已分享給 Service Account email
- 確認 `.env` 的 `DRIVE_FOLDER_ID` 正確

**查詢結果說找不到資料**
- 確認文件已上傳至 Drive 並執行 `/同步`
- `/同步` 後再執行 `/文件清單` 確認索引是否成功

**容器啟動失敗**
- 確認 `.env` 所有必填項目都有填值
- 執行 `docker compose logs` 查看錯誤原因
