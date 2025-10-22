#!/usr/bin/env bash

# STING Community Edition - Simple Installer
#
# Usage:
#   ./install_sting.sh          # Launch web setup wizard (recommended)
#   ./install_sting.sh --wizard # Launch web setup wizard (explicit)
#   ./install_sting.sh --cli    # CLI installation (advanced)

# Verify bash version (requires 3.0+ for pipefail support)
if [ -z "${BASH_VERSION:-}" ]; then
  echo "Error: This script requires bash. Please run with bash instead of sh."
  echo "Usage: bash $0"
  exit 1
fi

# Check bash version (3.0+ required for pipefail)
BASH_MAJOR="${BASH_VERSION%%.*}"
if [ "$BASH_MAJOR" -lt 3 ]; then
  echo "Error: This script requires bash 3.0 or newer (you have $BASH_VERSION)"
  echo "Please upgrade bash or use a newer system."
  exit 1
fi

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

# Source installation library (dependency check happens later, after sudo setup)
if [ -f "$LIB_DIR/installation.sh" ]; then
  source "$LIB_DIR/installation.sh"
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

# ============================================================================
# COMMON SETUP FOR BOTH WIZARD AND CLI MODES
# Pre-acquire sudo and create directories to avoid prompts during installation
# ============================================================================

log_message ""
log_message "The STING installer requires elevated privileges for system setup."
log_message "Checking sudo access (you may be prompted for password)..."

# Pre-acquire sudo privileges (needed for both wizard and CLI installation)
if ! sudo -v; then
  log_message "Error: Unable to obtain sudo privileges" "ERROR"
  log_message "The installer cannot proceed without sudo access" "ERROR"
  exit 1
fi
log_message "✅ Sudo privileges verified" "SUCCESS"

# Kill any existing sudo keepalive processes from previous failed installations
log_message "Cleaning up any stale sudo keepalive processes..." "INFO"
pkill -f "while true; do sudo -v; sleep" 2>/dev/null || true

# Start sudo keepalive in background to maintain privileges during installation
# This prevents password prompts during wizard installation
# On macOS/WSL2, we use a more aggressive refresh interval (30s instead of 50s)
log_message "Starting sudo keepalive process..." "INFO"

# Create a robust keepalive that logs failures and requests re-auth when needed
# IMPORTANT: More aggressive refresh on macOS (10s) to prevent credential cache expiry
# macOS sudo timeout is typically 5 minutes, but installation can take 15-20+ minutes
if [[ "$(uname)" == "Darwin" ]]; then
    KEEPALIVE_INTERVAL=10  # More aggressive on macOS
else
    KEEPALIVE_INTERVAL=20
fi

# Function to check if we're running under the wizard
is_wizard_mode() {
    [ -n "$WIZARD_CONFIG_PATH" ] || [ -f "/tmp/sting-setup-state/setup-state.json" ]
}

(
  CONSECUTIVE_FAILURES=0
  MAX_CONSECUTIVE_FAILURES=3

  while true; do
    # First try non-interactive refresh
    if sudo -n -v 2>/dev/null; then
      # Success - reset failure counter
      CONSECUTIVE_FAILURES=0
    else
      # Failed - increment counter
      CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
      echo "[$(date)] Sudo keepalive refresh failed (attempt $CONSECUTIVE_FAILURES/$MAX_CONSECUTIVE_FAILURES)" >> /tmp/sudo-keepalive.log 2>&1

      # If we've failed multiple times, try interactive refresh (will prompt user)
      if [ $CONSECUTIVE_FAILURES -ge $MAX_CONSECUTIVE_FAILURES ]; then
        echo "[$(date)] CRITICAL: Sudo credentials expired after $CONSECUTIVE_FAILURES attempts" >> /tmp/sudo-keepalive.log 2>&1

        # If running under wizard, create a flag file that wizard can detect
        if is_wizard_mode; then
          echo "[$(date)] Creating sudo-reauth-needed flag for wizard" >> /tmp/sudo-keepalive.log 2>&1
          touch /tmp/sting-setup-state/sudo-reauth-needed
        fi

        # On macOS, attempt one interactive prompt (will show TouchID or password prompt)
        if [[ "$(uname)" == "Darwin" ]]; then
          echo "[$(date)] Attempting interactive sudo prompt on macOS..." >> /tmp/sudo-keepalive.log 2>&1
          if sudo -v 2>/dev/null; then
            echo "[$(date)] Interactive sudo prompt succeeded" >> /tmp/sudo-keepalive.log 2>&1
            CONSECUTIVE_FAILURES=0
            rm -f /tmp/sting-setup-state/sudo-reauth-needed 2>/dev/null
          else
            echo "[$(date)] Interactive sudo prompt failed - installation may hang" >> /tmp/sudo-keepalive.log 2>&1
          fi
        fi
      fi
    fi
    sleep $KEEPALIVE_INTERVAL
  done
) &
SUDO_KEEPALIVE_PID=$!

# Verify the keepalive process started
if kill -0 "$SUDO_KEEPALIVE_PID" 2>/dev/null; then
  log_message "✅ Sudo keepalive active (PID: $SUDO_KEEPALIVE_PID)" "SUCCESS"
else
  log_message "⚠️  Warning: Sudo keepalive may not have started correctly" "WARNING"
fi

# Pre-create system directories to avoid sudo prompts during installation
log_message "Preparing system directories..." "INFO"

# Create /usr/local/bin on macOS (needed for msting wrapper command)
if [[ "$(uname)" == "Darwin" ]] && [ ! -d "/usr/local/bin" ]; then
  if sudo -n mkdir -p /usr/local/bin 2>/dev/null; then
    log_message "✅ Created /usr/local/bin" "SUCCESS"
  else
    log_message "⚠️  Could not create /usr/local/bin - msting command may not be available" "WARNING"
  fi
fi

# Create installation directory if it doesn't exist
# On macOS: $HOME/.sting-ce (user-owned, no sudo needed)
# On Linux: /opt/sting-ce (needs sudo)
if [ ! -d "$INSTALL_DIR" ]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    # macOS - create in user home (no sudo needed)
    if mkdir -p "$INSTALL_DIR" 2>/dev/null; then
      log_message "✅ Created $INSTALL_DIR" "SUCCESS"
    else
      log_message "⚠️  Could not create $INSTALL_DIR" "WARNING"
    fi
  else
    # Linux - create in /opt (needs sudo)
    log_message "Creating installation directory at $INSTALL_DIR..." "INFO"
    if sudo -n mkdir -p "$INSTALL_DIR" 2>/dev/null; then
      # Set ownership to current user
      sudo -n chown -R "$USER:$(id -gn)" "$INSTALL_DIR" 2>/dev/null
      log_message "✅ Created $INSTALL_DIR" "SUCCESS"
    else
      log_message "⚠️  Could not create $INSTALL_DIR" "WARNING"
    fi
  fi
fi

log_message ""

# ============================================================================
# SYSTEM DEPENDENCY CHECK
# Now that sudo is acquired and keepalive is running, check/install dependencies
# ============================================================================

log_message "Checking system dependencies..."
if ! check_and_install_dependencies; then
  log_message "Error: Failed to install required system dependencies" "ERROR"
  exit 1
fi
log_message "✅ System dependencies check completed successfully" "SUCCESS"
log_message ""

# ============================================================================
# WIZARD OR CLI INSTALLATION MODE
# ============================================================================

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

  # Check for existing installation BEFORE starting wizard
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

  # Update cleanup function to kill sudo keepalive (started in common setup above)
  cleanup_wizard() {
    log_message "Cleaning up wizard processes..." "INFO"

    # Kill sudo keepalive process
    if [ -n "${SUDO_KEEPALIVE_PID:-}" ]; then
      log_message "Stopping sudo keepalive (PID: $SUDO_KEEPALIVE_PID)..." "INFO"
      kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
      # Also kill any child processes
      pkill -P "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

    # Also kill by pattern as a fallback
    pkill -f "while true; do sudo -v; sleep" 2>/dev/null || true

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

  # ========================================================================
  # PRE-WIZARD HOSTNAME CONFIGURATION
  # Configure hostname BEFORE wizard starts to ensure it's resolvable
  # ========================================================================

  log_message ""
  log_message "╔════════════════════════════════════════════════════════════╗"
  log_message "║      🌐 STING Hostname Configuration                      ║"
  log_message "╚════════════════════════════════════════════════════════════╝"
  log_message ""
  log_message "STING needs a hostname for WebAuthn/Passkey support."
  log_message "This hostname will be used to access both the wizard and STING."
  log_message ""

  # Source hostname detection library
  if [ -f "$LIB_DIR/hostname_detection.sh" ]; then
    source "$LIB_DIR/hostname_detection.sh"
  else
    log_message "⚠️ hostname_detection.sh not found, using fallback" "WARNING"
    WIZARD_HOSTNAME="localhost"
  fi

  # Get hostname interactively (uses library's get_sting_hostname function)
  # Use ${STING_HOSTNAME:-} to avoid unbound variable error with set -u
  if [ -z "${STING_HOSTNAME:-}" ]; then
    WIZARD_HOSTNAME=$(get_sting_hostname true)
  else
    # Use pre-set environment variable
    WIZARD_HOSTNAME="$STING_HOSTNAME"
    log_message "Using pre-configured hostname: $WIZARD_HOSTNAME"
  fi

  # Validate we got a hostname
  if [ -z "$WIZARD_HOSTNAME" ]; then
    log_message "⚠️ No hostname configured, defaulting to localhost" "WARNING"
    WIZARD_HOSTNAME="localhost"
  fi

  log_message ""
  log_message "✅ Selected hostname: $WIZARD_HOSTNAME"
  log_message ""

  # Get local IP for hosts file updates
  LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

  # Update hosts files if needed (skip for localhost and IP addresses)
  if [ "$WIZARD_HOSTNAME" != "localhost" ] && ! [[ "$WIZARD_HOSTNAME" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    log_message "📝 Configuring DNS resolution for $WIZARD_HOSTNAME..."
    log_message ""

    # Update local /etc/hosts
    # On macOS, use 127.0.0.1 for local-only access (simpler than mDNS)
    # On Linux/WSL2, use actual IP for network access
    hosts_ip="$LOCAL_IP"
    if [[ "$(uname)" == "Darwin" ]]; then
      hosts_ip="127.0.0.1"
      log_message "Using 127.0.0.1 for macOS local access"
    fi

    if ! grep -q "[[:space:]]$WIZARD_HOSTNAME" /etc/hosts 2>/dev/null; then
      log_message "Updating /etc/hosts..."
      if echo "$hosts_ip  $WIZARD_HOSTNAME  # Added by STING installer" | sudo tee -a /etc/hosts >/dev/null 2>&1; then
        log_message "✅ /etc/hosts updated" "SUCCESS"
      else
        log_message "⚠️ Could not update /etc/hosts" "WARNING"
      fi
    else
      log_message "✅ Hostname already in /etc/hosts" "SUCCESS"
    fi

    # WSL2: Generate PowerShell helper script for Windows hosts file
    if is_wsl2 2>/dev/null; then
      log_message ""
      log_message "🪟 WSL2 detected - generating Windows hosts file helper..."

      # Generate PowerShell script in user's home directory (accessible from Windows)
      PS_SCRIPT="$HOME/setup-sting-hostname.ps1"

      cat > "$PS_SCRIPT" << 'PSEOF'
# STING Hostname Configuration for Windows
# This script updates the Windows hosts file to resolve STING hostname from WSL2
#
# Usage: Run this in PowerShell as Administrator
#   Right-click PowerShell -> Run as Administrator
#   .\setup-sting-hostname.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   STING Hostname Configuration for Windows           " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell icon" -ForegroundColor Yellow
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "  3. Navigate to: cd ~" -ForegroundColor Yellow
    Write-Host "  4. Run: .\setup-sting-hostname.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
PSEOF

      # Add hostname and IP to the PowerShell script
      cat >> "$PS_SCRIPT" << PSEOF
\$hostname = "$WIZARD_HOSTNAME"
\$ipAddress = "$LOCAL_IP"
PSEOF

      cat >> "$PS_SCRIPT" << 'PSEOF'

Write-Host "Hostname: $hostname" -ForegroundColor Cyan
Write-Host "IP Address: $ipAddress" -ForegroundColor Cyan
Write-Host ""

# Check if entry already exists
$hostsContent = Get-Content $hostsPath -Raw
if ($hostsContent -match [regex]::Escape($hostname)) {
    Write-Host "WARNING: Hostname '$hostname' already exists in hosts file" -ForegroundColor Yellow
    Write-Host ""
    $replace = Read-Host "Replace existing entry? (Y/N)"

    if ($replace -eq "Y" -or $replace -eq "y") {
        Write-Host "Removing old entry..." -ForegroundColor Yellow

        # Remove old entries
        $lines = Get-Content $hostsPath
        $newLines = $lines | Where-Object { $_ -notmatch [regex]::Escape($hostname) }
        $newLines | Set-Content $hostsPath

        Write-Host "Old entry removed" -ForegroundColor Green
    } else {
        Write-Host "Cancelled - no changes made" -ForegroundColor Yellow
        exit 0
    }
}

# Add new entry
Write-Host "Adding hostname to Windows hosts file..." -ForegroundColor Cyan
Add-Content -Path $hostsPath -Value "$ipAddress  $hostname  # Added by STING installer"

Write-Host "Windows hosts file updated successfully!" -ForegroundColor Green
Write-Host ""

# Test resolution
Write-Host "Testing hostname resolution..." -ForegroundColor Cyan
try {
    $result = Test-Connection -ComputerName $hostname -Count 1 -Quiet
    if ($result) {
        Write-Host "Hostname resolves correctly!" -ForegroundColor Green
    } else {
        Write-Host "Hostname added but ping test failed (this may be normal if ICMP is blocked)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not test hostname (this may be normal)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Configuration Complete!                            " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now access STING using the hostname:" -ForegroundColor Cyan
Write-Host "  http://${hostname}:8335" -ForegroundColor Green
Write-Host ""
PSEOF

      # Convert to Windows line endings (CRLF) and add UTF-8 BOM for PowerShell compatibility
      sed -i 's/$/\r/' "$PS_SCRIPT" 2>/dev/null || true
      # Add UTF-8 BOM (EF BB BF) which PowerShell prefers
      printf '\xEF\xBB\xBF' | cat - "$PS_SCRIPT" > "$PS_SCRIPT.tmp" && mv "$PS_SCRIPT.tmp" "$PS_SCRIPT"

      # Make the script accessible from Windows by converting path
      WINDOWS_PS_SCRIPT=$(wslpath -w "$PS_SCRIPT")

      # Also copy to Windows home directory for easier access
      WINDOWS_HOME=$(wslpath "$(cmd.exe /c "echo %USERPROFILE%" 2>/dev/null | tr -d '\r')")
      if [ -d "$WINDOWS_HOME" ]; then
        WINDOWS_PS_COPY="$WINDOWS_HOME/setup-sting-hostname.ps1"
        cp "$PS_SCRIPT" "$WINDOWS_PS_COPY" 2>/dev/null && \
          log_message "✅ PowerShell script also copied to Windows home directory" "SUCCESS"
      fi

      log_message "✅ PowerShell helper script generated" "SUCCESS"
      log_message ""
      log_message "╔════════════════════════════════════════════════════════════╗"
      log_message "║   📝 Windows Hosts File Configuration (Optional)          ║"
      log_message "╚════════════════════════════════════════════════════════════╝"
      log_message ""
      log_message "To use the hostname from your Windows browser:"
      log_message ""
      log_message "1️⃣  Open PowerShell as Administrator (Windows)"
      log_message "2️⃣  Run this command:"
      log_message ""
      log_message "   .\\setup-sting-hostname.ps1"
      log_message ""
      log_message "   (Script is in your Windows home directory)"
      log_message ""
      log_message "📁 Backup location (if needed): $WINDOWS_PS_SCRIPT"
      log_message ""
      log_message "OR use the IP address directly (works now):"
      log_message "   http://$LOCAL_IP:8335"
      log_message ""
      log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      log_message ""
      log_message "💡 TIP: You can run the PowerShell script now in another window,"
      log_message "   or continue and use the IP address for the wizard."
      log_message ""
    fi

    # Verify hostname resolves
    log_message ""
    log_message "🔍 Verifying hostname resolution..."
    if verify_hostname_resolves "$WIZARD_HOSTNAME" 2>&1 | while read line; do
      log_message "$line"
    done; then
      log_message "✅ Hostname is resolvable!" "SUCCESS"
    else
      log_message ""
      log_message "⚠️ Warning: Hostname may not be resolvable" "WARNING"
      log_message "   Wizard may not be accessible via hostname" "WARNING"
      log_message "   Fallback: Use IP address $LOCAL_IP instead" "WARNING"
      log_message ""
      read -p "Press Enter to continue or Ctrl+C to abort..."
    fi
  fi

  log_message ""

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

  # Show configured hostname (already verified to resolve)
  log_message "│     🌐  http://$WIZARD_HOSTNAME:$WIZARD_PORT"
  log_message "│                                                            │"

  # Show alternative IP access if different from hostname
  if [[ "$WIZARD_HOSTNAME" != "$LOCAL_IP" ]] && [[ "$LOCAL_IP" != "localhost" ]] && [[ "$LOCAL_IP" != "127.0.0.1" ]] && [[ -n "$LOCAL_IP" ]]; then
    log_message "│     Alternative (direct IP): http://$LOCAL_IP:$WIZARD_PORT"
    log_message "│                                                            │"
  fi

  # Add helpful hint for remote/VM installations
  if [[ "$IS_REMOTE" == "true" ]] || [[ "$LOCAL_IP" =~ ^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.) ]]; then
    log_message "│     ℹ️  Access from your browser (not from SSH session)   │"
    log_message "│                                                            │"
  fi

  log_message "└────────────────────────────────────────────────────────────┘"
  log_message ""
  log_message "💡 The wizard will guide you through 7 easy steps"
  log_message "⏹️  Press Ctrl+C to stop the wizard at any time"
  log_message ""

  # Launch wizard (don't use exec so trap cleanup works)
  cd "$WIZARD_DIR"
  export DEV_MODE=false
  export WIZARD_PORT="$WIZARD_PORT"
  export STING_HOSTNAME="$WIZARD_HOSTNAME"  # Primary: hostname for WebAuthn/Passkey compatibility
  export STING_HOST_IP="$LOCAL_IP"          # Secondary: IP address for reference/fallback

  # Start wizard and save PID
  "$WIZARD_DIR/venv/bin/python3" app.py &
  WIZARD_PID=$!
  echo "$WIZARD_PID" > "$WIZARD_PID_FILE"

  # Wait for wizard to finish
  wait "$WIZARD_PID"

else
  # CLI installation (advanced)
  log_message "Using CLI installation mode..."
  log_message ""

  # Check for existing installation
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
