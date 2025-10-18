#!/bin/bash
# fix_ubuntu_ip_access.sh - Quick fix for Ubuntu IP-based access issues
# This is a convenience wrapper that runs both configuration scripts

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   STING Ubuntu/Linux IP Access Configuration  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}This script will:${NC}"
echo "  1. Auto-detect your VM's IP address"
echo "  2. Update config.yml with the detected IP"
echo "  3. Regenerate all environment files using config_loader.py"
echo "  4. Update Kratos allowed URLs and CORS origins"
echo "  5. Restart affected services"
echo ""
echo -e "${YELLOW}This maintains Mac compatibility by only changing the config.yml domain.${NC}"
echo ""

read -p "Continue? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${GREEN}Step 1: Configuring platform-specific domain...${NC}"
echo ""

bash "${SCRIPT_DIR}/scripts/setup/configure_domain_for_platform.sh"

echo ""
echo -e "${GREEN}Step 2: Fixing Kratos allowed URLs...${NC}"
echo ""

bash "${SCRIPT_DIR}/scripts/setup/fix_kratos_allowed_urls.sh"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Configuration Complete!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your STING instance should now be accessible via IP address."
echo "Clear your browser cache if you still experience redirect issues."
echo ""
