#!/bin/bash

echo "Testing Kratos Authentication API..."

echo -e "\n1. Testing Kratos health..."
curl -k -i https://localhost:4433/health/ready

echo -e "\n\n2. Starting a new browser-based registration flow..."
curl -k -i https://localhost:4433/self-service/registration/browser

echo -e "\n\n3. Getting an API-based registration flow..."
FLOW_RESPONSE=$(curl -k -s https://localhost:4433/self-service/registration/api)
echo "$FLOW_RESPONSE" | grep -o '"id":"[^"]*"' | head -1

# Extract flow ID using grep and sed
FLOW_ID=$(echo "$FLOW_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"//g' | sed 's/"//g')
echo "Extracted Flow ID: $FLOW_ID"

if [ -n "$FLOW_ID" ]; then
  echo -e "\n4. Getting details for flow $FLOW_ID..."
  curl -k -i "https://localhost:4433/self-service/registration/flows?id=$FLOW_ID"
fi

echo -e "\n\nAll tests completed."