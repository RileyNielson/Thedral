@echo off
setlocal
title Thedral Studio Launcher
cd /d "%~dp0"

echo ============================================================
echo   THEDRAL STUDIO
echo ============================================================
echo   Lite: writing tools and deterministic analysis, no AI
echo   Full: Lite features plus local Ollama AI assistance
echo.
if /i "%THEDRAL_MODE%"=="FULL" goto FULL_MODE
choice /c LF /n /m "Choose a mode: [L]ite or [F]ull: "
if errorlevel 2 goto FULL_MODE
set "MODE=LITE"
set "ENABLE_AI=false"
set "REQUIREMENTS=requirements.txt"
goto CHECK_PYTHON

:FULL_MODE
set "MODE=FULL"
set "ENABLE_AI=true"
set "REQUIREMENTS=requirements-ai.txt"

:CHECK_PYTHON
if exist "venv\Scripts\python.exe" (
    set "PYTHON=%CD%\venv\Scripts\python.exe"
    goto CHECK_CORE_PACKAGES
)
where python >nul 2>&1
if not errorlevel 1 (
    python -m venv venv
    if errorlevel 1 goto SETUP_FAILED
    set "PYTHON=%CD%\venv\Scripts\python.exe"
    goto CHECK_CORE_PACKAGES
)
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -m venv venv
    if errorlevel 1 goto SETUP_FAILED
    set "PYTHON=%CD%\venv\Scripts\python.exe"
    goto CHECK_CORE_PACKAGES
)
echo ERROR: Python 3 is required. Install Python from https://www.python.org/downloads/
goto FAILED

:CHECK_CORE_PACKAGES
"%PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Thedral requires Python 3.11 or newer.
    goto FAILED
)
echo.
echo Checking Thedral's Python dependencies...
"%PYTHON%" -c "import fastapi, uvicorn, docx, pydantic, plotly, multipart, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing core requirements from %REQUIREMENTS%...
    "%PYTHON%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 goto SETUP_FAILED
)
set "CONFIG_FILE=%TEMP%\ThedralPort-%RANDOM%.txt"
"%PYTHON%" -c "from backend.config import PORT; print(PORT)" > "%CONFIG_FILE%" 2>nul
if errorlevel 1 (
    del "%CONFIG_FILE%" >nul 2>&1
    echo ERROR: Could not read the configured server port.
    goto FAILED
)
set /p "PORT="<"%CONFIG_FILE%"
del "%CONFIG_FILE%" >nul 2>&1
if not defined PORT (
    echo ERROR: Could not read the configured server port.
    goto FAILED
)
set "BASE_URL=http://127.0.0.1:%PORT%"
if /i "%MODE%"=="LITE" goto CHECK_EXISTING_SERVER

"%PYTHON%" -c "import ollama" >nul 2>&1
if errorlevel 1 (
    echo Installing local AI client...
    "%PYTHON%" -m pip install -r requirements-ai.txt
    if errorlevel 1 goto SETUP_FAILED
)

where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Ollama is not installed or is not on PATH.
    echo Install it from https://ollama.com/download and run this launcher again.
    goto FAILED
)

set "CONFIG_FILE=%TEMP%\ThedralModel-%RANDOM%.txt"
"%PYTHON%" -c "from backend.config import STUDIO_MODEL; print(STUDIO_MODEL)" > "%CONFIG_FILE%" 2>nul
if errorlevel 1 (
    del "%CONFIG_FILE%" >nul 2>&1
    echo ERROR: Could not read the configured model name.
    goto FAILED
)
set /p "MODEL="<"%CONFIG_FILE%"
del "%CONFIG_FILE%" >nul 2>&1
set "CONFIG_FILE=%TEMP%\ThedralOllamaHost-%RANDOM%.txt"
"%PYTHON%" -c "from backend.config import OLLAMA_HOST; print(OLLAMA_HOST)" > "%CONFIG_FILE%" 2>nul
if errorlevel 1 (
    del "%CONFIG_FILE%" >nul 2>&1
    echo ERROR: Could not read the configured Ollama address.
    goto FAILED
)
set /p "OLLAMA_HOST="<"%CONFIG_FILE%"
del "%CONFIG_FILE%" >nul 2>&1
if not defined MODEL (
    echo ERROR: Could not read the configured model name.
    goto FAILED
)
if not defined OLLAMA_HOST (
    echo ERROR: Could not read the configured Ollama address.
    goto FAILED
)
echo Checking Ollama and model "%MODEL%"...
set "MODEL_LIST=%TEMP%\ThedralOllamaModels-%RANDOM%.txt"
ollama list > "%MODEL_LIST%" 2>&1
if errorlevel 1 (
    echo ERROR: Could not list locally installed Ollama models.
    type "%MODEL_LIST%"
    del "%MODEL_LIST%" >nul 2>&1
    goto FAILED
)
findstr /i /b /c:"%MODEL% " "%MODEL_LIST%" >nul
if errorlevel 1 (
    echo ERROR: The configured model "%MODEL%" is not downloaded.
    echo Run this command, then launch Full mode again:
    echo   ollama pull %MODEL%
    del "%MODEL_LIST%" >nul 2>&1
    goto FAILED
)
del "%MODEL_LIST%" >nul 2>&1

:CHECK_EXISTING_SERVER
set "HEALTH_FILE=%TEMP%\ThedralHealth-%RANDOM%.json"
set "POLL_FILE=%TEMP%\ThedralPoll-%RANDOM%.json"
curl.exe --silent --fail "%BASE_URL%/api/health" > "%HEALTH_FILE%" 2>nul
if not errorlevel 1 (
    "%PYTHON%" -c "import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get('app') == 'Thedral Studio' else 1)" "%HEALTH_FILE%" >nul 2>&1
    if not errorlevel 1 (
        "%PYTHON%" -c "import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get('mode') == '%MODE%' else 1)" "%HEALTH_FILE%" >nul 2>&1
        if not errorlevel 1 (
            echo Thedral is already running in %MODE% mode.
            del "%HEALTH_FILE%" >nul 2>&1
            start "" "%BASE_URL%"
            goto FINISHED
        )
        echo ERROR: Thedral is already running in a different mode.
        echo Close its backend window, then run this launcher again.
        del "%HEALTH_FILE%" >nul 2>&1
        goto FAILED
    )
)
del "%HEALTH_FILE%" >nul 2>&1
where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js 20.19 or newer is required to build the studio interface.
    echo Install Node.js from https://nodejs.org/ and run this launcher again.
    goto FAILED
)
node -e "const [major,minor]=process.versions.node.split('.').map(Number); process.exit(major>22||(major===22&&minor>=12)||(major===20&&minor>=19)?0:1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: The frontend requires Node.js 20.19+ or 22.12+.
    echo Upgrade Node.js from https://nodejs.org/ and run this launcher again.
    goto FAILED
)
if exist "frontend\node_modules" goto BUILD_FRONTEND
echo Installing frontend packages...
pushd frontend
call npm ci
if errorlevel 1 (
    popd
    goto FRONTEND_SETUP_FAILED
)
popd

:BUILD_FRONTEND
echo Building the current studio interface...
pushd frontend
call npm run build
if errorlevel 1 (
    popd
    goto FRONTEND_SETUP_FAILED
)
popd

:START_BACKEND
echo.
echo Starting Thedral in %MODE% mode...
echo Backend output will appear in its own console window.
start "Thedral Backend (%MODE%)" "%PYTHON%" app.py

echo Waiting for Thedral to become ready...
for /l %%I in (1,1,30) do (
    curl.exe --silent --fail "%BASE_URL%/api/health" > "%POLL_FILE%" 2>nul
    if not errorlevel 1 goto SERVER_RESPONDING
    timeout /t 1 /nobreak >nul
)
del "%POLL_FILE%" >nul 2>&1
echo ERROR: Thedral did not become ready within 30 seconds.
echo Check the backend console for startup errors. It has been left open for diagnosis.
goto FAILED

:SERVER_RESPONDING
del "%POLL_FILE%" >nul 2>&1
rem Confirm the responding service is Thedral and is running in the requested mode.
curl.exe --silent --fail "%BASE_URL%/api/health" > "%HEALTH_FILE%" 2>nul
if errorlevel 1 goto STARTUP_FAILED
"%PYTHON%" -c "import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get('app') == 'Thedral Studio' else 1)" "%HEALTH_FILE%" >nul 2>&1
if errorlevel 1 goto STARTUP_FAILED
"%PYTHON%" -c "import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get('mode') == '%MODE%' else 1)" "%HEALTH_FILE%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Port 8000 is serving Thedral in a different mode.
    echo Close that backend console, then run this launcher again.
    del "%HEALTH_FILE%" >nul 2>&1
    goto FAILED
)
del "%HEALTH_FILE%" >nul 2>&1
echo Thedral is ready. Opening %BASE_URL%
start "" "%BASE_URL%"
echo Close the "Thedral Backend" console window to stop the server.
goto FINISHED

:STARTUP_FAILED
echo ERROR: Another service is using port 8000, or Thedral returned an unexpected response.
del "%HEALTH_FILE%" >nul 2>&1
goto FAILED

:SETUP_FAILED
echo ERROR: Setup failed. Review the message above, resolve it, and retry.
goto FAILED

:FRONTEND_SETUP_FAILED
echo ERROR: Frontend setup failed. Review the npm output above and retry.
goto FAILED

:FAILED
echo.
pause
exit /b 1

:FINISHED
echo.
pause
exit /b 0
