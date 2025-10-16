#!/usr/bin/env bash
#
# STING-CE Bootstrap Installer
#
# Quick install via:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE-Public/main/bootstrap.sh)"
#
# This script will:
#   1. Detect your platform (macOS, WSL, Debian/Ubuntu)
#   2. Check system requirements
#   3. Clone STING-CE repository
#   4. Launch the installation wizard
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Pretty logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Banner
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   STING-CE Bootstrap Installer             ║"
echo "║   Secure Trusted Intelligence & Networking ║"
echo "║                                            ║"
echo "║   Bee Smart. Bee Secure.                   ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Platform detection
log_info "Detecting platform..."

PLATFORM="unknown"
SUGGESTED_LOCATION=""

if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    SUGGESTED_LOCATION="$HOME/STING-CE-Public"
elif grep -qi microsoft /proc/version 2>/dev/null; then
    PLATFORM="WSL"
    SUGGESTED_LOCATION="$HOME/STING-CE-Public"
elif [[ -f /etc/debian_version ]]; then
    PLATFORM="Debian/Ubuntu"
    # For Linux, suggest current directory or let user choose /opt
    SUGGESTED_LOCATION="$PWD/STING-CE-Public"
else
    log_warning "Unknown platform detected. Attempting to proceed..."
    SUGGESTED_LOCATION="$PWD/STING-CE-Public"
fi

log_success "Platform: $PLATFORM"

# Check for required commands
log_info "Checking system requirements..."

MISSING_DEPS=()

if ! command -v git &> /dev/null; then
    MISSING_DEPS+=("git")
fi

if ! command -v curl &> /dev/null; then
    MISSING_DEPS+=("curl")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    log_error "Missing required dependencies: ${MISSING_DEPS[*]}"
    echo ""
    echo "Please install missing dependencies:"

    if [[ "$PLATFORM" == "macOS" ]]; then
        echo "  brew install ${MISSING_DEPS[*]}"
    elif [[ "$PLATFORM" == "Debian/Ubuntu" || "$PLATFORM" == "WSL" ]]; then
        echo "  sudo apt-get update"
        echo "  sudo apt-get install -y ${MISSING_DEPS[*]}"
    fi

    exit 1
fi

log_success "All requirements met"

# Check if Docker is installed (optional, installer will handle it)
if ! command -v docker &> /dev/null; then
    log_warning "Docker not found. The installer will offer to install it for you."
fi

# Ask for installation location
echo ""
log_info "Choose installation location"
echo "  Suggested: $SUGGESTED_LOCATION"
echo ""
read -p "Install location [$SUGGESTED_LOCATION]: " INSTALL_LOC
INSTALL_LOC=${INSTALL_LOC:-$SUGGESTED_LOCATION}

# Expand ~ to home directory
INSTALL_LOC="${INSTALL_LOC/#\~/$HOME}"

# Check if directory already exists
if [ -d "$INSTALL_LOC" ]; then
    log_error "Directory already exists: $INSTALL_LOC"
    read -p "Remove existing directory and continue? [y/N]: " REMOVE_EXISTING

    if [[ ! "$REMOVE_EXISTING" =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled."
        exit 0
    fi

    log_warning "Removing existing directory..."
    rm -rf "$INSTALL_LOC"
fi

# Create parent directory if needed
PARENT_DIR=$(dirname "$INSTALL_LOC")
if [ ! -d "$PARENT_DIR" ]; then
    log_info "Creating parent directory: $PARENT_DIR"
    mkdir -p "$PARENT_DIR"
fi

# Clone repository
echo ""
log_info "Cloning STING-CE repository..."
echo "  Repository: https://github.com/AlphaBytez/STING-CE-Public.git"
echo "  Location: $INSTALL_LOC"
echo ""

if git clone https://github.com/AlphaBytez/STING-CE-Public.git "$INSTALL_LOC"; then
    log_success "Repository cloned successfully"
else
    log_error "Failed to clone repository"
    exit 1
fi

# Change to installation directory
cd "$INSTALL_LOC" || {
    log_error "Failed to change to installation directory"
    exit 1
}

# Check if installer exists
if [ ! -f "./install_sting.sh" ]; then
    log_error "Installer not found at $INSTALL_LOC/install_sting.sh"
    exit 1
fi

# Make sure installer is executable
chmod +x ./install_sting.sh

# Launch installer
echo ""
log_success "STING-CE repository ready!"
echo ""
log_info "Launching installation wizard..."
echo ""

# Pause for a moment so user can read the messages
sleep 1

# Execute installer
exec ./install_sting.sh
