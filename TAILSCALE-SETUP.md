# Tailscale Setup for GitHub Codespaces

This repository includes automated Tailscale setup for GitHub Codespaces, allowing you to securely connect your Codespace to your Tailscale network.

## Quick Setup (Current Session)

For immediate setup in your current Codespace:

```bash
./setup-tailscale-now.sh
```

Then connect with your auth key:
```bash
tailscale up --auth-key=YOUR_AUTH_KEY
```

## Persistent Setup (Future Codespaces)

The repository includes devcontainer configuration that will automatically set up Tailscale in new Codespaces.

### Files included:
- `.devcontainer/devcontainer.json` - Main devcontainer configuration
- `.devcontainer/postCreateCommand.sh` - Runs after container creation
- `.devcontainer/postStartCommand.sh` - Runs when container starts
- `tailscale-codespace.sh` - Management script for Tailscale

## Getting an Auth Key

1. Go to https://login.tailscale.com/admin/settings/keys
2. Click "Generate auth key"
3. Set options:
   - ✅ Reusable (recommended for development)
   - ✅ Ephemeral (optional - device will be removed when disconnected)
   - Set appropriate expiration time
4. Copy the generated key (starts with `tskey-auth-`)

### 🔒 **Security Best Practices:**
- **NEVER commit auth keys to version control**
- Use the provided `tailscale-auth.template` file:
  ```bash
  cp tailscale-auth.template tailscale-auth.local
  # Edit tailscale-auth.local with your key
  source tailscale-auth.local
  ./tailscale-codespace.sh connect "$TAILSCALE_AUTH_KEY"
  ```
- Use ephemeral keys for temporary development
- Set reasonable expiration times (30-90 days for dev)
- Consider using OAuth login for production setups

## Usage

### Using the management script:
```bash
# Start Tailscale daemon
./tailscale-codespace.sh start

# Check status
./tailscale-codespace.sh status

# Connect to your tailnet
./tailscale-codespace.sh connect tskey-auth-your-key-here

# Disconnect
./tailscale-codespace.sh disconnect

# Stop daemon
./tailscale-codespace.sh stop
```

### Using Tailscale directly:
```bash
# Check status
tailscale status

# Connect
tailscale up --auth-key=tskey-auth-your-key-here

# Disconnect
tailscale down
```

## Troubleshooting

### If Tailscale isn't working:

1. **Check if tailscaled is running:**
   ```bash
   pgrep -x tailscaled
   ```

2. **Restart Tailscale:**
   ```bash
   ./tailscale-codespace.sh stop
   ./tailscale-codespace.sh start
   ```

3. **Check socket path:**
   ```bash
   ls -la /var/run/tailscale/
   ```

4. **Manual daemon start:**
   ```bash
   sudo tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &
   ```

### Common Issues:

- **"failed to connect to local tailscaled"**: The daemon isn't running. Use the management script to start it.
- **Permission denied**: Make sure directories have correct ownership and the user is in the right groups.
- **Auth key expired**: Generate a new auth key from the Tailscale admin panel.

## Security Notes

- Auth keys should be treated as secrets
- Use ephemeral keys for temporary development environments
- Set appropriate expiration times for auth keys
- Consider using OAuth login instead of auth keys for production setups

## What This Setup Does

1. **Creates persistent state directory**: `/var/lib/tailscale/` with proper permissions
2. **Sets up socket directory**: `/var/run/tailscale/` for daemon communication
3. **Installs management scripts**: For easy Tailscale lifecycle management
4. **Configures devcontainer**: Automatically sets up Tailscale in new Codespaces
5. **Mounts volumes**: Preserves Tailscale state across container restarts