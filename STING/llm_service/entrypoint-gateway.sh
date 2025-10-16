#!/bin/bash
set -e

# Skip startup during installation phase
if [ "$SKIP_STARTUP" = "true" ]; then
    echo "🏗️ SKIP_STARTUP is set, exiting without starting service"
    exit 0
fi

# Check if we're in Docker build context
if [ -n "$DOCKER_BUILDKIT" ] || [ -f /.dockerenv ] && [ -z "$HOSTNAME" ]; then
    echo "🏗️ Detected Docker build context, skipping service startup"
    exit 0
fi

echo "🚀 Starting LLM Gateway service"

# Start the gateway service
cd /app
export PORT=${PORT:-8080}
export PYTHONPATH=/app:$PYTHONPATH

echo "🚀 Starting gateway on port $PORT"

# Run the gateway server
echo "Running gateway_server.py"
exec python -u gateway_server.py