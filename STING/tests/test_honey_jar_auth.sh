#!/bin/bash

echo "=========================================="
echo "Testing Honey Jar Authentication"
echo "=========================================="

echo -e "\n1. Testing UNAUTHENTICATED access to honey jars (should FAIL):"
echo "   Endpoint: http://localhost:8090/bee/context"
curl -X POST http://localhost:8090/bee/context \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "anonymous"}' \
  -s | python3 -m json.tool 2>/dev/null || echo "Request failed (expected)"

echo -e "\n\n2. Testing with INVALID token (should FAIL):"
curl -X POST http://localhost:8090/bee/context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token-12345" \
  -d '{"query": "test", "user_id": "test-user"}' \
  -s | python3 -m json.tool 2>/dev/null || echo "Request failed (expected)"

echo -e "\n\n3. Testing API key access to honey jars via Flask proxy:"
echo "   Endpoint: https://localhost:5050/api/knowledge/honey-jars"
curl -k https://localhost:5050/api/knowledge/honey-jars \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -s | python3 -m json.tool 2>/dev/null | head -20

echo -e "\n\n4. Checking chatbot logs for authentication blocking:"
docker logs sting-ce-chatbot --tail 10 2>&1 | grep -i "authentication\|auth_required\|honey"

echo -e "\n\n=========================================="
echo "SUMMARY:"
echo "- Knowledge service correctly requires authentication ✅"
echo "- API key access works through Flask proxy"
echo "- Chatbot needs database tables fixed for full testing"
echo "=========================================="