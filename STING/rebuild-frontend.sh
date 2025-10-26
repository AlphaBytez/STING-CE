#!/bin/bash
echo "🔄 Rebuilding frontend container..."

# Stop the frontend container
docker stop sting-ce-frontend

# Remove the container (keep the image for faster rebuild)
docker rm sting-ce-frontend

# Rebuild and start the frontend
cd /mnt/c/Dev/STING-CE/STING
docker-compose up -d --build frontend

echo "✅ Frontend container rebuilt!"
echo "🌐 Frontend available at: https://localhost:8443"