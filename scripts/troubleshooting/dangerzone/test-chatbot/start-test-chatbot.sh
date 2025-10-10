#!/bin/bash
# Script to start the test chatbot service

set -e

echo "Starting test chatbot service..."

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Build and start the service
docker-compose build
docker-compose up -d

# Wait for the service to be ready
echo "Waiting for the test chatbot to be ready..."
for i in {1..10}; do
  if curl -s http://localhost:8082/health > /dev/null; then
    echo "✅ Test chatbot is ready!"
    echo ""
    echo "You can access it at: http://localhost:8082"
    echo "To send a test message, use:"
    echo "curl -X POST http://localhost:8082/chat/message -H \"Content-Type: application/json\" -d '{\"message\": \"Hello\", \"user_id\": \"test_user\"}'"
    echo ""
    echo "To view logs:"
    echo "docker logs -f sting-test-chatbot"
    exit 0
  fi
  echo "Waiting... ($i/10)"
  sleep 2
done

echo "❌ Test chatbot did not become ready in time. Check logs with:"
echo "docker logs sting-test-chatbot"
exit 1