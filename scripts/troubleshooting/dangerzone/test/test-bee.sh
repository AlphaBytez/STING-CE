#!/bin/bash

echo "🐝 Testing Bee..."

# Test 1: Basic chat
echo -e "\n1. Basic Chat Test:"
curl -s -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Bee!", "user_id": "test-user", "require_auth": false}' | jq .

# Test 2: Sentiment analysis
echo -e "\n2. Sentiment Analysis Test:"
curl -s -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "This is absolutely wonderful! I love it!", "user_id": "test-user", "require_auth": false}' | jq .

# Test 3: Tools
echo -e "\n3. Tools Test:"
curl -s -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for inventory data", "user_id": "test-user", "tools_enabled": ["search", "analytics"], "require_auth": false}' | jq .

echo -e "\n✅ Tests complete!"