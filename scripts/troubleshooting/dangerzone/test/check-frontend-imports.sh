#!/bin/bash
# Script to examine frontend imports and component loading

echo "Checking frontend container status..."
docker ps | grep "sting-frontend"

echo -e "\nChecking current MainInterface.js imports..."
docker exec sting-frontend-1 grep -A 10 "import " /app/src/components/MainInterface.js

echo -e "\nVerifying TestDashboard component exists in the container..."
docker exec sting-frontend-1 ls -la /app/src/components/TestDashboard.jsx

echo -e "\nVerifying route configuration in MainInterface.js..."
docker exec sting-frontend-1 grep -A 10 "<Routes>" /app/src/components/MainInterface.js

echo -e "\nChecking for any React router errors in the logs..."
docker logs sting-frontend-1 2>&1 | grep -i "route\|navigate\|error" | tail -n 20

echo -e "\nTo verify dashboard loading, login to your app and see if the TestDashboard appears."
echo "It should have a very distinctive red-to-green gradient background."
echo "If it does not appear, check browser console for errors and consider clearing cache."