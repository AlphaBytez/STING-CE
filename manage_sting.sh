#!/usr/bin/env bash
#
# STING Community Edition - Management Wrapper
#
# This is a convenience wrapper that allows you to run management commands
# from the repository root without needing to cd into STING/ first.
#

# Get the directory where this script is located
WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to STING directory and execute the real management script
cd "$WRAPPER_DIR/STING" || {
    echo "Error: STING directory not found at $WRAPPER_DIR/STING"
    exit 1
}

# Execute the real management script with all arguments passed through
exec ./manage_sting.sh "$@"
