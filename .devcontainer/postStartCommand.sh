#!/bin/bash

# Post-start script - runs every time the container starts

if command -v tailscaled &> /dev/null; then
    echo "Checking Tailscale status..."
    sudo mkdir -p /var/run/tailscale
    sudo chown -R vscode:vscode /var/run/tailscale

    if [ -x /usr/local/bin/start-tailscale.sh ]; then
        /usr/local/bin/start-tailscale.sh
    fi
    echo "Tailscale post-start setup complete!"
else
    echo "Tailscale not installed — skipping. Run install_sting.sh if needed."
fi