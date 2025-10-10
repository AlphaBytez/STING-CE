#!/bin/bash
# Script to fix the LLM Gateway service and other conflicts in STING

set -e

# Display banner
echo "====================================="
echo "  STING LLM Service Repair Script"
echo "====================================="

# Navigate to the STING directory
cd "$(dirname "$0")"
STING_DIR=$(pwd)

echo "Working in directory: $STING_DIR"

# Backup original files
echo "Creating backups of original files..."
timestamp=$(date +%Y%m%d%H%M%S)
mkdir -p backups

# Backup all necessary files
if [ -f "$STING_DIR/llm_service/server.py" ]; then
  cp "$STING_DIR/llm_service/server.py" "$STING_DIR/llm_service/server.py.bak.$timestamp"
  echo "✅ Backed up server.py"
fi

if [ -f "$STING_DIR/llm_service/Dockerfile.gateway" ]; then
  cp "$STING_DIR/llm_service/Dockerfile.gateway" "$STING_DIR/llm_service/Dockerfile.gateway.bak.$timestamp"
  echo "✅ Backed up Dockerfile.gateway"
fi

if [ -f "$STING_DIR/docker-compose.yml" ]; then
  cp "$STING_DIR/docker-compose.yml" "$STING_DIR/docker-compose.yml.bak.$timestamp"
  echo "✅ Backed up docker-compose.yml"
fi

# Apply fixed files
echo "Applying fixes to files..."
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

if [ -f "$STING_DIR/docker-compose.yml.fixed" ]; then
  cp "$STING_DIR/docker-compose.yml.fixed" "$STING_DIR/docker-compose.yml"
  echo "✅ Applied fixed docker-compose.yml"
else
  echo "❌ Fixed docker-compose.yml not found! Aborting."
  exit 1
fi

# Clean up all containers to avoid conflicts
echo "Stopping and removing all containers..."
docker-compose down
docker ps -a | grep 'sting-' | awk '{print $1}' | xargs -r docker rm -f

# Rebuild and restart services
echo "Rebuilding and restarting services..."
docker-compose build llm-gateway
if [ $? -ne 0 ]; then
  echo "❌ Failed to build llm-gateway service!"
  exit 1
fi

echo "Starting services with fixed configuration..."
docker-compose up -d
if [ $? -ne 0 ]; then
  echo "❌ Failed to start services!"
  exit 1
fi

echo "Waiting for LLM Gateway to initialize (90 seconds)..."
sleep 90

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
echo "  LLM Service repair complete!"
echo "====================================="
echo "If problems persist, check the logs with:"
echo "  docker-compose logs llm-gateway"
echo ""
echo "To test the chatbot integration, run:"
echo "  curl -X POST http://localhost:8081/chat -H 'Content-Type: application/json' -d '{\"message\":\"Hello\",\"user_id\":\"test\"}'"
echo "====================================="