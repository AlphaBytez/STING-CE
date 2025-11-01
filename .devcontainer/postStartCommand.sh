#!/bin/bash

# Post-start script to ensure Tailscale is running
echo "Checking Tailscale status..."

# Ensure socket directory exists
sudo mkdir -p /var/run/tailscale
sudo chown -R vscode:vscode /var/run/tailscale

# Start tailscale if needed
/usr/local/bin/start-tailscale.sh

# Add tailscale to PATH for current session
export PATH="/usr/bin:$PATH"

echo "Tailscale post-start setup complete!"