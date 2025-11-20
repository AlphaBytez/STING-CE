#!/bin/bash
# Chatbot service entrypoint script
set -e

echo "Starting chatbot service..."

# Sync Vault token from shared volume
# This ensures we always have the latest token after Vault initialization
echo "Syncing Vault token..."
VAULT_TOKEN_FILE="/app/conf/.vault-auto-init.json"
VAULT_TOKEN_ENV_FILE="/app/conf/.vault_token"

if [ -f "$VAULT_TOKEN_FILE" ]; then
    # Extract token from JSON file
    LATEST_VAULT_TOKEN=$(python3 -c "import json; data=json.load(open('$VAULT_TOKEN_FILE')); print(data.get('root_token', ''))" 2>/dev/null || echo "")
    if [ -n "$LATEST_VAULT_TOKEN" ] && [ "$LATEST_VAULT_TOKEN" != "$VAULT_TOKEN" ]; then
        echo "Found updated Vault token in $VAULT_TOKEN_FILE"
        export VAULT_TOKEN="$LATEST_VAULT_TOKEN"
        echo "✅ Vault token updated"
    fi
elif [ -f "$VAULT_TOKEN_ENV_FILE" ]; then
    # Fall back to simple token file
    LATEST_VAULT_TOKEN=$(cat "$VAULT_TOKEN_ENV_FILE" 2>/dev/null || echo "")
    if [ -n "$LATEST_VAULT_TOKEN" ] && [ "$LATEST_VAULT_TOKEN" != "$VAULT_TOKEN" ]; then
        echo "Found updated Vault token in $VAULT_TOKEN_ENV_FILE"
        export VAULT_TOKEN="$LATEST_VAULT_TOKEN"
        echo "✅ Vault token updated"
    fi
else
    echo "⚠️  No Vault token file found, using environment variable"
fi

echo "Current Vault token: ${VAULT_TOKEN:0:30}..."

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
    echo "Starting with provided command: $*"
    exec "$@"
else
    # Start the full Bee server
    echo "Starting Bee server on port 8888..."
    exec python -m chatbot.bee_server
fi