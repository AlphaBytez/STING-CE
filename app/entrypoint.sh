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
wait_for_service "supertokens" 3567 "Supertokens"

echo "All dependencies are available"

# Determine how to run the application based on environment
if [ "${APP_ENV}" = "production" ]; then
    echo "Starting application in production mode..."
    exec gunicorn \
        --bind 0.0.0.0:${APP_PORT:-5050} \
        --workers ${GUNICORN_WORKERS:-4} \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        "app.run:app"
else
    echo "Starting application in development mode..."
    exec python run.py
fi