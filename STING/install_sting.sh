#!/usr/bin/env bash

# STING Community Edition - Simple Installer
#
# Usage:
#   ./install_sting.sh          # Launch web setup wizard (recommended)
#   ./install_sting.sh --wizard # Launch web setup wizard (explicit)
#   ./install_sting.sh --cli    # CLI installation (advanced)

# Exit on any error
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source required libraries for dependency checks
LIB_DIR="$SCRIPT_DIR/lib"

# Platform detection for install directory (matching manage_sting.sh)
if [[ "$(uname)" == "Darwin" ]]; then
  # Mac-specific setup - use home directory
  DEFAULT_INSTALL_DIR="${HOME}/.sting-ce"
else
  # Linux setup - use /opt for system-wide installation
  DEFAULT_INSTALL_DIR="/opt/sting-ce"
fi

# Source bootstrap for logging functions
if [ -f "$LIB_DIR/bootstrap.sh" ]; then
  # Set up minimal environment for bootstrap
  export INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

  # Use temp directory for initial logs to avoid permission issues
  # The installation.sh will create proper directory with correct permissions
  export LOG_DIR="/tmp/sting-install-logs-$$"
  mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp"

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

# Check for CLI install flag
USE_CLI=false
if [ $# -gt 0 ]; then
  case "$1" in
    --cli|install)
      # CLI mode: either explicit --cli or 'install' subcommand (used by wizard)
      USE_CLI=true
      shift
      ;;
    --wizard)
      USE_CLI=false
      shift
      ;;
    --help|-h)
      echo "STING Community Edition Installer"
      echo ""
      echo "Usage:"
      echo "  ./install_sting.sh          # Launch web setup wizard (recommended)"
      echo "  ./install_sting.sh --wizard # Launch web setup wizard (explicit)"
      echo "  ./install_sting.sh --cli    # CLI installation (advanced users)"
      echo ""
      echo "The web wizard provides a user-friendly interface for:"
      echo "  • System configuration"
      echo "  • Admin account setup (passwordless)"
      echo "  • LLM backend configuration"
      echo "  • Email/SSL settings"
      echo ""
      echo "For CLI installation and management:"
      echo "  ./manage_sting.sh --help"
      exit 0
      ;;
  esac
fi

# Launch wizard by default (unless --cli specified)
if [ "$USE_CLI" = false ]; then
  log_message "=========================================="
  log_message "  Launching STING Setup Wizard...       "
  log_message "=========================================="
  log_message ""
  log_message "The wizard will guide you through:"
  log_message "  1. System configuration"
  log_message "  2. Data disk setup (optional)"
  log_message "  3. Admin account creation (passwordless)"
  log_message "  4. LLM backend configuration"
  log_message "  5. Email & SSL settings"
  log_message ""

  # Check if wizard exists
  WIZARD_DIR="$SCRIPT_DIR/web-setup"
  WIZARD_APP="$WIZARD_DIR/app.py"

  if [ ! -f "$WIZARD_APP" ]; then
    log_message "Error: Setup wizard not found at: $WIZARD_APP" "ERROR"
    log_message "Run with --cli flag for CLI installation" "INFO"
    exit 1
  fi

  # Check Python3
  if ! command -v python3 &> /dev/null; then
    log_message "Error: python3 is required for the setup wizard" "ERROR"
    exit 1
  fi

  # Wizard lifecycle management
  WIZARD_PORT=8335
  WIZARD_PID_FILE="/tmp/sting-wizard.pid"

  # Function to cleanup wizard processes
  cleanup_wizard() {
    log_message "Cleaning up wizard processes..." "INFO"

    # Kill processes using the wizard port
    if command -v lsof &> /dev/null; then
      local pids=$(lsof -ti :$WIZARD_PORT 2>/dev/null || true)
      if [ -n "$pids" ]; then
        log_message "Killing processes on port $WIZARD_PORT: $pids" "INFO"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
      fi
    fi

    # Remove PID file
    rm -f "$WIZARD_PID_FILE"

    log_message "Wizard cleanup complete" "INFO"
  }

  # Check if wizard is already running
  if [ -f "$WIZARD_PID_FILE" ]; then
    OLD_PID=$(cat "$WIZARD_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
      log_message "⚠️  WARNING: Wizard is already running (PID: $OLD_PID)" "WARNING"
      log_message "Stopping existing wizard..." "INFO"
      cleanup_wizard
      sleep 2
    else
      log_message "Cleaning up stale PID file..." "INFO"
      rm -f "$WIZARD_PID_FILE"
    fi
  fi

  # Check if port is in use
  if command -v lsof &> /dev/null && lsof -ti :$WIZARD_PORT &>/dev/null; then
    log_message "⚠️  WARNING: Port $WIZARD_PORT is already in use" "WARNING"
    log_message "Cleaning up port $WIZARD_PORT..." "INFO"
    cleanup_wizard
    sleep 2

    # Check again
    if lsof -ti :$WIZARD_PORT &>/dev/null; then
      log_message "Error: Failed to free port $WIZARD_PORT" "ERROR"
      log_message "Please manually stop any processes using port $WIZARD_PORT" "ERROR"
      exit 1
    fi
  fi

  # Set up trap to cleanup on exit
  trap cleanup_wizard EXIT INT TERM

  # Check/install wizard dependencies
  log_message "Checking wizard dependencies..."
  if [ ! -d "$WIZARD_DIR/venv" ]; then
    log_message "Creating virtual environment..."
    if ! python3 -m venv "$WIZARD_DIR/venv" 2>&1 | tee /tmp/venv-creation.log; then
      log_message "Error: Failed to create virtual environment" "ERROR"
      log_message "This usually means python3-venv is not installed" "ERROR"
      log_message "Install it with: sudo apt-get install python3-venv" "ERROR"
      exit 1
    fi
  fi

  # Verify venv was created successfully
  if [ ! -f "$WIZARD_DIR/venv/bin/pip" ]; then
    log_message "Error: Virtual environment creation failed - pip not found" "ERROR"
    log_message "Check /tmp/venv-creation.log for details" "ERROR"
    exit 1
  fi

  log_message "Installing wizard dependencies..."
  if ! "$WIZARD_DIR/venv/bin/pip" install -q -r "$WIZARD_DIR/requirements.txt" 2>&1 | tee /tmp/pip-install.log; then
    log_message "Error: Failed to install wizard dependencies" "ERROR"
    log_message "Check /tmp/pip-install.log for details" "ERROR"
    exit 1
  fi

  # Get local IP for display
  LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

  log_message ""
  log_message "=========================================="
  log_message "  Setup Wizard Starting...              "
  log_message "=========================================="
  log_message ""
  log_message "Open your browser and navigate to:"
  log_message "  🌐 http://$LOCAL_IP:$WIZARD_PORT"
  log_message "  🌐 http://localhost:$WIZARD_PORT"
  log_message ""
  log_message "Press Ctrl+C to stop the wizard"
  log_message ""

  # Launch wizard (don't use exec so trap cleanup works)
  cd "$WIZARD_DIR"
  export DEV_MODE=false
  export WIZARD_PORT="$WIZARD_PORT"

  # Start wizard and save PID
  "$WIZARD_DIR/venv/bin/python3" app.py &
  WIZARD_PID=$!
  echo "$WIZARD_PID" > "$WIZARD_PID_FILE"

  # Wait for wizard to finish
  wait "$WIZARD_PID"

else
  # CLI installation (advanced)
  log_message "Using CLI installation mode..."

  # Verify manage_sting.sh exists
  MANAGE_STING="$SCRIPT_DIR/manage_sting.sh"
  if [ ! -x "$MANAGE_STING" ]; then
    log_message "Error: manage_sting.sh not found or not executable at: $MANAGE_STING" "ERROR"
    exit 1
  fi

  # Forward remaining arguments to manage_sting.sh install
  if [ $# -eq 0 ]; then
    log_message "Delegating to manage_sting.sh install..."
    exec "$MANAGE_STING" install
  else
    log_message "Delegating to manage_sting.sh $*..."
    exec "$MANAGE_STING" "$@"
  fi
fi
