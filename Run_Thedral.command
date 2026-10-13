#!/bin/bash

set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================================"
echo "  THEDRAL STUDIO"
echo "  Lite: writing tools and deterministic analysis, no AI"
echo "  Full: Lite features plus local Ollama AI assistance"
echo "============================================================"
printf "Choose a mode: [L]ite or [F]ull: "
read -r MODE_CHOICE
case "${MODE_CHOICE:-L}" in
    [Ff]) MODE="FULL"; AI_ENABLED="true"; REQUIREMENTS="requirements-ai.txt" ;;
    [Ll]) MODE="LITE"; AI_ENABLED="false"; REQUIREMENTS="requirements.txt" ;;
    *) echo "Please enter L for Lite or F for Full."; read -r -p "Press Return to close."; exit 1 ;;
esac

if [ ! -x "$DIR/venv/bin/python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: Python 3 is required. Install it from https://www.python.org/downloads/"
        read -r -p "Press Return to close."
        exit 1
    fi
    echo "Creating the Python environment..."
    if ! python3 -m venv "$DIR/venv"; then
        echo "ERROR: Could not create the Python environment."
        read -r -p "Press Return to close."
        exit 1
    fi
fi
PYTHON="$DIR/venv/bin/python"
if ! "$PYTHON" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "ERROR: Thedral requires Python 3.11 or newer."
    read -r -p "Press Return to close."
    exit 1
fi

if ! "$PYTHON" -c "import fastapi, uvicorn, docx, pydantic, plotly, multipart, dotenv" >/dev/null 2>&1; then
    echo "Installing core Python requirements..."
    if ! "$PYTHON" -m pip install -r "$DIR/$REQUIREMENTS"; then
        echo "ERROR: Python dependency installation failed."
        read -r -p "Press Return to close."
        exit 1
    fi
fi

PORT="$("$PYTHON" -c "from backend.config import PORT; print(PORT)")" || {
    echo "ERROR: Could not read the configured server port."
    read -r -p "Press Return to close."
    exit 1
}
if [ -z "$PORT" ]; then
    echo "ERROR: The configured server port is empty."
    read -r -p "Press Return to close."
    exit 1
fi
BASE_URL="http://127.0.0.1:$PORT"

if [ "$MODE" = "FULL" ]; then
    if ! "$PYTHON" -c "import ollama" >/dev/null 2>&1; then
        echo "Installing the local AI client..."
        if ! "$PYTHON" -m pip install -r "$DIR/requirements-ai.txt"; then
            echo "ERROR: Local AI client installation failed."
            read -r -p "Press Return to close."
            exit 1
        fi
    fi
    if ! command -v ollama >/dev/null 2>&1; then
        echo "ERROR: Ollama is not installed. Install it from https://ollama.com/download"
        read -r -p "Press Return to close."
        exit 1
    fi
    OLLAMA_HOST="$("$PYTHON" -c "from backend.config import OLLAMA_HOST; print(OLLAMA_HOST)")" || {
        echo "ERROR: Could not read the configured Ollama address."
        read -r -p "Press Return to close."
        exit 1
    }
    if [ -z "$OLLAMA_HOST" ]; then
        echo "ERROR: The configured Ollama address is empty."
        read -r -p "Press Return to close."
        exit 1
    fi
    export OLLAMA_HOST
    if ! OLLAMA_MODELS="$(ollama list 2>&1)"; then
        echo "ERROR: Ollama is installed but its local service is not responding."
        echo "Start Ollama, then run this launcher again."
        echo "$OLLAMA_MODELS"
        read -r -p "Press Return to close."
        exit 1
    fi
    if ! MODEL="$("$PYTHON" -c "from backend.config import STUDIO_MODEL; print(STUDIO_MODEL)")" || [ -z "$MODEL" ]; then
        echo "ERROR: Could not read the configured model name."
        read -r -p "Press Return to close."
        exit 1
    fi
    if ! printf '%s\n' "$OLLAMA_MODELS" | grep -F "$MODEL" >/dev/null; then
        echo "ERROR: The configured model '$MODEL' is not downloaded."
        echo "Run: ollama pull $MODEL"
        read -r -p "Press Return to close."
        exit 1
    fi
fi

if ! command -v npm >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
    echo "ERROR: Node.js 20.19+ or 22.12+ is required to build the studio interface."
    echo "Install it from https://nodejs.org/ and run this launcher again."
    read -r -p "Press Return to close."
    exit 1
fi
if ! node -e "const [major,minor]=process.versions.node.split('.').map(Number); process.exit(major>22||(major===22&&minor>=12)||(major===20&&minor>=19)?0:1)"; then
    echo "ERROR: The frontend requires Node.js 20.19+ or 22.12+."
    echo "Upgrade Node.js from https://nodejs.org/ and run this launcher again."
    read -r -p "Press Return to close."
    exit 1
fi
if HEALTH="$(curl -fsS "$BASE_URL/api/health" 2>/dev/null)"; then
    if printf '%s' "$HEALTH" | grep -F '"app":"Thedral Studio"' >/dev/null; then
        if printf '%s' "$HEALTH" | grep -F "\"mode\":\"$MODE\"" >/dev/null; then
            echo "Thedral is already running in $MODE mode."
            open "$BASE_URL"
            read -r -p "Press Return to close."
            exit 0
        fi
        echo "ERROR: Thedral is already running in a different mode."
        echo "Close its backend process, then run this launcher again."
        read -r -p "Press Return to close."
        exit 1
    fi
fi

if ! "$PYTHON" -c "from backend.wiktionary_lexicon import get_lexicon_status; raise SystemExit(0 if get_lexicon_status().get('available') else 1)" >/dev/null 2>&1; then
    echo
    echo "Optional reader enhancement: English Wiktionary data is not installed."
    echo "Download size is about 418 MB. Thedral works without it."
    read -r -p "Download now? [y/N]: " DOWNLOAD_WIKTIONARY
    case "${DOWNLOAD_WIKTIONARY:-N}" in
        [Yy]|[Yy][Ee][Ss])
            echo "Downloading and installing English Wiktionary..."
            if ! "$PYTHON" -m backend.wiktionary_lexicon --download; then
                echo "Wiktionary download failed. Continuing without the optional lexicon."
            fi
            ;;
        *)
            echo "Skipping optional Wiktionary download."
            ;;
    esac
fi

if [ ! -d "$DIR/frontend/node_modules" ]; then
    echo "Installing frontend packages..."
    if ! npm --prefix "$DIR/frontend" ci; then
        echo "ERROR: Frontend dependency installation failed."
        read -r -p "Press Return to close."
        exit 1
    fi
fi
echo "Building the current studio interface..."
if ! npm --prefix "$DIR/frontend" run build; then
    echo "ERROR: Frontend build failed."
    read -r -p "Press Return to close."
    exit 1
fi

LOG_FILE="$DIR/exports/thedral-backend.log"
mkdir -p "$DIR/exports"
: > "$LOG_FILE"
BACKEND_PID=""
cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo
        echo "Stopping Thedral..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "Starting Thedral in $MODE mode..."
ENABLE_AI="$AI_ENABLED" "$PYTHON" "$DIR/app.py" >> "$LOG_FILE" 2>&1 &
BACKEND_PID=$!

READY=0
for _ in $(seq 1 30); do
    if HEALTH="$(curl -fsS "$BASE_URL/api/health" 2>/dev/null)" \
        && printf '%s' "$HEALTH" | grep -F '"app":"Thedral Studio"' >/dev/null \
        && printf '%s' "$HEALTH" | grep -F "\"mode\":\"$MODE\"" >/dev/null; then
        READY=1
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "ERROR: Thedral did not become ready in $MODE mode."
    echo "Backend log ($LOG_FILE):"
    cat "$LOG_FILE"
    read -r -p "Press Return to close."
    exit 1
fi

echo "Thedral is ready at $BASE_URL"
echo "Startup log: $LOG_FILE"
open "$BASE_URL"
echo "Keep this window open while using Thedral. Press Control-C to stop it."
wait "$BACKEND_PID"
