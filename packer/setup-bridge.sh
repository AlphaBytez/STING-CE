#!/bin/bash
# setup-bridge.sh - Configure bridged networking for QEMU Packer builds
#
# This script creates a network bridge (br0) required for building STING-CE OVA
# images with proper network connectivity during Docker container builds.
#
# Usage: sudo ./setup-bridge.sh [INTERFACE]
#   INTERFACE: Network interface to bridge (default: auto-detect)
#
# Requirements:
#   - Must be run as root
#   - iproute2 package installed
#
# Note: This will briefly interrupt network connectivity while setting up the bridge.

set -e

# Detect primary network interface if not specified
if [ -n "$1" ]; then
    INTERFACE="$1"
else
    # Find interface with default route
    INTERFACE=$(ip route | grep default | head -1 | awk '{print $5}')
    if [ -z "$INTERFACE" ]; then
        echo "ERROR: Could not detect primary network interface"
        echo "Usage: $0 [INTERFACE_NAME]"
        exit 1
    fi
fi

echo "=== STING-CE OVA Build: Network Bridge Setup ==="
echo "Interface: $INTERFACE"

# Check if bridge already exists
if ip link show br0 &>/dev/null; then
    echo "Bridge br0 already exists"
    ip addr show br0
    exit 0
fi

# Get current IP config
IP_ADDR=$(ip -4 addr show "$INTERFACE" | grep inet | awk '{print $2}')
GATEWAY=$(ip route | grep default | awk '{print $3}')

if [ -z "$IP_ADDR" ]; then
    echo "ERROR: Could not get IP address from $INTERFACE"
    exit 1
fi

echo "Current IP: $IP_ADDR"
echo "Gateway: $GATEWAY"

# Create QEMU bridge configuration
echo "Configuring QEMU bridge helper..."
mkdir -p /etc/qemu
echo "allow br0" > /etc/qemu/bridge.conf
chmod 644 /etc/qemu/bridge.conf

# Set setuid on bridge helper
BRIDGE_HELPER="/usr/lib/qemu/qemu-bridge-helper"
if [ -f "$BRIDGE_HELPER" ]; then
    chmod u+s "$BRIDGE_HELPER"
    echo "Set setuid on $BRIDGE_HELPER"
else
    echo "WARNING: qemu-bridge-helper not found at $BRIDGE_HELPER"
fi

# Create bridge
echo "Creating bridge br0..."
ip link add name br0 type bridge
ip link set br0 up

# Add interface to bridge
echo "Adding $INTERFACE to bridge..."
ip link set "$INTERFACE" master br0

# Move IP from interface to bridge
echo "Moving IP configuration to bridge..."
ip addr del "$IP_ADDR" dev "$INTERFACE" 2>/dev/null || true
ip addr add "$IP_ADDR" dev br0

# Re-add default route via bridge
ip route add default via "$GATEWAY" dev br0 2>/dev/null || true

# Configure DNS on the bridge (systemd-resolved needs this after IP move)
echo "Configuring DNS on bridge..."
resolvectl dns br0 "$GATEWAY" 8.8.8.8 2>/dev/null || true

echo ""
echo "=== Bridge Setup Complete ==="
ip addr show br0
echo ""
echo "Network connectivity test:"
if ping -c 1 8.8.8.8 &>/dev/null; then
    echo "✓ Internet connectivity OK"
else
    echo "✗ WARNING: No internet connectivity - check your network"
fi

echo ""
echo "You can now run the Packer build:"
echo "  cd packer && packer build -var-file=variables.pkrvars.hcl sting-ce.pkr.hcl"
