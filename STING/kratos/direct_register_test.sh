#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# URLS
KRATOS_PUBLIC_URL="https://localhost:4433"
FRONTEND_URL="https://localhost:3000"

# Test credentials
TIMESTAMP=$(date +%s)
TEST_EMAIL="test${TIMESTAMP}@example.com"
TEST_PASSWORD="Test1234!"

echo -e "${BLUE}=== STING Kratos Registration Test Script ===${NC}"
echo -e "${YELLOW}Testing with email: ${TEST_EMAIL}${NC}"

# Step 1: Check if services are running
echo -e "\n${BLUE}=== Step 1: Checking services ===${NC}"

echo -e "${YELLOW}Checking Kratos health...${NC}"
KRATOS_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" "${KRATOS_PUBLIC_URL}/health/ready" || echo "Connection failed")

if [[ "$KRATOS_RESPONSE" == "200" ]]; then
  echo -e "${GREEN}✓ Kratos is running and healthy${NC}"
else
  echo -e "${RED}❌ Kratos is not responding or unhealthy. Status: ${KRATOS_RESPONSE}${NC}"
  echo -e "${YELLOW}Consider restarting services with:${NC}"
  echo -e "   ./manage_sting.sh restart kratos"
fi

echo -e "${YELLOW}Checking Frontend availability...${NC}"
FRONTEND_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}" || echo "Connection failed")

if [[ "$FRONTEND_RESPONSE" == "200" ]]; then
  echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
  echo -e "${RED}❌ Frontend is not responding. Status: ${FRONTEND_RESPONSE}${NC}"
  echo -e "${YELLOW}Consider restarting services with:${NC}"
  echo -e "   ./manage_sting.sh restart frontend"
fi

# Step 2: Get a registration flow directly from Kratos
echo -e "\n${BLUE}=== Step 2: Getting registration flow from Kratos ===${NC}"
FLOW_RESPONSE=$(curl -k -s "${KRATOS_PUBLIC_URL}/self-service/registration/api")
FLOW_ID=$(echo "$FLOW_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$FLOW_ID" ]]; then
  echo -e "${RED}❌ Failed to get registration flow ID${NC}"
  echo -e "${YELLOW}Kratos response:${NC}"
  echo "$FLOW_RESPONSE" | head -30
  exit 1
else
  echo -e "${GREEN}✓ Got registration flow ID: ${FLOW_ID}${NC}"
fi

# Step 3: Get the registration form details
echo -e "\n${BLUE}=== Step 3: Examining registration form ===${NC}"
FORM_RESPONSE=$(curl -k -s "${KRATOS_PUBLIC_URL}/self-service/registration/flows?id=${FLOW_ID}")
ACTION_URL=$(echo "$FORM_RESPONSE" | grep -o '"action":"[^"]*"' | head -1 | cut -d'"' -f4)
CSRF_TOKEN=$(echo "$FORM_RESPONSE" | grep -o '"csrf_token","value":"[^"]*"' | cut -d'"' -f6)

echo -e "${YELLOW}Form action URL: ${ACTION_URL}${NC}"
echo -e "${YELLOW}CSRF token present: $(if [[ -z "$CSRF_TOKEN" ]]; then echo "No"; else echo "Yes"; fi)${NC}"

# Step 4: Display available form fields
echo -e "\n${BLUE}=== Step 4: Available form fields ===${NC}"
FIELDS=$(echo "$FORM_RESPONSE" | grep -o '"attributes":{"name":"[^"]*"' | grep -o 'name":"[^"]*"' | cut -d'"' -f3)

if [[ -z "$FIELDS" ]]; then
  echo -e "${RED}❌ No form fields found${NC}"
else
  echo -e "${GREEN}Available fields:${NC}"
  echo "$FIELDS" | while read field; do
    echo -e "  - ${field}"
  done
fi

# Step 5: Check available methods
echo -e "\n${BLUE}=== Step 5: Available registration methods ===${NC}"
METHODS=$(echo "$FORM_RESPONSE" | grep -o '"name":"method","type":"submit","value":"[^"]*"' | grep -o 'value":"[^"]*"' | cut -d'"' -f3)

if [[ -z "$METHODS" ]]; then
  echo -e "${RED}❌ No registration methods found${NC}"
  echo -e "${YELLOW}Using 'profile' as default method${NC}"
  METHOD="profile"
else
  echo -e "${GREEN}Available methods:${NC}"
  echo "$METHODS" | while read method; do
    echo -e "  - ${method}"
  done
  
  # Choose the first method
  METHOD=$(echo "$METHODS" | head -1)
  echo -e "${YELLOW}Using method: ${METHOD}${NC}"
fi

# Step 6: Prepare registration payload
echo -e "\n${BLUE}=== Step 6: Preparing registration payload ===${NC}"

if [[ "$METHOD" == "password" ]]; then
  PAYLOAD=$(cat <<EOF
{
  "method": "password",
  "password": "${TEST_PASSWORD}",
  "traits": {
    "email": "${TEST_EMAIL}"
  },
  "csrf_token": "${CSRF_TOKEN}"
}
EOF
)
else
  PAYLOAD=$(cat <<EOF
{
  "method": "${METHOD}",
  "traits": {
    "email": "${TEST_EMAIL}"
  },
  "csrf_token": "${CSRF_TOKEN}"
}
EOF
)
fi

echo -e "${YELLOW}Registration payload:${NC}"
echo "$PAYLOAD" | sed 's/^/  /'

# Step 7: Submit registration
echo -e "\n${BLUE}=== Step 7: Submitting registration ===${NC}"
REGISTER_RESPONSE=$(curl -k -v -X POST \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "${KRATOS_PUBLIC_URL}${ACTION_URL}" 2>&1)

STATUS_CODE=$(echo "$REGISTER_RESPONSE" | grep -o "< HTTP/[0-9.]* [0-9]*" | tail -1 | awk '{print $3}')

if [[ "$STATUS_CODE" == "200" || "$STATUS_CODE" == "302" ]]; then
  echo -e "${GREEN}✓ Registration successful (Status: ${STATUS_CODE})${NC}"
  
  # Check for redirection
  REDIRECT_URL=$(echo "$REGISTER_RESPONSE" | grep -o "Location: [^ ]*" | sed 's/Location: //')
  if [[ ! -z "$REDIRECT_URL" ]]; then
    echo -e "${GREEN}  Redirecting to: ${REDIRECT_URL}${NC}"
  fi
  
  # Check for session cookie
  SESSION_COOKIE=$(echo "$REGISTER_RESPONSE" | grep -o "ory_kratos_session[^;]*")
  if [[ ! -z "$SESSION_COOKIE" ]]; then
    echo -e "${GREEN}  Session cookie set: ${SESSION_COOKIE}${NC}"
  fi
  
  echo -e "\n${GREEN}SUCCESS: Registration completed for ${TEST_EMAIL}${NC}"
  echo -e "${YELLOW}Next steps:${NC}"
  echo -e "  1. Try logging in with these credentials"
  echo -e "  2. Check the user in the database"
else
  echo -e "${RED}❌ Registration failed (Status: ${STATUS_CODE})${NC}"
  
  # Try to extract error messages
  ERROR_MESSAGES=$(echo "$REGISTER_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
  
  if [[ ! -z "$ERROR_MESSAGES" ]]; then
    echo -e "${RED}Error messages:${NC}"
    echo "$ERROR_MESSAGES" | while read message; do
      echo -e "  - ${message}"
    done
  fi
  
  echo -e "${YELLOW}Response details:${NC}"
  echo "$REGISTER_RESPONSE" | grep -A 10 "< HTTP" | head -20
fi

echo -e "\n${BLUE}=== Test completed ===${NC}"