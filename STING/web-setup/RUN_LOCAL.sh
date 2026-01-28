#!/bin/bash
# Quick local testing script

echo "🐝 STING-CE Setup Wizard - Local Testing"
echo "========================================"
echo

# Check for existing wizard processes and clean them up
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXISTING_PIDS=$(pgrep -f "python.*${SCRIPT_DIR}/app.py" 2>/dev/null)

if [ -n "$EXISTING_PIDS" ]; then
    echo "⚠️  Found existing wizard processes:"
    echo "$EXISTING_PIDS" | while read pid; do
        echo "   PID $pid"
    done
    echo
    echo "Killing old wizard processes..."
    echo "$EXISTING_PIDS" | xargs kill 2>/dev/null
    sleep 1

    # Force kill if still running
    STILL_RUNNING=$(pgrep -f "python.*${SCRIPT_DIR}/app.py" 2>/dev/null)
    if [ -n "$STILL_RUNNING" ]; then
        echo "   Force killing stubborn processes..."
        echo "$STILL_RUNNING" | xargs kill -9 2>/dev/null
    fi

    echo "✅ Cleaned up old wizard processes"
    echo
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check if STING_SOURCE is set
if [ -z "$STING_SOURCE" ]; then
    echo "⚠️  STING_SOURCE not set!"
    echo "Run: export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh"
    exit 1
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo "✅ STING source: $STING_SOURCE"
echo "✅ Dev mode: enabled (uses ./sting-setup-state/)"
echo
echo "🚀 Starting wizard on http://localhost:8080"
echo "   Press Ctrl+C to stop"
echo

python3 app.py
