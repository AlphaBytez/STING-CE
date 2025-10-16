#!/bin/bash
# Script to update the test dashboard with a new timestamp
# This will modify the source file inside the Docker container

CONTAINER_NAME="sting-frontend-1"
FILE_PATH="/app/src/components/TestDashboard.jsx"
TIMESTAMP=$(date)

echo "Updating TestDashboard component inside Docker container..."

# Use docker exec to run commands inside the container
docker exec $CONTAINER_NAME sh -c "
  # Create a backup of the current file
  cp $FILE_PATH ${FILE_PATH}.bak
  
  # Update the timestamp in the file
  sed -i \"s/Last updated: .*/Last updated: $TIMESTAMP/g\" $FILE_PATH
  
  # Show the changes
  diff ${FILE_PATH}.bak $FILE_PATH
"

echo "TestDashboard component updated with timestamp: $TIMESTAMP"
echo "The changes should be visible in the browser after reloading the page."
echo "You may need to clear your browser cache (Ctrl+F5 or Cmd+Shift+R)."