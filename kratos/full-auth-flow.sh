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

# Generate unique test user for this run
TIMESTAMP=$(date +%s)
TEST_EMAIL="test_${TIMESTAMP}@example.com"
TEST_PASSWORD="Password123!"

echo -e "${BLUE}=== Complete Kratos Authentication Flow Test ===${NC}"
echo -e "${YELLOW}Using test email: ${TEST_EMAIL}${NC}"

# Step 1: Get a browser registration flow (this will set cookies)
echo -e "\n${BLUE}=== Step 1: Initializing browser registration flow ===${NC}"
REGISTER_RESPONSE=$(curl -k -v "${KRATOS_URL}/self-service/registration/browser" 2>&1)
REGISTER_FLOW_URL=$(echo "$REGISTER_RESPONSE" | grep -o 'Location: [^"\r]*' | tail -1 | sed 's/Location: //' | tr -d '\r')
REGISTER_FLOW_ID=$(echo "$REGISTER_FLOW_URL" | grep -o 'flow=[^&\r]*' | sed 's/flow=//' | tr -d '\r')

if [[ -z "$REGISTER_FLOW_ID" ]]; then
  echo -e "${RED}❌ Failed to get registration flow ID${NC}"
  echo -e "${YELLOW}Full Response:${NC}"
  echo "$REGISTER_RESPONSE" | grep -A 10 "< HTTP"
  exit 1
else
  echo -e "${GREEN}✓ Got registration flow ID: ${REGISTER_FLOW_ID}${NC}"
  echo -e "${YELLOW}Redirect URL: ${REGISTER_FLOW_URL}${NC}"
fi

# Extract cookies
CSRF_COOKIE=$(echo "$REGISTER_RESPONSE" | grep -o 'Set-Cookie: csrf_token[^;]*' | sed 's/Set-Cookie: //' | tr -d '\r')
echo -e "${YELLOW}CSRF Cookie: ${CSRF_COOKIE}${NC}"

# Step 2: Get registration form with flow ID
echo -e "\n${BLUE}=== Step 2: Getting registration form details ===${NC}"
FORM_RESPONSE=$(curl -k -s -H "Cookie: ${CSRF_COOKIE}" "${KRATOS_URL}/self-service/registration/flows?id=${REGISTER_FLOW_ID}")
CSRF_TOKEN=$(echo "$FORM_RESPONSE" | grep -o '"csrf_token","value":"[^"]*"' | cut -d'"' -f6)
UI_ACTION=$(echo "$FORM_RESPONSE" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)

echo -e "${YELLOW}CSRF Token: ${CSRF_TOKEN}${NC}"
echo -e "${YELLOW}Form action URL: ${UI_ACTION}${NC}"

# Show available registration methods
METHODS=$(echo "$FORM_RESPONSE" | grep -o '"method","type":"submit","value":"[^"]*"' | grep -o 'value":"[^"]*"' | cut -d'"' -f3)
echo -e "${YELLOW}Available registration methods:${NC}"
if [[ -z "$METHODS" ]]; then
  echo -e "${RED}No registration methods found${NC}"
else
  echo "$METHODS" | while read method; do
    echo -e "  - ${method}"
  done
fi

# Step 3: Create registration data
echo -e "\n${BLUE}=== Step 3: Creating registration payload ===${NC}"
# Use the first available method or profile as fallback
METHOD=$(echo "$METHODS" | head -1 || echo "profile")

echo -e "${YELLOW}Using method: ${METHOD}${NC}"

# Create registration payload
REGISTER_DATA=$(cat <<EOF
{
  "method": "${METHOD}",
  "csrf_token": "${CSRF_TOKEN}",
  "traits": {
    "email": "${TEST_EMAIL}"
  }
}
EOF
)

echo -e "${YELLOW}Registration payload: ${REGISTER_DATA}${NC}"

# Step 4: Submit registration
echo -e "\n${BLUE}=== Step 4: Submitting registration ===${NC}"
REGISTER_RESULT=$(curl -k -v -X POST \
  -H "Cookie: ${CSRF_COOKIE}" \
  -H "Content-Type: application/json" \
  -d "${REGISTER_DATA}" \
  "${KRATOS_URL}${UI_ACTION}" 2>&1)

# Check registration status
HTTP_STATUS=$(echo "$REGISTER_RESULT" | grep -o "< HTTP/[0-9.]* [0-9]*" | tail -1 | awk '{print $3}')
echo -e "${YELLOW}HTTP Status: ${HTTP_STATUS}${NC}"

if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "302" ]]; then
  echo -e "${GREEN}✓ Registration successful!${NC}"
  # Extract session cookie or redirect
  SESSION_COOKIE=$(echo "$REGISTER_RESULT" | grep -o "Set-Cookie: ory_kratos_session[^;]*" || echo "No session cookie found")
  if [[ "$SESSION_COOKIE" != "No session cookie found" ]]; then
    SESSION_COOKIE=${SESSION_COOKIE#"Set-Cookie: "}
    echo -e "${GREEN}Session cookie: ${SESSION_COOKIE}${NC}"
  fi
  
  # Update CSRF cookie
  NEW_CSRF_COOKIE=$(echo "$REGISTER_RESULT" | grep -o 'Set-Cookie: csrf_token[^;]*' | sed 's/Set-Cookie: //' | tr -d '\r')
  if [[ -n "$NEW_CSRF_COOKIE" ]]; then
    CSRF_COOKIE="$NEW_CSRF_COOKIE"
    echo -e "${GREEN}Updated CSRF cookie: ${CSRF_COOKIE}${NC}"
  fi
else
  echo -e "${RED}❌ Registration failed with status ${HTTP_STATUS}${NC}"
  echo -e "${YELLOW}Response details:${NC}"
  echo "$REGISTER_RESULT" | grep -A 20 "< HTTP" | head -25
  exit 1
fi

# Step 5: Initiate login flow
echo -e "\n${BLUE}=== Step 5: Initializing login flow ===${NC}"
LOGIN_RESPONSE=$(curl -k -v "${KRATOS_URL}/self-service/login/browser" 2>&1)
LOGIN_FLOW_URL=$(echo "$LOGIN_RESPONSE" | grep -o 'Location: [^"\r]*' | tail -1 | sed 's/Location: //' | tr -d '\r')
LOGIN_FLOW_ID=$(echo "$LOGIN_FLOW_URL" | grep -o 'flow=[^&\r]*' | sed 's/flow=//' | tr -d '\r')

if [[ -z "$LOGIN_FLOW_ID" ]]; then
  echo -e "${RED}❌ Failed to get login flow ID${NC}"
  echo -e "${YELLOW}Login Response:${NC}"
  echo "$LOGIN_RESPONSE" | grep -A 10 "< HTTP"
  exit 1
else
  echo -e "${GREEN}✓ Got login flow ID: ${LOGIN_FLOW_ID}${NC}"
  echo -e "${YELLOW}Login flow URL: ${LOGIN_FLOW_URL}${NC}"
fi

# Update CSRF cookie
NEW_CSRF_COOKIE=$(echo "$LOGIN_RESPONSE" | grep -o 'Set-Cookie: csrf_token[^;]*' | sed 's/Set-Cookie: //' | tr -d '\r')
if [[ -n "$NEW_CSRF_COOKIE" ]]; then
  CSRF_COOKIE="$NEW_CSRF_COOKIE"
  echo -e "${GREEN}Updated CSRF cookie: ${CSRF_COOKIE}${NC}"
fi

# Step 6: Get login form
echo -e "\n${BLUE}=== Step 6: Getting login form details ===${NC}"
LOGIN_FORM=$(curl -k -s -H "Cookie: ${CSRF_COOKIE}" "${KRATOS_URL}/self-service/login/flows?id=${LOGIN_FLOW_ID}")
LOGIN_CSRF_TOKEN=$(echo "$LOGIN_FORM" | grep -o '"csrf_token","value":"[^"]*"' | cut -d'"' -f6)
LOGIN_ACTION=$(echo "$LOGIN_FORM" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)

echo -e "${YELLOW}Login CSRF token: ${LOGIN_CSRF_TOKEN}${NC}"
echo -e "${YELLOW}Login action URL: ${LOGIN_ACTION}${NC}"

# Check for password method
LOGIN_METHODS=$(echo "$LOGIN_FORM" | grep -o '"method","type":"submit","value":"[^"]*"' | grep -o 'value":"[^"]*"' | cut -d'"' -f3)
echo -e "${YELLOW}Available login methods:${NC}"
if [[ -z "$LOGIN_METHODS" ]]; then
  echo -e "${RED}No login methods found${NC}"
else
  echo "$LOGIN_METHODS" | while read method; do
    echo -e "  - ${method}"
  done
fi

# Step 7: Submit login
echo -e "\n${BLUE}=== Step 7: Submitting login request ===${NC}"
LOGIN_METHOD=$(echo "$LOGIN_METHODS" | head -1 || echo "password")
echo -e "${YELLOW}Using login method: ${LOGIN_METHOD}${NC}"

# Create login payload
LOGIN_DATA=$(cat <<EOF
{
  "method": "${LOGIN_METHOD}",
  "csrf_token": "${LOGIN_CSRF_TOKEN}",
  "password": "${TEST_PASSWORD}",
  "identifier": "${TEST_EMAIL}"
}
EOF
)

echo -e "${YELLOW}Login payload: ${LOGIN_DATA}${NC}"

# Submit login request
LOGIN_RESULT=$(curl -k -v -X POST \
  -H "Cookie: ${CSRF_COOKIE}" \
  -H "Content-Type: application/json" \
  -d "${LOGIN_DATA}" \
  "${KRATOS_URL}${LOGIN_ACTION}" 2>&1)

# Check login result
LOGIN_STATUS=$(echo "$LOGIN_RESULT" | grep -o "< HTTP/[0-9.]* [0-9]*" | tail -1 | awk '{print $3}')
echo -e "${YELLOW}Login Status: ${LOGIN_STATUS}${NC}"

if [[ "$LOGIN_STATUS" == "200" || "$LOGIN_STATUS" == "302" ]]; then
  echo -e "${GREEN}✓ Login successful!${NC}"
  
  # Extract session cookie
  SESSION_COOKIE=$(echo "$LOGIN_RESULT" | grep -o "Set-Cookie: ory_kratos_session[^;]*" || echo "No session cookie found")
  if [[ "$SESSION_COOKIE" != "No session cookie found" ]]; then
    SESSION_COOKIE=${SESSION_COOKIE#"Set-Cookie: "}
    echo -e "${GREEN}Session cookie: ${SESSION_COOKIE}${NC}"
  fi
  
  # Extract redirect URL
  REDIRECT_URL=$(echo "$LOGIN_RESULT" | grep -o "Location: [^ \r]*" | sed 's/Location: //' | tr -d '\r' || echo "No redirect found")
  if [[ "$REDIRECT_URL" != "No redirect found" ]]; then
    echo -e "${GREEN}Redirect URL: ${REDIRECT_URL}${NC}"
  fi
else
  echo -e "${RED}❌ Login failed with status ${LOGIN_STATUS}${NC}"
  
  # Extract error message
  ERROR_MESSAGE=$(echo "$LOGIN_RESULT" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
  if [[ -n "$ERROR_MESSAGE" ]]; then
    echo -e "${RED}Error message: ${ERROR_MESSAGE}${NC}"
  fi
  
  echo -e "${YELLOW}Response details:${NC}"
  echo "$LOGIN_RESULT" | grep -A 25 "< HTTP" | head -30
fi

echo -e "\n${BLUE}=== Authentication flow test completed ===${NC}"