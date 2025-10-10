#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

KRATOS_URL="https://localhost:4433"
FRONTEND_URL="https://localhost:3000"

# Test user credentials
TEST_EMAIL="test@example.com"
TEST_PASSWORD="password"

echo -e "${BLUE}=== Testing Kratos Browser Login Flow ===${NC}"
echo -e "${YELLOW}Using test email: ${TEST_EMAIL}${NC}"

# Step 1: Initialize browser login flow to get the flow ID
echo -e "\n${BLUE}=== Step 1: Initializing browser login flow ===${NC}"
LOGIN_RESPONSE=$(curl -k -v "${KRATOS_URL}/self-service/login/browser" 2>&1)
LOGIN_FLOW_URL=$(echo "$LOGIN_RESPONSE" | grep -o 'Location: [^"]*' | tail -1 | sed 's/Location: //')
LOGIN_FLOW_ID=$(echo "$LOGIN_FLOW_URL" | grep -o 'flow=[^&]*' | sed 's/flow=//')

if [[ -z "$LOGIN_FLOW_ID" ]]; then
  echo -e "${RED}❌ Failed to get login flow ID from redirect${NC}"
  echo -e "${YELLOW}Browser Response:${NC}"
  echo "$LOGIN_RESPONSE" | grep -A 10 "< HTTP"
else
  echo -e "${GREEN}✓ Got login flow ID: ${LOGIN_FLOW_ID}${NC}"
  echo -e "${YELLOW}Redirect URL: ${LOGIN_FLOW_URL}${NC}"
fi

# Extract the CSRF cookie
CSRF_COOKIE=$(echo "$LOGIN_RESPONSE" | grep -o 'Set-Cookie: csrf_token_[^;]*' | sed 's/Set-Cookie: //')
echo -e "${YELLOW}CSRF Cookie: ${CSRF_COOKIE}${NC}"

# Step 2: Get login form
echo -e "\n${BLUE}=== Step 2: Getting login form ===${NC}"
FORM_RESPONSE=$(curl -k -s -H "Cookie: ${CSRF_COOKIE}" "${KRATOS_URL}/self-service/login/flows?id=${LOGIN_FLOW_ID}")
CSRF_TOKEN=$(echo "$FORM_RESPONSE" | grep -o '"csrf_token","value":"[^"]*"' | cut -d'"' -f6)
UI_ACTION=$(echo "$FORM_RESPONSE" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)

echo -e "${YELLOW}CSRF Token: ${CSRF_TOKEN}${NC}"
echo -e "${YELLOW}Form action URL: ${UI_ACTION}${NC}"

# Check if password method is available
PASSWORD_METHOD=$(echo "$FORM_RESPONSE" | grep -o '"method","type":"submit","value":"password"' || echo "Not found")
if [[ "$PASSWORD_METHOD" == "Not found" ]]; then
  echo -e "${RED}❌ Password method not available in form${NC}"
  echo -e "${YELLOW}Available methods:${NC}"
  echo "$FORM_RESPONSE" | grep -o '"method","type":"submit","value":"[^"]*"' | grep -o 'value":"[^"]*"' | cut -d'"' -f3 || echo "None"
else
  echo -e "${GREEN}✓ Password method is available${NC}"
fi

# Step 3: Prepare login data
echo -e "\n${BLUE}=== Step 3: Preparing login data ===${NC}"
LOGIN_DATA=$(cat <<EOF
{
  "method": "password",
  "csrf_token": "${CSRF_TOKEN}",
  "password": "${TEST_PASSWORD}",
  "identifier": "${TEST_EMAIL}"
}
EOF
)

echo -e "${YELLOW}Login data: ${LOGIN_DATA}${NC}"

# Step 4: Submit login
echo -e "\n${BLUE}=== Step 4: Submitting login ===${NC}"
LOGIN_RESULT=$(curl -k -v -X POST \
  -H "Cookie: ${CSRF_COOKIE}" \
  -H "Content-Type: application/json" \
  -d "${LOGIN_DATA}" \
  "${KRATOS_URL}${UI_ACTION}" 2>&1)

# Extract response status code
HTTP_STATUS=$(echo "$LOGIN_RESULT" | grep -o "< HTTP/[0-9.]* [0-9]*" | tail -1 | awk '{print $3}')
echo -e "${YELLOW}HTTP Status: ${HTTP_STATUS}${NC}"

if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "302" ]]; then
  echo -e "${GREEN}✓ Login successful!${NC}"
  
  # Check for session cookie or redirect
  SESSION_COOKIE=$(echo "$LOGIN_RESULT" | grep -o "Set-Cookie: ory_kratos_session[^;]*" || echo "No session cookie found")
  if [[ "$SESSION_COOKIE" != "No session cookie found" ]]; then
    SESSION_COOKIE=${SESSION_COOKIE#"Set-Cookie: "}
    echo -e "${GREEN}Session cookie: ${SESSION_COOKIE}${NC}"
  fi
  
  REDIRECT_URL=$(echo "$LOGIN_RESULT" | grep -o "Location: [^ ]*" | sed 's/Location: //' || echo "No redirect found")
  if [[ "$REDIRECT_URL" != "No redirect found" ]]; then
    echo -e "${GREEN}Redirect URL: ${REDIRECT_URL}${NC}"
  fi
else
  echo -e "${RED}❌ Login failed with status code ${HTTP_STATUS}${NC}"
  
  # Try to extract error message
  ERROR_MESSAGE=$(echo "$LOGIN_RESULT" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
  if [[ ! -z "$ERROR_MESSAGE" ]]; then
    echo -e "${RED}Error message: ${ERROR_MESSAGE}${NC}"
  fi
  
  echo -e "${YELLOW}Response details:${NC}"
  echo "$LOGIN_RESULT" | grep -A 20 "< HTTP" | head -25
fi

echo -e "\n${BLUE}=== Login test completed ===${NC}"