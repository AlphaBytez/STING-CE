#!/bin/bash
# Ollama Installation Script for STING
# Universal installer for Mac, Linux, and Windows/WSL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[OLLAMA INSTALL]${NC} $1"
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

# Detect platform
PLATFORM="$(uname)"
ARCH="$(uname -m)"

# Default models to install
DEFAULT_MODELS="${OLLAMA_MODELS_TO_INSTALL:-phi3:mini,deepseek-r1:latest}"

check_ollama_installed() {
    if command -v ollama >/dev/null 2>&1; then
        log "Ollama is already installed"
        ollama --version
        return 0
    else
        return 1
    fi
}

install_ollama() {
    log "Installing Ollama for $PLATFORM ($ARCH)..."
    
    case "$PLATFORM" in
        "Darwin")
            # macOS installation
            if command -v brew >/dev/null 2>&1; then
                log "Installing Ollama via Homebrew..."
                brew install ollama
            else
                log "Installing Ollama via official installer..."
                curl -fsSL https://ollama.ai/install.sh | sh
            fi
            ;;
        "Linux")
            # Linux installation
            log "Installing Ollama via official installer..."
            curl -fsSL https://ollama.ai/install.sh | sh
            ;;
        "MINGW"*|"CYGWIN"*|"MSYS"*)
            # Windows/WSL
            error "Windows installation requires manual download from https://ollama.ai/download"
            error "Please install Ollama manually and run this script again"
            return 1
            ;;
        *)
            error "Unsupported platform: $PLATFORM"
            return 1
            ;;
    esac
}

start_ollama_service() {
    log "Starting Ollama service..."
    
    case "$PLATFORM" in
        "Darwin")
            # macOS - start as background service
            if ! pgrep -f "ollama serve" >/dev/null; then
                log "Starting Ollama daemon..."
                nohup ollama serve >/dev/null 2>&1 &
                sleep 3
            fi
            ;;
        "Linux")
            # Linux - use systemd if available
            if command -v systemctl >/dev/null 2>&1; then
                log "Starting Ollama systemd service..."
                sudo systemctl start ollama || {
                    warning "Systemd service not available, starting manually..."
                    nohup ollama serve >/dev/null 2>&1 &
                    sleep 3
                }
                sudo systemctl enable ollama 2>/dev/null || true
            else
                log "Starting Ollama daemon manually..."
                nohup ollama serve >/dev/null 2>&1 &
                sleep 3
            fi
            ;;
    esac
    
    # Wait for Ollama to be ready
    log "Waiting for Ollama to be ready..."
    for i in {1..30}; do
        if curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
            log "Ollama is ready!"
            return 0
        fi
        sleep 2
    done
    
    error "Ollama failed to start or is not responding"
    return 1
}

install_models() {
    local models="$1"
    log "Installing Ollama models: $models"
    
    IFS=',' read -ra MODEL_ARRAY <<< "$models"
    for model in "${MODEL_ARRAY[@]}"; do
        model=$(echo "$model" | xargs)  # trim whitespace
        if [ -n "$model" ]; then
            log "Installing model: $model"
            if ollama pull "$model"; then
                log "[+] Successfully installed: $model"
            else
                error "[-] Failed to install: $model"
            fi
        fi
    done
}

verify_installation() {
    log "Verifying Ollama installation..."
    
    # Check if Ollama is running
    if ! curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
        error "Ollama is not responding on port 11434"
        return 1
    fi
    
    # List installed models
    log "Installed models:"
    ollama list
    
    # Test with a simple prompt
    log "Testing Ollama with a simple prompt..."
    local test_model
    if ollama list | grep -q "phi3:mini"; then
        test_model="phi3:mini"
    elif ollama list | grep -q "deepseek-r1:latest"; then
        test_model="deepseek-r1:latest"
    else
        warning "No test models available"
        return 0
    fi
    
    log "Testing with model: $test_model"
    echo "Hello, this is a test." | ollama run "$test_model" --verbose=false | head -3
    
    log "[+] Ollama installation verified successfully!"
}

main() {
    log "STING Ollama Installation Script"
    log "Platform: $PLATFORM ($ARCH)"
    
    # Check if already installed
    if check_ollama_installed; then
        info "Ollama is already installed, checking service status..."
    else
        # Install Ollama
        install_ollama || {
            error "Failed to install Ollama"
            exit 1
        }
    fi
    
    # Start Ollama service
    start_ollama_service || {
        error "Failed to start Ollama service"
        exit 1
    }
    
    # Install default models
    if [ "${OLLAMA_AUTO_INSTALL:-true}" = "true" ]; then
        install_models "$DEFAULT_MODELS"
    else
        info "Skipping model installation (OLLAMA_AUTO_INSTALL=false)"
    fi
    
    # Verify installation
    verify_installation || {
        error "Installation verification failed"
        exit 1
    }
    
    log " Ollama installation completed successfully!"
    log "You can now use Ollama with STING's AI features"
    log ""
    log "Useful commands:"
    log "  ollama list                    # List installed models"
    log "  ollama pull <model>           # Install a new model"
    log "  ollama run <model>            # Chat with a model"
    log "  ./sting-llm status            # Check STING LLM services"
}

# Run main function
main "$@"