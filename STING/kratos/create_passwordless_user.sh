#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check for email parameter
if [ -z "$1" ]; then
  # Generate a test email if none provided
  TIMESTAMP=$(date +%s)
  TEST_EMAIL="test${TIMESTAMP}@example.com"
  echo -e "${YELLOW}No email provided, using generated email: ${TEST_EMAIL}${NC}"
else
  TEST_EMAIL="$1"
  echo -e "${YELLOW}Using provided email: ${TEST_EMAIL}${NC}"
fi

# URLs
KRATOS_PUBLIC_URL="https://localhost:4433"

echo -e "${BLUE}=== STING Kratos User Registration Script ===${NC}"

# Get browser flow (to get a CSRF token from a cookie)
echo -e "\n${BLUE}=== Step 1: Initializing a browser flow to obtain CSRF cookie ===${NC}"
BROWSER_RESPONSE=$(curl -k -v "${KRATOS_PUBLIC_URL}/self-service/registration/browser" 2>&1)
CSRF_COOKIE=$(echo "$BROWSER_RESPONSE" | grep -o "csrf_token_[^=]*=[^;]*" | head -1)

if [[ -z "$CSRF_COOKIE" ]]; then
  echo -e "${RED}❌ No CSRF cookie found in browser flow${NC}"
else
  echo -e "${GREEN}✓ Got CSRF cookie: ${CSRF_COOKIE}${NC}"
fi

# Initialize an API flow 
echo -e "\n${BLUE}=== Step 2: Initializing API registration flow ===${NC}"
API_RESPONSE=$(curl -k -s -H "Cookie: ${CSRF_COOKIE}" "${KRATOS_PUBLIC_URL}/self-service/registration/api")
FLOW_ID=$(echo "$API_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$FLOW_ID" ]]; then
  echo -e "${RED}❌ Failed to get flow ID${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Got flow ID: ${FLOW_ID}${NC}"
fi

# Get the action URL and available methods
FLOW_DETAILS=$(curl -k -s -H "Cookie: ${CSRF_COOKIE}" "${KRATOS_PUBLIC_URL}/self-service/registration/flows?id=${FLOW_ID}")
ACTION_URL=$(echo "$FLOW_DETAILS" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)
CSRF_TOKEN=$(echo "$FLOW_DETAILS" | grep -o '"name":"csrf_token".*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)

echo -e "${YELLOW}Action URL: ${ACTION_URL}${NC}"
echo -e "${YELLOW}CSRF token from form: ${CSRF_TOKEN:-NONE}${NC}"

# Construct minimal payload
echo -e "\n${BLUE}=== Step 3: Preparing minimal registration payload ===${NC}"
PAYLOAD=$(cat <<EOF
{
  "method": "profile",
  "csrf_token": "${CSRF_TOKEN}",
  "traits": {
    "email": "${TEST_EMAIL}"
  }
}
EOF
)

echo -e "${YELLOW}Registration payload:${NC}"
echo "$PAYLOAD" | sed 's/^/  /'

# Submit registration
echo -e "\n${BLUE}=== Step 4: Submitting registration ===${NC}"
REGISTER_RESPONSE=$(curl -k -v -X POST \
  -H "Content-Type: application/json" \
  -H "Cookie: ${CSRF_COOKIE}" \
  -d "$PAYLOAD" \
  "${KRATOS_PUBLIC_URL}${ACTION_URL}" 2>&1)

HTTP_STATUS=$(echo "$REGISTER_RESPONSE" | grep -o "< HTTP/[0-9.]* [0-9]*" | tail -1 | awk '{print $3}')
echo -e "${YELLOW}HTTP Status: ${HTTP_STATUS}${NC}"

if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "302" ]]; then
  echo -e "${GREEN}✓ Registration successful!${NC}"
  # Extract identity ID if available
  IDENTITY_ID=$(echo "$REGISTER_RESPONSE" | grep -o '"identity":{[^}]*"id":"[^"]*"' | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
  
  if [[ ! -z "$IDENTITY_ID" ]]; then
    echo -e "${GREEN}Created identity ID: ${IDENTITY_ID}${NC}"
  fi
  
  echo -e "\n${GREEN}SUCCESS: User registered with email: ${TEST_EMAIL}${NC}"
else
  echo -e "${RED}❌ Registration failed. Status: ${HTTP_STATUS}${NC}"
  
  # Extract error messages
  ERROR_MESSAGES=$(echo "$REGISTER_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
  
  if [[ ! -z "$ERROR_MESSAGES" ]]; then
    echo -e "${RED}Error messages:${NC}"
    echo "$ERROR_MESSAGES" | sort | uniq | while read message; do
      echo -e "  - ${message}"
    done
  fi
  
  echo -e "${YELLOW}Full response headers:${NC}"
  echo "$REGISTER_RESPONSE" | grep -i "< http\|location\|cookie\|csrf\|error"
fi

echo -e "\n${BLUE}=== Registration attempt completed ===${NC}"