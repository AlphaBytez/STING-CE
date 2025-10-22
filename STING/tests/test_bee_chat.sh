#!/bin/bash

echo "Testing Bee Chat connectivity..."
echo "================================"

# Test 1: External AI health
echo -e "\n1. Testing External AI health..."
curl -s http://localhost:8091/health | jq '.' || echo "Failed to connect to external AI directly"

# Test 2: Backend Bee health
echo -e "\n2. Testing Backend Bee health endpoint..."
curl -sk https://localhost:5050/api/bee/health | jq '.' || echo "Failed to connect to backend"

# Test 3: Frontend proxy to backend
echo -e "\n3. Testing Frontend proxy to Bee health..."
curl -sk https://localhost:8443/api/bee/health | jq '.' || echo "Failed to connect through frontend"

# Test 4: External AI proxy through backend
echo -e "\n4. Testing External AI proxy route..."
curl -sk https://localhost:5050/api/external-ai/health | jq '.' || echo "Failed to connect to external AI through proxy"

# Test 5: Direct bee chat test
echo -e "\n5. Testing direct Bee chat endpoint..."
curl -s -X POST http://localhost:8091/bee/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello test", "user_id": "test_user"}' | \
  jq -r '.response' | head -20 || echo "Failed to send test message"

# Test 6: Bee chat through backend proxy
echo -e "\n6. Testing Bee chat through backend proxy..."
curl -sk -X POST https://localhost:5050/api/external-ai/bee/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello test", "user_id": "test_user"}' | \
  jq -r '.response' | head -20 || echo "Failed to send message through proxy"

echo -e "\n================================"
echo "Tests complete. Check output above for any failures."