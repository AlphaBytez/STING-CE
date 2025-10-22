#!/bin/bash
# test_manual_verification.sh - Test manual email verification flow

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "Testing Manual Email Verification Flow"
echo "======================================"

# 1. Clear mailpit
echo -e "${YELLOW}Clearing mailpit messages...${NC}"
curl -s -X DELETE http://localhost:8025/api/v1/messages

# 2. Get a verification flow
echo -e "\n${YELLOW}Creating verification flow...${NC}"
FLOW_RESPONSE=$(curl -s -k -L -H "Accept: application/json" \
  https://localhost:4433/self-service/verification/browser)

# Check if flow creation was successful
if echo "$FLOW_RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    echo -e "${RED}Error creating verification flow:${NC}"
    echo "$FLOW_RESPONSE" | jq '.error'
    exit 1
fi

# Extract flow ID from redirect URL or response
if echo "$FLOW_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
    FLOW_ID=$(echo "$FLOW_RESPONSE" | jq -r '.id')
    echo -e "${GREEN}✓ Flow created: $FLOW_ID${NC}"
else
    echo -e "${RED}Could not extract flow ID${NC}"
    echo "Response: $FLOW_RESPONSE"
    exit 1
fi

# 3. Get CSRF token from flow
CSRF_TOKEN=$(echo "$FLOW_RESPONSE" | jq -r '.ui.nodes[] | select(.attributes.name == "csrf_token") | .attributes.value')
echo -e "CSRF Token: ${CSRF_TOKEN:0:20}..."

# 4. Submit email for verification
EMAIL="manualtest$(date +%s)@example.com"
echo -e "\n${YELLOW}Requesting verification for: $EMAIL${NC}"

VERIFY_RESPONSE=$(curl -s -k -X POST \
  "https://localhost:4433/self-service/verification?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -d "method=code&email=$EMAIL&csrf_token=$CSRF_TOKEN")

echo "Verification response:"
echo "$VERIFY_RESPONSE" | jq '.'

# 4. Check for success messages
if echo "$VERIFY_RESPONSE" | jq -e '.ui.messages[] | select(.type == "info")' >/dev/null 2>&1; then
    echo -e "\n${GREEN}✓ Verification request submitted successfully${NC}"
    INFO_MSG=$(echo "$VERIFY_RESPONSE" | jq -r '.ui.messages[] | select(.type == "info") | .text')
    echo "Message: $INFO_MSG"
else
    echo -e "\n${RED}✗ No success message found${NC}"
fi

# 5. Wait and check mailpit
echo -e "\n${YELLOW}Waiting for email...${NC}"
sleep 3

EMAILS=$(curl -s http://localhost:8025/api/v1/messages)
EMAIL_COUNT=$(echo "$EMAILS" | jq '.total')

echo -e "Emails in mailpit: ${BLUE}$EMAIL_COUNT${NC}"

if [ "$EMAIL_COUNT" -gt 0 ]; then
    echo -e "\n${GREEN}✓ Verification email sent!${NC}"
    echo "$EMAILS" | jq '.messages[] | {
        to: .To[0].Address,
        subject: .Subject,
        snippet: .Snippet,
        created: .Created
    }'
    
    # Extract verification link if present
    MESSAGE_ID=$(echo "$EMAILS" | jq -r '.messages[0].ID')
    MESSAGE_BODY=$(curl -s http://localhost:8025/api/v1/messages/$MESSAGE_ID)
    
    echo -e "\n${YELLOW}Email body preview:${NC}"
    echo "$MESSAGE_BODY" | jq -r '.Text' | head -20
else
    echo -e "\n${RED}✗ No verification email sent${NC}"
fi

# 6. Check Kratos logs
echo -e "\n${YELLOW}Recent Kratos courier logs:${NC}"
docker logs sting-ce-kratos --tail 30 2>&1 | grep -i "courier\|smtp\|email\|verify" | tail -10 || echo "No relevant logs"

# 7. Check courier messages in DB
echo -e "\n${YELLOW}Courier messages in database:${NC}"
docker exec sting-ce-db psql -U postgres -d sting_app -c "
SELECT id, status, recipient, subject, created_at 
FROM courier_messages 
WHERE recipient LIKE '%$EMAIL%' OR recipient LIKE '%manual%'
ORDER BY created_at DESC 
LIMIT 5;" 2>/dev/null || echo "Could not query courier messages"

echo -e "\n${BLUE}Summary:${NC}"
echo "- Email requested: $EMAIL"
echo "- Flow ID: $FLOW_ID"
echo "- Emails sent: $EMAIL_COUNT"