@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo =================================================================
echo    LAUNCHING THEDRAL SOVEREIGN STUDIO (WINDOWS 10)
echo =================================================================

:: 1. Self-Installing Virtual Environment
if not exist "venv" (
    echo [1/3] First-time setup: Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/3] Installing Python requirements (FastAPI, docx, uvicorn)...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

set PYTHON_CMD=venv\Scripts\python.exe

:: 2. Self-Installing Node Modules
if not exist "node_modules" (
    echo [3/3] First-time setup: Installing interface packages...
    call npm install
)

:: 3. Start Backend in Background
set ENABLE_AI=false
echo Starting Thedral Backend (Port 8000)...
start /B "" %PYTHON_CMD% app.py

:: 4. Start Frontend in Background
echo Starting Studio Interface (Port 5173)...
start /B "" cmd /c "npm run dev -- --host"

:: 5. Wait 4 seconds and open in default browser
timeout /t 4 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo.
echo =================================================================
echo  THEDRAL IS LIVE!
echo  Desktop: http://localhost:5173
echo  Close this window to stop the studio.
echo =================================================================
pause
