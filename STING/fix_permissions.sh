#!/bin/bash
# STING Permission Fix Script
# Fixes common permission issues after installation or updates
# Works on macOS, Linux, Debian, and WSL2

echo "STING Permission Fix Script"
echo "=========================="

# Detect platform
PLATFORM="unknown"
if [[ "$(uname)" == "Darwin" ]]; then
    PLATFORM="macos"
    echo "Platform: macOS"
elif [[ "$(uname)" == "Linux" ]]; then
    if grep -qi microsoft /proc/version 2>/dev/null; then
        PLATFORM="wsl2"
        echo "Platform: WSL2 (Windows Subsystem for Linux)"
    else
        PLATFORM="linux"
        echo "Platform: Linux"
    fi
fi

# Find STING installation directory based on platform
if [[ "$PLATFORM" == "macos" ]]; then
    INSTALL_DIR="${HOME}/.sting-ce"
else
    # Linux/WSL2 typically uses /opt/sting-ce
    INSTALL_DIR="/opt/sting-ce"
    # Check if user has a local installation
    if [ ! -d "$INSTALL_DIR" ] && [ -d "${HOME}/.sting-ce" ]; then
        INSTALL_DIR="${HOME}/.sting-ce"
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo "ERROR: STING installation not found at $INSTALL_DIR"
    echo "Please run the installation script first."
    exit 1
fi

echo "Found STING installation at: $INSTALL_DIR"

# Fix permissions on manage_sting.sh
echo -n "Fixing permissions on manage_sting.sh... "
if [ -f "$INSTALL_DIR/manage_sting.sh" ]; then
    chmod +x "$INSTALL_DIR/manage_sting.sh"
    echo "✓"
else
    echo "✗ (file not found)"
fi

# Fix permissions on all shell scripts
echo -n "Fixing permissions on all shell scripts... "
find "$INSTALL_DIR" -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null
echo "✓"

# Fix msting command if it exists
if [ -f "/usr/local/bin/msting" ]; then
    echo -n "Fixing permissions on msting command... "
    sudo chmod +x /usr/local/bin/msting
    echo "✓"
fi

# Fix ownership if needed (only if files are owned by root)
if [ -n "$(find "$INSTALL_DIR" -user root -print -quit 2>/dev/null)" ]; then
    echo -n "Fixing ownership (some files owned by root)... "
    # Get the correct group name based on platform
    if [[ "$PLATFORM" == "macos" ]]; then
        GROUP_NAME="$(id -gn)"
    else
        # On Linux/WSL2, use the user's primary group
        GROUP_NAME="$(id -gn $USER)"
    fi
    sudo chown -R "$USER:$GROUP_NAME" "$INSTALL_DIR"
    echo "✓"
fi

# WSL2-specific fixes
if [[ "$PLATFORM" == "wsl2" ]]; then
    echo "Applying WSL2-specific fixes..."
    
    # Fix Docker socket permissions if needed
    if [ -S "/var/run/docker.sock" ]; then
        echo -n "Checking Docker socket permissions... "
        if ! docker ps >/dev/null 2>&1; then
            echo "fixing..."
            sudo chmod 666 /var/run/docker.sock || sudo usermod -aG docker $USER
            echo "✓ (you may need to log out and back in)"
        else
            echo "✓"
        fi
    fi
    
    # Fix potential Windows permission inheritance issues
    if [ -d "$INSTALL_DIR" ]; then
        echo -n "Fixing potential Windows permission inheritance... "
        find "$INSTALL_DIR" -type f -exec chmod 644 {} \; 2>/dev/null
        find "$INSTALL_DIR" -type d -exec chmod 755 {} \; 2>/dev/null
        find "$INSTALL_DIR" -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null
        echo "✓"
    fi
fi

# Linux-specific fixes
if [[ "$PLATFORM" == "linux" ]] || [[ "$PLATFORM" == "wsl2" ]]; then
    # Fix SELinux contexts if SELinux is enabled (mainly for RHEL/CentOS/Fedora)
    if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce)" != "Disabled" ]; then
        echo -n "Fixing SELinux contexts... "
        sudo restorecon -R "$INSTALL_DIR" 2>/dev/null || true
        echo "✓"
    fi
    
    # Ensure user is in docker group
    if ! groups | grep -q docker; then
        echo "Note: You're not in the 'docker' group. You may need to run:"
        echo "  sudo usermod -aG docker $USER"
        echo "  Then log out and back in."
    fi
fi

# Test the fix
echo ""
echo "Testing the fix..."
if [ -x "$INSTALL_DIR/manage_sting.sh" ]; then
    echo "✓ manage_sting.sh is now executable"
    
    # Test msting command
    if command -v msting >/dev/null 2>&1; then
        echo "✓ msting command is available"
        echo ""
        echo "Success! You can now use:"
        echo "  msting status"
        echo "  msting update frontend --sync-only"
        echo "  msting help"
    else
        echo "! msting command not found in PATH"
        echo "  You may need to run the installation script again"
    fi
else
    echo "✗ Failed to fix permissions"
    echo "  Please check the installation and try again"
fi

# Additional checks for all platforms
echo ""
echo "Additional checks:"

# Check if Docker is accessible
echo -n "Docker access... "
if docker ps >/dev/null 2>&1; then
    echo "✓"
else
    echo "✗"
    echo "  You may need to:"
    if [[ "$PLATFORM" == "wsl2" ]]; then
        echo "  - Ensure Docker Desktop is running on Windows"
        echo "  - Check WSL2 integration in Docker Desktop settings"
    elif [[ "$PLATFORM" == "linux" ]]; then
        echo "  - Add yourself to the docker group: sudo usermod -aG docker $USER"
        echo "  - Log out and back in"
        echo "  - Or run Docker commands with sudo"
    fi
fi

# Check environment files
if [ -d "$INSTALL_DIR/env" ]; then
    echo -n "Environment files... "
    chmod 700 "$INSTALL_DIR/env" 2>/dev/null
    find "$INSTALL_DIR/env" -name "*.env" -type f -exec chmod 600 {} \; 2>/dev/null
    echo "✓"
fi

echo ""
echo "Permission fix complete!"
echo "Platform: $PLATFORM"
echo "Install directory: $INSTALL_DIR"