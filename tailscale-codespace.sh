#!/bin/bash

# Tailscale management script for Codespaces
# Usage: ./tailscale-codespace.sh [start|stop|status|connect|disconnect]

SOCKET_PATH="/var/run/tailscale/tailscaled.sock"
STATE_PATH="/var/lib/tailscale/tailscaled.state"

start_tailscale() {
    echo "Starting Tailscale..."
    
    # Create necessary directories
    sudo mkdir -p /var/lib/tailscale /var/run/tailscale
    sudo chown -R vscode:vscode /var/lib/tailscale /var/run/tailscale
    
    # Check if already running
    if pgrep -x "tailscaled" > /dev/null; then
        echo "Tailscaled is already running"
        return 0
    fi
    
    # Start tailscaled
    sudo tailscaled --state="$STATE_PATH" --socket="$SOCKET_PATH" &
    sleep 3
    
    if pgrep -x "tailscaled" > /dev/null; then
        echo "Tailscaled started successfully"
    else
        echo "Failed to start tailscaled"
        return 1
    fi
}

stop_tailscale() {
    echo "Stopping Tailscale..."
    sudo pkill -x tailscaled
    echo "Tailscaled stopped"
}

status_tailscale() {
    if pgrep -x "tailscaled" > /dev/null; then
        echo "Tailscaled is running"
        tailscale --socket="$SOCKET_PATH" status 2>/dev/null || echo "Tailscale not connected to tailnet"
    else
        echo "Tailscaled is not running"
    fi
}

connect_tailscale() {
    if [ -z "$1" ]; then
        echo "Usage: $0 connect <auth-key>"
        echo "Get an auth key from: https://login.tailscale.com/admin/settings/keys"
        echo ""
        echo "⚠️  WARNING: Never commit auth keys to version control!"
        echo "   Use ephemeral keys for temporary development environments."
        return 1
    fi
    
    start_tailscale
    echo "Connecting to Tailscale..."
    echo "⚠️  Using auth key (keep this secure!)"
    tailscale --socket="$SOCKET_PATH" up --auth-key="$1"
}

disconnect_tailscale() {
    echo "Disconnecting from Tailscale..."
    tailscale --socket="$SOCKET_PATH" down
}

case "$1" in
    start)
        start_tailscale
        ;;
    stop)
        stop_tailscale
        ;;
    status)
        status_tailscale
        ;;
    connect)
        connect_tailscale "$2"
        ;;
    disconnect)
        disconnect_tailscale
        ;;
    *)
        echo "Usage: $0 {start|stop|status|connect <auth-key>|disconnect}"
        echo ""
        echo "Examples:"
        echo "  $0 start                          # Start tailscaled daemon"
        echo "  $0 status                         # Check status"
        echo "  $0 connect tskey-auth-xxxxx       # Connect with auth key"
        echo "  $0 disconnect                     # Disconnect from tailnet"
        echo ""
        echo "Get an auth key from: https://login.tailscale.com/admin/settings/keys"
        exit 1
        ;;
esac