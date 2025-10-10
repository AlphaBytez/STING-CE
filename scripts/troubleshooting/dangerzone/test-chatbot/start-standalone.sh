#!/bin/bash
# Script to start the standalone test chatbot service

set -e

echo "Starting standalone test chatbot service..."

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Make sure server.py is executable
chmod +x standalone-server.py

# Stop any existing container
docker rm -f sting-standalone-chatbot 2>/dev/null || true

# Start the service
docker-compose -f standalone-compose.yml up -d

# Wait for the service to be ready
echo "Waiting for the standalone test chatbot to be ready..."
for i in {1..10}; do
  if curl -s http://localhost:8082/health > /dev/null 2>&1; then
    echo "✅ Standalone test chatbot is ready!"
    echo ""
    echo "You can access it at: http://localhost:8082"
    echo "To send a test message, use:"
    echo "curl -X POST http://localhost:8082/chat/message -H \"Content-Type: application/json\" -d '{\"message\": \"Hello\", \"user_id\": \"test_user\"}'"
    echo ""
    echo "To view logs:"
    echo "docker logs -f sting-standalone-chatbot"
    exit 0
  fi
  echo "Waiting... ($i/10)"
  sleep 2
done

echo "❌ Standalone test chatbot did not become ready in time. Check logs with:"
echo "docker logs sting-standalone-chatbot"
exit 1