#!/bin/bash
# Script to deploy logout fix to running frontend container

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default container name
CONTAINER_NAME="sting-frontend-1"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo -e "${RED}Error: Frontend container '$CONTAINER_NAME' not found or not running!${NC}"
  echo -e "${YELLOW}Available containers:${NC}"
  docker ps --format "{{.Names}}" | grep frontend
  
  # Ask for container name
  read -p "Enter frontend container name: " custom_container
  
  if [ -z "$custom_container" ]; then
    echo "Exiting..."
    exit 1
  fi
  
  CONTAINER_NAME=$custom_container
fi

echo -e "${GREEN}Deploying logout fix to container: $CONTAINER_NAME${NC}"

# Copy MainInterface.js to container
echo -e "${YELLOW}Updating MainInterface.js...${NC}"
docker cp "./src/components/MainInterface.js" "${CONTAINER_NAME}:/app/src/components/MainInterface.js"
if [ $? -eq 0 ]; then
  echo -e "${GREEN}MainInterface.js updated successfully${NC}"
else
  echo -e "${RED}Failed to update MainInterface.js${NC}"
fi

# Copy LogoutPage.jsx to container
echo -e "${YELLOW}Updating LogoutPage.jsx...${NC}"
docker cp "./src/components/auth/LogoutPage.jsx" "${CONTAINER_NAME}:/app/src/components/auth/LogoutPage.jsx"
if [ $? -eq 0 ]; then
  echo -e "${GREEN}LogoutPage.jsx updated successfully${NC}"
else
  echo -e "${RED}Failed to update LogoutPage.jsx${NC}"
fi

echo -e "${GREEN}Logout fix deployed. Please refresh your browser to see the changes.${NC}"