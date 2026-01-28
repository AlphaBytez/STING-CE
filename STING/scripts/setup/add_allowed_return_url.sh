#!/bin/bash
# add_allowed_return_url.sh - Add a custom URL to Kratos allowed_return_urls
# Useful for Codespaces, Gitpod, and other forwarded environments

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

# Function to add URL to allowed_return_urls
add_allowed_url() {
    local new_url=$1

    log_info "Adding URL to Kratos allowed_return_urls: $new_url"

    if [ ! -f "$KRATOS_CONFIG" ]; then
        log_error "Kratos config not found at $KRATOS_CONFIG"
        return 1
    fi

    # Backup original
    cp "$KRATOS_CONFIG" "$KRATOS_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"

    # Use Python to add the URL if it doesn't already exist
    python3 << EOF
import yaml
import sys

config_file = "${KRATOS_CONFIG}"
new_url = "${new_url}"

# Read the config
with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# Update allowed_return_urls
if 'selfservice' in config:
    allowed_urls = config['selfservice'].get('allowed_return_urls', [])

    # Add the new URL and common paths
    urls_to_add = [
        new_url,
        f"{new_url}/",
        f"{new_url}/dashboard",
        f"{new_url}/login",
        f"{new_url}/register",
        f"{new_url}/post-registration",
        f"{new_url}/dashboard/settings",
        f"{new_url}/dashboard/reports",
        f"{new_url}/*",  # Wildcard to match all paths
    ]

    added_count = 0
    for url in urls_to_add:
        if url not in allowed_urls:
            allowed_urls.append(url)
            added_count += 1

    config['selfservice']['allowed_return_urls'] = allowed_urls

    # Also update CORS origins if needed
    if 'serve' in config and 'public' in config['serve'] and 'cors' in config['serve']['public']:
        origins = config['serve']['public']['cors'].get('allowed_origins', [])
        if new_url not in origins:
            origins.append(new_url)
            config['serve']['public']['cors']['allowed_origins'] = origins

    # Write updated config
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Added {added_count} new URLs to allowed_return_urls")
else:
    print("Error: selfservice section not found in Kratos config")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "URLs added successfully to Kratos configuration"
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
    echo " Add Allowed Return URL to Kratos"
    echo "=============================================="
    echo ""

    # Detect if running in a known forwarded environment
    if [ -n "$CODESPACE_NAME" ]; then
        log_info "GitHub Codespaces detected"
        # Construct the Codespaces URL
        AUTO_URL="https://${CODESPACE_NAME}-8443.app.github.dev"
        log_info "Detected URL: $AUTO_URL"
        echo ""
        read -p "Use this URL? (Y/n) [or enter custom]: " -r INPUT

        if [[ -z "$INPUT" ]] || [[ "$INPUT" =~ ^[Yy]$ ]]; then
            URL="$AUTO_URL"
        elif [[ "$INPUT" =~ ^[Nn]$ ]]; then
            read -p "Enter custom URL (e.g., https://xxx-8443.app.github.dev): " CUSTOM_URL
            URL="$CUSTOM_URL"
        else
            URL="$INPUT"
        fi
    elif [ -n "$GITPOD_WORKSPACE_URL" ]; then
        log_info "Gitpod detected"
        # Gitpod URL pattern: https://8443-workspace-id.gitpod.io
        AUTO_URL="${GITPOD_WORKSPACE_URL/https:\/\//https://8443-}"
        log_info "Detected URL: $AUTO_URL"
        echo ""
        read -p "Use this URL? (Y/n) [or enter custom]: " -r INPUT

        if [[ -z "$INPUT" ]] || [[ "$INPUT" =~ ^[Yy]$ ]]; then
            URL="$AUTO_URL"
        elif [[ "$INPUT" =~ ^[Nn]$ ]]; then
            read -p "Enter custom URL: " CUSTOM_URL
            URL="$CUSTOM_URL"
        else
            URL="$INPUT"
        fi
    else
        log_info "Enter the URL you're accessing STING from"
        echo "  Examples:"
        echo "    - https://xxx-8443.app.github.dev (Codespaces)"
        echo "    - https://8443-workspace.gitpod.io (Gitpod)"
        echo "    - https://your-vm.example.com:8443 (Custom VM)"
        echo ""
        read -p "URL: " URL
    fi

    # Validate URL format
    if [[ ! "$URL" =~ ^https?:// ]]; then
        log_error "Invalid URL format. Must start with http:// or https://"
        exit 1
    fi

    log_success "Using URL: $URL"

    echo ""
    log_info "This will:"
    echo "  1. Add the URL to Kratos allowed_return_urls"
    echo "  2. Add the URL to CORS allowed_origins"
    echo "  3. Restart Kratos service"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled by user"
        exit 0
    fi

    # Add the URL
    if add_allowed_url "$URL"; then
        restart_kratos

        echo ""
        echo "=============================================="
        log_success "URL added successfully!"
        echo "=============================================="
        echo ""
        echo "You can now access STING at: $URL"
        echo ""
        log_info "Your frontend will automatically use this URL for redirects"
        echo ""
    else
        log_error "Configuration update failed"
        exit 1
    fi
}

main "$@"
