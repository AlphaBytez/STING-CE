#!/bin/bash
# test_verification_api.sh - Test email verification using API endpoints

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "Testing Email Verification via API"
echo "=================================="

# 1. Clear mailpit
echo -e "${YELLOW}Clearing mailpit messages...${NC}"
curl -s -X DELETE http://localhost:8025/api/v1/messages

# 2. Create a test user first (if not exists)
EMAIL="apiverifytest$(date +%s)@example.com"
echo -e "\n${YELLOW}Creating test user with email: $EMAIL${NC}"

# Get registration flow
REG_FLOW=$(curl -s -k https://localhost:4433/self-service/registration/api | jq -r '.id')

# Submit profile
curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$REG_FLOW" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "method=profile&traits.email=$EMAIL&traits.name.first=API&traits.name.last=Test" > /dev/null

# Complete registration
REG_RESPONSE=$(curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$REG_FLOW" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "method=password&password=ApiTest123!&traits.email=$EMAIL&traits.name.first=API&traits.name.last=Test")

IDENTITY_ID=$(echo $REG_RESPONSE | jq -r '.identity.id')
echo -e "${GREEN}✓ User created: $IDENTITY_ID${NC}"

# 3. Create verification flow via API
echo -e "\n${YELLOW}Creating verification flow via API...${NC}"
FLOW_RESPONSE=$(curl -s -k -X GET \
  "https://localhost:4433/self-service/verification/api" \
  -H "Accept: application/json")

if echo "$FLOW_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    echo -e "${RED}Error creating verification flow:${NC}"
    echo "$FLOW_RESPONSE" | jq '.error'
    exit 1
fi

FLOW_ID=$(echo "$FLOW_RESPONSE" | jq -r '.id')
echo -e "${GREEN}✓ Flow created: $FLOW_ID${NC}"

# 4. Submit verification request
echo -e "\n${YELLOW}Submitting verification request...${NC}"
VERIFY_RESPONSE=$(curl -s -k -X POST \
  "https://localhost:4433/self-service/verification?flow=$FLOW_ID" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{\"method\":\"code\",\"email\":\"$EMAIL\"}")

echo "Response:"
echo "$VERIFY_RESPONSE" | jq '.'

# Check if we got the code entry screen
if echo "$VERIFY_RESPONSE" | jq -e '.ui.nodes[] | select(.attributes.name == "code")' >/dev/null 2>&1; then
    echo -e "\n${GREEN}✓ Verification code requested!${NC}"
    echo "The system is now waiting for a verification code to be entered."
fi

# 5. Check mailpit for emails
echo -e "\n${YELLOW}Checking for verification emails...${NC}"
sleep 3

EMAILS=$(curl -s http://localhost:8025/api/v1/messages)
EMAIL_COUNT=$(echo "$EMAILS" | jq '.total')

echo -e "Emails in mailpit: ${BLUE}$EMAIL_COUNT${NC}"

if [ "$EMAIL_COUNT" -gt 0 ]; then
    echo -e "\n${GREEN}✓ Verification email sent!${NC}"
    
    # Show email details
    echo "$EMAILS" | jq '.messages[] | select(.To[0].Address == "'$EMAIL'") | {
        to: .To[0].Address,
        subject: .Subject,
        snippet: .Snippet
    }'
    
    # Extract verification code
    MESSAGE_ID=$(echo "$EMAILS" | jq -r '.messages[] | select(.To[0].Address == "'$EMAIL'") | .ID' | head -1)
    if [ -n "$MESSAGE_ID" ]; then
        MESSAGE=$(curl -s http://localhost:8025/api/v1/messages/$MESSAGE_ID)
        echo -e "\n${YELLOW}Email content:${NC}"
        echo "$MESSAGE" | jq -r '.Text' | grep -E "(code|verification|confirm)" | head -10
    fi
else
    echo -e "\n${RED}✗ No verification email sent${NC}"
fi

# 6. Check database
echo -e "\n${YELLOW}Checking courier messages in database:${NC}"
docker exec sting-ce-db psql -U postgres -d sting_app -c "
SELECT status, recipient, subject, created_at 
FROM courier_messages 
WHERE recipient LIKE '%$EMAIL%'
ORDER BY created_at DESC 
LIMIT 3;" 2>/dev/null || echo "No courier messages found"

echo -e "\n${BLUE}Summary:${NC}"
echo "- User email: $EMAIL"
echo "- Flow ID: $FLOW_ID"
echo "- Emails sent: $EMAIL_COUNT"