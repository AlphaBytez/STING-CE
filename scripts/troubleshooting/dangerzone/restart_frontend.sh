#!/bin/bash
# Script to restart frontend with updated configuration

# Stop only the frontend container
echo "Stopping frontend container..."
docker compose stop frontend

# Kill any existing process using port 3000 (React dev server)
echo "Checking for processes using port 3000..."
lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs -r kill -9

# Build and restart frontend 
echo "Building and restarting frontend..."
docker compose up -d --build frontend

# Wait for frontend to start
echo "Waiting for frontend to become ready..."
sleep 5

# Check if frontend is running
if docker compose ps frontend | grep Up; then
  echo "Frontend successfully restarted."
  echo "You can now access it at: https://localhost:3000"
else
  echo "Frontend failed to start. Check logs with: docker compose logs frontend"
fi

# Show first 20 lines of logs
echo "Showing latest logs:"
docker compose logs --tail 20 frontend