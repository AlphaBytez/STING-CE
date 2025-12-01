#!/bin/bash
# 04-setup-first-boot.sh - Install first-boot service for STING-CE
set -e

echo "=== STING-CE OVA Build: First Boot Service Setup ==="

# Install systemd service
echo "Installing first-boot systemd service..."
cp /tmp/sting-first-boot.service /etc/systemd/system/
chmod 644 /etc/systemd/system/sting-first-boot.service

# Install first-boot script
echo "Installing first-boot script..."
mkdir -p /opt/sting-ce-source/packer/files
cp /tmp/sting-first-boot.sh /opt/sting-ce-source/packer/files/
chmod +x /opt/sting-ce-source/packer/files/sting-first-boot.sh

# Enable the service
echo "Enabling first-boot service..."
systemctl daemon-reload
systemctl enable sting-first-boot.service

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
    echo "STING-CE has not been installed yet."
    echo ""
    echo "Starting the installer now..."
    echo "(You can also access the web wizard once it starts)"
    echo ""
    sleep 2
    sudo /opt/sting-ce-source/install_sting.sh || true
fi
EOF

echo "=== First boot service setup complete ==="
