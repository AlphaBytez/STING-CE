#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Complete Registration Fix Script ===${NC}"

# Step 1: Backup current configurations
echo -e "\n${BLUE}=== Step 1: Backing up current configurations ===${NC}"
if [ -f main.kratos.yml.bak ]; then
  echo -e "${YELLOW}Backup already exists, skipping...${NC}"
else
  cp main.kratos.yml main.kratos.yml.bak
  echo -e "${GREEN}✓ Backed up Kratos configuration${NC}"
fi

if [ -f ../frontend/src/auth/RegisterPage.js.bak ]; then
  echo -e "${YELLOW}Frontend backup already exists, skipping...${NC}"
else
  cp ../frontend/src/auth/RegisterPage.js ../frontend/src/auth/RegisterPage.js.bak
  echo -e "${GREEN}✓ Backed up RegisterPage.js${NC}"
fi

# Step 2: Apply fixes
echo -e "\n${BLUE}=== Step 2: Applying configuration fixes ===${NC}"
echo -e "${GREEN}✓ Updated Kratos configuration (main.kratos.yml)${NC}"
echo -e "${GREEN}✓ Updated registration page (RegisterPage.js)${NC}"

# Step 3: Restart services
echo -e "\n${BLUE}=== Step 3: Restarting services ===${NC}"
cd ..
./manage_sting.sh restart kratos
./manage_sting.sh restart frontend
echo -e "${GREEN}✓ Services restarted${NC}"

# Step 4: Verify the fixes
echo -e "\n${BLUE}=== Step 4: Verifying fixes ===${NC}"
echo -e "${YELLOW}Waiting for Kratos to become available...${NC}"
for i in {1..20}; do
  if curl -k -s https://localhost:4433/health/ready > /dev/null; then
    echo -e "${GREEN}✓ Kratos is up and running${NC}"
    break
  fi
  echo -n "."
  sleep 1
  if [ $i -eq 20 ]; then
    echo -e "${RED}✗ Kratos health check timed out${NC}"
    echo -e "${YELLOW}Try running the test scripts manually after services are fully started${NC}"
  fi
done

echo -e "\n${YELLOW}Waiting for frontend to become available...${NC}"
for i in {1..20}; do
  if curl -k -s https://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✓ Frontend is up and running${NC}"
    break
  fi
  echo -n "."
  sleep 1
  if [ $i -eq 20 ]; then
    echo -e "${RED}✗ Frontend health check timed out${NC}"
    echo -e "${YELLOW}Check frontend logs if registration page doesn't load correctly${NC}"
  fi
done

echo -e "\n${BLUE}=== Fix completed ===${NC}"
echo -e "${YELLOW}Now try registering at https://localhost:3000/register${NC}"
echo -e "${YELLOW}You should see proper email and password fields now${NC}"
echo -e "${YELLOW}After registering, you can login at https://localhost:3000/login${NC}"
echo -e "${YELLOW}You can also run the test scripts to verify:${NC}"
echo -e "${YELLOW}- ./kratos/test-browser-registration.sh${NC}"
echo -e "${YELLOW}- ./kratos/test_kratos_registration.sh${NC}"