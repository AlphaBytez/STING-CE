#!/bin/bash
# Automatically configure Ollama endpoint for Docker containers
# This script detects the correct Ollama URL based on the environment

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/mnt/c/Development/STING-CE/STING}"

# Detect Ollama endpoint
detect_ollama_endpoint() {
    echo "Detecting Ollama endpoint..." >&2
    
    # Check if we're in WSL2
    if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "WSL2 environment detected" >&2
        
        # Get WSL2 host IP
        WSL_IP=$(hostname -I | awk '{print $1}')
        if [ -n "$WSL_IP" ]; then
            # Test if Ollama is accessible via WSL IP
            if curl -sf "http://${WSL_IP}:11434/v1/models" >/dev/null 2>&1; then
                echo "http://${WSL_IP}:11434"
                return 0
            fi
        fi
    fi
    
    # Try host.docker.internal (works on Docker Desktop)
    if curl -sf "http://host.docker.internal:11434/v1/models" >/dev/null 2>&1; then
        echo "http://host.docker.internal:11434"
        return 0
    fi
    
    # Try localhost (for native Docker)
    if curl -sf "http://localhost:11434/v1/models" >/dev/null 2>&1; then
        echo "http://localhost:11434"
        return 0
    fi
    
    # Default fallback
    echo "http://host.docker.internal:11434"
    return 1
}

# Update .env file
update_env_file() {
    local ollama_url="$1"
    local env_file="${INSTALL_DIR}/.env"
    
    echo "Updating .env with Ollama endpoint: $ollama_url" >&2
    
    # Ensure .env exists
    touch "$env_file"
    
    # Update or add OLLAMA_BASE_URL
    if grep -q "^OLLAMA_BASE_URL=" "$env_file"; then
        sed -i "s|^OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$ollama_url|" "$env_file"
    else
        echo "OLLAMA_BASE_URL=$ollama_url" >> "$env_file"
    fi
}

# Update Docker environment files
update_docker_env() {
    local ollama_url="$1"
    local env_dir="${INSTALL_DIR}/env"
    
    # Update external-ai.env if it exists
    if [ -f "$env_dir/external-ai.env" ]; then
        echo "Updating external-ai.env" >&2
        if grep -q "^OLLAMA_BASE_URL=" "$env_dir/external-ai.env"; then
            sed -i "s|^OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$ollama_url|" "$env_dir/external-ai.env"
        else
            echo "OLLAMA_BASE_URL=$ollama_url" >> "$env_dir/external-ai.env"
        fi
    fi
    
    # Update llm-gateway.env if it exists
    if [ -f "$env_dir/llm-gateway.env" ]; then
        echo "Updating llm-gateway.env" >&2
        if grep -q "^OLLAMA_ENDPOINT=" "$env_dir/llm-gateway.env"; then
            sed -i "s|^OLLAMA_ENDPOINT=.*|OLLAMA_ENDPOINT=$ollama_url|" "$env_dir/llm-gateway.env"
        else
            echo "OLLAMA_ENDPOINT=$ollama_url" >> "$env_dir/llm-gateway.env"
        fi
    fi
}

# Ensure Ollama is running with correct binding
ensure_ollama_running() {
    echo "Checking Ollama service..." >&2
    
    # Check if Ollama is running
    if ! pgrep -f "ollama serve" >/dev/null; then
        echo "Starting Ollama service..." >&2
        
        # Start with binding to all interfaces for WSL2
        if grep -qi microsoft /proc/version 2>/dev/null; then
            export OLLAMA_HOST=0.0.0.0:11434
        fi
        
        # Find Ollama binary
        OLLAMA_BIN=""
        if [ -x "$HOME/.ollama/bin/ollama" ]; then
            OLLAMA_BIN="$HOME/.ollama/bin/ollama"
        elif command -v ollama >/dev/null 2>&1; then
            OLLAMA_BIN="ollama"
        else
            echo "ERROR: Ollama not found. Please install Ollama first." >&2
            return 1
        fi
        
        # Start Ollama
        nohup "$OLLAMA_BIN" serve > /tmp/ollama-configure.log 2>&1 &
        
        # Wait for it to be ready
        echo "Waiting for Ollama to start..." >&2
        for i in {1..30}; do
            if curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
                echo "Ollama is ready!" >&2
                break
            fi
            sleep 2
        done
    else
        echo "Ollama is already running" >&2
    fi
}

# Main execution
main() {
    # Ensure Ollama is running
    ensure_ollama_running
    
    # Detect endpoint
    OLLAMA_URL=$(detect_ollama_endpoint)
    if [ $? -eq 0 ]; then
        echo "Successfully detected Ollama endpoint: $OLLAMA_URL" >&2
    else
        echo "WARNING: Could not verify Ollama endpoint, using default: $OLLAMA_URL" >&2
    fi
    
    # Update configuration
    update_env_file "$OLLAMA_URL"
    update_docker_env "$OLLAMA_URL"
    
    # Export for immediate use
    export OLLAMA_BASE_URL="$OLLAMA_URL"
    
    echo "Ollama endpoint configured: $OLLAMA_URL" >&2
    echo "$OLLAMA_URL"
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi