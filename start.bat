@echo off
chcp 65001 >nul
echo ============================================================
echo  行政小秘書 LINE Bot 啟動中...
echo ============================================================

:: 啟動 Cloudflare Tunnel（背景）
start "Cloudflare Tunnel" /min cloudflared.exe tunnel --url http://localhost:3002

:: 等候 Tunnel 建立
timeout /t 3 /nobreak >nul

:: 啟動 LINE Bot 服務
echo [啟動] LINE Bot 服務 port 3002
.venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 3002

pause
