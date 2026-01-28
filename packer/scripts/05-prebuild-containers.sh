#!/bin/bash
# 05-prebuild-containers.sh - Load or build STING-CE Docker containers
#
# This script either:
# 1. Loads pre-built images from tarball (fast, ~2-5 min) - if tarball exists
# 2. Falls back to building images (slow, ~60-90 min) - if no tarball
#
# The tarball is created by build-ova.sh on the host where network is fast.
set -e

echo "=== STING-CE OVA Build: Docker Container Setup ==="

STING_SOURCE="/opt/sting-ce-source"
IMAGES_TARBALL="/tmp/sting-ce-images.tar.gz"

cd "$STING_SOURCE/STING"

# Set INSTALL_DIR - required by docker-compose.yml volume mounts
export INSTALL_DIR="$STING_SOURCE/STING"

# Create .env file for docker compose
echo "INSTALL_DIR=$INSTALL_DIR" > .env
echo "STING_VERSION=latest" >> .env
echo "HOSTNAME=localhost" >> .env

echo "Created .env file with INSTALL_DIR=$INSTALL_DIR"

# Ensure Docker is running
systemctl start docker
sleep 5

# Check if pre-built images tarball exists
if [ -f "$IMAGES_TARBALL" ]; then
    echo ""
    echo "=== Found pre-built images tarball ==="
    echo "Loading images from $IMAGES_TARBALL (this is much faster than building)"

    TARBALL_SIZE=$(du -h "$IMAGES_TARBALL" | cut -f1)
    echo "Tarball size: $TARBALL_SIZE"

    echo ""
    echo "Loading Docker images (this may take 2-5 minutes)..."

    # Load images from compressed tarball
    if gunzip -c "$IMAGES_TARBALL" | docker load; then
        echo ""
        echo "=== Images loaded successfully ==="

        # Remove tarball to save disk space
        echo "Removing tarball to save disk space..."
        rm -f "$IMAGES_TARBALL"

        # Tag images for docker compose
        echo ""
        echo "Verifying loaded images..."
        docker images | head -20

        echo ""
        echo "=== Pre-built images loaded successfully ==="
        echo "First-boot install will be ~5-10 minutes."

        # Create marker file so installation script knows images are pre-built
        touch "$STING_SOURCE/.ova-prebuild"
        echo "Created OVA prebuild marker file"
        exit 0
    else
        echo "ERROR: Failed to load images from tarball"
        echo "Falling back to building images..."
        rm -f "$IMAGES_TARBALL"
    fi
fi

# If we get here, no tarball exists - fall back to building
echo ""
echo "=== No pre-built images tarball found ==="
echo "Building images from scratch (this may take 60-90 minutes)..."
echo ""
echo "TIP: For faster builds, use build-ova.sh which pre-builds images on the host"

# Wait for network to be fully available
echo "Waiting for network connectivity..."
for i in {1..30}; do
    if curl -s --connect-timeout 2 https://registry-1.docker.io/v2/ &>/dev/null || \
       curl -s --connect-timeout 2 https://hub.docker.com &>/dev/null; then
        echo "Network is ready (Docker registry reachable)"
        break
    fi
    echo "Waiting for network... attempt $i/30"
    sleep 2
done

# Helper function to build with retries
build_with_retry() {
    local service=$1
    local max_attempts=3
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo "Building $service (attempt $attempt/$max_attempts)..."
        if docker compose build "$service"; then
            return 0
        fi
        echo "Build failed, retrying in 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done

    echo "WARNING: Failed to build $service after $max_attempts attempts"
    return 1
}

echo "=== Phase 1: Pulling External Images ==="

# Core infrastructure
docker pull postgres:16 || true
docker pull redis:7-alpine || true
docker pull nginx:1.27-alpine || true
docker pull oryd/kratos:v1.3.0 || true
docker pull chromadb/chroma:0.5.20 || true
docker pull axllent/mailpit:v1.21.5 || true

# Base images for builds
docker pull python:3.11-slim || true
docker pull python:3.12.8-slim || true
docker pull node:20-alpine || true
docker pull hashicorp/vault:1.15 || true

echo "=== Phase 2: Building STING-CE Images ==="
export STING_VERSION=latest

# Build images - continue on failure
build_with_retry vault || true
build_with_retry utils || true
build_with_retry app || true
build_with_retry frontend || true
build_with_retry chatbot || true
build_with_retry knowledge || true
build_with_retry external-ai || true
build_with_retry messaging || true
build_with_retry nectar-worker || true
build_with_retry public-bee || true
build_with_retry report-worker || true
build_with_retry qe-bee-worker || true

echo ""
echo "=== Phase 3: Cleanup ==="
docker builder prune -f --filter "until=1h" || true
docker image prune -f || true

echo ""
echo "=== Final Image Summary ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -25

echo ""
echo "=== Pre-build complete ==="
