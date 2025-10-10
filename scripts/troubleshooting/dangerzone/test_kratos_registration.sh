#!/bin/bash
#
# Kratos Registration and Login Flow Test Script
#
# This script tests the Kratos registration and login flows using curl.
# It performs the following steps:
# 1. Verifies Kratos is running by checking its API version
# 2. Initializes a registration flow
# 3. Examines the registration flow details
# 4. Submits a test registration with test credentials
# 5. Verifies the registration in the admin API
# 6. Tests login with the newly created user
#
# Usage: ./test_kratos_registration.sh
#
# Requirements:
# - curl
# - jq (recommended for JSON formatting)
#
set -e

KRATOS_PUBLIC_URL="https://localhost:4433"
KRATOS_ADMIN_URL="http://localhost:4434"

# Create a unique test user email
TEST_EMAIL="test-user-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"

# Skip SSL verification for local testing
CURL_OPTS="-k"

# Use jq if available, or cat if not
if command -v jq &> /dev/null; then
    FORMAT_JSON="jq"
else
    echo "jq not found, using cat instead. Install jq for better JSON formatting."
    FORMAT_JSON="cat"
fi

# Clean up any previous test files
rm -f cookies.txt flow_response.json

echo "Testing Kratos registration with email: $TEST_EMAIL"

echo "=== Step 1: Check if Kratos is responding by getting API version ==="
curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/version" | $FORMAT_JSON

echo -e "\n=== Step 2: Initialize a registration flow ==="
FLOW_RESPONSE=$(curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/self-service/registration/browser" \
    -H "Accept: application/json" \
    --cookie-jar cookies.txt \
    --cookie cookies.txt)

echo $FLOW_RESPONSE | $FORMAT_JSON > flow_response.json
FLOW_ID=$(echo $FLOW_RESPONSE | jq -r '.id')
CSRF_TOKEN=$(echo $FLOW_RESPONSE | jq -r '.ui.nodes[] | select(.attributes.name=="csrf_token") | .attributes.value')

echo -e "\nFlow ID: $FLOW_ID"
echo -e "CSRF Token: $CSRF_TOKEN"

echo -e "\n=== Step 3: Examine the registration flow details ==="
curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/self-service/registration/flows?id=${FLOW_ID}" \
    -H "Accept: application/json" \
    --cookie-jar cookies.txt \
    --cookie cookies.txt | $FORMAT_JSON

echo -e "\n=== Step 4: Submit a test registration ==="
curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/self-service/registration?flow=${FLOW_ID}" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    --cookie-jar cookies.txt \
    --cookie cookies.txt \
    -d "{
        \"csrf_token\": \"${CSRF_TOKEN}\",
        \"method\": \"password\",
        \"password\": \"$TEST_PASSWORD\",
        \"traits\": {
            \"email\": \"$TEST_EMAIL\"
        }
    }" | $FORMAT_JSON

echo -e "\n=== Step 5: Verify registration in admin API ==="
curl $CURL_OPTS -v "${KRATOS_ADMIN_URL}/identities" \
    -H "Accept: application/json" | $FORMAT_JSON | grep -A 10 "$TEST_EMAIL" || echo "User not found in identities list"

echo -e "\n=== Step 6: Try to login with the newly created user ==="
echo "Initializing login flow for: $TEST_EMAIL"
LOGIN_FLOW_RESPONSE=$(curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/self-service/login/browser" \
    -H "Accept: application/json" \
    --cookie-jar login_cookies.txt \
    --cookie login_cookies.txt)

LOGIN_FLOW_ID=$(echo $LOGIN_FLOW_RESPONSE | jq -r '.id')
LOGIN_CSRF_TOKEN=$(echo $LOGIN_FLOW_RESPONSE | jq -r '.ui.nodes[] | select(.attributes.name=="csrf_token") | .attributes.value')

echo -e "\nLogin Flow ID: $LOGIN_FLOW_ID"
echo -e "Login CSRF Token: $LOGIN_CSRF_TOKEN"

echo -e "\nAttempting login with created user..."
curl $CURL_OPTS -v "${KRATOS_PUBLIC_URL}/self-service/login?flow=${LOGIN_FLOW_ID}" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    --cookie-jar login_cookies.txt \
    --cookie login_cookies.txt \
    -d "{
        \"csrf_token\": \"${LOGIN_CSRF_TOKEN}\",
        \"method\": \"password\",
        \"password\": \"$TEST_PASSWORD\",
        \"password_identifier\": \"$TEST_EMAIL\"
    }" | $FORMAT_JSON

echo -e "\nDone testing Kratos registration and login flow"