#!/bin/bash
# Debug script for Kratos login API

echo "=== KRATOS LOGIN API DEBUGGING ==="
echo ""

# Check Kratos health
echo "1. Checking Kratos health..."
HEALTH_RESULT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4434/admin/health/ready)
if [ "$HEALTH_RESULT" == "200" ]; then
  echo "✅ Kratos health check passed"
else
  echo "❌ Kratos health check failed with status $HEALTH_RESULT"
  echo "   Make sure Kratos is running and accessible."
  exit 1
fi
echo ""

# Initiate login flow
echo "2. Initiating login flow..."
LOGIN_RESPONSE=$(curl -s http://localhost:4433/self-service/login/browser)
if [ -z "$LOGIN_RESPONSE" ]; then
  echo "❌ Failed to get login flow response"
  exit 1
fi

# Extract flow ID
FLOW_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
if [ -z "$FLOW_ID" ]; then
  echo "❌ Failed to extract flow ID from response"
  echo "Response was: $LOGIN_RESPONSE"
  exit 1
fi
echo "✅ Login flow initiated with ID: $FLOW_ID"
echo ""

# Get flow details
echo "3. Fetching flow details..."
FLOW_DETAILS=$(curl -s "http://localhost:4433/self-service/login/flows?id=$FLOW_ID")
if [ -z "$FLOW_DETAILS" ]; then
  echo "❌ Failed to get flow details"
  exit 1
fi
echo "✅ Flow details retrieved"
echo ""

# Test frontend CORS
echo "4. Testing CORS from frontend origin..."
CORS_RESULT=$(curl -s -I -H "Origin: http://localhost:3000" \
  "http://localhost:4433/self-service/login/flows?id=$FLOW_ID" | grep -i "access-control-allow-origin")
if [ -z "$CORS_RESULT" ]; then
  echo "❌ CORS headers not found in response"
  echo "   This may cause frontend access issues"
else
  echo "✅ CORS headers found: $CORS_RESULT"
fi
echo ""

# Summarize results
echo "=== SUMMARY ==="
echo "Kratos API is accessible: $([ "$HEALTH_RESULT" == "200" ] && echo "Yes" || echo "No")"
echo "Login flow creation: $([ -n "$FLOW_ID" ] && echo "Working" || echo "Failed")"
echo "Flow details retrieval: $([ -n "$FLOW_DETAILS" ] && echo "Working" || echo "Failed")"
echo "CORS configuration: $([ -n "$CORS_RESULT" ] && echo "Properly configured" || echo "Issue detected")"
echo ""

# Save debug data
echo "Saving debug data to login-debug-data.json..."
cat > login-debug-data.json << EOF
{
  "timestamp": "$(date)",
  "health_check": {
    "endpoint": "http://localhost:4434/admin/health/ready",
    "status_code": $HEALTH_RESULT
  },
  "login_flow": {
    "flow_id": "$FLOW_ID",
    "raw_response": $LOGIN_RESPONSE
  },
  "flow_details": $FLOW_DETAILS,
  "cors_headers": "$(echo "$CORS_RESULT" | tr -d '\r\n')"
}
EOF

echo "Debug data saved. You can attach this file to support requests."
echo ""
echo "To test the login flow in a browser, visit:"
echo "http://localhost:4433/self-service/login/flows?id=$FLOW_ID"
echo ""
echo "To examine the frontend issue, check the browser console for errors,"
echo "and verify environment variables in ./frontend/.env.local"