#!/usr/bin/env bash
#
# STING Community Edition - Installer Wrapper
#
# This is a convenience wrapper that allows you to run the installer
# from the repository root without needing to cd into STING/ first.
#

# Get the directory where this script is located
WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to STING directory and execute the real installer
cd "$WRAPPER_DIR/STING" || {
    echo "Error: STING directory not found at $WRAPPER_DIR/STING"
    exit 1
}

# Execute the real install script with all arguments passed through
exec ./install_sting.sh "$@"
