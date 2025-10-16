#!/bin/bash
# Display STING access information after installation

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source required functions
if [[ -f "${SCRIPT_DIR}/lib/domain_manager.sh" ]]; then
    source "${SCRIPT_DIR}/lib/domain_manager.sh"
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get current domain
domain=$(get_current_domain)

# If no domain set yet, generate one
if [[ "$domain" == "localhost" ]] && [[ -d "$HOME/.sting-ce" ]]; then
    echo "Generating unique domain for your STING installation..."
    domain=$(generate_sting_domain)
    save_domain "$domain"
    
    # Try to register mDNS
    if check_mdns_support; then
        register_mdns_service "$domain" >/dev/null 2>&1 &
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ STING Installation Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ "$domain" != "localhost" ]]; then
    echo -e "🌐 Your STING Domain: ${BLUE}${domain}${NC}"
    echo ""
    echo "Access STING at:"
    echo -e "  Frontend:    ${BLUE}https://${domain}:3000${NC}"
    echo -e "  API:         ${BLUE}https://${domain}:5050${NC}"
    echo -e "  Auth:        ${BLUE}https://${domain}:4433${NC}"
    echo ""
    
    if check_mdns_support; then
        echo -e "${GREEN}✅ This domain is accessible from any device on your network${NC}"
    else
        echo "ℹ️  To access from other devices, add to their /etc/hosts:"
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_IP")
        echo "   ${ip}    ${domain}"
    fi
else
    echo "Access STING at:"
    echo -e "  Frontend:    ${BLUE}https://localhost:3000${NC}"
    echo -e "  API:         ${BLUE}https://localhost:5050${NC}"
    echo -e "  Auth:        ${BLUE}https://localhost:4433${NC}"
    echo ""
    echo -e "${YELLOW}💡 Tip: Run ./setup_local_domain.sh to enable:${NC}"
    echo "   • Unique domain for your installation"
    echo "   • WebAuthn passkeys across devices"
    echo "   • Network-wide access"
fi

echo ""
echo "Next steps:"
echo "  1. Accept the self-signed certificate warning in your browser"
echo "  2. Create your first admin user"
echo "  3. Explore the Bee Chat and Honey Jars features"
echo ""
echo "Useful commands:"
echo "  ./manage_sting.sh status     # Check service health"
echo "  ./manage_sting.sh logs       # View logs"
echo "  ./manage_sting.sh stop       # Stop services"
echo ""

# Create quick reference file
if [[ -d "$HOME/.sting-ce" ]]; then
    cat > "$HOME/.sting-ce/ACCESS_INFO.txt" << EOF
STING Access Information
========================

Domain: ${domain}
URL: https://${domain}:8443

To view this again: ./show_access_info.sh
To change domain: ./setup_local_domain.sh
EOF
fi