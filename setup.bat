@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo  LINE 行政小秘書 Docker 一鍵安裝 (Windows)
echo ============================================================
echo.

:: ── 1. 檢查 Docker Desktop ─────────────────────────────────────
echo [1/3] 檢查 Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo [錯誤] Docker Desktop 未啟動或未安裝。
    echo 請先安裝並啟動 Docker Desktop，再重新執行本程式：
    echo   https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)
echo [OK] Docker Desktop 可用

:: ── 2. 檢查 WSL2 ───────────────────────────────────────────────
echo [2/3] 檢查 WSL2...
wsl --status >nul 2>&1
if errorlevel 1 (
    echo.
    echo [錯誤] 未偵測到 WSL2。
    echo 請以系統管理員身份開啟 PowerShell 並執行：
    echo   wsl --install
    echo 完成後重新開機，再重新執行本程式。
    echo.
    pause
    exit /b 1
)
echo [OK] WSL2 可用

:: ── 3. 轉換路徑並在 WSL2 執行 install.sh ──────────────────────
echo [3/3] 啟動安裝精靈...
echo.

for /f "delims=" %%i in ('wsl wslpath -u "%CD%"') do set WSL_DIR=%%i

echo 正在 WSL2 中執行 install.sh，請依提示輸入資料。
echo.

wsl bash -c "cd '!WSL_DIR!' && bash install.sh"

if errorlevel 1 (
    echo.
    echo [錯誤] 安裝過程中發生問題，請查看上方訊息。
    echo 如需協助，請回報錯誤訊息。
) else (
    echo.
    echo [完成] 安裝程式執行完畢。
    echo 請依畫面指示完成 LINE Developers Webhook 設定。
)

echo.
pause
