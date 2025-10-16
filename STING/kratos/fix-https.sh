#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Fix HTTPS Certificate Validation ===${NC}"

# Step 1: Visit Kratos health endpoint to accept certificate
echo -e "\n${BLUE}=== Step 1: Opening Kratos health endpoint to accept certificate ===${NC}"
echo -e "${YELLOW}Please visit https://localhost:4433/health/ready in your browser${NC}"
echo -e "${YELLOW}Click 'Advanced' and 'Proceed to localhost (unsafe)'${NC}"
echo -e "${GREEN}Press Enter when done...${NC}"
read

# Step 2: Visit Kratos admin endpoint to accept that certificate too
echo -e "\n${BLUE}=== Step 2: Opening Kratos admin endpoint to accept certificate ===${NC}"
echo -e "${YELLOW}Please visit https://localhost:4434/health/ready in your browser${NC}"
echo -e "${YELLOW}Click 'Advanced' and 'Proceed to localhost (unsafe)'${NC}"
echo -e "${GREEN}Press Enter when done...${NC}"
read

# Step 3: Restart services
echo -e "\n${BLUE}=== Step 3: Restarting services ===${NC}"
cd ..
./manage_sting.sh restart kratos
./manage_sting.sh restart frontend

echo -e "\n${GREEN}=== HTTPS certificate validation fixed ===${NC}"
echo -e "${YELLOW}Now try logging in at https://localhost:3000/login${NC}"
echo -e "${YELLOW}with email: test@example.com and password: password${NC}"