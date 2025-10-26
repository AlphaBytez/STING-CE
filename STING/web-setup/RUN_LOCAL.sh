#!/bin/bash
# Quick local testing script

echo "🐝 STING-CE Setup Wizard - Local Testing"
echo "========================================"
echo

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
