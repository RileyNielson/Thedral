@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo =================================================================
echo    LAUNCHING THEDRAL SOVEREIGN STUDIO (WINDOWS 10)
echo =================================================================

:: 1. Activate Python Virtual Environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    set PYTHON_CMD=venv\Scripts\python.exe
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set PYTHON_CMD=.venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

:: 2. Start FastAPI Backend in Background
echo Starting Thedral Backend (Port 8000)...
start /B "" %PYTHON_CMD% app.py

:: 3. Start Vite Frontend in Background
echo Starting Studio Interface (Port 5173)...
start /B "" cmd /c "npm run dev -- --host"

:: 4. Wait 3 seconds and open default browser
timeout /t 3 /nobreak >nul
echo Opening studio in browser...
start http://localhost:5173

echo.
echo =================================================================
echo  THEDRAL IS LIVE!
echo  Desktop: http://localhost:5173
echo  Close this window to stop the studio.
echo =================================================================
pause