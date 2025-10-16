#!/bin/bash

# Test the unified login flow with the new check-user endpoint

set -e

KRATOS_URL="${KRATOS_URL:-https://localhost:4433}"
API_URL="${API_URL:-https://localhost:5050}"
FRONTEND_URL="${FRONTEND_URL:-https://localhost:3000}"

echo "=== Testing Unified Login Flow ==="
echo

# Test 1: Check if user exists (non-existent user)
echo "1. Testing check-user endpoint with non-existent user..."
curl -k -X POST "$API_URL/api/auth/check-user" \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@example.com"}' | jq .
echo

# Test 2: Check if user exists (existing user)
echo "2. Testing check-user endpoint with existing user (if any)..."
curl -k -X POST "$API_URL/api/auth/check-user" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' | jq .
echo

# Test 3: Access the unified login page
echo "3. Testing access to unified login page..."
curl -k -I "$FRONTEND_URL/login" | head -n 5
echo

echo "=== Test complete ==="
echo
echo "To fully test the flow:"
echo "1. Open https://localhost:3000/login in your browser"
echo "2. Enter an email address"
echo "3. The system should check if the user exists"
echo "4. If user exists, show available auth methods"
echo "5. If user doesn't exist, show registration prompt"