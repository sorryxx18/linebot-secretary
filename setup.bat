@echo off
chcp 65001 >nul
echo ============================================================
echo  行政小秘書 LINE Bot 安裝程式
echo ============================================================
echo.

:: 確認 Python 版本
python --version 2>nul || (
    echo [錯誤] 未找到 Python，請先安裝 Python 3.11 以上版本
    echo 下載：https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER%

:: 建立虛擬環境
if not exist ".venv" (
    echo [步驟 1/5] 建立虛擬環境...
    python -m venv .venv
)
echo [OK] 虛擬環境

:: 安裝套件
echo [步驟 2/5] 安裝套件（可能需要 2-3 分鐘）...
.venv\Scripts\pip install -r requirements.txt -q
echo [OK] 套件安裝完成

:: 建立 .env
if not exist ".env" (
    echo [步驟 3/5] 建立設定檔...
    copy .env.example .env
    echo.
    echo [重要] 請用記事本開啟 .env 填入以下資料：
    echo   - LINE_CHANNEL_SECRET
    echo   - LINE_CHANNEL_ACCESS_TOKEN
    echo   - GOOGLE_API_KEY
    echo   - GOOGLE_SA_KEY （Service Account JSON 路徑）
    echo   - DRIVE_FOLDER_ID
    echo   - PUBLIC_BASE_URL （Cloudflare Tunnel 設定後填入）
    notepad .env
) else (
    echo [OK] .env 已存在
)

:: 建立資料夾
echo [步驟 4/5] 建立資料夾...
if not exist "data\raw" mkdir data\raw
if not exist "data\extracted" mkdir data\extracted
if not exist "logs" mkdir logs
echo [OK] 資料夾

:: 下載 Cloudflare Tunnel
echo [步驟 5/5] 確認 Cloudflare Tunnel...
if not exist "cloudflared.exe" (
    echo 正在下載 cloudflared...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
    echo [OK] cloudflared.exe 下載完成
) else (
    echo [OK] cloudflared.exe 已存在
)

echo.
echo ============================================================
echo  安裝完成！
echo ============================================================
echo.
echo 下一步：
echo 1. 確認 .env 已填入所有資料
echo 2. 執行 start.bat 啟動服務
echo 3. 將 Cloudflare Tunnel 網址填入：
echo    a. .env 的 PUBLIC_BASE_URL
echo    b. LINE Developers Console 的 Webhook URL
echo.
pause
