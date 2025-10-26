#!/bin/bash
# Enhanced Ollama checker and installer for WSL2
# This script provides programmatic Ollama installation and verification for WSL2 environments

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OLLAMA_VERSION="${OLLAMA_VERSION:-v0.5.4}"
INSTALL_DIR="${HOME}/.ollama"
OLLAMA_BIN="${INSTALL_DIR}/bin/ollama"
OLLAMA_MODELS="${OLLAMA_MODELS:-phi3:mini deepseek-r1:latest}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

log() {
    echo -e "${GREEN}[OLLAMA CHECK]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Detect WSL2
is_wsl2() {
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
        if [[ -f /proc/sys/fs/binfmt_misc/WSLInterop ]]; then
            return 0  # WSL2
        fi
    fi
    return 1
}

# Check if Ollama is installed
check_ollama_installed() {
    # Check global installation first
    if command -v ollama >/dev/null 2>&1; then
        log "Ollama found in PATH: $(which ollama)"
        return 0
    fi
    
    # Check local installation
    if [[ -x "$OLLAMA_BIN" ]]; then
        log "Ollama found at: $OLLAMA_BIN"
        return 0
    fi
    
    return 1
}

# Check if Ollama service is running
check_ollama_running() {
    if curl -sf "http://localhost:${OLLAMA_PORT}/v1/models" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Get Ollama version
get_ollama_version() {
    local ollama_cmd
    if command -v ollama >/dev/null 2>&1; then
        ollama_cmd="ollama"
    elif [[ -x "$OLLAMA_BIN" ]]; then
        ollama_cmd="$OLLAMA_BIN"
    else
        echo "unknown"
        return
    fi
    
    $ollama_cmd --version 2>/dev/null | grep -oE 'ollama version [0-9.]+' | cut -d' ' -f3 || echo "unknown"
}

# Check installed models
check_installed_models() {
    local ollama_cmd
    if command -v ollama >/dev/null 2>&1; then
        ollama_cmd="ollama"
    elif [[ -x "$OLLAMA_BIN" ]]; then
        ollama_cmd="$OLLAMA_BIN"
    else
        return 1
    fi
    
    log "Checking installed models..."
    local models=$($ollama_cmd list 2>/dev/null | tail -n +2 | awk '{print $1}')
    
    if [[ -z "$models" ]]; then
        warning "No models installed"
        return 1
    else
        info "Installed models:"
        echo "$models" | while read -r model; do
            echo "  - $model"
        done
        return 0
    fi
}

# Install Ollama for WSL2
install_ollama_wsl2() {
    log "Installing Ollama for WSL2..."
    
    # Create directories
    mkdir -p "${INSTALL_DIR}/bin"
    
    # Detect architecture
    local arch
    case $(uname -m) in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) error "Unsupported architecture: $(uname -m)"; return 1 ;;
    esac
    
    # Download Ollama binary
    local download_url="https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-${arch}"
    
    log "Downloading Ollama ${OLLAMA_VERSION} for Linux ${arch}..."
    if ! curl -L --progress-bar "$download_url" -o "$OLLAMA_BIN"; then
        error "Failed to download Ollama"
        return 1
    fi
    
    # Make executable
    chmod +x "$OLLAMA_BIN"
    
    # Create start script
    cat > "${INSTALL_DIR}/start_ollama.sh" << 'EOF'
#!/bin/bash
OLLAMA_DIR="$(dirname "$0")"
export OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0:11434}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-5m}"

echo "Starting Ollama service..."
nohup "$OLLAMA_DIR/bin/ollama" serve > "$OLLAMA_DIR/ollama.log" 2>&1 &
echo $! > "$OLLAMA_DIR/ollama.pid"
echo "Ollama started with PID: $(cat "$OLLAMA_DIR/ollama.pid")"
echo "Logs: $OLLAMA_DIR/ollama.log"
EOF
    chmod +x "${INSTALL_DIR}/start_ollama.sh"
    
    # Create stop script
    cat > "${INSTALL_DIR}/stop_ollama.sh" << 'EOF'
#!/bin/bash
OLLAMA_DIR="$(dirname "$0")"
if [[ -f "$OLLAMA_DIR/ollama.pid" ]]; then
    PID=$(cat "$OLLAMA_DIR/ollama.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Ollama (PID: $PID)..."
        kill "$PID"
        rm -f "$OLLAMA_DIR/ollama.pid"
        echo "Ollama stopped"
    else
        echo "Ollama not running"
        rm -f "$OLLAMA_DIR/ollama.pid"
    fi
else
    echo "No PID file found"
fi
EOF
    chmod +x "${INSTALL_DIR}/stop_ollama.sh"
    
    # Update PATH in .bashrc if not already present
    if ! grep -q "/.ollama/bin" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# Ollama" >> ~/.bashrc
        echo "export PATH=\"\$HOME/.ollama/bin:\$PATH\"" >> ~/.bashrc
        echo "export OLLAMA_HOST=\"0.0.0.0:11434\"" >> ~/.bashrc
    fi
    
    # Export for current session
    export PATH="$HOME/.ollama/bin:$PATH"
    
    log "Ollama installed successfully!"
    info "Installation directory: $INSTALL_DIR"
    info "To start Ollama: ${INSTALL_DIR}/start_ollama.sh"
    info "To stop Ollama: ${INSTALL_DIR}/stop_ollama.sh"
    
    return 0
}

# Start Ollama service
start_ollama_service() {
    if check_ollama_running; then
        log "Ollama is already running"
        return 0
    fi
    
    log "Starting Ollama service..."
    
    # Try local installation first
    if [[ -x "${INSTALL_DIR}/start_ollama.sh" ]]; then
        "${INSTALL_DIR}/start_ollama.sh"
    elif command -v ollama >/dev/null 2>&1; then
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        echo $! > /tmp/ollama.pid
    else
        error "Ollama not found"
        return 1
    fi
    
    # Wait for service to be ready
    log "Waiting for Ollama to start..."
    for i in {1..30}; do
        if check_ollama_running; then
            log "Ollama is ready!"
            return 0
        fi
        sleep 2
    done
    
    error "Ollama failed to start"
    return 1
}

# Download required models
download_models() {
    local ollama_cmd
    if command -v ollama >/dev/null 2>&1; then
        ollama_cmd="ollama"
    elif [[ -x "$OLLAMA_BIN" ]]; then
        ollama_cmd="$OLLAMA_BIN"
    else
        error "Ollama not found"
        return 1
    fi
    
    log "Downloading required models..."
    
    for model in $OLLAMA_MODELS; do
        info "Downloading $model..."
        if $ollama_cmd pull "$model"; then
            log "✅ $model downloaded successfully"
        else
            warning "Failed to download $model"
        fi
    done
}

# Run diagnostics
run_diagnostics() {
    echo "=== Ollama Diagnostics for WSL2 ==="
    echo ""
    
    # Check WSL2
    if is_wsl2; then
        info "✅ Running in WSL2"
    else
        warning "Not running in WSL2"
    fi
    
    # Check installation
    if check_ollama_installed; then
        info "✅ Ollama is installed (version: $(get_ollama_version))"
    else
        error "❌ Ollama is not installed"
    fi
    
    # Check service
    if check_ollama_running; then
        info "✅ Ollama service is running on port $OLLAMA_PORT"
    else
        warning "❌ Ollama service is not running"
    fi
    
    # Check models
    if check_ollama_installed; then
        check_installed_models
    fi
    
    # Check network accessibility
    echo ""
    log "Checking network accessibility..."
    if curl -sf "http://localhost:${OLLAMA_PORT}/v1/models" >/dev/null 2>&1; then
        info "✅ API accessible at http://localhost:${OLLAMA_PORT}"
    else
        warning "❌ API not accessible"
    fi
    
    # Custom domain check
    if [[ -n "$DOMAIN_NAME" ]] && [[ "$DOMAIN_NAME" != "localhost" ]]; then
        if curl -sf "http://${DOMAIN_NAME}:${OLLAMA_PORT}/v1/models" >/dev/null 2>&1; then
            info "✅ API accessible at http://${DOMAIN_NAME}:${OLLAMA_PORT}"
        else
            warning "❌ API not accessible via custom domain ${DOMAIN_NAME}"
        fi
    fi
}

# Main installation flow
install_flow() {
    log "Starting automated Ollama setup for WSL2..."
    
    # Check if already installed
    if check_ollama_installed; then
        log "Ollama is already installed"
        
        # Check if running
        if ! check_ollama_running; then
            log "Starting Ollama service..."
            if ! start_ollama_service; then
                error "Failed to start Ollama service"
                return 1
            fi
        fi
    else
        # Install Ollama
        if ! install_ollama_wsl2; then
            error "Failed to install Ollama"
            return 1
        fi
        
        # Start service
        if ! start_ollama_service; then
            error "Failed to start Ollama service"
            return 1
        fi
    fi
    
    # Download models if needed
    if ! check_installed_models >/dev/null 2>&1; then
        download_models
    fi
    
    log "✅ Ollama setup complete!"
    return 0
}

# Custom domain configuration helper
configure_custom_domain() {
    local domain="${1:-sting.local}"
    
    log "Configuring Ollama for custom domain: $domain"
    
    # Update Ollama host configuration
    export OLLAMA_HOST="0.0.0.0:${OLLAMA_PORT}"
    
    # Create systemd service file for WSL2 (if systemd is available)
    if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running &>/dev/null; then
        info "Creating systemd service for automatic startup..."
        
        sudo tee /etc/systemd/system/ollama.service > /dev/null << EOF
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=$USER
Environment="OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT}"
Environment="OLLAMA_MODELS=$HOME/.ollama/models"
ExecStart=$OLLAMA_BIN serve
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable ollama.service
        sudo systemctl start ollama.service
        
        info "Ollama configured as systemd service"
    fi
    
    # Add to Windows hosts file reminder
    warning "Remember to add this to your Windows hosts file (C:\\Windows\\System32\\drivers\\etc\\hosts):"
    echo "  127.0.0.1    $domain"
    echo "  ::1          $domain"
}

# Usage
case "${1:-check}" in
    check|status)
        run_diagnostics
        ;;
    install)
        install_flow
        ;;
    start)
        start_ollama_service
        ;;
    stop)
        if [[ -x "${INSTALL_DIR}/stop_ollama.sh" ]]; then
            "${INSTALL_DIR}/stop_ollama.sh"
        else
            error "Stop script not found"
        fi
        ;;
    models)
        check_installed_models
        ;;
    download-models)
        download_models
        ;;
    configure-domain)
        configure_custom_domain "${2:-sting.local}"
        ;;
    test)
        # Test Ollama with a simple prompt
        if command -v ollama >/dev/null 2>&1; then
            ollama run phi3:mini "Hello, are you working?"
        elif [[ -x "$OLLAMA_BIN" ]]; then
            "$OLLAMA_BIN" run phi3:mini "Hello, are you working?"
        else
            error "Ollama not found"
        fi
        ;;
    *)
        echo "Ollama WSL2 Check and Install Script"
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  check|status      - Run diagnostics and check Ollama status"
        echo "  install           - Install Ollama if not present and set up models"
        echo "  start             - Start Ollama service"
        echo "  stop              - Stop Ollama service"
        echo "  models            - List installed models"
        echo "  download-models   - Download required models"
        echo "  configure-domain  - Configure Ollama for custom domain access"
        echo "  test              - Test Ollama with a simple prompt"
        echo ""
        echo "Environment Variables:"
        echo "  OLLAMA_VERSION    - Ollama version to install (default: v0.5.4)"
        echo "  OLLAMA_MODELS     - Models to download (default: 'phi3:mini deepseek-r1:latest')"
        echo "  OLLAMA_PORT       - Port for Ollama API (default: 11434)"
        echo "  DOMAIN_NAME       - Custom domain for testing (default: localhost)"
        ;;
esac