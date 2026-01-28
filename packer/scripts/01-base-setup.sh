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

# Configure avahi for .local hostname resolution (IPv4 preferred)
echo "Configuring Avahi/mDNS..."

# Disable IPv6 in Avahi to ensure clients resolve to IPv4
# Many networks/clients have issues with IPv6 mDNS resolution
if [ -f /etc/avahi/avahi-daemon.conf ]; then
    sed -i 's/^#*use-ipv4=.*/use-ipv4=yes/' /etc/avahi/avahi-daemon.conf
    sed -i 's/^#*use-ipv6=.*/use-ipv6=no/' /etc/avahi/avahi-daemon.conf
    # If the settings don't exist, add them under [server]
    if ! grep -q "^use-ipv4=" /etc/avahi/avahi-daemon.conf; then
        sed -i '/^\[server\]/a use-ipv4=yes' /etc/avahi/avahi-daemon.conf
    fi
    if ! grep -q "^use-ipv6=" /etc/avahi/avahi-daemon.conf; then
        sed -i '/^\[server\]/a use-ipv6=no' /etc/avahi/avahi-daemon.conf
    fi
fi

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
   https://github.com/AlphaBytez/STING-CE

 ============================================

EOF

# Disable Ubuntu Pro ads in MOTD
echo "Disabling Ubuntu Pro messages..."
pro config set apt_news=false 2>/dev/null || true
chmod -x /etc/update-motd.d/10-help-text 2>/dev/null || true
chmod -x /etc/update-motd.d/50-motd-news 2>/dev/null || true
chmod -x /etc/update-motd.d/88-esm-announce 2>/dev/null || true
chmod -x /etc/update-motd.d/91-contract-ua-esm-status 2>/dev/null || true

# Configure GRUB for a larger default console resolution
# This helps users see the VM console clearly on first boot
echo "Configuring default display resolution..."
if [ -f /etc/default/grub ]; then
    # Set 1024x768 as default - works well on most hypervisors
    sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash video=1024x768"/' /etc/default/grub
    # Also set GRUB menu resolution
    if ! grep -q "GRUB_GFXMODE" /etc/default/grub; then
        echo 'GRUB_GFXMODE=1024x768' >> /etc/default/grub
    fi
    if ! grep -q "GRUB_GFXPAYLOAD_LINUX" /etc/default/grub; then
        echo 'GRUB_GFXPAYLOAD_LINUX=keep' >> /etc/default/grub
    fi
    update-grub
fi

# Install Docker bridge veth fix for VirtualBox
# This fixes a VirtualBox-specific bug where veth interfaces don't auto-attach to the bridge
echo "Installing Docker bridge veth fix (VirtualBox workaround)..."
if [ -f /tmp/docker-veth-fix.sh ]; then
    install -m 755 /tmp/docker-veth-fix.sh /usr/local/bin/docker-veth-fix.sh
fi
if [ -f /tmp/docker-veth-fix.service ]; then
    install -m 644 /tmp/docker-veth-fix.service /etc/systemd/system/docker-veth-fix.service
fi
if [ -f /tmp/docker-veth-fix.timer ]; then
    install -m 644 /tmp/docker-veth-fix.timer /etc/systemd/system/docker-veth-fix.timer
    systemctl daemon-reload
    systemctl enable docker-veth-fix.timer
fi

echo "=== Base setup complete ==="
