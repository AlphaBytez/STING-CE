#!/bin/bash
# Detect the correct Ollama host URL for Docker containers

# Try different methods to find Ollama
detect_ollama_host() {
    # 1. Check if Ollama is running locally in WSL2
    if curl -sf http://localhost:11434 >/dev/null 2>&1; then
        # Get WSL2 IP address
        WSL_IP=$(hostname -I | awk '{print $1}')
        if [ -n "$WSL_IP" ]; then
            echo "http://${WSL_IP}:11434"
            return 0
        fi
    fi
    
    # 2. Check host.docker.internal (works on Docker Desktop)
    if curl -sf http://host.docker.internal:11434 >/dev/null 2>&1; then
        echo "http://host.docker.internal:11434"
        return 0
    fi
    
    # 3. Check if Ollama is running in a container
    if curl -sf http://ollama:11434 >/dev/null 2>&1; then
        echo "http://ollama:11434"
        return 0
    fi
    
    # Default fallback
    echo "http://host.docker.internal:11434"
    return 1
}

# Main
OLLAMA_URL=$(detect_ollama_host)
echo "Detected Ollama URL: $OLLAMA_URL"

# Update .env file if it exists
if [ -f "/mnt/c/Development/STING-CE/STING/.env" ]; then
    if grep -q "OLLAMA_BASE_URL=" "/mnt/c/Development/STING-CE/STING/.env"; then
        sed -i "s|OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$OLLAMA_URL|" "/mnt/c/Development/STING-CE/STING/.env"
    else
        echo "OLLAMA_BASE_URL=$OLLAMA_URL" >> "/mnt/c/Development/STING-CE/STING/.env"
    fi
    echo "Updated .env with OLLAMA_BASE_URL=$OLLAMA_URL"
fi

# Export for immediate use
export OLLAMA_BASE_URL="$OLLAMA_URL"