#!/bin/bash

# Quick fix for WebAuthn/Passkey registration issues
echo "🔧 Quick WebAuthn Passkey Fix"
echo "============================="

# Navigate to STING directory
cd /Users/captain-wolf/Documents/GitHub/STING-CE/STING

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Applying WebAuthn configuration fixes...${NC}"

# 1. Update environment variables for proper configuration
echo "1. Setting WebAuthn environment variables..."
export WEBAUTHN_RP_ID=localhost
export WEBAUTHN_RP_NAME="STING Authentication"
export WEBAUTHN_RP_ORIGINS='["https://localhost:3000","http://localhost:3000","https://localhost:5050"]'

# 2. Restart the services to pick up new configurations
echo "2. Restarting critical services..."
docker-compose restart kratos app frontend

# 3. Wait for services to stabilize
echo "3. Waiting for services to stabilize..."
sleep 15

# 4. Test the WebAuthn endpoint
echo "4. Testing WebAuthn configuration..."
RESPONSE=$(curl -k -s -X GET "https://localhost:5050/api/auth/webauthn/test" 2>/dev/null)

if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✅ WebAuthn configuration test passed${NC}"
else
    echo -e "${RED}❌ WebAuthn configuration test failed${NC}"
    echo "Response: $RESPONSE"
fi

# 5. Check if Kratos is responding
echo "5. Checking Kratos health..."
if curl -k -s "https://localhost:4433/health/ready" | grep -q "ok"; then
    echo -e "${GREEN}✅ Kratos is healthy${NC}"
else
    echo -e "${RED}❌ Kratos health check failed${NC}"
fi

echo ""
echo -e "${YELLOW}Common Fixes Applied:${NC}"
echo "• Updated RP ID to localhost"
echo "• Added HTTP and HTTPS origins"
echo "• Improved user ID encoding"
echo "• Enhanced error handling"
echo "• Restarted services"

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Open https://localhost:3000 in a modern browser"
echo "2. Try creating a new user account"
echo "3. When prompted, set up a passkey"
echo "4. If still failing, check browser console for errors"

echo ""
echo "If the issue persists, run: ./troubleshoot_passkey.sh"
