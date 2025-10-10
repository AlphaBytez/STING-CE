#!/bin/bash
# Script to fix both authentication routing conflicts and SuperTokens issues

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting combined fix for authentication routing and SuperTokens issues${NC}"

# 1. Fix SuperTokens environment issues first
echo -e "${YELLOW}Step 1: Fixing SuperTokens environment issues${NC}"
./troubleshooting/fix_supertokens_env.sh

# 2. Apply routing fix to AuthenticationWrapper.jsx
echo -e "${YELLOW}Step 2: Fixing authentication routing conflict${NC}"

AUTH_WRAPPER="./frontend/src/auth/AuthenticationWrapper.jsx"

if [ -f "$AUTH_WRAPPER" ]; then
    echo -e "${YELLOW}Backing up AuthenticationWrapper.jsx${NC}"
    cp "$AUTH_WRAPPER" "${AUTH_WRAPPER}.bak.$(date +%Y%m%d%H%M%S)"
    
    # Update the route path
    echo -e "${YELLOW}Updating dashboard route in AuthenticationWrapper.jsx${NC}"
    sed -i'.tmp' -e 's|path="/dashboard"|path="/dashboard/*"|g' "$AUTH_WRAPPER"
    
    # Update the import for MainInterface
    echo -e "${YELLOW}Updating imports to use MainInterface instead of Dashboard${NC}"
    sed -i'.tmp' -e 's|import Dashboard from.*|import MainInterface from '\''../components/MainInterface'\''|' "$AUTH_WRAPPER"
    
    # Update the component being rendered
    echo -e "${YELLOW}Updating rendered component to MainInterface${NC}"
    sed -i'.tmp' -e 's|<Dashboard />|<MainInterface />|g' "$AUTH_WRAPPER"
    
    # Clean up temporary files
    rm -f "$AUTH_WRAPPER.tmp"
    
    echo -e "${GREEN}Successfully updated AuthenticationWrapper.jsx${NC}"
else
    echo -e "${RED}Could not find AuthenticationWrapper.jsx at $AUTH_WRAPPER${NC}"
    echo -e "${RED}Routing fix could not be applied${NC}"
fi

# 3. Rebuild the frontend container
echo -e "${YELLOW}Step 3: Rebuilding frontend container${NC}"
cd "$(dirname "$0")"

echo -e "${YELLOW}Stopping and removing frontend container...${NC}"
docker-compose stop frontend
docker-compose rm -f frontend

echo -e "${YELLOW}Building and starting new frontend container...${NC}"
docker-compose up -d --build frontend

echo -e "${GREEN}All fixes have been applied!${NC}"
echo -e "${YELLOW}Notes:${NC}"
echo -e "1. After logging in, you should now see the correct dashboard layout"
echo -e "2. The 'msting update frontend' command should now work without errors"
echo -e "3. If you still encounter issues, try a full restart: ${GREEN}./manage_sting.sh restart${NC}"
echo -e "4. You may need to clear your browser cache (Ctrl+F5 or Cmd+Shift+R)"