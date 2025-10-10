#!/bin/bash
# Script to fix the LLM Gateway service in STING

set -e

# Display banner
echo "====================================="
echo "  STING LLM Gateway Repair Script"
echo "====================================="

# Navigate to the STING directory
cd "$(dirname "$0")"
STING_DIR=$(pwd)

echo "Working in directory: $STING_DIR"

# Backup original files
echo "Creating backups of original files..."
timestamp=$(date +%Y%m%d%H%M%S)
mkdir -p backups

if [ -f "$STING_DIR/llm_service/server.py" ]; then
  cp "$STING_DIR/llm_service/server.py" "$STING_DIR/llm_service/server.py.bak.$timestamp"
  echo "✅ Backed up server.py"
fi

if [ -f "$STING_DIR/llm_service/Dockerfile.gateway" ]; then
  cp "$STING_DIR/llm_service/Dockerfile.gateway" "$STING_DIR/llm_service/Dockerfile.gateway.bak.$timestamp"
  echo "✅ Backed up Dockerfile.gateway"
fi

# Copy fixed files
echo "Applying fixes..."
if [ -f "$STING_DIR/llm_service/server.py.fixed" ]; then
  cp "$STING_DIR/llm_service/server.py.fixed" "$STING_DIR/llm_service/server.py"
  echo "✅ Applied fixed server.py"
else
  echo "❌ Fixed server.py not found! Aborting."
  exit 1
fi

if [ -f "$STING_DIR/llm_service/Dockerfile.gateway.fixed" ]; then
  cp "$STING_DIR/llm_service/Dockerfile.gateway.fixed" "$STING_DIR/llm_service/Dockerfile.gateway"
  echo "✅ Applied fixed Dockerfile.gateway"
else
  echo "❌ Fixed Dockerfile.gateway not found! Aborting."
  exit 1
fi

# Rebuild and restart the LLM Gateway service
echo "Rebuilding and restarting LLM Gateway service..."
docker-compose build llm-gateway
if [ $? -ne 0 ]; then
  echo "❌ Failed to build llm-gateway service!"
  exit 1
fi

echo "Stopping existing LLM Gateway container..."
docker-compose stop llm-gateway
if [ $? -ne 0 ]; then
  echo "⚠️ Warning: Could not stop llm-gateway container"
fi

echo "Starting LLM Gateway with fixed configuration..."
docker-compose up -d llm-gateway
if [ $? -ne 0 ]; then
  echo "❌ Failed to start llm-gateway service!"
  exit 1
fi

echo "Waiting for LLM Gateway to initialize (60 seconds)..."
sleep 60

# Check if the service is healthy
echo "Checking LLM Gateway health..."
docker-compose ps llm-gateway | grep "Up" > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ LLM Gateway service is running"
else
  echo "❌ LLM Gateway service is not running properly!"
  docker-compose logs llm-gateway --tail 50
  exit 1
fi

# Test the LLM Gateway
echo "Testing LLM Gateway API..."
curl -s http://localhost:8085/health | grep "healthy" > /dev/null
if [ $? -eq 0 ]; then
  echo "✅ LLM Gateway is responding to health checks"
else
  echo "⚠️ Warning: LLM Gateway health check failed!"
  curl -v http://localhost:8085/health
fi

echo ""
echo "====================================="
echo "  LLM Gateway repair complete!"
echo "====================================="
echo "If problems persist, check the logs with:"
echo "  docker-compose logs llm-gateway"
echo ""
echo "To test the chatbot integration, run:"
echo "  ./test-chatbot-api.sh"
echo "====================================="