#!/bin/bash

echo "Stopping the wait for unnecessary services on Mac..."

# Find and kill the manage_sting.sh process that's waiting
pkill -f "wait_for_service llama3-service" 2>/dev/null || true

# Start the stub services manually if needed
cd "$(dirname "$0")"
docker compose up -d llm-gateway 2>/dev/null

echo "You can now continue with the installation."
echo "The LLM services are optional on Mac since you'll use native Python."
echo ""
echo "To install PyTorch for native LLM service:"
echo "pip3 install torch torchvision transformers accelerate fastapi uvicorn"