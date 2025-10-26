#!/bin/bash
# fix_kratos_allowed_urls.sh - Fix Kratos allowed URLs for IP-based access
# This script updates kratos.yml to add IP-based URLs to allowed_return_urls and CORS origins

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
KRATOS_CONFIG="${INSTALL_DIR}/kratos/kratos.yml"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get current domain from config
get_current_domain() {
    local config_file="${INSTALL_DIR}/conf/config.yml"

    if [ -f "$config_file" ]; then
        # Try to extract domain using grep
        grep "^  domain:" "$config_file" | awk '{print $2}' | tr -d '"' | head -1
    else
        echo "localhost"
    fi
}

# Update Kratos configuration
update_kratos_config() {
    local domain=$1

    log_info "Updating Kratos configuration for domain: $domain"

    if [ ! -f "$KRATOS_CONFIG" ]; then
        log_error "Kratos config not found at $KRATOS_CONFIG"
        return 1
    fi

    # Backup original
    cp "$KRATOS_CONFIG" "$KRATOS_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"

    # Create temporary file for modifications
    local temp_file=$(mktemp)

    # Read through the file and add IP-based URLs if not already present
    python3 << EOF
import yaml
import sys

config_file = "${KRATOS_CONFIG}"
domain = "${domain}"

# Read the config
with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# Update serve.public.base_url
if 'serve' in config and 'public' in config['serve']:
    config['serve']['public']['base_url'] = f"https://{domain}:8443"

# Update CORS allowed_origins
if 'serve' in config and 'public' in config['serve'] and 'cors' in config['serve']['public']:
    origins = config['serve']['public']['cors'].get('allowed_origins', [])
    new_origins = [
        f"http://{domain}:8443",
        f"https://{domain}:8443"
    ]

    # Add new origins if not already present
    for origin in new_origins:
        if origin not in origins:
            origins.append(origin)

    config['serve']['public']['cors']['allowed_origins'] = origins

# Update selfservice URLs
if 'selfservice' in config:
    # Update default_browser_return_url
    config['selfservice']['default_browser_return_url'] = f"https://{domain}:8443/dashboard"

    # Update allowed_return_urls
    allowed_urls = config['selfservice'].get('allowed_return_urls', [])
    new_urls = [
        f"https://{domain}:8443",
        f"https://{domain}:8443/dashboard",
        f"https://{domain}:8443/login",
        f"https://{domain}:8443/register",
        f"https://{domain}:8443/post-registration",
        f"https://{domain}:8443/dashboard/reports",
        f"https://{domain}:8443/dashboard/settings",
        f"http://{domain}:8443",
        f"http://{domain}:8443/dashboard",
        f"http://{domain}:8443/login",
    ]

    for url in new_urls:
        if url not in allowed_urls:
            allowed_urls.append(url)

    config['selfservice']['allowed_return_urls'] = allowed_urls

    # Update UI URLs in flows
    if 'flows' in config['selfservice']:
        flows = config['selfservice']['flows']

        if 'error' in flows:
            flows['error']['ui_url'] = f"https://{domain}:8443/error"

        if 'settings' in flows:
            flows['settings']['ui_url'] = f"https://{domain}:8443/dashboard/settings?tab=security"

        if 'login' in flows:
            flows['login']['ui_url'] = f"https://{domain}:8443/login"
            if 'after' in flows['login']:
                flows['login']['after']['default_browser_return_url'] = f"https://{domain}:8443/dashboard"

        if 'registration' in flows:
            flows['registration']['ui_url'] = f"https://{domain}:8443/register"
            if 'after' in flows['registration']:
                flows['registration']['after']['default_browser_return_url'] = f"https://{domain}:8443/post-registration"

        if 'verification' in flows:
            flows['verification']['ui_url'] = f"https://{domain}:8443/verification"
            if 'after' in flows['verification']:
                flows['verification']['after']['default_browser_return_url'] = f"https://{domain}:8443/dashboard"

        if 'recovery' in flows:
            flows['recovery']['ui_url'] = f"https://{domain}:8443/recovery"

        if 'logout' in flows and 'after' in flows['logout']:
            flows['logout']['after']['default_browser_return_url'] = f"https://{domain}:8443/login"

# Update WebAuthn RP configuration
if 'selfservice' in config and 'methods' in config['selfservice']:
    methods = config['selfservice']['methods']

    if 'webauthn' in methods and 'config' in methods['webauthn']:
        webauthn_config = methods['webauthn']['config']

        if 'rp' in webauthn_config:
            # Update RP ID
            webauthn_config['rp']['id'] = domain

            # Update RP origins
            origins = webauthn_config['rp'].get('origins', [])
            new_origins = [
                f"https://{domain}:8443",
                f"http://{domain}:8443"
            ]

            for origin in new_origins:
                if origin not in origins:
                    origins.append(origin)

            webauthn_config['rp']['origins'] = origins

# Update session cookie domain
if 'session' in config and 'cookie' in config['session']:
    config['session']['cookie']['domain'] = domain

# Write updated config
with open(config_file, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print(f"Updated Kratos configuration for domain: {domain}")
EOF

    if [ $? -eq 0 ]; then
        log_success "Kratos configuration updated successfully"
        return 0
    else
        log_error "Failed to update Kratos configuration"
        return 1
    fi
}

# Restart Kratos service
restart_kratos() {
    log_info "Restarting Kratos service..."

    cd "$INSTALL_DIR"

    if docker compose restart kratos; then
        log_success "Kratos restarted successfully"
        sleep 5
        return 0
    else
        log_error "Failed to restart Kratos"
        return 1
    fi
}

# Main function
main() {
    echo ""
    echo "=============================================="
    echo " Fix Kratos Allowed URLs"
    echo "=============================================="
    echo ""

    # Get current domain from config
    CURRENT_DOMAIN=$(get_current_domain)

    log_info "Current domain in config.yml: $CURRENT_DOMAIN"

    echo ""
    read -p "Use this domain? (Y/n) [or enter custom]: " -r INPUT

    if [[ -z "$INPUT" ]] || [[ "$INPUT" =~ ^[Yy]$ ]]; then
        DOMAIN="$CURRENT_DOMAIN"
    elif [[ "$INPUT" =~ ^[Nn]$ ]]; then
        read -p "Enter domain or IP: " CUSTOM_DOMAIN
        DOMAIN="$CUSTOM_DOMAIN"
    else
        DOMAIN="$INPUT"
    fi

    log_success "Using domain: $DOMAIN"

    echo ""
    log_info "This will:"
    echo "  1. Update Kratos allowed_return_urls"
    echo "  2. Update Kratos CORS allowed_origins"
    echo "  3. Update WebAuthn RP ID and origins"
    echo "  4. Update session cookie domain"
    echo "  5. Restart Kratos service"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled by user"
        exit 0
    fi

    # Update Kratos config
    if update_kratos_config "$DOMAIN"; then
        restart_kratos

        echo ""
        echo "=============================================="
        log_success "Kratos configuration updated!"
        echo "=============================================="
        echo ""
        echo "You can now access STING at: https://${DOMAIN}:8443"
        echo ""
    else
        log_error "Configuration update failed"
        exit 1
    fi
}

main "$@"
