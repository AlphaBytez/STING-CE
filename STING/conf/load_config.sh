#!/bin/bash

# Source config utilities for centralized config generation
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"
if [ -f "${SCRIPT_DIR}/config_utils.sh" ]; then
    source "${SCRIPT_DIR}/config_utils.sh"
    source "${SCRIPT_DIR}/logging.sh"
fi

CONFIG_PATH="${INSTALL_DIR}/conf/config.yml"

# Check for .env file and load it if it exists
if [ -f ${INSTALL_DIR}/.env ]; then
    echo "Loading environment variables from .env file..."
    set -a
    source ${INSTALL_DIR}/.env
    set +a
else
    echo "Loading configuration and setting environment variables..."
    
    # Use centralized config generation via utils container instead of local Python
    if command -v generate_config_via_utils >/dev/null 2>&1; then
        log_message "Generating config via utils container..."
        generate_config_via_utils "runtime" "config.yml"
    else
        log_message "WARNING: Config utils not available, skipping config generation" "WARNING"
    fi
    
    if [ -f ${INSTALL_DIR}/.env ]; then
        set -a
        source ${INSTALL_DIR}/.env
        set +a
    fi
fi

# Further commands
echo "Configuration loaded successfully."

# Print debug information
echo "FLASK_DEBUG is set to: $FLASK_DEBUG"
echo "FLASK_APP is set to: $FLASK_APP"