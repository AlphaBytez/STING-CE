#!/bin/bash
# Display installation completion message with domain info

# Source domain functions if available
if [[ -f "${SCRIPT_DIR}/lib/domain_manager.sh" ]]; then
    source "${SCRIPT_DIR}/lib/domain_manager.sh"
fi

# Display installation complete message
display_installation_complete() {
    local domain="${1:-localhost}"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ STING Installation Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    if [[ "$domain" != "localhost" ]]; then
        echo "🌐 Your STING Domain: ${domain}"
        echo ""
        echo "Access STING at:"
        echo "  Frontend:    https://${domain}:8443"
        echo "  API:         https://${domain}:5050"
        echo "  Auth:        https://${domain}:4433"
        echo ""
        
        # Check if mDNS is available
        if command -v dns-sd >/dev/null 2>&1 || command -v avahi-browse >/dev/null 2>&1; then
            echo "✅ This domain is accessible from any device on your network"
        else
            echo "ℹ️  To access from other devices, add to their /etc/hosts:"
            local ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_IP")
            echo "   ${ip}    ${domain}"
        fi
    else
        echo "Access STING at:"
        echo "  Frontend:    https://localhost:8443"
        echo "  API:         https://localhost:5050"
        echo "  Auth:        https://localhost:4433"
        echo ""
        echo "💡 Tip: Run ./setup_local_domain.sh to enable:"
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
    
    # Save the domain info to a file for easy reference
    if [[ "$domain" != "localhost" ]] && [[ -n "${STING_INSTALL_DIR}" ]]; then
        echo "$domain" > "${STING_INSTALL_DIR}/.sting_domain"
        echo "https://${domain}:8443" > "${STING_INSTALL_DIR}/.sting_url"
    fi
}

# Export function
export -f display_installation_complete