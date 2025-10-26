#!/bin/bash
# WSL2 Quick Setup Script for STING with Custom Domain
# This script automates the configuration of STING for WSL2 environments

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default configuration
DEFAULT_DOMAIN="sting.local"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Functions
log() {
    echo -e "${GREEN}[WSL2 SETUP]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if running in WSL2
check_wsl2() {
    if [[ ! -f /proc/version ]] || ! grep -qi microsoft /proc/version; then
        error "This script is designed for WSL2 environments only"
    fi
    
    if [[ ! -f /proc/sys/fs/binfmt_misc/WSLInterop ]]; then
        error "This appears to be WSL1. Please upgrade to WSL2"
    fi
    
    log "✅ WSL2 environment detected"
}

# Prompt for domain
get_domain() {
    echo ""
    info "Custom domains help avoid WSL2 networking issues with localhost"
    echo -e "${CYAN}Enter custom domain (default: $DEFAULT_DOMAIN):${NC} "
    read -r custom_domain
    
    DOMAIN="${custom_domain:-$DEFAULT_DOMAIN}"
    log "Using domain: $DOMAIN"
}

# Create environment file
create_env_file() {
    log "Creating environment configuration..."
    
    cat > "$PROJECT_DIR/.env.wsl2" << EOF
# WSL2 Custom Domain Configuration
DOMAIN_NAME=$DOMAIN
REACT_APP_API_URL=https://$DOMAIN:5050
REACT_APP_KRATOS_PUBLIC_URL=https://$DOMAIN:4433
PUBLIC_URL=https://$DOMAIN:8443
WEBAUTHN_RP_ID=$DOMAIN

# Ollama Configuration
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS="phi3:mini deepseek-r1:latest"
OLLAMA_AUTO_INSTALL=true

# WSL2 Optimizations
COMPOSE_HTTP_TIMEOUT=120
DOCKER_CLIENT_TIMEOUT=120
EOF
    
    log "Environment file created: .env.wsl2"
}

# Update config.yml
update_config() {
    log "Updating configuration for custom domain..."
    
    local config_file="$PROJECT_DIR/conf/config.yml"
    
    if [[ -f "$config_file" ]]; then
        # Backup original
        cp "$config_file" "${config_file}.backup"
        
        # Update using Python for proper YAML handling
        python3 << EOF
import yaml
import sys

with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)

# Update domain references
config['application']['host'] = '$DOMAIN'
config['application']['ssl']['domain'] = '$DOMAIN'
config['frontend']['react']['api_url'] = 'https://$DOMAIN:5050'
config['kratos']['public_url'] = 'https://$DOMAIN:4433'
config['kratos']['cookie_domain'] = '$DOMAIN'
config['kratos']['selfservice']['default_return_url'] = 'https://$DOMAIN:8443'
config['kratos']['selfservice']['login']['ui_url'] = 'https://$DOMAIN:8443/login'
config['kratos']['selfservice']['registration']['ui_url'] = 'https://$DOMAIN:8443/register'
config['kratos']['methods']['webauthn']['rp_id'] = '$DOMAIN'
config['kratos']['methods']['webauthn']['origin'] = 'https://$DOMAIN:8443'

with open('$config_file', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("✅ Configuration updated successfully")
EOF
    else
        warning "config.yml not found, will use environment variables only"
    fi
}

# Generate Windows hosts file entry
generate_hosts_entry() {
    log "Generating Windows hosts file entry..."
    
    local hosts_entry="# STING WSL2 Custom Domain
127.0.0.1    $DOMAIN
::1          $DOMAIN"
    
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}IMPORTANT: Add these lines to your Windows hosts file:${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "$hosts_entry"
    echo ""
    echo -e "${INFO}Windows hosts file location:${NC}"
    echo "C:\\Windows\\System32\\drivers\\etc\\hosts"
    echo ""
    echo -e "${INFO}To edit (requires Administrator):${NC}"
    echo "1. Press Win+R, type: notepad C:\\Windows\\System32\\drivers\\etc\\hosts"
    echo "2. Right-click Notepad and 'Run as Administrator'"
    echo "3. Add the lines above and save"
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    
    # Save to file for easy copying
    echo "$hosts_entry" > "$PROJECT_DIR/hosts_entry_for_windows.txt"
    log "Hosts entry saved to: hosts_entry_for_windows.txt"
}

# Install Ollama for WSL2
setup_ollama() {
    log "Setting up Ollama for WSL2..."
    
    if [[ -x "$PROJECT_DIR/scripts/check_and_install_ollama_wsl2.sh" ]]; then
        # Source the environment
        source "$PROJECT_DIR/.env.wsl2"
        
        # Run Ollama setup
        "$PROJECT_DIR/scripts/check_and_install_ollama_wsl2.sh" install
        "$PROJECT_DIR/scripts/check_and_install_ollama_wsl2.sh" configure-domain "$DOMAIN"
    else
        warning "Ollama WSL2 script not found, skipping Ollama setup"
    fi
}

# Create launch script
create_launch_script() {
    log "Creating WSL2 launch script..."
    
    cat > "$PROJECT_DIR/launch_sting_wsl2.sh" << 'EOF'
#!/bin/bash
# Launch STING with WSL2 optimizations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load WSL2 environment
if [[ -f "$SCRIPT_DIR/.env.wsl2" ]]; then
    source "$SCRIPT_DIR/.env.wsl2"
    export $(grep -v '^#' "$SCRIPT_DIR/.env.wsl2" | xargs)
fi

# Start Ollama first (if not running)
if ! curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
    echo "Starting Ollama..."
    if [[ -x "$SCRIPT_DIR/scripts/check_and_install_ollama_wsl2.sh" ]]; then
        "$SCRIPT_DIR/scripts/check_and_install_ollama_wsl2.sh" start
    fi
fi

# Launch STING
echo "Starting STING with custom domain: $DOMAIN_NAME"
"$SCRIPT_DIR/manage_sting.sh" start

echo ""
echo "STING is starting up!"
echo "Access the application at: https://$DOMAIN_NAME:8443"
echo ""
echo "If you haven't already, make sure to:"
echo "1. Add the domain to your Windows hosts file"
echo "2. Accept the self-signed certificate in your browser"
EOF
    
    chmod +x "$PROJECT_DIR/launch_sting_wsl2.sh"
    log "Launch script created: launch_sting_wsl2.sh"
}

# Main execution
main() {
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}       WSL2 Quick Setup for STING with Custom Domain${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check environment
    check_wsl2
    
    # Get configuration
    get_domain
    
    # Create configuration files
    create_env_file
    update_config
    
    # Generate hosts entry
    generate_hosts_entry
    
    # Setup Ollama
    echo ""
    read -p "Setup Ollama for WSL2 now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_ollama
    fi
    
    # Create launch script
    create_launch_script
    
    # Final instructions
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ WSL2 setup complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Add the domain to your Windows hosts file (see above)"
    echo "2. Run the installation: ./install_sting.sh install"
    echo "3. Or use the quick launcher: ./launch_sting_wsl2.sh"
    echo ""
    echo -e "${INFO}Your custom domain:${NC} https://$DOMAIN:8443"
    echo ""
    echo -e "${GREEN}Happy STINGing! 🐝${NC}"
}

# Run main
main