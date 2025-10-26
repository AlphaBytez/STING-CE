#!/bin/bash

echo "Starting STING Messaging Service..."

# Set environment variables
export MESSAGING_ENCRYPTION_ENABLED=true
export MESSAGING_QUEUE_ENABLED=true
export MESSAGING_NOTIFICATIONS_ENABLED=true
export MESSAGING_STORAGE_BACKEND=memory
export MAX_MESSAGE_SIZE=1048576
export MESSAGE_RETENTION_DAYS=30

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting messaging service on port 8889..."
python server.py