#!/bin/bash
# Script to start the advanced test chatbot service

set -e

echo "Starting advanced test chatbot service..."

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Make sure server.py is executable
chmod +x advanced-server.py

# Stop any existing container
docker rm -f sting-advanced-chatbot 2>/dev/null || true

# Install curl in the container
echo "FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*" > Dockerfile.curl

# Build a quick image with curl
docker build -t python-with-curl -f Dockerfile.curl .

# Update the docker-compose file to use our image
sed -i.bak 's/image: python:3.12-slim/image: python-with-curl/' advanced-compose.yml

# Start the service
docker-compose -f advanced-compose.yml up -d

# Wait for the service to be ready
echo "Waiting for the advanced test chatbot to be ready..."
for i in {1..10}; do
  if curl -s http://localhost:8083/health > /dev/null 2>&1; then
    echo "✅ Advanced test chatbot is ready!"
    echo ""
    echo "You can access it at: http://localhost:8083"
    echo "To send a test message, use:"
    echo "curl -X POST http://localhost:8083/chat/message -H \"Content-Type: application/json\" -d '{\"message\": \"Hello\", \"user_id\": \"test_user\"}'"
    echo ""
    echo "To view logs:"
    echo "docker logs -f sting-advanced-chatbot"
    exit 0
  fi
  echo "Waiting... ($i/10)"
  sleep 2
done

echo "❌ Advanced test chatbot did not become ready in time. Check logs with:"
echo "docker logs sting-advanced-chatbot"
exit 1