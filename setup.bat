@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo  LINE 行政小秘書 Docker 一鍵安裝 (Windows)
echo ============================================================
echo.

:: ── 1. 檢查 Docker Desktop ─────────────────────────────────────
echo [1/3] 檢查 Docker Desktop...

where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo [未安裝] 偵測不到 Docker，正在開啟 Docker Desktop 下載頁面...
    echo 請下載並安裝 Docker Desktop，完成後重新執行本程式。
    echo.
    powershell -Command "Start-Process 'https://www.docker.com/products/docker-desktop'"
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo [未啟動] Docker Desktop 已安裝但尚未啟動。
    echo 請先開啟 Docker Desktop，等待它完全啟動後再重新執行本程式。
    echo.
    :: 嘗試自動啟動 Docker Desktop
    set DOCKER_APP="%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    if exist !DOCKER_APP! (
        echo 正在自動啟動 Docker Desktop，請稍候...
        start "" !DOCKER_APP!
        echo.
        echo 請等待 Docker Desktop 完全就緒（系統匣出現鯨魚圖示）後，
        echo 再重新執行本程式。
    )
    pause
    exit /b 1
)
echo [OK] Docker Desktop 已啟動

:: ── 2. 檢查 WSL2 ───────────────────────────────────────────────
echo [2/3] 檢查 WSL2...

wsl --status >nul 2>&1
if errorlevel 1 (
    echo.
    echo [未安裝] 偵測不到 WSL2。
    echo.
    set /p INSTALL_WSL="是否立即以系統管理員身份安裝 WSL2？(Y/n): "
    set INSTALL_WSL=!INSTALL_WSL!
    if "!INSTALL_WSL!"=="" set INSTALL_WSL=Y
    if /i "!INSTALL_WSL!"=="Y" (
        echo.
        echo 正在以系統管理員身份執行 wsl --install，完成後需重新開機...
        powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -Command wsl --install' -Verb RunAs -Wait"
        echo.
        echo WSL2 安裝完成，請重新開機後再次執行本程式。
        pause
        exit /b 0
    ) else (
        echo.
        echo 請以系統管理員身份開啟 PowerShell 並手動執行：
        echo   wsl --install
        echo 完成後重新開機，再重新執行本程式。
        pause
        exit /b 1
    )
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
