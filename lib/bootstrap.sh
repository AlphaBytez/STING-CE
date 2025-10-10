#!/bin/bash
# bootstrap.sh - Minimal bootstrap for modular STING
# This provides basic logging functionality before the full logging module loads

# Ensure log directory exists
export LOG_DIR="${LOG_DIR:-/tmp}"
export LOG_FILE="${LOG_FILE:-/tmp/manage_sting.log}"

# Simple log_message function that works everywhere
log_message() {
    local message="$1"
    local level="${2:-INFO}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Color codes
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local NC='\033[0m' # No Color
    
    # Set color based on level
    local color=""
    case "$level" in
        ERROR) color="$RED" ;;
        SUCCESS) color="$GREEN" ;;
        WARNING) color="$YELLOW" ;;
    esac
    
    # Output to console
    if [ -n "$color" ]; then
        echo -e "${color}${timestamp} - ${message}${NC}"
    else
        echo "${timestamp} - ${message}"
    fi
    
    # Also write to log file if possible (silently skip on error)
    echo "${timestamp} - [${level}] ${message}" >> "$LOG_FILE" 2>/dev/null || true
}

# Export the function so it's available to all modules
export -f log_message