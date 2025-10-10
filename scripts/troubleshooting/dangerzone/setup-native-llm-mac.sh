#!/bin/bash
# Setup Native LLM Service for macOS
# This script ensures the native sting-llm service is properly configured and started on Mac

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[NATIVE-LLM]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[NATIVE-LLM]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if modern Ollama + External AI stack is running
check_modern_stack() {
    # Check if Ollama is running
    if pgrep -f "ollama" >/dev/null 2>&1; then
        # Check if External AI service is running
        if curl -sf http://localhost:8091/health >/dev/null 2>&1; then
            return 0  # Modern stack is running
        fi
    fi
    return 1  # Modern stack not running
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    error "This script is only for macOS systems"
    exit 1
fi

log "Setting up native LLM service for macOS with MPS acceleration..."

# 1. Stop any Docker LLM gateway that might be running
log "Stopping Docker LLM gateway (if running)..."
docker stop sting-ce-llm-gateway 2>/dev/null || true

# 2. Skip local model check - using HuggingFace models
log "Using HuggingFace models - will download automatically on first use"

# 3. Verify nginx proxy configuration exists
log "Checking nginx proxy configuration..."
if [ ! -f "nginx-llm-proxy.conf" ]; then
    warning "nginx-llm-proxy.conf not found - proxy may not work correctly"
else
    log "Nginx proxy configuration found"
fi

# 4. Start the native sting-llm service
log "Starting native LLM service..."
if ./sting-llm start; then
    log "Native LLM service started successfully"
    
    # 5. Wait for service to be ready and test it
    sleep 5
    # Check the External AI service on port 8091 (modern stack)
    if curl -sf http://localhost:8091/health >/dev/null 2>&1; then
        SERVICE_INFO=$(curl -s http://localhost:8091/health)
        log "External AI service is healthy"
        
        # 6. Restart Bee chatbot to pick up new configuration
        log "Restarting Bee chatbot to use native LLM service..."
        docker restart sting-ce-chatbot 2>/dev/null || warning "Could not restart Bee chatbot (may not be running yet)"
        
        log "✅ Native LLM setup complete!"
        log "   - External AI service: http://localhost:8091"
        log "   - Ollama service: http://localhost:11434"
        log "   - Modern LLM stack is operational"
        
    else
        error "Native LLM service started but health check failed"
        exit 1
    fi
else
    error "Failed to start native LLM service"
    exit 1
fi