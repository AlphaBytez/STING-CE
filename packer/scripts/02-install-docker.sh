#!/bin/bash
# 02-install-docker.sh - Install Docker and Docker Compose for STING-CE
set -e

echo "=== STING-CE OVA Build: Docker Installation ==="

# User to add to docker group
STING_USER="${STING_USER:-sting}"

# Remove any old Docker packages
echo "Removing old Docker packages (if any)..."
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
echo "Adding Docker GPG key..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "Adding Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update and install Docker
echo "Installing Docker..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# Start and enable Docker
echo "Starting Docker service..."
systemctl start docker
systemctl enable docker

# Add user to docker group
echo "Adding ${STING_USER} to docker group..."
usermod -aG docker "${STING_USER}"

# Verify Docker installation
echo "Verifying Docker installation..."
docker --version
docker compose version

# Configure Docker daemon for STING
echo "Configuring Docker daemon..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF

# Restart Docker to apply config
systemctl restart docker

# Note: We intentionally don't pre-pull Docker images here.
# The STING installer pulls all required images during setup.
# Pre-pulling base images would add ~1.2GB to OVA size with minimal benefit
# since 20+ other images still need to be downloaded anyway.

echo "=== Docker installation complete ==="
