#!/bin/bash
set -e

echo "Starting application entrypoint..."

# Wait for dependencies if needed
function wait_for_service() {
    local host=$1
    local port=$2
    local service=$3

    echo "Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port"; do
        echo "$service is unavailable - sleeping"
        sleep 1
    done
    echo "$service is up!"
}

# Wait for essential services
wait_for_service "vault" 8200 "Vault"
wait_for_service "db" 5432 "PostgreSQL"

echo "All dependencies are available"

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

# Determine how to run the application based on environment
if [ "${APP_ENV}" = "production" ]; then
    echo "Starting application in production mode..."
    exec gunicorn \
        --bind "0.0.0.0:${APP_PORT:-5050}" \
        --workers "${GUNICORN_WORKERS:-4}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --access-logfile - \
        --error-logfile - \
        "app.run:app"
else
    echo "Starting application in development mode..."
    exec python run.py
fi