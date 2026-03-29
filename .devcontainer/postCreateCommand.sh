#!/bin/bash

# Post-create setup for GitHub Codespaces
# This script runs after the container is created

# --- Tailscale setup (optional - skip if not installed) ---
if command -v tailscaled &> /dev/null; then
    echo "Setting up Tailscale for persistent use in Codespace..."

    sudo mkdir -p /var/lib/tailscale
    sudo chown -R vscode:vscode /var/lib/tailscale

    sudo mkdir -p /var/run/tailscale
    sudo chown -R vscode:vscode /var/run/tailscale

    sudo tee /usr/local/bin/start-tailscale.sh > /dev/null << 'EOF'
#!/bin/bash
if ! command -v tailscaled &> /dev/null; then
    echo "Tailscale is not installed. Skipping."
    exit 0
fi
if ! pgrep -x "tailscaled" > /dev/null; then
    echo "Starting tailscaled..."
    sudo tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
    sleep 2
fi
if ! tailscale status --socket=/var/run/tailscale/tailscaled.sock > /dev/null 2>&1; then
    echo "Tailscale needs authentication. Run: tailscale up --auth-key=YOUR_AUTH_KEY"
else
    echo "Tailscale is running and authenticated"
fi
EOF
    sudo chmod +x /usr/local/bin/start-tailscale.sh

    /usr/local/bin/start-tailscale.sh

    echo "Tailscale setup complete!"
    echo "To connect to your tailnet, run: tailscale up --auth-key=YOUR_AUTH_KEY"
    echo "Get an auth key from: https://login.tailscale.com/admin/settings/keys"
else
    echo "Tailscale not installed — skipping Tailscale setup."
    echo "Run install_sting.sh to install all dependencies including Tailscale."
fi