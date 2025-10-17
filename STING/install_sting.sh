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

# Source services.sh at global scope (required for service health checks)
# CRITICAL: Must be sourced here, NOT inside functions, so all functions can access it
# IMPORTANT: Save SCRIPT_DIR first, as services.sh will overwrite it with lib directory
STING_ROOT_DIR="$SCRIPT_DIR"
if [ -f "$LIB_DIR/services.sh" ]; then
  source "$LIB_DIR/services.sh"
  # Restore SCRIPT_DIR to point to STING root, not lib directory
  SCRIPT_DIR="$STING_ROOT_DIR"
else
  log_message "ERROR: services.sh not found - service health checks will fail" "ERROR"
  exit 1
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

      # Check if it's the ensurepip issue (Ubuntu 24.10+)
      if grep -q "ensurepip is not available" /tmp/venv-creation.log 2>/dev/null; then
        log_message "Detected Ubuntu 24.10+ - trying version-specific python-venv package..." "INFO"

        # Get Python version
        local py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3.12")

        log_message "Installing python${py_version}-venv..." "INFO"
        if sudo apt-get install -y "python${py_version}-venv" 2>&1 | tee -a /tmp/venv-creation.log; then
          log_message "Retrying virtual environment creation..." "INFO"
          if ! python3 -m venv "$WIZARD_DIR/venv" 2>&1 | tee -a /tmp/venv-creation.log; then
            log_message "Error: Still failed to create virtual environment" "ERROR"
            log_message "Check /tmp/venv-creation.log for details" "ERROR"
            exit 1
          fi
        else
          log_message "Failed to install python${py_version}-venv" "ERROR"
          log_message "Try manually: sudo apt-get install python${py_version}-venv" "ERROR"
          exit 1
        fi
      else
        log_message "This usually means python3-venv is not installed" "ERROR"
        log_message "Install it with: sudo apt-get install python3-venv" "ERROR"
        exit 1
      fi
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

  # Pre-acquire sudo privileges before starting wizard
  # The wizard will need sudo to install STING when user clicks "Install"
  log_message ""
  log_message "The STING installer requires elevated privileges."
  log_message "Checking sudo access (you may be prompted for password)..."
  if ! sudo -v; then
    log_message "Error: Unable to obtain sudo privileges" "ERROR"
    log_message "The wizard cannot install STING without sudo access" "ERROR"
    exit 1
  fi
  log_message "✅ Sudo privileges verified" "SUCCESS"

  # Check for existing installation BEFORE starting wizard/keepalive
  log_message "Checking for existing STING installation..." "INFO"

  has_install_dir=false
  has_containers=false
  has_volumes=false

  if [ -d "/opt/sting-ce" ] && [ -f "/opt/sting-ce/docker-compose.yml" ]; then
    has_install_dir=true
  fi

  if docker ps -a --filter "name=sting-ce" --format '{{.Names}}' 2>/dev/null | grep -q "sting-ce"; then
    has_containers=true
  fi

  if docker volume ls --filter "name=sting" --format '{{.Name}}' 2>/dev/null | grep -q "sting"; then
    has_volumes=true
  fi

  # If any existing installation artifacts found
  if [ "$has_install_dir" = true ] || [ "$has_containers" = true ] || [ "$has_volumes" = true ]; then
    log_message "" "WARNING"
    log_message "⚠️  EXISTING INSTALLATION DETECTED" "WARNING"
    log_message "" "WARNING"

    if [ "$has_install_dir" = true ]; then
      log_message "  • Installation directory exists: /opt/sting-ce" "WARNING"
    fi
    if [ "$has_containers" = true ]; then
      container_count=$(docker ps -a --filter "name=sting-ce" --format '{{.Names}}' 2>/dev/null | wc -l)
      log_message "  • Found $container_count STING container(s)" "WARNING"
    fi
    if [ "$has_volumes" = true ]; then
      volume_count=$(docker volume ls --filter "name=sting" --format '{{.Name}}' 2>/dev/null | wc -l)
      log_message "  • Found $volume_count STING volume(s)" "WARNING"
    fi

    log_message "" "WARNING"
    log_message "An existing or partial installation will prevent the installer from working correctly." "WARNING"
    log_message "" "WARNING"

    # Interactive prompt to clean up
    echo ""
    echo "Would you like to automatically clean up the existing installation?"
    echo ""
    echo "  [1] Yes - Remove everything and start fresh (recommended)"
    echo "  [2] No  - Exit and let me clean up manually"
    echo ""
    read -p "Enter your choice [1-2]: " cleanup_choice

    case "$cleanup_choice" in
      1|yes|y|Y)
        log_message "Running automatic cleanup..." "INFO"
        log_message "Executing: ./manage_sting.sh uninstall --purge" "INFO"

        if "${SCRIPT_DIR}/manage_sting.sh" uninstall --purge; then
          log_message "✅ Cleanup successful! Continuing with installation..." "SUCCESS"
          sleep 2
        else
          log_message "Cleanup failed. Please manually run: ./manage_sting.sh uninstall --purge" "ERROR"
          exit 1
        fi
        ;;
      2|no|n|N)
        log_message "Installation cancelled." "INFO"
        log_message "To clean up manually, run: ./manage_sting.sh uninstall --purge" "INFO"
        exit 0
        ;;
      *)
        log_message "Invalid choice. Installation cancelled." "ERROR"
        log_message "To clean up manually, run: ./manage_sting.sh uninstall --purge" "INFO"
        exit 1
        ;;
    esac
  else
    log_message "✅ No existing installation found" "SUCCESS"
  fi

  # Kill any existing sudo keepalive processes from previous failed installations
  log_message "Cleaning up any stale sudo keepalive processes..." "INFO"
  pkill -f "while true; do sudo -v; sleep" 2>/dev/null || true

  # Start sudo keepalive in background to maintain privileges during installation
  (while true; do sudo -v; sleep 50; done) &
  SUDO_KEEPALIVE_PID=$!

  # Update cleanup function to kill sudo keepalive
  cleanup_wizard() {
    log_message "Cleaning up wizard processes..." "INFO"

    # Kill sudo keepalive
    if [ -n "$SUDO_KEEPALIVE_PID" ]; then
      kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

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

  # Get local IP for display
  LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

  # Detect installation scenario
  IS_REMOTE=false
  if [[ "$LOCAL_IP" != "127.0.0.1" ]] && [[ "$LOCAL_IP" != "localhost" ]] && [[ -n "$LOCAL_IP" ]]; then
    # Check if we're on a VM/remote server (has non-loopback IP)
    if [[ ! "$LOCAL_IP" =~ ^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.) ]] || command -v systemd-detect-virt &>/dev/null; then
      IS_REMOTE=true
    fi
  fi

  log_message ""
  log_message "╔════════════════════════════════════════════════════════════╗"
  log_message "║                                                            ║"
  log_message "║           🐝 STING SETUP WIZARD IS READY! 🐝              ║"
  log_message "║                                                            ║"
  log_message "╚════════════════════════════════════════════════════════════╝"
  log_message ""
  log_message "┌────────────────────────────────────────────────────────────┐"
  log_message "│  📱 OPEN YOUR BROWSER AND NAVIGATE TO:                    │"
  log_message "│                                                            │"

  # Show primary URL based on scenario
  if [[ "$IS_REMOTE" == "true" ]] || [[ "$LOCAL_IP" =~ ^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.) ]]; then
    # Remote VM or network installation - show IP as primary
    log_message "│     🌐  http://$LOCAL_IP:$WIZARD_PORT                       "
    log_message "│                                                            │"
    log_message "│     ℹ️  Access from your browser (not from SSH session)   │"
  else
    # Local installation - show localhost
    log_message "│     🌐  http://localhost:$WIZARD_PORT                       "
    if [[ "$LOCAL_IP" != "localhost" ]] && [[ -n "$LOCAL_IP" ]]; then
      log_message "│                                                            │"
      log_message "│     🌐  http://$LOCAL_IP:$WIZARD_PORT (network access)     "
    fi
  fi

  log_message "│                                                            │"
  log_message "└────────────────────────────────────────────────────────────┘"
  log_message ""
  log_message "💡 The wizard will guide you through 7 easy steps"
  log_message "⏹️  Press Ctrl+C to stop the wizard at any time"
  log_message ""

  # Launch wizard (don't use exec so trap cleanup works)
  cd "$WIZARD_DIR"
  export DEV_MODE=false
  export WIZARD_PORT="$WIZARD_PORT"
  export STING_HOST_IP="$LOCAL_IP"  # For redirect URL after installation

  # Start wizard and save PID
  "$WIZARD_DIR/venv/bin/python3" app.py &
  WIZARD_PID=$!
  echo "$WIZARD_PID" > "$WIZARD_PID_FILE"

  # Wait for wizard to finish
  wait "$WIZARD_PID"

else
  # CLI installation (advanced)
  log_message "Using CLI installation mode..."

  # Pre-acquire sudo privileges before installation starts
  log_message "Installation requires elevated privileges for system setup..."
  log_message "Checking sudo access (you may be prompted for password)..."
  if ! sudo -v; then
    log_message "Error: Unable to obtain sudo privileges" "ERROR"
    log_message "Installation cannot proceed without sudo access" "ERROR"
    exit 1
  fi
  log_message "✅ Sudo privileges verified" "SUCCESS"

  # Check for existing installation BEFORE starting keepalive
  log_message "Checking for existing STING installation..." "INFO"

  has_install_dir=false
  has_containers=false
  has_volumes=false

  if [ -d "/opt/sting-ce" ] && [ -f "/opt/sting-ce/docker-compose.yml" ]; then
    has_install_dir=true
  fi

  if docker ps -a --filter "name=sting-ce" --format '{{.Names}}' 2>/dev/null | grep -q "sting-ce"; then
    has_containers=true
  fi

  if docker volume ls --filter "name=sting" --format '{{.Name}}' 2>/dev/null | grep -q "sting"; then
    has_volumes=true
  fi

  # If any existing installation artifacts found
  if [ "$has_install_dir" = true ] || [ "$has_containers" = true ] || [ "$has_volumes" = true ]; then
    log_message "" "WARNING"
    log_message "⚠️  EXISTING INSTALLATION DETECTED" "WARNING"
    log_message "" "WARNING"

    if [ "$has_install_dir" = true ]; then
      log_message "  • Installation directory exists: /opt/sting-ce" "WARNING"
    fi
    if [ "$has_containers" = true ]; then
      container_count=$(docker ps -a --filter "name=sting-ce" --format '{{.Names}}' 2>/dev/null | wc -l)
      log_message "  • Found $container_count STING container(s)" "WARNING"
    fi
    if [ "$has_volumes" = true ]; then
      volume_count=$(docker volume ls --filter "name=sting" --format '{{.Name}}' 2>/dev/null | wc -l)
      log_message "  • Found $volume_count STING volume(s)" "WARNING"
    fi

    log_message "" "WARNING"
    log_message "An existing or partial installation will prevent the installer from working correctly." "WARNING"
    log_message "" "WARNING"

    # Interactive prompt to clean up
    echo ""
    echo "Would you like to automatically clean up the existing installation?"
    echo ""
    echo "  [1] Yes - Remove everything and start fresh (recommended)"
    echo "  [2] No  - Exit and let me clean up manually"
    echo ""
    read -p "Enter your choice [1-2]: " cleanup_choice

    case "$cleanup_choice" in
      1|yes|y|Y)
        log_message "Running automatic cleanup..." "INFO"
        log_message "Executing: ./manage_sting.sh uninstall --purge" "INFO"

        if "${SCRIPT_DIR}/manage_sting.sh" uninstall --purge; then
          log_message "✅ Cleanup successful! Continuing with installation..." "SUCCESS"
          sleep 2
        else
          log_message "Cleanup failed. Please manually run: ./manage_sting.sh uninstall --purge" "ERROR"
          exit 1
        fi
        ;;
      2|no|n|N)
        log_message "Installation cancelled." "INFO"
        log_message "To clean up manually, run: ./manage_sting.sh uninstall --purge" "INFO"
        exit 0
        ;;
      *)
        log_message "Invalid choice. Installation cancelled." "ERROR"
        log_message "To clean up manually, run: ./manage_sting.sh uninstall --purge" "INFO"
        exit 1
        ;;
    esac
  else
    log_message "✅ No existing installation found" "SUCCESS"
  fi

  # Kill any existing sudo keepalive processes from previous failed installations
  log_message "Cleaning up any stale sudo keepalive processes..." "INFO"
  pkill -f "while true; do sudo -v; sleep" 2>/dev/null || true

  # Keep sudo session alive in background during installation
  # This prevents timeout during long operations
  (while true; do sudo -v; sleep 50; done) &
  SUDO_KEEPALIVE_PID=$!

  # Cleanup function to kill sudo keepalive
  cleanup_sudo() {
    if [ -n "$SUDO_KEEPALIVE_PID" ]; then
      kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
  }
  trap cleanup_sudo EXIT INT TERM

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
