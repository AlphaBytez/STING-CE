#!/bin/bash
# fix_hostname.sh - Fix hostname configuration for STING installation
# This script updates all hostname references to ensure consistent authentication

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

# Detect installation directory
if [ -n "$INSTALL_DIR" ]; then
    STING_INSTALL_DIR="$INSTALL_DIR"
elif [ -d "/opt/sting-ce" ]; then
    STING_INSTALL_DIR="/opt/sting-ce"
elif [ -d "$HOME/sting-ce" ]; then
    STING_INSTALL_DIR="$HOME/sting-ce"
elif [ -d "./STING" ]; then
    STING_INSTALL_DIR="$(pwd)/STING"
else
    log_error "Could not detect STING installation directory"
    exit 1
fi

log_info "STING installation directory: $STING_INSTALL_DIR"

# Get the hostname to use
if [ -n "$1" ]; then
    NEW_HOSTNAME="$1"
    log_info "Using provided hostname: $NEW_HOSTNAME"
elif [ -f "${STING_INSTALL_DIR}/.sting_domain" ]; then
    NEW_HOSTNAME=$(cat "${STING_INSTALL_DIR}/.sting_domain")
    log_info "Using hostname from .sting_domain: $NEW_HOSTNAME"
elif [ -n "$STING_HOSTNAME" ]; then
    NEW_HOSTNAME="$STING_HOSTNAME"
    log_info "Using STING_HOSTNAME environment variable: $NEW_HOSTNAME"
else
    log_error "No hostname specified!"
    echo ""
    echo "Usage: $0 <hostname>"
    echo "Example: $0 captain-den.local"
    echo ""
    echo "Or set STING_HOSTNAME environment variable:"
    echo "  export STING_HOSTNAME=captain-den.local"
    echo "  $0"
    exit 1
fi

# Validate hostname
if [ -z "$NEW_HOSTNAME" ] || [ "$NEW_HOSTNAME" = "localhost" ]; then
    log_warning "Hostname is 'localhost' - this may cause issues with remote access"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Starting hostname configuration update"
log_info "New hostname: $NEW_HOSTNAME"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect OS for sed compatibility
if [[ "$(uname)" == "Darwin" ]]; then
    SED_INPLACE="sed -i ''"
    SED_I_FLAG="-i ''"
else
    SED_INPLACE="sed -i"
    SED_I_FLAG="-i"
fi

# Track changes
CHANGES_MADE=0
ERRORS=()

# Function to backup file
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backed up: $file"
    fi
}

# 1. Update config.yml
log_info "Step 1/6: Updating config.yml..."
CONFIG_FILE="${STING_INSTALL_DIR}/conf/config.yml"
if [ -f "$CONFIG_FILE" ]; then
    backup_file "$CONFIG_FILE"

    # Update domain field in system section
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/^  domain: .*/  domain: $NEW_HOSTNAME/" "$CONFIG_FILE"
    else
        sed -i "s/^  domain: .*/  domain: $NEW_HOSTNAME/" "$CONFIG_FILE"
    fi

    log_success "Updated config.yml domain to: $NEW_HOSTNAME"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    log_warning "config.yml not found at: $CONFIG_FILE"
    ERRORS+=("config.yml not found")
fi
echo ""

# 2. Update frontend/public/env.js
log_info "Step 2/6: Updating frontend/public/env.js..."
FRONTEND_ENV="${STING_INSTALL_DIR}/frontend/public/env.js"
if [ -f "$FRONTEND_ENV" ]; then
    backup_file "$FRONTEND_ENV"

    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$NEW_HOSTNAME:8443'|g" "$FRONTEND_ENV"
        sed -i '' "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$NEW_HOSTNAME:5050'|g" "$FRONTEND_ENV"
        sed -i '' "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$NEW_HOSTNAME:4433'|g" "$FRONTEND_ENV"
        # Also replace any IP addresses in other URLs
        sed -i '' "s|http://[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}:|http://$NEW_HOSTNAME:|g" "$FRONTEND_ENV"
    else
        sed -i "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$NEW_HOSTNAME:8443'|g" "$FRONTEND_ENV"
        sed -i "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$NEW_HOSTNAME:5050'|g" "$FRONTEND_ENV"
        sed -i "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$NEW_HOSTNAME:4433'|g" "$FRONTEND_ENV"
        # Also replace any IP addresses in other URLs
        sed -i "s|http://[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}:|http://$NEW_HOSTNAME:|g" "$FRONTEND_ENV"
    fi

    log_success "Updated frontend/public/env.js"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    log_warning "frontend/public/env.js not found at: $FRONTEND_ENV"
    ERRORS+=("frontend/public/env.js not found")
fi
echo ""

# 3. Update app/static/env.js
log_info "Step 3/6: Updating app/static/env.js..."
APP_ENV="${STING_INSTALL_DIR}/app/static/env.js"
if [ -f "$APP_ENV" ]; then
    backup_file "$APP_ENV"

    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$NEW_HOSTNAME:8443'|g" "$APP_ENV"
        sed -i '' "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$NEW_HOSTNAME:5050'|g" "$APP_ENV"
        sed -i '' "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$NEW_HOSTNAME:4433'|g" "$APP_ENV"
        # Also replace any IP addresses in other URLs
        sed -i '' "s|http://[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}:|http://$NEW_HOSTNAME:|g" "$APP_ENV"
    else
        sed -i "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$NEW_HOSTNAME:8443'|g" "$APP_ENV"
        sed -i "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$NEW_HOSTNAME:5050'|g" "$APP_ENV"
        sed -i "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$NEW_HOSTNAME:4433'|g" "$APP_ENV"
        # Also replace any IP addresses in other URLs
        sed -i "s|http://[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}:|http://$NEW_HOSTNAME:|g" "$APP_ENV"
    fi

    log_success "Updated app/static/env.js"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    log_warning "app/static/env.js not found (may not exist yet)"
fi
echo ""

# 4. Update Kratos configuration
log_info "Step 4/6: Updating Kratos configuration..."
KRATOS_CONFIG="${STING_INSTALL_DIR}/kratos/kratos.yml"
if [ -f "$KRATOS_CONFIG" ]; then
    backup_file "$KRATOS_CONFIG"

    # Get current hostname from kratos.yml
    OLD_HOSTNAME=$(grep -oP "https://\K[^:]+(?=:8443)" "$KRATOS_CONFIG" | head -1)

    if [ -n "$OLD_HOSTNAME" ] && [ "$OLD_HOSTNAME" != "$NEW_HOSTNAME" ]; then
        log_info "Replacing old hostname '$OLD_HOSTNAME' with '$NEW_HOSTNAME' in Kratos config"

        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|$OLD_HOSTNAME|$NEW_HOSTNAME|g" "$KRATOS_CONFIG"
        else
            sed -i "s|$OLD_HOSTNAME|$NEW_HOSTNAME|g" "$KRATOS_CONFIG"
        fi

        log_success "Updated Kratos configuration"
        CHANGES_MADE=$((CHANGES_MADE + 1))
    else
        log_info "Kratos config already uses hostname: $NEW_HOSTNAME"
    fi
elif [ -f "${STING_INSTALL_DIR}/kratos/kratos.yml.template" ]; then
    log_info "Generating kratos.yml from template..."
    sed "s/__STING_HOSTNAME__/$NEW_HOSTNAME/g" \
        "${STING_INSTALL_DIR}/kratos/kratos.yml.template" > \
        "$KRATOS_CONFIG"
    log_success "Generated Kratos configuration"
    CHANGES_MADE=$((CHANGES_MADE + 1))
else
    log_warning "Kratos configuration not found"
    ERRORS+=("Kratos configuration not found")
fi
echo ""

# 5. Save hostname to .sting_domain file
log_info "Step 5/6: Saving hostname to .sting_domain..."
echo "$NEW_HOSTNAME" > "${STING_INSTALL_DIR}/.sting_domain"
echo "https://${NEW_HOSTNAME}:8443" > "${STING_INSTALL_DIR}/.sting_url"
log_success "Saved hostname to .sting_domain"
echo ""

# 6. Regenerate environment files
log_info "Step 6/6: Regenerating environment files..."
if [ -f "${STING_INSTALL_DIR}/conf/config_loader.py" ]; then
    cd "${STING_INSTALL_DIR}/conf"

    # Set environment variables for config_loader
    export INSTALL_DIR="$STING_INSTALL_DIR"
    export STING_DOMAIN="$NEW_HOSTNAME"

    if python3 config_loader.py config.yml --mode bootstrap; then
        log_success "Regenerated environment files"
        CHANGES_MADE=$((CHANGES_MADE + 1))
    else
        log_error "Failed to regenerate environment files"
        ERRORS+=("Environment file regeneration failed")
    fi
else
    log_warning "config_loader.py not found, skipping environment regeneration"
fi
echo ""

# Summary
echo ""
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Hostname configuration update complete!"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $CHANGES_MADE -gt 0 ]; then
    log_success "Changes made: $CHANGES_MADE files updated"
    echo ""
    log_info "New hostname: $NEW_HOSTNAME"
    log_info "Access URL: https://${NEW_HOSTNAME}:8443"
    echo ""

    # Show any errors
    if [ ${#ERRORS[@]} -gt 0 ]; then
        log_warning "Warnings/Errors encountered:"
        for error in "${ERRORS[@]}"; do
            echo "  - $error"
        done
        echo ""
    fi

    # Restart instructions
    log_info "Next steps:"
    echo "  1. Restart STING services:"
    echo "     cd $STING_INSTALL_DIR"
    echo "     ./manage_sting.sh restart"
    echo ""
    echo "  2. Update /etc/hosts on client machines (if accessing remotely):"
    echo "     <SERVER_IP>  $NEW_HOSTNAME"
    echo ""
    echo "  3. Clear browser cache and cookies for old URLs"
    echo ""
    echo "  4. Access STING at: https://${NEW_HOSTNAME}:8443"
    echo ""
else
    log_warning "No changes were made - all files already configured correctly?"
fi

exit 0
