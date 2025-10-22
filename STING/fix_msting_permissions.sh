#!/bin/bash
# Quick fix for msting permission issues
# This script fixes the msting wrapper to not require execute permissions

echo "🔧 STING msting Permission Fix"
echo "================================"
echo ""

# Detect install directory
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${HOME}/.sting-ce"
else
    INSTALL_DIR="/opt/sting-ce"
fi

echo "Install directory: $INSTALL_DIR"
echo ""

# Fix 1: Update the msting wrapper to use bash explicitly
echo "Step 1: Updating /usr/local/bin/msting wrapper..."
if sudo tee /usr/local/bin/msting > /dev/null <<'EOF'
#!/bin/bash
# msting - STING Community Edition Management Command
# This wrapper calls the installed manage_sting.sh script

# Determine install directory
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
fi

# Call the actual script using bash explicitly (doesn't require execute perms)
exec bash "$INSTALL_DIR/manage_sting.sh" "$@"
EOF
then
    sudo chmod +x /usr/local/bin/msting
    echo "✅ Updated msting wrapper successfully"
else
    echo "❌ Failed to update msting wrapper"
    exit 1
fi

# Fix 2: Set execute permissions on manage_sting.sh (still good practice)
echo ""
echo "Step 2: Setting execute permissions on manage_sting.sh..."
if [ -f "$INSTALL_DIR/manage_sting.sh" ]; then
    sudo chmod +x "$INSTALL_DIR/manage_sting.sh"
    echo "✅ Set execute permissions on manage_sting.sh"
else
    echo "⚠️  manage_sting.sh not found at $INSTALL_DIR"
fi

# Fix 3: Fix all shell scripts in the directory
echo ""
echo "Step 3: Fixing permissions on all shell scripts..."
sudo find "$INSTALL_DIR" -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null
echo "✅ Fixed permissions on all .sh files"

# Test the fix
echo ""
echo "Testing the fix..."
echo "Running: msting help"
echo "---"
if msting help 2>&1 | head -5; then
    echo "---"
    echo ""
    echo "✅ SUCCESS! The msting command is now working."
    echo ""
    echo "You can now run:"
    echo "  sudo msting create admin admin@sting.local"
    echo "  msting status"
    echo "  msting help"
else
    echo "---"
    echo ""
    echo "⚠️  There may still be issues. Try running:"
    echo "  sudo bash $INSTALL_DIR/manage_sting.sh help"
fi
