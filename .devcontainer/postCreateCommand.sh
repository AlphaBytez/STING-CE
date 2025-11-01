#!/bin/bash

# Tailscale setup for GitHub Codespaces
# This script runs after the container is created

echo "Setting up Tailscale for persistent use in Codespace..."

# Create tailscale state directory
sudo mkdir -p /var/lib/tailscale
sudo chown -R vscode:vscode /var/lib/tailscale

# Create a systemd-style service script for tailscaled
sudo tee /usr/local/bin/start-tailscale.sh > /dev/null << 'EOF'
#!/bin/bash

# Start tailscaled if not running
if ! pgrep -x "tailscaled" > /dev/null; then
    echo "Starting tailscaled..."
    sudo tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
    sleep 2
fi

# Check if we need to authenticate
if ! tailscale status --socket=/var/run/tailscale/tailscaled.sock > /dev/null 2>&1; then
    echo "Tailscale needs authentication. Run: tailscale up --auth-key=YOUR_AUTH_KEY"
else
    echo "Tailscale is running and authenticated"
fi
EOF

sudo chmod +x /usr/local/bin/start-tailscale.sh

# Create socket directory
sudo mkdir -p /var/run/tailscale
sudo chown -R vscode:vscode /var/run/tailscale

# Start tailscale now
/usr/local/bin/start-tailscale.sh

echo "Tailscale setup complete!"
echo "To connect to your tailnet, run: tailscale up --auth-key=YOUR_AUTH_KEY"
echo "Get an auth key from: https://login.tailscale.com/admin/settings/keys"