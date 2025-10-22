#!/bin/bash

# Test OTP Passwordless Authentication Flow
# This script tests the email/SMS OTP login flow with proper CSRF handling

KRATOS_URL="https://localhost:4433"
EMAIL="test@example.com"
PHONE="+12125551234"
COOKIE_JAR="/tmp/kratos-cookies.txt"

echo "=== Testing OTP Passwordless Authentication ==="
echo ""

# Clean up old cookies
rm -f $COOKIE_JAR

# Step 1: Initialize login flow with cookie support
echo "1. Initializing login flow..."
FLOW_RESPONSE=$(curl -k -s -c $COOKIE_JAR -X GET \
  "${KRATOS_URL}/self-service/login/api" \
  -H "Accept: application/json")

FLOW_ID=$(echo $FLOW_RESPONSE | jq -r '.id')
echo "   Flow ID: $FLOW_ID"

# Extract CSRF token from the flow response
CSRF_TOKEN=$(echo $FLOW_RESPONSE | jq -r '.ui.nodes[] | select(.attributes.name == "csrf_token") | .attributes.value')
echo "   CSRF Token: ${CSRF_TOKEN:0:20}..."

# Step 2: Request OTP code with CSRF token
echo ""
echo "2. Requesting OTP code for email: $EMAIL"
LOGIN_RESPONSE=$(curl -k -s -b $COOKIE_JAR -c $COOKIE_JAR -X POST \
  "${KRATOS_URL}/self-service/login/flows/${FLOW_ID}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{
    \"method\": \"code\",
    \"identifier\": \"$EMAIL\",
    \"csrf_token\": \"$CSRF_TOKEN\"
  }")

echo "   Response:"
echo $LOGIN_RESPONSE | jq '.'

# Check if code method is available
if echo $LOGIN_RESPONSE | jq -e '.error' > /dev/null; then
  ERROR_MSG=$(echo $LOGIN_RESPONSE | jq -r '.error.message // .error.reason // "Unknown error"')
  
  # Check if it's because code method is not configured
  if echo $LOGIN_RESPONSE | grep -q "code"; then
    echo ""
    echo "⚠️  The 'code' method might not be available in this flow."
    echo "   Let's check available methods..."
    echo ""
    echo "Available authentication methods:"
    echo $FLOW_RESPONSE | jq -r '.ui.nodes[] | select(.group != "default") | .group' | sort | uniq
  else
    echo "   ✗ Error: $ERROR_MSG"
  fi
else
  echo "   ✓ OTP code sent successfully!"
  echo ""
  echo "📧 Check your email at: http://localhost:8025"
  echo ""
  echo "3. To complete login, enter the code from your email:"
  echo "   curl -k -b $COOKIE_JAR -X POST '${KRATOS_URL}/self-service/login/flows/${FLOW_ID}' \\"
  echo "     -H 'Accept: application/json' \\"
  echo "     -H 'Content-Type: application/json' \\"
  echo "     -d '{\"method\": \"code\", \"code\": \"YOUR_CODE_HERE\", \"csrf_token\": \"$CSRF_TOKEN\"}'"
fi

echo ""
echo "=== Checking Authentication Methods Configuration ==="
echo ""

# Check if code method is enabled in Kratos config
echo "Checking Kratos configuration..."
if docker exec sting-ce-kratos grep -q "code:" /etc/config/kratos/kratos.yml; then
  echo "✓ Code method is configured in kratos.yml"
else
  echo "✗ Code method is NOT configured in kratos.yml"
fi

echo ""
echo "=== Testing Traditional Password Login ==="
echo ""

# Test traditional password login to verify Kratos is working
echo "Creating test login flow..."
TEST_FLOW=$(curl -k -s -c $COOKIE_JAR -X GET \
  "${KRATOS_URL}/self-service/login/api" \
  -H "Accept: application/json")

echo "Available methods in login flow:"
echo $TEST_FLOW | jq -r '.ui.nodes[] | select(.attributes.name == "method") | .attributes.value' | sort | uniq

# Clean up
rm -f $COOKIE_JAR

echo ""
echo "✓ Test completed"