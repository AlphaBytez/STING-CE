#!/bin/bash
# Script to restart just the frontend service without a full rebuild
# This should be faster for testing small changes

cd ..

echo "Restarting only the frontend service..."
docker-compose stop frontend && docker-compose rm -f frontend

echo "Starting frontend service..."
docker-compose up -d frontend

echo "Frontend service restarted."
echo "Please allow a moment for the service to initialize."

echo "You should now be able to see the TestDashboard component when you log in."
echo "It will have a distinctive red-to-green gradient background if it's loading correctly."