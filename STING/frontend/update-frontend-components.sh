#!/bin/bash
# Script to update frontend components without rebuilding the entire frontend

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

echo -e "${BLUE}=== Updating frontend components in container '$CONTAINER_NAME' ===${NC}"

# Directory paths
LOCAL_COMPONENTS_DIR="./src/components"
CONTAINER_COMPONENTS_DIR="/app/src/components"

# Make sure the local components directory exists
if [ ! -d "$LOCAL_COMPONENTS_DIR" ]; then
  echo -e "${RED}Error: Local components directory '$LOCAL_COMPONENTS_DIR' not found!${NC}"
  exit 1
fi

# Components to copy - add more specific paths as needed
COMPONENTS=(
  "auth/LogoutPage.jsx"
)

# Copy each component
for component in "${COMPONENTS[@]}"; do
  local_path="${LOCAL_COMPONENTS_DIR}/${component}"
  container_path="${CONTAINER_COMPONENTS_DIR}/${component}"
  
  # Check if the local file exists
  if [ ! -f "$local_path" ]; then
    echo -e "${RED}Skipping: '$local_path' does not exist${NC}"
    continue
  fi
  
  # Create directory in container if needed
  component_dir=$(dirname "$component")
  if [ "$component_dir" != "." ]; then
    echo -e "${BLUE}Ensuring directory exists: $component_dir${NC}"
    docker exec $CONTAINER_NAME mkdir -p "${CONTAINER_COMPONENTS_DIR}/${component_dir}"
  fi
  
  # Copy the file to the container
  echo -e "${YELLOW}Copying: $component${NC}"
  docker cp "$local_path" "${CONTAINER_NAME}:${container_path}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: $component${NC}"
  else
    echo -e "${RED}Failed to copy: $component${NC}"
  fi
done

# Update AppRoutes.js
LOCAL_ROUTES_PATH="./src/AppRoutes.js"
CONTAINER_ROUTES_PATH="/app/src/AppRoutes.js"

if [ -f "$LOCAL_ROUTES_PATH" ]; then
  echo -e "${YELLOW}Copying: AppRoutes.js${NC}"
  docker cp "$LOCAL_ROUTES_PATH" "${CONTAINER_NAME}:${CONTAINER_ROUTES_PATH}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: AppRoutes.js${NC}"
  else
    echo -e "${RED}Failed to copy: AppRoutes.js${NC}"
  fi
else
  echo -e "${RED}Skipping: '$LOCAL_ROUTES_PATH' does not exist${NC}"
fi

# Update MainInterface.js
LOCAL_INTERFACE_PATH="./src/components/MainInterface.js"
CONTAINER_INTERFACE_PATH="/app/src/components/MainInterface.js"

if [ -f "$LOCAL_INTERFACE_PATH" ]; then
  echo -e "${YELLOW}Copying: MainInterface.js${NC}"
  docker cp "$LOCAL_INTERFACE_PATH" "${CONTAINER_NAME}:${CONTAINER_INTERFACE_PATH}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: MainInterface.js${NC}"
  else
    echo -e "${RED}Failed to copy: MainInterface.js${NC}"
  fi
else
  echo -e "${RED}Skipping: '$LOCAL_INTERFACE_PATH' does not exist${NC}"
fi

# Update KratosProvider.jsx
LOCAL_PROVIDER_PATH="./src/auth/KratosProvider.jsx"
CONTAINER_PROVIDER_PATH="/app/src/auth/KratosProvider.jsx"

if [ -f "$LOCAL_PROVIDER_PATH" ]; then
  echo -e "${YELLOW}Copying: KratosProvider.jsx${NC}"
  docker cp "$LOCAL_PROVIDER_PATH" "${CONTAINER_NAME}:${CONTAINER_PROVIDER_PATH}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: KratosProvider.jsx${NC}"
  else
    echo -e "${RED}Failed to copy: KratosProvider.jsx${NC}"
  fi
else
  echo -e "${RED}Skipping: '$LOCAL_PROVIDER_PATH' does not exist${NC}"
fi

# Update DebugPage.jsx 
LOCAL_DEBUG_PATH="./src/components/auth/DebugPage.jsx"
CONTAINER_DEBUG_PATH="/app/src/components/auth/DebugPage.jsx"

if [ -f "$LOCAL_DEBUG_PATH" ]; then
  echo -e "${YELLOW}Copying: DebugPage.jsx${NC}"
  docker cp "$LOCAL_DEBUG_PATH" "${CONTAINER_NAME}:${CONTAINER_DEBUG_PATH}"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully copied: DebugPage.jsx${NC}"
  else
    echo -e "${RED}Failed to copy: DebugPage.jsx${NC}"
  fi
else
  echo -e "${RED}Skipping: '$LOCAL_DEBUG_PATH' does not exist${NC}"
fi

echo -e "${GREEN}=== Frontend components updated successfully! ===${NC}"
echo -e "${YELLOW}Note: You may need to refresh your browser to see the changes.${NC}"