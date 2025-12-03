#!/bin/bash
# docker-veth-fix.sh - Fix VirtualBox Docker bridge veth attachment bug
# This script attaches orphaned veth interfaces to the Docker bridge
# Required for VirtualBox VMs where veth interfaces don't auto-attach

# Find the sting_local bridge (Docker custom network)
BRIDGE=$(ip link show type bridge 2>/dev/null | grep -oP 'br-[a-f0-9]+' | head -1)

if [ -z "$BRIDGE" ]; then
    # No custom bridge found, nothing to fix
    exit 0
fi

# Check if bridge is UP
BRIDGE_STATE=$(ip link show "$BRIDGE" 2>/dev/null | grep -oP 'state \K\w+')
if [ "$BRIDGE_STATE" != "UP" ]; then
    ip link set "$BRIDGE" up 2>/dev/null
fi

FIXED=0
# Find all veth interfaces and check if they're attached to the bridge
for veth in $(ip link show type veth 2>/dev/null | grep -oP 'veth[a-f0-9]+(?=@)' | sort -u); do
    # Check if veth has a master (is attached to a bridge)
    master=$(ip link show "$veth" 2>/dev/null | grep -oP 'master \K[^ ]+')

    if [ -z "$master" ]; then
        # Veth is not attached to any bridge - attach it
        if ip link set "$veth" master "$BRIDGE" 2>/dev/null; then
            logger -t docker-veth-fix "Attached $veth to $BRIDGE"
            ((FIXED++))
        fi
    fi
done

if [ $FIXED -gt 0 ]; then
    logger -t docker-veth-fix "Fixed $FIXED orphaned veth interface(s)"
fi

exit 0
