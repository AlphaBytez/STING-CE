#!/bin/bash
set -e

# Stop all containers
echo "Stopping all containers..."
docker-compose down || true

# Remove containers and volumes
echo "Removing containers and volumes..."
docker-compose rm -f -v || true

# Safely remove the .env file
echo "Removing .env file..."
if [ -f "/opt/sting-ce/conf/.env" ]; then
    rm -f "/opt/sting-ce/conf/.env"
fi

# Remove any symbolic links to .env
echo "Removing .env symlinks..."
find /opt/sting-ce -type l -name ".env" -delete

# Clean up any temporary files
echo "Cleaning up temporary files..."
find /opt/sting-ce -name "*.tmp" -delete
find /opt/sting-ce -name "*.pyc" -delete

echo "Cleanup completed."