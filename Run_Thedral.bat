@echo off
title Thedral Sovereign Studio
cd /d "%~dp0"

echo ===================================================
echo   LAUNCHING THEDRAL SOVEREIGN STUDIO
echo ===================================================

if exist venv goto HAS_VENV
echo Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Installing Python dependencies...
pip install -r requirements.txt
goto CHECK_NODE

:HAS_VENV
call venv\Scripts\activate.bat

:CHECK_NODE
if exist node_modules goto START_SERVERS
echo Installing interface dependencies...
call npm install

:START_SERVERS
set ENABLE_AI=false

echo Starting Backend Server on Port 8000...
start "" venv\Scripts\python.exe app.py

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
