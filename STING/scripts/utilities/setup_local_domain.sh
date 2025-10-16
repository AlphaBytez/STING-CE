#!/bin/bash
# Setup STING local domain for easy access and WebAuthn compatibility

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define STING_INSTALL_DIR if not set
if [[ -z "$STING_INSTALL_DIR" ]]; then
    STING_INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
fi

# Define log_message if not already defined
if ! declare -f log_message >/dev/null 2>&1; then
    log_message() {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    }
fi

# Load domain manager functions
source "${SCRIPT_DIR}/lib/domain_manager.sh"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "🌐 STING Local Domain Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if STING is installed
if [[ ! -d "${STING_INSTALL_DIR}" ]]; then
    echo -e "${RED}Error: STING is not installed. Please run install_sting.sh first.${NC}"
    exit 1
fi

# Get current domain
current_domain=$(get_current_domain)
echo -e "Current domain: ${BLUE}${current_domain}${NC}"
echo ""

# Check mDNS support
if check_mdns_support; then
    echo -e "${GREEN}✅ mDNS support detected - domain will be accessible from other devices${NC}"
    mdns_available=true
else
    echo -e "${YELLOW}⚠️  mDNS not available - will use hosts file (local access only)${NC}"
    mdns_available=false
fi
echo ""

# Options menu
echo "Choose domain configuration:"
echo "1) Automatic - Generate unique domain from machine ID (Recommended)"
echo "2) Custom - Choose your own domain prefix"
echo "3) Simple - Use 'sting.hive' (may conflict with other installations)"
echo "4) Keep current - Use '${current_domain}'"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        # Automatic domain generation
        new_domain=$(generate_sting_domain)
        echo -e "\n${GREEN}Generated domain: ${new_domain}${NC}"
        ;;
    2)
        # Custom domain
        echo ""
        echo "Enter custom domain prefix (lowercase letters, numbers, hyphens only)"
        echo "Example: 'my-sting' will become 'my-sting.sting.hive'"
        read -p "Domain prefix: " custom_prefix
        
        # Validate and generate domain
        if new_domain=$(generate_sting_domain "$custom_prefix"); then
            echo -e "\n${GREEN}Custom domain: ${new_domain}${NC}"
        else
            echo -e "${RED}Invalid domain prefix. Exiting.${NC}"
            exit 1
        fi
        ;;
    3)
        # Simple domain
        new_domain="sting.hive"
        echo -e "\n${YELLOW}Warning: Using simple domain may conflict with other STING installations${NC}"
        ;;
    4)
        # Keep current
        echo -e "\n${BLUE}Keeping current domain: ${current_domain}${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

# Confirm domain change
if [[ "$new_domain" != "$current_domain" ]]; then
    echo ""
    read -p "Change domain from '${current_domain}' to '${new_domain}'? (y/n): " confirm
    
    if [[ "$confirm" != "y" ]]; then
        echo "Domain setup cancelled."
        exit 0
    fi
fi

echo ""
echo "Setting up domain: ${new_domain}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop any existing mDNS service
stop_mdns_service

# Update configuration files
update_domain_config "$new_domain" "$current_domain"

# Update config_loader.py to use new domain
if [[ -f "${SCRIPT_DIR}/conf/config_loader.py" ]]; then
    echo "Updating config_loader.py with new domain..."
    sed -i.bak "s/localhost/${new_domain}/g" "${SCRIPT_DIR}/conf/config_loader.py"
fi

# Register mDNS service if available
if [[ "$mdns_available" == "true" ]]; then
    echo "Registering mDNS service..."
    register_mdns_service "$new_domain"
else
    echo "Adding domain to /etc/hosts..."
    update_hosts_file "$new_domain" "add"
fi

# Regenerate environment files
echo "Regenerating environment files..."
cd "${STING_INSTALL_DIR}"

# Use centralized config generation via utils container instead of local Python
if [[ -f "${STING_INSTALL_DIR}/lib/config_utils.sh" ]]; then
    source "${STING_INSTALL_DIR}/lib/config_utils.sh"
    source "${STING_INSTALL_DIR}/lib/logging.sh"
    
    if generate_config_via_utils "runtime" "config.yml"; then
        echo "Environment files regenerated via utils container"
    else
        echo -e "${YELLOW}Warning: Could not regenerate environment files via utils container${NC}"
    fi
else
    echo -e "${YELLOW}Warning: Config utils not available, skipping environment file regeneration${NC}"
fi

# Update running services
echo ""
echo "Updating services with new domain..."
echo ""

# Check if services are running
if docker ps | grep -q "sting-ce"; then
    read -p "STING services are running. Restart them now? (y/n): " restart_services
    
    if [[ "$restart_services" == "y" ]]; then
        echo "Restarting services..."
        "${SCRIPT_DIR}/manage_sting.sh" restart || {
            echo -e "${YELLOW}Warning: Could not restart services automatically${NC}"
            echo "Please run: ./manage_sting.sh restart"
        }
    else
        echo ""
        echo -e "${YELLOW}Important: You must restart STING services for the domain change to take effect${NC}"
        echo "Run: ./manage_sting.sh restart"
    fi
else
    echo "STING services are not running. Start them with:"
    echo "./manage_sting.sh start"
fi

# Show final information
echo ""
echo -e "${GREEN}✅ Domain setup complete!${NC}"
echo ""
show_domain_info

# Additional instructions
echo "Next steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ "$mdns_available" == "true" ]]; then
    echo "1. Access STING from any device on your network using:"
    echo "   ${BLUE}https://${new_domain}:3000${NC}"
    echo ""
    echo "2. Accept the self-signed certificate warning in your browser"
    echo ""
    echo "3. WebAuthn passkeys created on this domain will work across all devices!"
else
    echo "1. Access STING from this machine using:"
    echo "   ${BLUE}https://${new_domain}:3000${NC}"
    echo ""
    echo "2. To access from other devices, add this to their /etc/hosts:"
    echo "   ${BLUE}$(hostname -I | awk '{print $1}')    ${new_domain}${NC}"
    echo ""
    echo "3. Accept the self-signed certificate warning in your browser"
fi

echo ""
echo "Domain configuration saved. This domain will be used for all future STING operations."
echo ""