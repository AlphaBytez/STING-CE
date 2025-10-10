#!/bin/bash

echo "Testing Bee with LLM integration..."

# Test with auth bypass by not setting require_auth
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi bee, can you help me?",
    "user_id": "test-user",
    "conversation_id": "test-conv-'$(date +%s)'",
    "require_auth": false
  }' | jq .

echo -e "\n\nChecking LLM Gateway health..."
curl http://localhost:8085/health | jq .

echo -e "\n\nChecking Bee service health..."
curl http://localhost:8888/health | jq .