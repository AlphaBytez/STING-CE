#!/bin/bash
# Script to test Kratos login flow directly

echo "🔍 Testing Kratos login flow directly..."

# Define variables
KRATOS_URL="https://localhost:4433"

# Test direct connection to Kratos
echo "⏳ Testing connection to Kratos at $KRATOS_URL..."
curl -k "$KRATOS_URL/health/ready" || {
  echo "❌ Cannot connect to Kratos health endpoint. Check if Kratos is running."
  exit 1
}

# Create a login flow via API
echo -e "\n⏳ Testing login flow creation..."
FLOW_RESPONSE=$(curl -k -s "$KRATOS_URL/self-service/login/api")

# Check if we got a proper response
if [[ $FLOW_RESPONSE == *"id"* ]]; then
  echo "✅ Login flow created successfully!"
  FLOW_ID=$(echo $FLOW_RESPONSE | grep -o '"id":"[^"]*' | head -1 | sed 's/"id":"//g')
  echo "   Flow ID: $FLOW_ID"
  
  # Get more details about the flow
  echo -e "\n⏳ Getting flow details..."
  curl -k -s "$KRATOS_URL/self-service/login/flows?id=$FLOW_ID" | grep -o '"method":"[^"]*' | sort | uniq
else
  echo "❌ Failed to create login flow. Response:"
  echo "$FLOW_RESPONSE"
fi

echo -e "\n🔍 Testing browser flow (this opens a browser window)..."
open "$KRATOS_URL/self-service/login/browser"

echo -e "\n📋 Additional diagnostic information:"
echo "1. Check if Kratos is running: docker ps | grep kratos"
echo "2. Check Kratos logs: docker logs \$(docker ps | grep kratos | awk '{print \$1}')"
echo "3. Verify CORS settings in kratos/main.kratos.yml"
echo "4. Try directly accessing Kratos health endpoint in your browser:"
echo "   $KRATOS_URL/health/ready"
echo "   (accept any certificate warnings)"
echo "5. Check frontend environment variables:"
echo "   cat frontend/public/env.js"

echo -e "\n💡 If the issue persists, try running the fix script:"
echo "   ./fix-auth-debug.sh"