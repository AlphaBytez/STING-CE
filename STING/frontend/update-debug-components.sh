#!/bin/bash
# Script to update frontend debug components

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default container name
CONTAINER_NAME="sting-frontend-1"

# Check if frontend container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
  echo -e "${RED}Error: Frontend container '$CONTAINER_NAME' not found or not running!${NC}"
  echo -e "${YELLOW}Available containers:${NC}"
  docker ps --format "{{.Names}}" | grep frontend
  
  # Ask user to specify container name if needed
  read -p "Enter frontend container name (or press Enter to exit): " custom_container
  
  if [ -z "$custom_container" ]; then
    echo "Exiting..."
    exit 1
  fi
  
  CONTAINER_NAME=$custom_container
  
  # Verify the specified container exists
  if ! docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${RED}Error: Container '$CONTAINER_NAME' not found or not running!${NC}"
    exit 1
  fi
fi

echo -e "${BLUE}=== Updating debug components in container '$CONTAINER_NAME' ===${NC}"

# Components to copy
COMPONENTS=(
  "src/components/auth/KratosDebug.jsx"
  "src/components/auth/BasicKratosLogin.jsx"
  "src/components/auth/DebugPage.jsx"
  "src/AppRoutes.js"
)

# Copy each file to the container
for file in "${COMPONENTS[@]}"; do
  local_path="./${file}"
  container_path="/app/${file}"
  
  # Check if the local file exists
  if [ ! -f "$local_path" ]; then
    echo -e "${RED}Skipping: '$local_path' does not exist${NC}"
    continue
  fi
  
  # Create directory in container if needed
  dir=$(dirname "$container_path")
  docker exec $CONTAINER_NAME mkdir -p "$dir"
  
  # Copy file to container
  echo -e "${YELLOW}Copying: $file${NC}"
  docker cp "$local_path" "${CONTAINER_NAME}:${container_path}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: $file${NC}"
  else
    echo -e "${RED}Failed to copy: $file${NC}"
  fi
done

echo -e "${GREEN}=== Debug components updated successfully! ===${NC}"
echo -e "${YELLOW}Note: You may need to refresh your browser to see the changes.${NC}"
echo -e "${BLUE}Access the debug page at: ${NC}https://localhost:8443/debug"
echo -e "${BLUE}Access the basic login at: ${NC}https://localhost:8443/login-basic"