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
echo [1/3] Setting up Python environment...
python -m venv venv >nul 2>&1
if not exist venv\Scripts\python.exe py -m venv venv >nul 2>&1

:CHECK_BACKEND_PACKAGES
if exist venv\Lib\site-packages\uvicorn goto CHECK_VITE
echo [2/3] Installing backend requirements...
call venv\Scripts\pip.exe install fastapi uvicorn python-docx pydantic plotly python-multipart

:CHECK_VITE
if exist node_modules\vite goto LAUNCH_STUDIO
echo [3/3] Installing interface packages, please wait...
call npm install

:LAUNCH_STUDIO
set ENABLE_AI=false

echo Starting Backend Server on Port 8000...
start "" venv\Scripts\python.exe app.py

echo Starting Interface on Port 5173...
start "" cmd /c "npm run dev -- --host"

timeout /t 5 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo ===================================================
echo   THEDRAL IS LIVE!
echo   Keep this window open while writing.
echo ===================================================
pause
