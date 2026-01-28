#!/bin/bash

# Quick Tailscale setup for current session
echo "Setting up Tailscale for current Codespace session..."

# Create directories
sudo mkdir -p /var/lib/tailscale /var/run/tailscale
sudo chown -R $USER:$USER /var/lib/tailscale /var/run/tailscale

# Kill any existing tailscaled processes
sudo pkill -f tailscaled || true

# Start tailscaled
echo "Starting tailscaled..."
sudo tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# Wait for it to start
sleep 3

# Check if it's running
if pgrep -x "tailscaled" > /dev/null; then
    echo "✅ Tailscaled is running!"
    
    # Set up environment for easy use
    export TAILSCALE_SOCKET=/var/run/tailscale/tailscaled.sock
    echo "export TAILSCALE_SOCKET=/var/run/tailscale/tailscaled.sock" >> ~/.bashrc
    
    echo ""
    echo "🚀 To connect to your Tailscale network:"
    echo "   1. Get an auth key from: https://login.tailscale.com/admin/settings/keys"
    echo "   2. Run: tailscale up --auth-key=YOUR_AUTH_KEY"
    echo "   3. Or use: ./tailscale-codespace.sh connect YOUR_AUTH_KEY"
    echo ""
    echo "💡 Use './tailscale-codespace.sh status' to check connection status"
else
    echo "❌ Failed to start tailscaled"
    exit 1
fi