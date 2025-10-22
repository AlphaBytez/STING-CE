#!/bin/bash
# Local Ollama Installation Script for STING
# Installs Ollama in user directory without requiring sudo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[OLLAMA LOCAL]${NC} $1"
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

# Configuration
OLLAMA_HOME="${HOME}/.ollama"
OLLAMA_BIN="${OLLAMA_HOME}/bin"
OLLAMA_MODELS="${OLLAMA_HOME}/models"
OLLAMA_VERSION="${OLLAMA_VERSION:-latest}"

# Create directories
mkdir -p "${OLLAMA_BIN}"
mkdir -p "${OLLAMA_MODELS}"
mkdir -p "${OLLAMA_HOME}/logs"

# Detect architecture
ARCH=$(uname -m)
case ${ARCH} in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64|arm64)
        ARCH="arm64"
        ;;
    *)
        error "Unsupported architecture: ${ARCH}"
        exit 1
        ;;
esac

# Download Ollama binary
download_ollama() {
    log "Downloading Ollama binary for Linux ${ARCH}..."
    
    # Get latest version
    local latest_version=$(curl -sL https://api.github.com/repos/ollama/ollama/releases/latest | grep '"tag_name"' | cut -d '"' -f 4)
    log "Latest version: ${latest_version}"
    
    # Download URL for the tarball
    local download_url="https://github.com/ollama/ollama/releases/download/${latest_version}/ollama-linux-${ARCH}.tgz"
    log "Download URL: $download_url"
    
    local temp_file="/tmp/ollama-download-$$.tgz"
    
    # Download with progress
    if command -v wget >/dev/null 2>&1; then
        wget --show-progress -O "${temp_file}" "${download_url}"
    elif command -v curl >/dev/null 2>&1; then
        curl -L --progress-bar -o "${temp_file}" "${download_url}"
    else
        error "Neither wget nor curl found. Please install one of them."
        exit 1
    fi
    
    # Extract the binary
    log "Extracting Ollama binary..."
    cd "${OLLAMA_HOME}"
    tar -xzf "${temp_file}" || {
        error "Failed to extract Ollama archive"
        rm -f "${temp_file}"
        exit 1
    }
    
    # Move binary to the correct location
    if [ -f "${OLLAMA_HOME}/bin/bin/ollama" ]; then
        mv "${OLLAMA_HOME}/bin/bin/ollama" "${OLLAMA_BIN}/ollama"
        rm -rf "${OLLAMA_HOME}/bin/bin" "${OLLAMA_HOME}/bin/lib"
    elif [ -f "${OLLAMA_HOME}/bin/ollama" ]; then
        # Already in the right place
        true
    else
        error "Could not find ollama binary after extraction"
        exit 1
    fi
    
    # Clean up
    rm -f "${temp_file}"
    
    # Make executable
    chmod +x "${OLLAMA_BIN}/ollama"
    
    log "Ollama binary installed to ${OLLAMA_BIN}/ollama"
}

# Create systemd user service (optional)
create_service_file() {
    log "Creating Ollama service configuration..."
    
    cat > "${OLLAMA_HOME}/ollama.service" << EOF
#!/bin/bash
# Ollama service runner
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export OLLAMA_MODELS="${OLLAMA_MODELS}"
export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-5m}"

cd "${OLLAMA_HOME}"
exec "${OLLAMA_BIN}/ollama" serve
EOF
    
    chmod +x "${OLLAMA_HOME}/ollama.service"
    
    # Create start/stop scripts
    cat > "${OLLAMA_BIN}/ollama-start" << 'EOF'
#!/bin/bash
OLLAMA_HOME="$(dirname "$(dirname "$(readlink -f "$0")")")"
PIDFILE="${OLLAMA_HOME}/ollama.pid"

if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
    echo "Ollama is already running (PID: $(cat $PIDFILE))"
    exit 0
fi

echo "Starting Ollama service..."
nohup "${OLLAMA_HOME}/ollama.service" > "${OLLAMA_HOME}/logs/ollama.log" 2>&1 &
echo $! > "$PIDFILE"
echo "Ollama started (PID: $!)"
echo "Logs: ${OLLAMA_HOME}/logs/ollama.log"
EOF
    
    cat > "${OLLAMA_BIN}/ollama-stop" << 'EOF'
#!/bin/bash
OLLAMA_HOME="$(dirname "$(dirname "$(readlink -f "$0")")")"
PIDFILE="${OLLAMA_HOME}/ollama.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping Ollama (PID: $PID)..."
        kill $PID
        rm -f "$PIDFILE"
        echo "Ollama stopped"
    else
        echo "Ollama not running (stale PID file)"
        rm -f "$PIDFILE"
    fi
else
    echo "Ollama is not running"
fi
EOF
    
    chmod +x "${OLLAMA_BIN}/ollama-start" "${OLLAMA_BIN}/ollama-stop"
}

# Setup environment
setup_environment() {
    log "Setting up environment..."
    
    # Add to PATH in bashrc if not already there
    if ! grep -q "${OLLAMA_BIN}" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# Ollama local installation" >> ~/.bashrc
        echo "export PATH=\"${OLLAMA_BIN}:\$PATH\"" >> ~/.bashrc
        echo "export OLLAMA_MODELS=\"${OLLAMA_MODELS}\"" >> ~/.bashrc
    fi
    
    # Create wrapper script for easier access
    cat > "${OLLAMA_BIN}/ollama-wrapper" << EOF
#!/bin/bash
export OLLAMA_MODELS="${OLLAMA_MODELS}"
exec "${OLLAMA_BIN}/ollama" "\$@"
EOF
    chmod +x "${OLLAMA_BIN}/ollama-wrapper"
    
    # Symlink as 'ollama' for convenience
    ln -sf "${OLLAMA_BIN}/ollama-wrapper" "${OLLAMA_BIN}/ollama"
}

# Start Ollama service
start_ollama() {
    log "Starting Ollama service..."
    
    export PATH="${OLLAMA_BIN}:${PATH}"
    
    # Check if already running
    if pgrep -f "ollama serve" >/dev/null; then
        log "Ollama is already running"
        return 0
    fi
    
    # Start using our script
    "${OLLAMA_BIN}/ollama-start"
    
    # Wait for service to be ready
    log "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
            log "Ollama is ready!"
            return 0
        fi
        sleep 2
    done
    
    error "Ollama failed to start"
    return 1
}

# Download phi3 model
download_phi3() {
    log "Downloading phi3:mini model..."
    
    export PATH="${OLLAMA_BIN}:${PATH}"
    
    # Pull the model
    if "${OLLAMA_BIN}/ollama" pull phi3:mini; then
        log "Successfully downloaded phi3:mini"
    else
        error "Failed to download phi3:mini"
        return 1
    fi
    
    # Also get deepseek-r1 if requested
    if [ "${DOWNLOAD_DEEPSEEK:-false}" = "true" ]; then
        log "Downloading deepseek-r1:latest model..."
        "${OLLAMA_BIN}/ollama" pull deepseek-r1:latest || warning "Failed to download deepseek-r1"
    fi
}

# Test installation
test_installation() {
    log "Testing Ollama installation..."
    
    export PATH="${OLLAMA_BIN}:${PATH}"
    
    # List models
    log "Installed models:"
    "${OLLAMA_BIN}/ollama" list
    
    # Test generation
    log "Testing model generation..."
    echo "Say 'Hello, STING!' in a friendly way." | "${OLLAMA_BIN}/ollama" run phi3:mini || warning "Generation test failed"
    
    # Test API
    log "Testing API endpoint..."
    curl -s http://localhost:11434/v1/models | jq '.' || warning "API test failed"
}

# Main installation flow
main() {
    log "Starting local Ollama installation..."
    log "Installation directory: ${OLLAMA_HOME}"
    
    # Check if already installed
    if [ -f "${OLLAMA_BIN}/ollama" ]; then
        warning "Ollama already installed at ${OLLAMA_BIN}/ollama"
        read -p "Reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Using existing installation"
        else
            download_ollama
        fi
    else
        download_ollama
    fi
    
    # Setup environment and service files
    create_service_file
    setup_environment
    
    # Start service
    start_ollama || exit 1
    
    # Download models
    download_phi3 || exit 1
    
    # Test installation
    test_installation
    
    log "✅ Ollama installation completed!"
    log ""
    log "📝 Quick Start Guide:"
    log "  Start Ollama:  ${OLLAMA_BIN}/ollama-start"
    log "  Stop Ollama:   ${OLLAMA_BIN}/ollama-stop"
    log "  List models:   ${OLLAMA_BIN}/ollama list"
    log "  Chat:          ${OLLAMA_BIN}/ollama run phi3:mini"
    log ""
    log "🔧 Environment Setup:"
    log "  Add to your current shell: export PATH=\"${OLLAMA_BIN}:\$PATH\""
    log "  Or reload your shell:      source ~/.bashrc"
    log ""
    log "🐳 Docker Integration:"
    log "  The external-ai service will connect to: http://host.docker.internal:11434"
    log "  Test with: curl http://localhost:8091/ollama/status"
}

# Run main
main "$@"