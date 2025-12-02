#!/bin/bash
# 06-prebuild-wizard.sh - Pre-build the web setup wizard's Python venv
#
# This ensures the wizard can start immediately on first boot without
# needing to download pip packages (which could fail if network is slow).
set -e

echo "=== STING-CE OVA Build: Pre-building Wizard Dependencies ==="

STING_SOURCE="/opt/sting-ce-source"
WIZARD_DIR="$STING_SOURCE/STING/web-setup"

# Check if wizard directory exists
if [ ! -d "$WIZARD_DIR" ]; then
    echo "ERROR: Wizard directory not found at $WIZARD_DIR"
    exit 1
fi

cd "$WIZARD_DIR"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Upgrade pip first
echo "Upgrading pip..."
./venv/bin/pip install --upgrade pip

# Install wizard dependencies
echo "Installing wizard dependencies (this may take a minute)..."
if [ -f "requirements.txt" ]; then
    ./venv/bin/pip install -r requirements.txt
else
    echo "WARNING: requirements.txt not found, installing minimal deps"
    ./venv/bin/pip install flask pyyaml requests
fi

# Verify installation
echo "Verifying installation..."
./venv/bin/python3 -c "import flask; print(f'Flask {flask.__version__} installed')"

# Set proper permissions
echo "Setting permissions..."
chown -R root:root venv

echo ""
echo "=== Wizard venv pre-built successfully ==="
echo "Contents: $(du -sh venv | cut -f1)"
