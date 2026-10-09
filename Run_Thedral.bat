@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

REM 1. Stop any background python processes
taskkill /F /IM python.exe >nul 2>&1

REM 2. Check Python Environment
if exist venv\Scripts\python.exe goto CHECK_BACKEND_PACKAGES
echo [1/2] Setting up Python environment...
python -m venv venv >nul 2>&1
if not exist venv\Scripts\python.exe py -m venv venv >nul 2>&1

:CHECK_BACKEND_PACKAGES
if exist venv\Lib\site-packages\uvicorn goto LAUNCH_STUDIO
echo [2/2] Installing backend requirements...
call venv\Scripts\pip.exe install fastapi uvicorn python-docx pydantic plotly python-multipart

:LAUNCH_STUDIO
set ENABLE_AI=false

echo Starting Thedral Core on Port 8000...
start "" venv\Scripts\python.exe app.py

timeout /t 3 /nobreak >nul
echo Opening studio in browser...
start http://localhost:8000

echo ===================================================
echo   THEDRAL IS LIVE!
echo   Keep this window open while writing.
echo ===================================================
pause