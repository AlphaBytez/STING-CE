#!/bin/bash

# Script to update a specific STING service
# Usage: ./update_service.sh <service_name>

# Determine the installation directory
if [[ "$(uname)" == "Darwin" ]]; then
    # Mac-specific setup
    INSTALL_DIR="$HOME/.sting-ce"
else
    # Linux setup
    INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
fi

# Source directory is where the script is run from
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STING_ROOT="$SOURCE_DIR"

# Function to log messages
log_message() {
    local message="$1"
    local level="${2:-INFO}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

update_service() {
    local service="$1"
    
    if [ -z "$service" ]; then
        log_message "Error: Service name must be provided" "ERROR"
        echo "Usage: $0 <service_name>"
        echo "Available services: app, chatbot, frontend, llm-gateway, etc."
        return 1
    fi
    
    log_message "Updating service: $service" "INFO"
    
    # Validate service exists
    if ! grep -q "^[[:space:]]*$service:" "$STING_ROOT/docker-compose.yml"; then
        log_message "Error: Service '$service' not found in docker-compose.yml" "ERROR"
        return 1
    fi
    
    # Copy updated files from source to install directory
    case "$service" in
        chatbot)
            log_message "Copying chatbot files to $INSTALL_DIR..." "INFO"
            mkdir -p "$INSTALL_DIR/chatbot"
            cp -r "$STING_ROOT/chatbot/"* "$INSTALL_DIR/chatbot/"
            
            # Copy LLM service chat module which is needed by chatbot
            mkdir -p "$INSTALL_DIR/llm_service/chat"
            cp -r "$STING_ROOT/llm_service/chat/"* "$INSTALL_DIR/llm_service/chat/"
            ;;
            
        frontend)
            log_message "Copying frontend files to $INSTALL_DIR..." "INFO"
            mkdir -p "$INSTALL_DIR/frontend"
            cp -r "$STING_ROOT/frontend/src" "$INSTALL_DIR/frontend/"
            cp -r "$STING_ROOT/frontend/public" "$INSTALL_DIR/frontend/"
            cp "$STING_ROOT/frontend/package.json" "$INSTALL_DIR/frontend/"
            ;;
            
        llm-gateway)
            log_message "Copying LLM gateway files to $INSTALL_DIR..." "INFO"
            mkdir -p "$INSTALL_DIR/llm_service/gateway"
            cp -r "$STING_ROOT/llm_service/gateway/"* "$INSTALL_DIR/llm_service/gateway/"
            ;;
            
        app)
            log_message "Copying app files to $INSTALL_DIR..." "INFO"
            mkdir -p "$INSTALL_DIR/app"
            cp -r "$STING_ROOT/app/"* "$INSTALL_DIR/app/"
            ;;
            
        *)
            log_message "Generic update for service: $service" "INFO"
            # For other services, try to guess the directory structure
            if [ -d "$STING_ROOT/$service" ]; then
                mkdir -p "$INSTALL_DIR/$service"
                cp -r "$STING_ROOT/$service/"* "$INSTALL_DIR/$service/"
            else
                log_message "Warning: Could not find directory for service '$service'" "WARNING"
                log_message "Only rebuilding container without updating files" "WARNING"
            fi
            ;;
    esac
    
    # Rebuild and restart the service
    log_message "Rebuilding and restarting $service..." "INFO"
    
    # Change to install directory
    cd "$INSTALL_DIR"
    
    # Rebuild and restart the service
    if docker compose up -d --force-recreate --build "$service"; then
        log_message "Service '$service' successfully updated" "SUCCESS"
        return 0
    else
        log_message "Failed to update service '$service'" "ERROR"
        return 1
    fi
}

# Main execution
if [ "$#" -ne 1 ]; then
    log_message "Error: Incorrect number of arguments" "ERROR"
    echo "Usage: $0 <service_name>"
    exit 1
fi

update_service "$1"
exit $?