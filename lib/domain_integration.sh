#!/bin/bash
# Domain integration for STING installation process

# Source domain manager
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/domain_manager.sh"

# Check if domain setup is needed during installation
check_domain_setup() {
    local current_domain=$(get_current_domain)
    
    if [[ "$current_domain" == "localhost" ]]; then
        return 0  # Setup needed
    else
        return 1  # Already configured
    fi
}

# Prompt for domain setup during installation
prompt_domain_setup() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Local Domain Configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "STING can configure a local domain for:"
    echo "  • WebAuthn passkey compatibility across devices"
    echo "  • Consistent URLs for all services"
    echo "  • Network-wide access (with mDNS)"
    echo ""
    echo "Would you like to configure a local domain now?"
    echo "(You can also run ./setup_local_domain.sh later)"
    echo ""
    
    read -p "Configure local domain? (y/n) [y]: " setup_domain
    setup_domain=${setup_domain:-y}
    
    if [[ "$setup_domain" == "y" ]]; then
        # Run domain setup in automated mode
        setup_domain_automated
        return $?
    else
        echo ""
        echo "Skipping domain setup. Using localhost for now."
        echo "Run ./setup_local_domain.sh to configure later."
        return 1
    fi
}

# Automated domain setup for installation
setup_domain_automated() {
    echo ""
    echo "Setting up local domain..."
    
    # Generate domain automatically
    local new_domain=$(generate_sting_domain)
    
    echo "Generated domain: ${new_domain}"
    
    # Update configuration
    update_domain_config "$new_domain" "localhost"
    
    # Register mDNS if available
    if check_mdns_support; then
        register_mdns_service "$new_domain"
        echo "✅ mDNS service registered"
    else
        update_hosts_file "$new_domain" "add"
        echo "✅ Added to /etc/hosts"
    fi
    
    # Update frontend configuration
    update_frontend_config "$new_domain"
    
    echo ""
    echo "✅ Domain configuration complete: ${new_domain}"
    
    return 0
}

# Update frontend configuration with new domain
update_frontend_config() {
    local domain="$1"
    local frontend_env="${STING_INSTALL_DIR}/env/frontend.env"
    
    if [[ -f "$frontend_env" ]]; then
        # Update REACT_APP_API_URL
        sed -i.bak "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=\"https://${domain}:5050/api\"|" "$frontend_env"
        
        # Update REACT_APP_KRATOS_URL
        sed -i.bak "s|REACT_APP_KRATOS_URL=.*|REACT_APP_KRATOS_URL=\"https://${domain}:4433\"|" "$frontend_env"
        
        # Update PUBLIC_URL if present
        if grep -q "PUBLIC_URL=" "$frontend_env"; then
            sed -i.bak "s|PUBLIC_URL=.*|PUBLIC_URL=\"https://${domain}:8443\"|" "$frontend_env"
        fi
        
        log_message "Updated frontend configuration for domain: $domain"
    fi
}

# Display domain info after installation
display_domain_access_info() {
    local domain=$(get_current_domain)
    
    if [[ "$domain" != "localhost" ]]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 Access STING at: https://${domain}:8443"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if check_mdns_support; then
            echo "✅ Domain accessible from any device on your network"
        else
            echo "ℹ️  Domain accessible from this machine only"
            echo "   To access from other devices, add to their /etc/hosts:"
            echo "   $(hostname -I | awk '{print $1}')    ${domain}"
        fi
    else
        echo ""
        echo "Access STING at: https://localhost:8443"
        echo ""
        echo "💡 Tip: Run ./setup_local_domain.sh to enable:"
        echo "   • WebAuthn passkeys across devices"
        echo "   • Network-wide access"
    fi
}

# Cleanup function for uninstall
cleanup_domain() {
    local domain=$(get_current_domain)
    
    if [[ "$domain" != "localhost" ]]; then
        # Stop mDNS service
        stop_mdns_service
        
        # Remove from hosts file
        update_hosts_file "$domain" "remove"
        
        # Remove domain file
        rm -f "${STING_INSTALL_DIR}/.sting_domain"
        
        log_message "Domain configuration cleaned up"
    fi
}

# Export functions for use in installation scripts
export -f check_domain_setup
export -f prompt_domain_setup
export -f setup_domain_automated
export -f update_frontend_config
export -f display_domain_access_info
export -f cleanup_domain