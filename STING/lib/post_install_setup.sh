#!/bin/bash
# Post-installation setup for STING
# This script is called after successful installation to set up domain and display info

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source required functions
if [[ -f "${PROJECT_ROOT}/lib/domain_manager.sh" ]]; then
    source "${PROJECT_ROOT}/lib/domain_manager.sh"
fi

if [[ -f "${PROJECT_ROOT}/lib/installation_complete.sh" ]]; then  
    source "${PROJECT_ROOT}/lib/installation_complete.sh"
fi

# Function to set up domain during first installation
setup_installation_domain() {
    local current_domain=$(get_current_domain)
    
    if [[ "$current_domain" == "localhost" ]]; then
        # First time installation - generate domain
        echo ""
        echo "Setting up unique domain for your STING installation..."
        
        local new_domain=$(generate_sting_domain)
        save_domain "$new_domain"
        
        # Register with mDNS if available
        if check_mdns_support; then
            register_mdns_service "$new_domain" >/dev/null 2>&1 &
        fi
        
        echo "$new_domain"
    else
        # Domain already configured
        echo "$current_domain"
    fi
}

# Main execution
main() {
    # Set up or get domain
    STING_DOMAIN=$(setup_installation_domain)
    
    # Display installation complete message
    display_installation_complete "$STING_DOMAIN"
    
    # Create a quick reference file
    if [[ -n "${STING_INSTALL_DIR}" ]]; then
        cat > "${STING_INSTALL_DIR}/QUICK_START.txt" << EOF
STING Quick Start
================

Your STING Domain: ${STING_DOMAIN}

Access STING:
  https://${STING_DOMAIN}:8443

Useful Commands:
  ./manage_sting.sh status     # Check service health
  ./manage_sting.sh logs       # View logs  
  ./manage_sting.sh stop       # Stop services
  ./setup_local_domain.sh      # Change domain

EOF
    fi
}

# Run main function
main