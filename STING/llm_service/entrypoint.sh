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

echo "🚀 Starting LLM service"

# Skip model download if models already exist
if [ -d "/app/models/TinyLlama-1.1B-Chat" ]; then
    echo "🔍 Model tinyllama already exists, skipping download"
else
    echo "🔍 Model tinyllama not found, will download during service startup"
fi

# Start the service
cd /app
export PORT=8080
echo "🚀 Starting server on port $PORT"
# Use exec to replace the shell process with Python
# This ensures proper signal handling and prevents blocking
exec python -u server.py