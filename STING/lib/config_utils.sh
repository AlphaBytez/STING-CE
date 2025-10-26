#!/bin/bash
# Centralized Configuration Generation via Utils Container
# Eliminates local config generation for cross-platform compatibility

# Global function to execute commands in utils container
exec_in_utils() {
    local cmd="$1"
    local timeout="${2:-30}"
    
    # Use direct docker exec for better reliability after container startup
    if timeout "$timeout" docker exec sting-ce-utils bash -c "$cmd" 2>/dev/null; then
        return 0
    else
        # Fallback to docker compose exec if direct exec fails
        if timeout "$timeout" docker compose --profile installation exec utils bash -c "$cmd" 2>/dev/null; then
            return 0
        else
            log_message "Failed to execute in utils container: $cmd" "ERROR"
            return 1
        fi
    fi
}

# Ensure utils container is running and ready
ensure_utils_container() {
    local max_attempts=30
    local attempt=1
    
    log_message "Ensuring utils container is available for config generation..."
    
    # Check if container exists and is running
    if ! docker ps --format '{{.Names}}' | grep -q "sting-ce-utils"; then
        log_message "Starting utils container..."
        if ! docker compose --profile installation up -d utils; then
            log_message "Failed to start utils container" "ERROR"
            return 1
        fi
    else
        # Container exists - verify it's using current image
        local current_image_id=$(docker inspect sting-ce-utils --format '{{.Image}}' 2>/dev/null)
        local latest_image_id=$(docker images sting-ce-utils:latest --format '{{.ID}}' 2>/dev/null)
        
        if [ -n "$current_image_id" ] && [ -n "$latest_image_id" ] && [ "$current_image_id" != "sha256:$latest_image_id" ]; then
            log_message "Utils container is using outdated image, restarting with latest..."
            docker compose --profile installation stop utils >/dev/null 2>&1
            docker compose --profile installation up -d utils
        fi
    fi
    
    # Wait for container to be ready with dependencies
    while [ $attempt -le $max_attempts ]; do
        if exec_in_utils "python3 -c 'import hvac; import yaml; import requests; print(\"Dependencies OK\")'" 10; then
            log_message "Utils container is ready with all dependencies" "SUCCESS"
            return 0
        fi
        
        log_message "Waiting for utils container dependencies... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Utils container did not become ready in time" "ERROR"
    return 1
}

# Centralized config generation function
generate_config_via_utils() {
    local mode="${1:-runtime}"
    local config_file="${2:-config.yml}"
    
    log_message "Generating configuration files via utils container (mode: $mode)..."
    
    # Ensure utils container is ready
    if ! ensure_utils_container; then
        log_message "Cannot proceed without utils container" "ERROR"
        return 1
    fi
    
    # Ensure directories exist in container
    exec_in_utils "mkdir -p /app/env /app/conf" || {
        log_message "Failed to create directories in utils container" "ERROR"
        return 1
    }
    
    # Run config generation in utils container
    if exec_in_utils "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py $config_file --mode $mode" 60; then
        log_message "Configuration files generated successfully via utils container" "SUCCESS"
        
        # Copy generated env files from container to host
        copy_config_from_utils
        
        return 0
    else
        log_message "Configuration generation failed in utils container" "ERROR"
        return 1
    fi
}

# Copy generated config files from utils container to host
copy_config_from_utils() {
    log_message "Copying generated environment files from utils container..."
    
    # Get list of generated env files from utils container
    local env_files
    env_files=$(exec_in_utils "find /app/env -name '*.env' -type f 2>/dev/null || true")
    
    if [ -n "$env_files" ]; then
        # Copy each env file
        local file_count=0
        while IFS= read -r container_file; do
            # Skip empty lines
            if [ -n "$container_file" ] && [ "$container_file" != " " ]; then
                local filename=$(basename "$container_file")
                local host_path="${INSTALL_DIR}/env/$filename"
                
                # Copy from container to host
                if docker cp "sting-ce-utils:$container_file" "$host_path" 2>/dev/null; then
                    log_message "Copied $filename"
                    file_count=$((file_count + 1))
                    # Special check for observability.env
                    if [ "$filename" = "observability.env" ]; then
                        log_message "Observability services configuration ready" "SUCCESS"
                    fi
                else
                    log_message "Failed to copy $filename" "WARNING"
                fi
            fi
        done <<< "$env_files"
        
        log_message "Copied $file_count environment files from utils container"
        
        # Also copy to conf directory for backward compatibility
        if [ -d "${INSTALL_DIR}/conf" ]; then
            cp "${INSTALL_DIR}/env/"*.env "${INSTALL_DIR}/conf/" 2>/dev/null || true
        fi
        
        log_message "Environment files copied successfully" "SUCCESS"
    else
        log_message "No environment files found in utils container" "WARNING"
        return 1
    fi
}

# Validate that config generation worked
validate_config_generation() {
    # All services that are started during installation need their env files
    local required_files=(
        # Core infrastructure
        "db.env"              # PostgreSQL database
        "vault.env"           # HashiCorp Vault for secrets
        "redis.env"           # Redis for caching/sessions
        
        # Authentication & Security
        "kratos.env"          # Ory Kratos authentication
        
        # Application services
        "app.env"             # Flask backend
        "frontend.env"        # React frontend
        "knowledge.env"       # Knowledge service
        "chatbot.env"         # Bee Chat service
        
        # Observability stack (if enabled)
        "observability.env"   # Grafana, Loki, Promtail
        
        # Supporting services
        "messaging.env"       # RabbitMQ messaging
        "profile.env"         # Profile service configs
    )
    
    log_message "Validating generated configuration files..."
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "${INSTALL_DIR}/env/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        log_message "All required configuration files generated successfully" "SUCCESS"
        return 0
    else
        log_message "Missing configuration files: ${missing_files[*]}" "ERROR"
        return 1
    fi
}

# Export functions for use in other modules
export -f exec_in_utils
export -f ensure_utils_container
export -f generate_config_via_utils
export -f copy_config_from_utils
export -f validate_config_generation