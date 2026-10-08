@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

:: 1. Close any stuck old server processes from earlier
taskkill /F /IM python.exe >nul 2>&1

:: 2. Check Python environment and packages
if not exist "%~dp0venv\Scripts\python.exe" (
    echo [1/3] Setting up Python environment...
    python -m venv venv >nul 2>&1 || py -m venv venv >nul 2>&1
)

if not exist "%~dp0venv\Lib\site-packages\uvicorn" (
    echo [2/3] Installing backend requirements...
    call "%~dp0venv\Scripts\pip.exe" install fastapi uvicorn python-docx pydantic plotly python-multipart
)

:: 3. Check if Vite is installed; if missing, install automatically
if not exist "%~dp0node_modules\vite" (
    echo [3/3] Installing interface packages (takes about 30 seconds)...
    call npm install
)

:: 4. Start Servers
set ENABLE_AI=false

echo Starting Backend Server on Port 8000...
start "" "%~dp0venv\Scripts\python.exe" app.py

echo Starting Interface on Port 5173...
start "" cmd /c "npm run dev -- --host"

:: 5. Open Browser
timeout /t 5 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo ===================================================
echo  THEDRAL IS LIVE!
echo  Keep this window open while writing.
echo ===================================================
pause
