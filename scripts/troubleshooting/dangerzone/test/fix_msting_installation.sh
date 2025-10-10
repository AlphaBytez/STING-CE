#!/bin/bash

# fix_msting_installation.sh - Fix the msting command installation
# This script addresses the missing msting command installation

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Platform detection
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
fi

# Check if we're in the right directory
check_environment() {
    if [ ! -f "$SCRIPT_DIR/manage_sting.sh" ]; then
        print_error "This script must be run from the STING directory"
        exit 1
    fi
    
    print_info "STING directory: $SCRIPT_DIR"
    print_info "Install directory: $INSTALL_DIR"
}

# Function to install msting command
install_msting_command() {
    print_info "Installing msting command..."
    
    local target_path="/usr/local/bin/msting"
    local source_path="$SCRIPT_DIR/manage_sting.sh"
    
    # Create wrapper script content
    local wrapper_content="#!/bin/bash
# msting - STING Community Edition Management Command
# This wrapper calls the installed manage_sting.sh script

# Determine install directory based on platform
if [[ \"\$(uname)\" == \"Darwin\" ]]; then
    INSTALL_DIR=\"\${INSTALL_DIR:-\$HOME/.sting-ce}\"
else
    INSTALL_DIR=\"\${INSTALL_DIR:-/opt/sting-ce}\"
fi

# Check if manage_sting.sh exists in install directory
if [ -f \"\$INSTALL_DIR/manage_sting.sh\" ]; then
    # Call the installed version
    exec \"\$INSTALL_DIR/manage_sting.sh\" \"\$@\"
elif [ -f \"$SCRIPT_DIR/manage_sting.sh\" ]; then
    # Fallback to source directory
    exec \"$SCRIPT_DIR/manage_sting.sh\" \"\$@\"
else
    echo \"Error: STING installation not found\"
    echo \"Expected locations:\"
    echo \"  \$INSTALL_DIR/manage_sting.sh\"
    echo \"  $SCRIPT_DIR/manage_sting.sh\"
    exit 1
fi
"
    
    # Try to create wrapper with sudo
    if command -v sudo >/dev/null 2>&1; then
        print_info "Creating msting command (requires sudo)..."
        echo "$wrapper_content" | sudo tee "$target_path" >/dev/null
        sudo chmod +x "$target_path"
        print_success "msting command installed successfully"
    else
        print_warning "sudo not available. Manual installation required:"
        echo ""
        echo "Run the following commands as root:"
        echo "cat > $target_path << 'EOF'"
        echo "$wrapper_content"
        echo "EOF"
        echo "chmod +x $target_path"
        return 1
    fi
}

# Function to fix the installation script
fix_installation_script() {
    print_info "Fixing installation script to include msting command..."
    
    # Check if the install_msting_command call is missing from lib/installation.sh
    if ! grep -q "install_msting_command" "$SCRIPT_DIR/lib/installation.sh" 2>/dev/null; then
        print_warning "install_msting_command not found in installation.sh"
        return 0
    fi
    
    # Check if it's being called in the main installation function
    if ! grep -A 20 "install_msting()" "$SCRIPT_DIR/lib/installation.sh" | grep -q "install_msting_command"; then
        print_warning "install_msting_command may not be called during installation"
        
        # Try to fix it by adding the call
        local install_function_end
        install_function_end=$(grep -n "log_message.*installation complete" "$SCRIPT_DIR/lib/installation.sh" | head -1 | cut -d: -f1)
        
        if [ ! -z "$install_function_end" ]; then
            print_info "Adding msting command installation to install function..."
            
            # Create a backup
            cp "$SCRIPT_DIR/lib/installation.sh" "$SCRIPT_DIR/lib/installation.sh.bak.$(date +%Y%m%d_%H%M%S)"
            
            # Insert the call before the completion message
            sed -i.tmp "${install_function_end}i\\
    # Install msting command\\
    install_msting_command || print_warning \"Failed to install msting command\"\\
" "$SCRIPT_DIR/lib/installation.sh"
            
            rm -f "$SCRIPT_DIR/lib/installation.sh.tmp"
            print_success "Fixed installation script"
        fi
    fi
}

# Function to check if msting command exists and works
check_msting_command() {
    print_info "Checking msting command..."
    
    if command -v msting >/dev/null 2>&1; then
        print_success "msting command is available"
        
        # Test if it works
        if msting --help >/dev/null 2>&1; then
            print_success "msting command works correctly"
            
            # Show version info
            echo ""
            print_info "Testing msting command:"
            msting --version 2>/dev/null || msting status 2>/dev/null || echo "msting command installed but may need configuration"
        else
            print_warning "msting command exists but may not work correctly"
        fi
    else
        print_warning "msting command not found in PATH"
        return 1
    fi
}

# Function to update the interface module to include msting installation
fix_interface_module() {
    print_info "Checking interface module for msting installation..."
    
    local interface_file="$SCRIPT_DIR/lib/interface.sh"
    
    if [ -f "$interface_file" ]; then
        # Check if install command calls install_msting_command
        if grep -A 10 "install.*)" "$interface_file" | grep -q "install_msting"; then
            print_success "Interface module already includes msting installation"
        else
            print_warning "Interface module may be missing msting installation call"
            
            # Add a note for manual fixing
            echo ""
            print_info "To fix manually, ensure the install command in lib/interface.sh includes:"
            echo "    load_module \"installation\""
            echo "    install_msting \"\$@\""
        fi
    else
        print_warning "Interface module not found"
    fi
}

# Function to create a quick installer for msting
create_msting_installer() {
    print_info "Creating standalone msting installer..."
    
    cat > "$SCRIPT_DIR/install_msting.sh" << 'EOF'
#!/bin/bash
# Standalone msting command installer

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Platform detection
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
fi

target_path="/usr/local/bin/msting"

wrapper_content="#!/bin/bash
# msting - STING Community Edition Management Command

# Determine install directory based on platform
if [[ \"\$(uname)\" == \"Darwin\" ]]; then
    INSTALL_DIR=\"\${INSTALL_DIR:-\$HOME/.sting-ce}\"
else
    INSTALL_DIR=\"\${INSTALL_DIR:-/opt/sting-ce}\"
fi

# Check if manage_sting.sh exists in install directory
if [ -f \"\$INSTALL_DIR/manage_sting.sh\" ]; then
    exec \"\$INSTALL_DIR/manage_sting.sh\" \"\$@\"
elif [ -f \"$SCRIPT_DIR/manage_sting.sh\" ]; then
    exec \"$SCRIPT_DIR/manage_sting.sh\" \"\$@\"
else
    echo \"Error: STING installation not found\"
    exit 1
fi
"

echo "Installing msting command..."
echo "$wrapper_content" | sudo tee "$target_path" >/dev/null
sudo chmod +x "$target_path"
echo "✅ msting command installed successfully"
EOF
    
    chmod +x "$SCRIPT_DIR/install_msting.sh"
    print_success "Created standalone installer: install_msting.sh"
}

# Main execution
main() {
    echo "🔧 STING msting Command Installation Fix"
    echo "========================================"
    echo ""
    
    check_environment
    echo ""
    
    # Check current status
    if check_msting_command; then
        echo ""
        print_info "msting command is already working. No action needed."
        exit 0
    fi
    
    echo ""
    print_info "Attempting to fix msting command installation..."
    echo ""
    
    # Try to install the command
    if install_msting_command; then
        echo ""
        check_msting_command
    fi
    
    echo ""
    fix_installation_script
    echo ""
    fix_interface_module
    echo ""
    create_msting_installer
    
    echo ""
    echo "🎉 msting Installation Fix Complete!"
    echo ""
    echo "What was done:"
    echo "• Installed msting command to /usr/local/bin/msting"
    echo "• Created standalone installer: install_msting.sh"
    echo "• Checked installation script for future installs"
    echo ""
    echo "Usage:"
    echo "  msting status       # Check STING status"
    echo "  msting start        # Start STING services"
    echo "  msting stop         # Stop STING services"
    echo "  msting install      # Install STING"
    echo "  msting --help       # Show all commands"
    echo ""
    
    if ! command -v msting >/dev/null 2>&1; then
        print_warning "If msting command still doesn't work, run:"
        print_info "  sudo ./install_msting.sh"
    fi
}

# Run main function
main "$@"
