#!/bin/bash
# Chatbot service entrypoint script
set -e

echo "Starting chatbot service..."
python --version 2>&1
echo "Current directory:"
pwd
echo "Directory contents:"
ls -la
echo "PYTHONPATH: $PYTHONPATH"

# Check if bee_server.py exists (modern server)
if [ -f /app/chatbot/bee_server.py ]; then
    echo "Found bee_server.py at /app/chatbot/bee_server.py"
else
    echo "ERROR: bee_server.py not found at /app/chatbot/bee_server.py"
    echo "Contents of /app:"
    ls -la /app
    echo "Contents of /app/chatbot:"
    ls -la /app/chatbot 2>/dev/null || echo "Directory not found"
    exit 1
fi

# Set PYTHONPATH to include the app directory
export PYTHONPATH="${PYTHONPATH}:/app"

# Check if a command was provided via docker-compose
if [ $# -gt 0 ]; then
    echo "Starting with provided command: $@"
    exec "$@"
else
    # Start the full Bee server
    echo "Starting Bee server on port 8888..."
    exec python -m chatbot.bee_server
fi