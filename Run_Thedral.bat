@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

REM 1. Create virtual environment if missing
if not exist "venv" (
    echo [1/3] Creating Python environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/3] Installing Python requirements...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM 2. Install interface packages if missing
if not exist "node_modules" (
    echo [3/3] Installing interface packages...
    call npm install
)

REM 3. Start Backend & Frontend
set ENABLE_AI=false
echo Starting Backend...
start "" venv\Scripts\python.exe app.py

echo Starting Frontend...
start "" cmd /c "npm run dev -- --host"

REM 4. Open Browser
timeout /t 4 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo ===================================================
echo  THEDRAL IS LIVE! 
echo  Keep this window open while writing.
echo ===================================================
pause
