#!/bin/bash

# =============================================================================
# Thedral Sovereign Studio — 1-Click Desktop Launcher
# =============================================================================

# Resolve project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================="
echo "   🚀 LAUNCHING THEDRAL SOVEREIGN STUDIO"
echo "================================================================="
echo "Directory: $DIR"

# 1. Activate Python Virtual Environment
if [ -d "$DIR/venv" ]; then
    source "$DIR/venv/bin/activate"
    PYTHON_CMD="$DIR/venv/bin/python"
elif [ -d "$DIR/.venv" ]; then
    source "$DIR/.venv/bin/activate"
    PYTHON_CMD="$DIR/.venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# 2. Check for Ollama (Local AI)
if command -v ollama >/dev/null 2>&1; then
    if ! pgrep -x "ollama" > /dev/null; then
        echo "🧠 Starting local Ollama engine..."
        ollama serve >/dev/null 2>&1 &
        sleep 2
    else
        echo "🧠 Local Ollama engine is already running."
    fi
else
    echo "⚠️ Ollama not detected in PATH. Studio running in offline math mode."
fi

# 3. Start Thedral FastAPI Backend
echo "⚡ Starting Thedral Backend Core (Port 8000)..."
$PYTHON_CMD app.py > /dev/null 2>&1 &
BACKEND_PID=$!

# 4. Start Vite Frontend Server
echo "🎨 Starting Studio Interface (Port 5173)..."
npm run dev -- --host > /dev/null 2>&1 &
FRONTEND_PID=$!

# Trap Ctrl+C or terminal close to shut down both processes cleanly
cleanup() {
    echo ""
    echo "🛑 Shutting down Thedral Studio..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Wait for servers to spin up
sleep 2

# 5. Open Default Web Browser
echo "🌐 Opening Thedral in browser..."
open "http://localhost:5173"

echo ""
echo "✨ THEDRAL IS LIVE!"
echo "   Desktop:  http://localhost:5173"
echo "   Close this window to stop the studio."
echo "================================================================="

# Keep launcher alive
wait