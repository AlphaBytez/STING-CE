#!/bin/bash

echo "=== STING-CE Bee + LLM Integration Test ==="
echo "Testing at $(date)"
echo

echo "1. Checking Bee service health..."
curl -s http://localhost:8888/health | jq -r '"Status: " + .status + ", LLM Gateway: " + (.components.llm_gateway|tostring)'

echo -e "\n2. Testing chat without auth (for demo)..."
curl -s -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi Bee! Can you tell me a short joke?",
    "user_id": "demo-user",
    "conversation_id": "demo-'$(date +%s)'",
    "require_auth": false
  }' | jq -r '"Response: " + .response + "\nProcessing time: " + (.processing_time|tostring) + " seconds"'

echo -e "\n=== Test Complete ==="