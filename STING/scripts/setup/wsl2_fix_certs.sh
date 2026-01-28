#!/bin/bash
# WSL2 Certificate Volume Fix
# This script ensures certificates are properly copied to Docker volumes on WSL2

echo "WSL2 Certificate Fix Script"
echo "=========================="

# Check if running on WSL2
if ! grep -q microsoft /proc/version &> /dev/null; then
    echo "This script is intended for WSL2 environments only."
    exit 0
fi

# Define paths
CERT_DIR="/mnt/c/Development/STING-CE/STING/certs"
VOLUME_NAME="sting_sting_certs"

# Check if certificates exist
if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
    echo "ERROR: Certificates not found in $CERT_DIR"
    echo "Please ensure server.crt and server.key exist."
    exit 1
fi

# Check if volume exists
if ! docker volume ls | grep -q "$VOLUME_NAME"; then
    echo "Creating Docker volume: $VOLUME_NAME"
    docker volume create "$VOLUME_NAME"
fi

# Copy certificates to volume using Alpine container
echo "Copying certificates to Docker volume..."
cat "$CERT_DIR/server.crt" | docker run -i --rm -v "$VOLUME_NAME:/certs" alpine sh -c "cat > /certs/server.crt"
cat "$CERT_DIR/server.key" | docker run -i --rm -v "$VOLUME_NAME:/certs" alpine sh -c "cat > /certs/server.key"

# Verify certificates were copied
echo "Verifying certificates in volume..."
docker run --rm -v "$VOLUME_NAME:/certs" alpine ls -la /certs/

echo "Certificate fix completed successfully!"