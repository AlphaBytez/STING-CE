#!/bin/bash
# STING Management Script - Core Utilities Module
# This module provides fundamental utilities used throughout the system

# Safe logging function that works before logging.sh is loaded
safe_log() {
    local message="$1"
    if declare -f safe_log >/dev/null 2>&1; then
        safe_log "$message"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $message"
    fi
}

# Exit codes
export E_GENERAL=1
export E_PERMISSION=2
export E_CONFIG=4
export E_VERSION=5

# Platform detection (needed for check_root and other functions)
export IS_MACOS=false
if [[ "$(uname)" == "Darwin" ]]; then
    export IS_MACOS=true
fi

# Check if running with appropriate privileges
check_root() {
    # Skip check if SKIP_ROOT_CHECK is set
    if [[ "$SKIP_ROOT_CHECK" == "true" ]]; then
        return 0
    fi
    
    if [[ "$IS_MACOS" == "true" ]]; then
        # On macOS, allow non-root for development
        return 0
    fi
    
    # Commands that don't need root
    local no_root_commands=("status" "logs" "help" "debug" "version" "info" "list" "ps" "dev" "create" "export-certs")
    for cmd in "${no_root_commands[@]}"; do
        if [[ "$COMMAND" == "$cmd" ]] || [[ "$1" == "$cmd" ]]; then
            return 0
        fi
    done
    
    # Commands that will handle their own privilege escalation
    local self_escalating_commands=("install" "uninstall" "reinstall" "update" "start" "stop" "restart" "build")
    for cmd in "${self_escalating_commands[@]}"; do
        if [[ "$COMMAND" == "$cmd" ]] || [[ "$1" == "$cmd" ]]; then
            return 0
        fi
    done
    
    # For other commands on Linux, check if root is needed
    if [[ $EUID -ne 0 ]]; then
        echo "ERROR: This script must be run as root for command: ${COMMAND:-$1}"
        echo "Try using: sudo msting ${COMMAND:-$1}"
        exit $E_PERMISSION
    fi
}

# Handle errors with cleanup
handle_error() {
    local exit_code=$1
    local error_message=$2
    safe_log "Error: $error_message (Exit Code: $exit_code)"
    cleanup
    exit $exit_code
}

# General cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        safe_log "An error occurred (Exit Code: $exit_code). Performing cleanup..."

        # Stop any running services if docker compose is available
        if command -v docker >/dev/null 2>&1 && [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
            safe_log "Stopping any running STING services..."
            docker compose -f "${INSTALL_DIR}/docker-compose.yml" down 2>/dev/null || true
        fi

        # Remove any temporary files or directories
        if [[ -n "$temp_dir" && -d "$temp_dir" ]]; then
            safe_log "Removing temporary directory: $temp_dir"
            rm -rf "$temp_dir"
        fi
    fi
}


# Get application environment from config
get_app_env() {
    local config_file="${CONFIG_DIR}/config.yml"
    if [ ! -f "$config_file" ]; then
        safe_log "ERROR: Configuration file not found: $config_file"
        return 1
    fi

    # Using grep and cut to extract APP_ENV value
    local app_env
    app_env=$(grep "^APP_ENV:" "$config_file" | cut -d':' -f2 | tr -d ' ')
    if [ -z "$app_env" ]; then
        app_env="development"  # Default fallback
    fi
    echo "$app_env" 
}

# Create file checksum for verification
create_checksum() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" > "${file}.checksum"
    elif command -v shasum >/dev/null 2>&1; then
        # macOS fallback
        shasum -a 256 "$file" > "${file}.checksum"
    else
        safe_log "WARNING: No checksum utility found"
        return 1
    fi
}

# Verify file checksum
verify_checksum() {
    local file="$1"
    if [ ! -f "${file}.checksum" ]; then
        safe_log "WARNING: No checksum file found for $file"
        return 1
    fi
    
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -c "${file}.checksum"
    elif command -v shasum >/dev/null 2>&1; then
        # macOS fallback
        shasum -a 256 -c "${file}.checksum"
    else
        safe_log "WARNING: No checksum utility found"
        return 1
    fi
}

# Forgiving yes/no prompt with retry logic
# Usage: prompt_yes_no "Question text?" [default_yes/default_no] [max_attempts]
# Returns: 0 for yes, 1 for no
prompt_yes_no() {
    local question="$1"
    local default="${2:-default_no}"  # default_yes or default_no
    local max_attempts="${3:-3}"
    local attempts=0

    while [ $attempts -lt $max_attempts ]; do
        # Show prompt with default indicator
        if [ "$default" = "default_yes" ]; then
            read -p "$question [Y/n]: " response
        else
            read -p "$question [y/N]: " response
        fi

        # Normalize input: trim whitespace, lowercase, remove extra characters
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z]//g')

        # Handle empty response (use default)
        if [ -z "$response" ]; then
            if [ "$default" = "default_yes" ]; then
                return 0
            else
                return 1
            fi
        fi

        # Check response
        case "$response" in
            yes|y)
                return 0
                ;;
            no|n)
                return 1
                ;;
            *)
                attempts=$((attempts + 1))
                if [ $attempts -lt $max_attempts ]; then
                    echo "❌ Invalid input. Please type 'yes' or 'no' (attempt $attempts/$max_attempts)"
                    echo ""
                else
                    echo "❌ Too many invalid attempts."
                    # Use default on max attempts
                    if [ "$default" = "default_yes" ]; then
                        echo "Defaulting to: yes"
                        return 0
                    else
                        echo "Defaulting to: no"
                        return 1
                    fi
                fi
                ;;
        esac
    done
}

# Export functions for use in other modules
export -f check_root
export -f handle_error
export -f cleanup
export -f get_app_env
export -f create_checksum
export -f verify_checksum
export -f prompt_yes_no