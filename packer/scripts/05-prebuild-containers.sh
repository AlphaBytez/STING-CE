#!/bin/bash
# 05-prebuild-containers.sh - Pre-cache Docker base images for faster first install
#
# Community Edition: Only pulls base images that STING builds FROM.
# STING service images are built on first boot by install_sting.sh.
# This reduces OVA size from ~15GB to ~3-5GB.
set -e

echo "=== STING-CE OVA Build: Docker Base Image Cache ==="

# Ensure Docker is running
systemctl start docker
sleep 5

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

echo "=== Pulling base images (saves ~5-10 min on first boot) ==="

# Core infrastructure images (used directly, not built)
docker pull postgres:16 || true
docker pull redis:7-alpine || true
docker pull nginx:1.27-alpine || true
docker pull oryd/kratos:v1.3.0 || true
docker pull chromadb/chroma:0.5.20 || true
docker pull axllent/mailpit:v1.21.5 || true
docker pull hashicorp/vault:1.15 || true

# Base images used in Dockerfiles (cache the FROM layers)
docker pull python:3.11-slim || true
docker pull node:18.20.6-alpine || true

echo ""
echo "=== Cleanup ==="
docker builder prune -f || true
docker image prune -f || true

echo ""
echo "=== Cached Image Summary ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -15

echo ""
echo "=== Base image cache complete ==="
echo "STING service images will be built on first boot (~15-30 min)"
