#!/usr/bin/env bash

# Pretty installer wrapper for STING Community Edition
# Handles system dependencies and delegates to manage_sting.sh install

# Exit on any error
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source required libraries for dependency checks
LIB_DIR="$SCRIPT_DIR/lib"

# Source bootstrap for logging functions
if [ -f "$LIB_DIR/bootstrap.sh" ]; then
  # Set up minimal environment for bootstrap
  export INSTALL_DIR="${INSTALL_DIR:-${HOME}/.sting-ce}"
  export LOG_DIR="$INSTALL_DIR/logs"
  mkdir -p "$LOG_DIR"
  
  source "$LIB_DIR/bootstrap.sh"
else
  # Fallback logging function if bootstrap.sh is not available
  log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  }
fi

# Pretty banner
log_message "=========================================="
log_message "   STING Community Edition Installer    "
log_message "=========================================="

# Source installation library for dependency checks
if [ -f "$LIB_DIR/installation.sh" ]; then
  log_message "Checking system dependencies..."
  source "$LIB_DIR/installation.sh"
  
  # Check and install system dependencies before proceeding
  if ! check_and_install_dependencies; then
    log_message "Error: Failed to install required system dependencies" "ERROR"
    exit 1
  fi
  
  log_message "System dependencies check completed successfully"
else
  log_message "Warning: Could not find installation.sh - skipping dependency checks" "WARNING"
fi

# Verify manage_sting.sh exists
MANAGE_STING="$SCRIPT_DIR/manage_sting.sh"
if [ ! -x "$MANAGE_STING" ]; then
  log_message "Error: manage_sting.sh not found or not executable at: $MANAGE_STING" "ERROR"
  exit 1
fi

# Forward all arguments to manage_sting.sh install (or default to install if no args)
if [ $# -eq 0 ]; then
  log_message "Delegating to manage_sting.sh install..."
  exec "$MANAGE_STING" install
else
  log_message "Delegating to manage_sting.sh $*..."
  exec "$MANAGE_STING" "$@"
fi
