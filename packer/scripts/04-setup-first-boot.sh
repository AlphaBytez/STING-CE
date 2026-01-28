#!/bin/bash
# 04-setup-first-boot.sh - Install first-boot service for STING-CE
set -e

echo "=== STING-CE OVA Build: First Boot Service Setup ==="

# Note: We use bashrc-triggered install (Path B) instead of systemd service
# This gives users visibility into the install process via console
# The systemd service files are kept but NOT enabled to avoid race conditions

# Create a simpler auto-login getty override for console
# This shows the STING banner and instructions on the VM console
echo "Configuring auto-login for console..."
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin sting --noclear %I $TERM
EOF

# Add first-boot trigger to user's bashrc
echo "Adding first-boot trigger to user profile..."
cat >> /home/sting/.bashrc << 'EOF'

# STING-CE First Boot Check
if [ ! -f /opt/sting-ce/.installed ] && [ -z "$STING_INSTALLER_RUNNING" ]; then
    export STING_INSTALLER_RUNNING=1
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  🐝 STING-CE Quick Start - First Time Setup               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Starting STING installer..."
    echo ""
    sudo /opt/sting-ce-source/STING/install_sting.sh || true
fi
EOF

echo "=== First boot service setup complete ==="
