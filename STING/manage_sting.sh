#!/bin/bash
# manage_sting.sh - Main entry point for STING Community Edition
# This is a clean modular implementation that replaces the 4600+ line monolith

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SCRIPT_DIR
# Save the original directory
ORIGINAL_SCRIPT_DIR="$SCRIPT_DIR"

# Platform detection and environment setup (matching legacy behavior)
if [[ "$(uname)" == "Darwin" ]]; then
    # Mac-specific setup
    export INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
    export LOG_DIR="$INSTALL_DIR/logs"
    export CONFIG_DIR="$INSTALL_DIR/conf"
    # Use current user for Mac
    export STING_USER="$USER"
    export STING_GROUP="staff"
else
    # Linux setup
    export INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
    export LOG_DIR="$INSTALL_DIR/logs"
    export CONFIG_DIR="$INSTALL_DIR/conf"
    # Use standard Linux user/group
    export STING_USER="${SUDO_USER:-$USER}"
    export STING_GROUP="$(id -gn ${SUDO_USER:-$USER})"
fi
export SOURCE_DIR="$SCRIPT_DIR"

# Load bootstrap for basic logging first
source "${SCRIPT_DIR}/lib/bootstrap.sh" || {
    echo "ERROR: Failed to load bootstrap.sh"
    exit 1
}

# Apply WSL2 Docker fixes if needed (must be done before any Docker operations)
if [ -f "${SCRIPT_DIR}/lib/docker_wsl_fix.sh" ]; then
    source "${SCRIPT_DIR}/lib/docker_wsl_fix.sh"
    # Only apply fix if we're in WSL2
    if is_wsl2 2>/dev/null; then
        fix_docker_credential_helper 2>/dev/null || true
    fi
fi

# Skip HF_TOKEN loading - using Ollama/External AI instead
# Legacy HF_TOKEN support removed for cleaner modern AI stack

# Now we can use log_message safely
log_message "Starting STING management script..."

# Set up signal handlers for graceful shutdown
cleanup_on_exit() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_message "Script interrupted or failed (exit code: $exit_code)" "WARNING"
    fi
    # Add any cleanup tasks here if needed
    exit $exit_code
}

# Trap signals for graceful shutdown (comprehensive signal coverage)
trap cleanup_on_exit EXIT
trap 'log_message "Received interrupt signal, cleaning up..." "WARNING"; exit 130' HUP INT QUIT PIPE TERM

# Load core modules in dependency order
declare -a CORE_MODULES=(
    "core"
    "logging"      # This will enhance the bootstrap logging
    "environment"
    "configuration"
)

# Load core modules
for module in "${CORE_MODULES[@]}"; do
    module_path="${ORIGINAL_SCRIPT_DIR}/lib/${module}.sh"
    if [ -f "$module_path" ]; then
        # Silently load core modules
        source "$module_path" || {
            log_message "ERROR: Failed to load module: $module" "ERROR"
            exit 1
        }
    else
        log_message "WARNING: Module not found: $module" "WARNING"
    fi
done

# Module loader for on-demand loading
load_module() {
    local module="$1"
    local module_path="${ORIGINAL_SCRIPT_DIR}/lib/${module}.sh"
    
    # Check if already loaded
    if [[ "$LOADED_MODULES" == *" $module "* ]]; then
        return 0
    fi
    
    if [ -f "$module_path" ]; then
        source "$module_path" || {
            log_message "ERROR: Failed to load module: $module" "ERROR"
            return 1
        }
        LOADED_MODULES="$LOADED_MODULES $module "
    else
        log_message "ERROR: Module not found: $module" "ERROR"
        return 1
    fi
}

# Track loaded modules (simple alternative to associative arrays)
LOADED_MODULES=""

# Load the interface module which contains main() and show_help()
load_module "interface" || {
    log_message "ERROR: Cannot load interface module" "ERROR"
    exit 1
}

# Quick dependency check for critical tools (jq for status, docker for everything)
check_critical_dependencies() {
    local missing_critical=()
    
    # Check for jq (needed for status and JSON parsing)
    if ! command -v jq >/dev/null 2>&1; then
        missing_critical+=("jq")
    fi
    
    # Check for docker (needed for everything)
    if ! command -v docker >/dev/null 2>&1; then
        missing_critical+=("docker")
    fi
    
    if [ ${#missing_critical[@]} -gt 0 ]; then
        echo "⚠️  Missing critical dependencies: ${missing_critical[*]}"
        echo "Installing missing dependencies..."
        
        # Load installation module to use check_and_install_dependencies
        load_module "installation" || {
            echo "ERROR: Cannot load installation module for dependency installation"
            return 1
        }
        
        # Run the full dependency check and installation
        if ! check_and_install_dependencies; then
            echo "ERROR: Failed to install critical dependencies"
            echo "Please install manually:"
            if [[ "$(uname)" == "Darwin" ]]; then
                echo "  brew install ${missing_critical[*]}"
            else
                echo "  sudo apt update && sudo apt install ${missing_critical[*]}"
            fi
            return 1
        fi
    fi
}

# Run critical dependency check for commands that need them
case "${1:-status}" in
    status|debug|logs|health|beeacon)
        check_critical_dependencies || exit 1
        ;;
    *)
        # For other commands, just check if they exist but don't force install
        if ! command -v jq >/dev/null 2>&1 && [[ "${1:-}" =~ ^(status|debug|logs|health|beeacon)$ ]]; then
            check_critical_dependencies || exit 1
        fi
        ;;
esac

# The interface module's main() function will handle loading other modules as needed
main "$@"