@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

:: Check if a working python.exe actually exists inside venv
if exist "%~dp0venv\Scripts\python.exe" goto HAS_VENV

echo [1/3] Setting up Python environment...
:: Remove broken/empty venv folder if it exists
if exist venv rmdir /s /q venv >nul 2>&1

:: Create fresh venv (tries python, falls back to py launcher)
python -m venv venv >nul 2>&1
if not exist "%~dp0venv\Scripts\python.exe" (
    py -m venv venv >nul 2>&1
)

if not exist "%~dp0venv\Scripts\python.exe" (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [2/3] Installing Python requirements...
call "%~dp0venv\Scripts\pip.exe" install -r requirements.txt

:HAS_VENV

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

timeout /t 4 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo ===================================================
echo  THEDRAL IS LIVE!
echo  Keep this window open while writing.
echo ===================================================
pause
