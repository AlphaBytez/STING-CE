#!/bin/bash
# sting-first-boot.sh - First boot setup for STING-CE OVA
# This script runs once on first boot to launch the installer

set -e

STING_SOURCE="/opt/sting-ce-source"
STING_INSTALL="/opt/sting-ce"
LOG_FILE="/var/log/sting-first-boot.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== STING-CE First Boot Setup Starting ==="

# Check if already installed
if [ -f "${STING_INSTALL}/.installed" ]; then
    log "STING-CE already installed, skipping first boot setup"
    exit 0
fi

# Wait for network
log "Waiting for network..."
for i in {1..30}; do
    if ping -c 1 8.8.8.8 &> /dev/null; then
        log "Network is available"
        break
    fi
    sleep 2
done

# Wait for Docker
log "Waiting for Docker..."
for i in {1..30}; do
    if docker info &> /dev/null; then
        log "Docker is available"
        break
    fi
    sleep 2
done

# Get network info for display
PRIMARY_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

log "VM Network Info:"
log "  Hostname: ${HOSTNAME}"
log "  IP Address: ${PRIMARY_IP}"

# Display welcome message on console
cat << EOF

╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║   🐝 STING-CE Quick Start VM - First Boot                     ║
║                                                                ║
║   Your VM is ready! The STING installer will start shortly.   ║
║                                                                ║
║   Network Info:                                                ║
║     Hostname: ${HOSTNAME}
║     IP Address: ${PRIMARY_IP}
║                                                                ║
║   After installation completes, access STING at:              ║
║     https://${PRIMARY_IP}:8443
║                                                                ║
║   Or if using .local hostname:                                 ║
║     https://sting.local:8443                                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

EOF

# Check if installer exists
if [ ! -f "${STING_SOURCE}/install_sting.sh" ]; then
    # Try STING subdirectory
    if [ -f "${STING_SOURCE}/STING/install_sting.sh" ]; then
        INSTALLER="${STING_SOURCE}/STING/install_sting.sh"
    else
        log "ERROR: STING installer not found!"
        log "Please run manually: git clone https://github.com/AlphaBytez/STING-CE.git && cd STING-CE && ./install_sting.sh"
        exit 1
    fi
else
    INSTALLER="${STING_SOURCE}/install_sting.sh"
fi

log "Found installer at: ${INSTALLER}"

# Make executable
chmod +x "${INSTALLER}"

# Launch the installer
log "Launching STING installer..."
log "The web-based setup wizard will be available at:"
log "  http://${PRIMARY_IP}:5000"
log ""
log "Or run the installer manually with:"
log "  sudo ${INSTALLER}"
log ""

# Change to source directory and run installer
cd "${STING_SOURCE}"

# Run installer (it will handle the rest)
# Using exec to replace this script with the installer
exec "${INSTALLER}"
