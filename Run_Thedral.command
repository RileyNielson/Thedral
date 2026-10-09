#!/bin/bash

# =============================================================================
# Thedral Sovereign Studio — 1-Click Mac Launcher
# =============================================================================

# Resolve project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================="
echo "   🚀 LAUNCHING THEDRAL SOVEREIGN STUDIO (MAC)"
echo "================================================================="

# 1. Self-Installing Python Environment
if [ ! -f "$DIR/venv/bin/python" ]; then
    echo "[1/2] First-time setup: Creating Python virtual environment..."
    python3 -m venv venv
    
    echo "[2/2] Installing Python requirements..."
    "$DIR/venv/bin/pip" install fastapi uvicorn python-docx pydantic plotly python-multipart
fi

export ENABLE_AI=false

# 2. Start Thedral Backend Core
echo "⚡ Starting Thedral Core on Port 8000..."
"$DIR/venv/bin/python" app.py > /dev/null 2>&1 &
BACKEND_PID=$!

# Trap Ctrl+C or terminal close to shut down process cleanly
cleanup() {
    echo ""
    echo "🛑 Shutting down Thedral Studio..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 3. Wait for server to spin up and open Browser
sleep 3
echo "🌐 Opening Thedral in browser..."
open "http://localhost:8000"

echo ""
echo "✨ THEDRAL IS LIVE!"
echo "   Desktop:  http://localhost:8000"
echo "   Close this terminal window to stop the studio."
echo "================================================================="

# Keep launcher alive
wait
