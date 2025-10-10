#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}      STING Passkey Authentication Configuration          ${NC}"
echo -e "${BLUE}===========================================================${NC}"

# Stop services
echo -e "${BLUE}Stopping Kratos and Frontend services...${NC}"
./manage_sting.sh stop kratos frontend

# Copy the new passkey schema to the right location
echo -e "${BLUE}Copying passkey schema...${NC}"
# First, create a temp container to mount the volume
TEMP_CONTAINER=$(docker run -d -v sting-ce_kratos-conf:/data alpine:latest sleep 60)
# Copy the schema file to the container
docker cp kratos/passkey-identity.schema.json $TEMP_CONTAINER:/data/
# Set proper permissions
docker exec $TEMP_CONTAINER chmod 644 /data/passkey-identity.schema.json
# Remove the temp container when done
docker stop $TEMP_CONTAINER && docker rm $TEMP_CONTAINER

# Rebuild and start services
echo -e "${BLUE}Rebuilding and starting services...${NC}"
./manage_sting.sh build kratos frontend
./manage_sting.sh start kratos frontend

# Wait for Kratos to be ready
echo -e "${BLUE}Waiting for Kratos to be ready...${NC}"
for i in {1..30}; do
  if curl -sk https://localhost:4433/health/ready > /dev/null 2>&1; then
    echo -e "${GREEN}Kratos is ready!${NC}"
    break
  fi
  echo -n "."
  sleep 1
  if [ $i -eq 30 ]; then
    echo -e "${RED}Timed out waiting for Kratos to be ready${NC}"
    exit 1
  fi
done

# Get the Kratos container ID
KRATOS_CONTAINER=$(docker ps | grep kratos | awk '{print $1}')
echo -e "${BLUE}Found Kratos container: ${GREEN}$KRATOS_CONTAINER${NC}"

# Run Kratos migration
echo -e "${BLUE}Running Kratos migration to update schema...${NC}"
docker exec $KRATOS_CONTAINER kratos migrate sql -e --yes

echo -e "${GREEN}Services restarted successfully!${NC}"
echo 
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}                   Testing Instructions                    ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo 
echo -e "${GREEN}1. Open Debug Page:${NC} https://localhost:3000/debug"
echo "   Use this page to check Kratos status and test authentication flows"
echo 
echo -e "${GREEN}2. Test Browser WebAuthn Support:${NC} https://localhost:3000/passkey-test.html"
echo "   This page directly tests if your browser supports WebAuthn/passkeys"
echo 
echo -e "${GREEN}3. Register with Passkey:${NC} https://localhost:3000/register"
echo "   Create a new account with passkey support"
echo 
echo -e "${GREEN}4. Login with Passkey:${NC} https://localhost:3000/login"
echo "   Sign in using your passkey" 
echo 
echo -e "${BLUE}===========================================================${NC}"
echo -e "${RED}If you encounter issues:${NC}"
echo "  - Check browser console for errors (F12 in most browsers)"
echo "  - Ensure your browser supports WebAuthn (Chrome, Firefox, Safari, Edge)"
echo "  - Try using a different browser"
echo "  - Clear browser cache and cookies for localhost"
echo -e "${BLUE}===========================================================${NC}"