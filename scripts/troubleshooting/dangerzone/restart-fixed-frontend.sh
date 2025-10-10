#!/bin/bash
# Script to restart the frontend with the authentication wrapper fix

cd "$(dirname "$0")"

# Echo modifications
echo "Fixed routing conflict in AuthenticationWrapper.jsx"
echo "Updated to use MainInterface instead of Dashboard directly"
echo "Changed route pattern from /dashboard to /dashboard/* for nested routes"

echo "Stopping and removing frontend container..."
docker-compose stop frontend
docker-compose rm -f frontend

echo "Rebuilding and starting frontend container..."
docker-compose up -d --build frontend

echo "Frontend service restarted."
echo "Please try logging in again."
echo "You should now see the TestDashboard component (with the red-to-green gradient)."
echo "If this doesn't fix the issue, try clearing browser cache (Ctrl+F5 or Cmd+Shift+R)"