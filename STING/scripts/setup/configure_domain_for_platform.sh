#!/bin/bash
# configure_domain_for_platform.sh - Auto-detect platform and configure domain
# This script detects if running on Mac (localhost) or Linux/Ubuntu (IP-based)
# and updates config.yml accordingly, then regenerates env files.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

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

# Detect platform
detect_platform() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
    elif [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
        echo "wsl2"
    elif [[ "$(uname)" == "Linux" ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Detect IP address for Linux/WSL
detect_ip_address() {
    local platform=$1

    case "$platform" in
        macos)
            # Mac uses localhost
            echo "localhost"
            ;;
        wsl2)
            # WSL2: Get Windows host IP or WSL IP
            # Try to get the WSL IP that's accessible from Windows
            ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "localhost"
            ;;
        linux)
            # Linux: Get primary network interface IP
            ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1 || echo "localhost"
            ;;
        *)
            echo "localhost"
            ;;
    esac
}

# Update config.yml with detected domain
update_config_yml() {
    local domain=$1
    local config_file="${INSTALL_DIR}/conf/config.yml"

    if [ ! -f "$config_file" ]; then
        log_error "Config file not found at $config_file"
        return 1
    fi

    log_info "Updating config.yml with domain: $domain"

    # Backup original
    cp "$config_file" "$config_file.backup.$(date +%Y%m%d_%H%M%S)"

    # Update system.domain using yq if available, otherwise sed
    if command -v yq &> /dev/null; then
        yq eval ".system.domain = \"$domain\"" -i "$config_file"
        log_success "Updated config.yml using yq"
    else
        # Fallback to sed
        sed -i "s|^  domain:.*|  domain: $domain  # Auto-configured by platform detection|" "$config_file"
        log_success "Updated config.yml using sed"
    fi
}

# Regenerate environment files using config_loader.py
regenerate_env_files() {
    log_info "Regenerating environment files..."

    cd "${INSTALL_DIR}/conf"

    # Run config_loader.py
    if [ -f "config_loader.py" ]; then
        python3 config_loader.py config.yml --mode runtime
        log_success "Environment files regenerated"
    else
        log_error "config_loader.py not found"
        return 1
    fi
}

# Update frontend env.js files directly (for runtime reload)
update_frontend_env_js() {
    local domain=$1
    local protocol="${2:-https}"

    log_info "Updating frontend env.js files for runtime..."

    # Update frontend public/env.js
    local frontend_env="${INSTALL_DIR}/frontend/public/env.js"
    if [ -f "$frontend_env" ]; then
        cat > "$frontend_env" <<EOF
window.env = {
  REACT_APP_API_URL: '${protocol}://${domain}:5050',
  REACT_APP_KRATOS_PUBLIC_URL: '${protocol}://${domain}:4433',
  REACT_APP_KRATOS_BROWSER_URL: '${protocol}://${domain}:4433'
};
EOF
        log_success "Updated $frontend_env"
    fi

    # Update app static/env.js
    local app_env="${INSTALL_DIR}/app/static/env.js"
    if [ -f "$app_env" ]; then
        cat > "$app_env" <<EOF
window.env = {
  REACT_APP_API_URL: '${protocol}://${domain}:5050',
  REACT_APP_KRATOS_PUBLIC_URL: '${protocol}://${domain}:4433',
  REACT_APP_KRATOS_BROWSER_URL: '${protocol}://${domain}:4433'
};
EOF
        log_success "Updated $app_env"
    fi
}

# Restart affected services
restart_services() {
    log_info "Restarting affected services..."

    cd "$INSTALL_DIR"

    # Check if docker compose is available
    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose not available"
        return 1
    fi

    # Restart Kratos (auth changes)
    log_info "Restarting Kratos..."
    docker compose restart kratos
    sleep 5

    # Restart frontend (new env vars)
    log_info "Restarting frontend..."
    docker compose restart frontend
    sleep 3

    # Restart app (new env vars)
    log_info "Restarting app..."
    docker compose restart app

    log_success "Services restarted"
}

# Main function
main() {
    echo ""
    echo "=============================================="
    echo " STING Platform Domain Configuration"
    echo "=============================================="
    echo ""

    # Detect platform
    PLATFORM=$(detect_platform)
    log_info "Detected platform: $PLATFORM"

    # Detect appropriate domain/IP
    DETECTED_DOMAIN=$(detect_ip_address "$PLATFORM")
    log_info "Detected domain/IP: $DETECTED_DOMAIN"

    # Allow user override
    echo ""
    log_info "Detected configuration:"
    echo "  Platform: $PLATFORM"
    echo "  Domain/IP: $DETECTED_DOMAIN"
    echo ""

    read -p "Use this domain/IP? (Y/n) [or enter custom]: " -r INPUT

    if [[ -z "$INPUT" ]] || [[ "$INPUT" =~ ^[Yy]$ ]]; then
        DOMAIN="$DETECTED_DOMAIN"
    elif [[ "$INPUT" =~ ^[Nn]$ ]]; then
        read -p "Enter custom domain or IP: " CUSTOM_DOMAIN
        DOMAIN="$CUSTOM_DOMAIN"
    else
        DOMAIN="$INPUT"
    fi

    log_success "Using domain: $DOMAIN"

    echo ""
    log_info "This will:"
    echo "  1. Update ${INSTALL_DIR}/conf/config.yml"
    echo "  2. Regenerate all environment files"
    echo "  3. Update frontend runtime env.js files"
    echo "  4. Restart Kratos, frontend, and app services"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled by user"
        exit 0
    fi

    # Execute configuration updates
    update_config_yml "$DOMAIN"
    regenerate_env_files
    update_frontend_env_js "$DOMAIN"
    restart_services

    echo ""
    echo "=============================================="
    log_success "Domain configuration completed!"
    echo "=============================================="
    echo ""
    echo "Access STING at: https://${DOMAIN}:8443"
    echo ""

    if [[ "$PLATFORM" != "macos" ]] && [[ "$DOMAIN" != "localhost" ]]; then
        log_warning "Note: You may need to accept the self-signed certificate"
        log_info "If you still have login redirect issues, run:"
        echo "  cd ${INSTALL_DIR} && bash scripts/setup/fix_kratos_allowed_urls.sh"
    fi

    echo ""
}

main "$@"
