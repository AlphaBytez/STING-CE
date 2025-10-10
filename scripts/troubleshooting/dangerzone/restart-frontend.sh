#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}      STING Frontend Restart       ${NC}"
echo -e "${BLUE}===========================================================${NC}"

# Stop and rebuild frontend
echo -e "${BLUE}Stopping frontend service...${NC}"
docker-compose stop frontend

echo -e "${BLUE}Rebuilding frontend service...${NC}"
docker-compose build frontend

echo -e "${BLUE}Starting frontend service...${NC}"
docker-compose up -d frontend

echo -e "${GREEN}Frontend service restarted successfully!${NC}"
echo
echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}                   Testing Instructions                    ${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo
echo -e "${GREEN}1. Open Login Page:${NC} https://localhost:3000/login"
echo "   The login page now supports passkeys but falls back to password auth"
echo
echo -e "${GREEN}2. Open Registration Page:${NC} https://localhost:3000/register"
echo "   The registration page creates an account with password and adds passkey"
echo 
echo -e "${GREEN}3. Debug Page:${NC} https://localhost:3000/debug"
echo "   Use this page to check auth status and test various components"
echo
echo -e "${GREEN}4. WebAuthn Test:${NC} https://localhost:3000/passkey-test.html"
echo "   A standalone page that tests WebAuthn API directly"
echo 
echo -e "${BLUE}===========================================================${NC}"