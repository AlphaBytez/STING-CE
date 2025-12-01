#!/bin/bash
# 01-base-setup.sh - Base system setup for STING-CE OVA
set -e

echo "=== STING-CE OVA Build: Base Setup ==="

# Wait for any background processes
sleep 10

# Update package lists
echo "Updating package lists..."
apt-get update

# Upgrade existing packages
echo "Upgrading system packages..."
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install essential packages
echo "Installing essential packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    wget \
    git \
    jq \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    apt-transport-https \
    openssh-server \
    sudo \
    vim \
    htop \
    net-tools \
    dnsutils \
    avahi-daemon \
    avahi-utils \
    libnss-mdns \
    open-vm-tools \
    python3 \
    python3-pip \
    python3-venv

# Configure avahi for .local hostname resolution
echo "Configuring Avahi/mDNS..."
systemctl enable avahi-daemon
systemctl start avahi-daemon || true

# Set timezone to UTC (user can change)
echo "Setting timezone to UTC..."
timedatectl set-timezone UTC

# Configure SSH
echo "Configuring SSH..."
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd || true

# Create MOTD banner
echo "Creating STING-CE welcome banner..."
cat > /etc/motd << 'EOF'

  ____  _____ ___ _   _  ____       ____ _____
 / ___||_   _|_ _| \ | |/ ___|     / ___| ____|
 \___ \  | |  | ||  \| | |  _ ____| |   |  _|
  ___) | | |  | || |\  | |_| |____| |___| |___
 |____/  |_| |___|_| \_|\____|     \____|_____|

 Secure Trusted Intelligence and Networking Guardian
 Community Edition - Quick Start VM

 ============================================

 FIRST TIME SETUP:
   The STING installer should start automatically.
   If not, run: sudo /opt/sting-ce-source/install_sting.sh

 ACCESS STING:
   Web UI: https://<this-vm-ip>:8443

 HELPFUL COMMANDS:
   sudo msting status    - Check service status
   sudo msting logs      - View logs
   sudo msting restart   - Restart services

 DOCUMENTATION:
   https://github.com/AlphaBytez/STING-CE-Public

 ============================================

EOF

# Disable Ubuntu Pro ads in MOTD
echo "Disabling Ubuntu Pro messages..."
pro config set apt_news=false 2>/dev/null || true
chmod -x /etc/update-motd.d/10-help-text 2>/dev/null || true
chmod -x /etc/update-motd.d/50-motd-news 2>/dev/null || true
chmod -x /etc/update-motd.d/88-esm-announce 2>/dev/null || true
chmod -x /etc/update-motd.d/91-contract-ua-esm-status 2>/dev/null || true

echo "=== Base setup complete ==="
