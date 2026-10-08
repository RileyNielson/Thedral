@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

:: Check if backend packages are already installed
if exist "%~dp0venv\Lib\site-packages\uvicorn" goto HAS_PACKAGES

echo [1/3] Setting up Python environment...
if not exist "%~dp0venv\Scripts\python.exe" (
    python -m venv venv >nul 2>&1
    if not exist "%~dp0venv\Scripts\python.exe" (
        py -m venv venv >nul 2>&1
    )
)

echo [2/3] Installing Python requirements...
if exist "%~dp0requirements.txt" (
    call "%~dp0venv\Scripts\pip.exe" install -r "%~dp0requirements.txt"
) else (
    call "%~dp0venv\Scripts\pip.exe" install fastapi uvicorn python-docx pydantic plotly
)

:HAS_PACKAGES

:: Check interface packages
if exist "%~dp0node_modules" goto START_SERVERS
echo [3/3] Installing interface packages...
call npm install

:START_SERVERS
set ENABLE_AI=false

echo Starting Backend Server on Port 8000...
start "" "%~dp0venv\Scripts\python.exe" app.py

echo Starting Interface on Port 5173...
start "" cmd /c "npm run dev -- --host"

timeout /t 5 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo ===================================================
echo  THEDRAL IS LIVE!
echo  Keep this window open while writing.
echo ===================================================
pause
