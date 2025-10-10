#!/bin/bash

# Explicitly pull the image first
docker pull mailhog/mailhog:latest

# Verify image exists
if ! docker image inspect mailhog/mailhog:latest >/dev/null 2>&1; then
    echo "Failed to pull Mailhog image"
    exit 1
fi

# Remove existing container if it exists
docker rm -f sting-mailhog 2>/dev/null || true

# Run Mailhog container
docker run -d \
    --name sting-mailhog \
    --network sting_local \
    -p 1025:1025 \
    -p 8025:8025 \
    mailhog/mailhog:latest

echo "Mailhog container started successfully"
