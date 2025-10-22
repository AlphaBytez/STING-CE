#!/bin/bash
# test_email_verification.sh - Test email verification flow

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing Email Verification Flow"
echo "==============================="

# 1. Clear mailpit messages
echo -e "${YELLOW}Clearing mailpit messages...${NC}"
curl -s -X DELETE http://localhost:8025/api/v1/messages

# 2. Create a new user with unique email
EMAIL="verifytest$(date +%s)@example.com"
echo -e "${YELLOW}Creating user with email: $EMAIL${NC}"

# Get registration flow
FLOW_ID=$(curl -s -k https://localhost:4433/self-service/registration/api | jq -r '.id')

# Submit profile
curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "method=profile&traits.email=$EMAIL&traits.name.first=Verify&traits.name.last=Test" > /dev/null

# Complete registration
RESPONSE=$(curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "method=password&password=VerifyTest123!&traits.email=$EMAIL&traits.name.first=Verify&traits.name.last=Test")

IDENTITY_ID=$(echo $RESPONSE | jq -r '.identity.id')
SESSION_TOKEN=$(echo $RESPONSE | jq -r '.session_token')

echo -e "${GREEN}✓ User created successfully${NC}"
echo "  Identity ID: $IDENTITY_ID"
echo "  Session Token: ${SESSION_TOKEN:0:20}..."

# 3. Check verification status
echo -e "\n${YELLOW}Checking verification status...${NC}"
VERIFY_STATUS=$(curl -s -k https://localhost:4434/admin/identities/$IDENTITY_ID | jq -r '.verifiable_addresses[0].verified')
echo "  Verified: $VERIFY_STATUS"

# 4. Wait and check for emails
echo -e "\n${YELLOW}Waiting for emails...${NC}"
sleep 3

# Check mailpit
EMAILS=$(curl -s http://localhost:8025/api/v1/messages | jq '.total')
echo "  Emails in mailpit: $EMAILS"

if [ "$EMAILS" -gt 0 ]; then
    echo -e "\n${GREEN}✓ Verification emails found!${NC}"
    curl -s http://localhost:8025/api/v1/messages | jq '.messages[] | {to: .To[0].Address, subject: .Subject, snippet: .Snippet}'
else
    echo -e "\n${RED}✗ No verification emails sent${NC}"
    
    # Try to manually trigger verification
    echo -e "\n${YELLOW}Attempting manual verification trigger...${NC}"
    
    # Check if we can create a verification flow
    echo "Checking verification endpoint..."
    curl -v -k https://localhost:4433/self-service/verification/browser 2>&1 | grep -E "(HTTP|Location)"
fi

# 5. Check Kratos courier logs
echo -e "\n${YELLOW}Recent Kratos courier logs:${NC}"
docker logs sting-ce-kratos --tail 20 2>&1 | grep -i "courier\|smtp\|email\|verify" || echo "No relevant logs found"

# 6. Check courier messages in database
echo -e "\n${YELLOW}Checking courier messages in database:${NC}"
docker exec sting-ce-db psql -U postgres -d kratos -c "SELECT id, status, subject, created_at FROM courier_messages ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "Could not query courier messages"

echo -e "\n${YELLOW}Summary:${NC}"
echo "- User created: $EMAIL"
echo "- Verification status: $VERIFY_STATUS"
echo "- Emails sent: $EMAILS"
echo ""
echo "To view Mailpit UI: http://localhost:8025"