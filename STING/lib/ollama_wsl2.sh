#!/bin/bash
# WSL2-specific Ollama installation and management module
# This module enhances STING's Ollama integration for WSL2 environments

# Source core functions if not already loaded
[[ -z "$SCRIPT_DIR" ]] && SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# WSL2 Detection
is_wsl2_environment() {
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
        if [[ -f /proc/sys/fs/binfmt_misc/WSLInterop ]]; then
            return 0  # WSL2
        fi
    fi
    return 1
}

# Enhanced Ollama installation for WSL2
install_ollama_wsl2_enhanced() {
    local install_dir="${INSTALL_DIR:-/opt/sting-ce}"
    
    log_message "Detected WSL2 environment - using enhanced Ollama installation..."
    
    # Check if we should use custom domain
    local use_custom_domain=false
    local custom_domain="sting.local"
    
    if [[ -f "${install_dir}/env/app.env" ]]; then
        source "${install_dir}/env/app.env"
        if [[ -n "$DOMAIN_NAME" ]] && [[ "$DOMAIN_NAME" != "localhost" ]]; then
            use_custom_domain=true
            custom_domain="$DOMAIN_NAME"
            log_message "Will configure Ollama for custom domain: $custom_domain"
        fi
    fi
    
    # Run the WSL2-specific installer
    if bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" install; then
        log_message "[+] Ollama installed successfully for WSL2"
        
        # Configure for custom domain if needed
        if [[ "$use_custom_domain" == "true" ]]; then
            log_message "Configuring Ollama for custom domain access..."
            bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" configure-domain "$custom_domain"
        fi
        
        # Update STING configuration
        update_ollama_configuration_wsl2
        
        return 0
    else
        log_message "Failed to install Ollama for WSL2" "ERROR"
        return 1
    fi
}

# Update STING configuration for WSL2 Ollama
update_ollama_configuration_wsl2() {
    local install_dir="${INSTALL_DIR:-/opt/sting-ce}"
    local env_file="${install_dir}/env/llm-gateway.env"
    
    if [[ -f "$env_file" ]]; then
        # Backup original
        cp "$env_file" "${env_file}.bak"
        
        # Update Ollama endpoint based on domain configuration
        if [[ -n "$DOMAIN_NAME" ]] && [[ "$DOMAIN_NAME" != "localhost" ]]; then
            sed -i "s|OLLAMA_ENDPOINT=.*|OLLAMA_ENDPOINT=http://${DOMAIN_NAME}:11434|g" "$env_file"
        else
            sed -i "s|OLLAMA_ENDPOINT=.*|OLLAMA_ENDPOINT=http://localhost:11434|g" "$env_file"
        fi
        
        # Ensure Ollama is enabled
        sed -i "s|OLLAMA_ENABLED=.*|OLLAMA_ENABLED=true|g" "$env_file"
        
        log_message "Updated Ollama configuration for WSL2"
    fi
}

# Check Ollama status with WSL2 enhancements
check_ollama_status_wsl2() {
    log_message "Checking Ollama status in WSL2..."
    
    # Run diagnostics
    bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" check
    
    # Additional WSL2-specific checks
    if is_wsl2_environment; then
        log_message "WSL2-specific network checks:"
        
        # Check if Windows firewall might be blocking
        if ! curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
            log_message "Ollama API not accessible. This might be due to:" "WARNING"
            log_message "  1. Windows firewall blocking the connection" "WARNING"
            log_message "  2. Ollama not bound to all interfaces (0.0.0.0)" "WARNING"
            log_message "  3. WSL2 network configuration issues" "WARNING"
            
            # Suggest fixes
            log_message "Suggested fixes:" "INFO"
            log_message "  1. Add Windows firewall exception for port 11434" "INFO"
            log_message "  2. Ensure OLLAMA_HOST=0.0.0.0:11434 is set" "INFO"
            log_message "  3. Consider using custom domain setup" "INFO"
        fi
    fi
}

# Programmatic model management for WSL2
ensure_models_installed_wsl2() {
    local required_models="${OLLAMA_MODELS_TO_INSTALL:-phi3:mini deepseek-r1:latest}"
    
    log_message "Ensuring required models are installed..."
    
    # Check current models
    local installed_models=$(bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" models 2>/dev/null | grep -E "^\s*-" | sed 's/^[[:space:]]*-[[:space:]]*//')
    
    # Download missing models
    for model in $required_models; do
        if ! echo "$installed_models" | grep -q "$model"; then
            log_message "Model $model not found, downloading..."
            bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" download-models
            break
        fi
    done
    
    log_message "[+] All required models are available"
}

# Integration with STING's installation process
ollama_wsl2_integration_check() {
    if ! is_wsl2_environment; then
        return 1  # Not WSL2, use standard installation
    fi
    
    log_message "WSL2 detected - using enhanced Ollama integration"
    
    # Check if Ollama is already properly configured
    if bash "${SCRIPT_DIR}/scripts/check_and_install_ollama_wsl2.sh" check >/dev/null 2>&1; then
        log_message "Ollama is already configured for WSL2"
        ensure_models_installed_wsl2
        return 0
    fi
    
    # Perform WSL2-specific installation
    if install_ollama_wsl2_enhanced; then
        ensure_models_installed_wsl2
        return 0
    fi
    
    return 1
}

# Export functions for use in other scripts
export -f is_wsl2_environment
export -f install_ollama_wsl2_enhanced
export -f check_ollama_status_wsl2
export -f ollama_wsl2_integration_check