#!/bin/bash
# Quick restart script for the chatbot service

# Directory of this script
SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SOURCE_DIR"

echo "Restarting STING Chatbot service..."

# Stop running containers
echo "Stopping chatbot service..."
cd chatbot && docker-compose down
cd ..

# Restart the frontend to ensure updated env variables
echo "Updating frontend environment..."
./restart-frontend.sh

# Restart the chatbot service
echo "Starting chatbot service..."
./start-chatbot.sh

echo "Chatbot service restart completed!"