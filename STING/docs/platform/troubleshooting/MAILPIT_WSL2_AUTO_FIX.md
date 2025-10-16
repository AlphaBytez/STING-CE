# Mailpit WSL2 Automatic Port Cleanup

## Overview

This document describes the OS-aware mailpit lifecycle management system that automatically handles the recurring WSL2 port binding issue.

## The Problem

On WSL2, mailpit frequently fails to start with errors like:
```
Error: ports are not available: exposing port TCP 127.0.0.1:8025 -> 127.0.0.1:0:
listen tcp4 127.0.0.1:8025: bind: Only one usage of each socket address is normally permitted.
```

**Root Cause**: Windows' `wslrelay.exe` or `com.docker.backend` processes hold onto ports (8025, 1025) even after containers stop, creating zombie port bindings.

## The Solution

STING now includes **OS-aware mailpit lifecycle management** that automatically:

1. **Detects the platform** (WSL2, Linux, macOS)
2. **Cleans up zombie processes** before starting mailpit
3. **Releases held ports** after stopping mailpit
4. **Handles Windows-specific port forwarding** issues

## Architecture

### Components

1. **`lib/mailpit_lifecycle.sh`** - Standalone lifecycle management script
2. **`lib/services.sh`** - Integration hooks in service management
3. **`lib/platform_helper.sh`** - OS detection utilities

### Automatic Integration

The lifecycle hooks are automatically triggered:

- **Pre-start**: Runs before `docker compose up -d mailpit`
  - Kills zombie docker-proxy processes
  - Terminates WSL relay holding ports
  - Verifies ports are clear

- **Post-stop**: Runs after `docker compose stop`
  - Releases Windows port forwarding
  - Cleans up lingering processes

## Usage

### Automatic (Recommended)

Just use normal STING commands - the hooks run automatically:

```bash
# Start services (mailpit cleanup happens automatically)
./manage_sting.sh start

# Stop services (mailpit cleanup happens automatically)
./manage_sting.sh stop
```

### Manual Troubleshooting

If mailpit still has issues, use the dedicated tool:

```bash
# Check current port status
./lib/mailpit_lifecycle.sh status

# Example output:
# Port 1025: AVAILABLE
# Port 8025: HELD BY WINDOWS (PID: 21184, Process: com.docker.backend)

# Force restart with full cleanup
./lib/mailpit_lifecycle.sh restart

# Just clean up zombie processes
./lib/mailpit_lifecycle.sh cleanup

# Check mailpit health
./lib/mailpit_lifecycle.sh health
```

### Advanced Commands

```bash
# Run pre-start cleanup manually
./lib/mailpit_lifecycle.sh pre-start

# Run post-stop cleanup manually
./lib/mailpit_lifecycle.sh post-stop

# Get help
./lib/mailpit_lifecycle.sh help
```

## Platform-Specific Behavior

### WSL2 (Windows Subsystem for Linux 2)

- **Detected by**: Checking `/proc/version` for "microsoft"
- **Cleanup includes**:
  - Killing zombie `docker-proxy` processes (Linux side)
  - Killing zombie `mailpit` processes (Linux side)
  - Terminating `wslrelay.exe` via PowerShell (Windows side)
  - Stopping `com.docker.backend` port bindings (Windows side)

### Native Linux

- **Cleanup includes**:
  - Killing zombie `docker-proxy` processes
  - Killing zombie `mailpit` processes

### macOS

- **Cleanup includes**:
  - Standard zombie process cleanup
  - Docker Desktop handles port forwarding natively

## Technical Details

### Port Detection

The script checks ports using multiple methods (fallback chain):
1. `lsof -i :PORT` (most reliable)
2. `ss -tlnp | grep :PORT` (Linux fallback)
3. `netstat -tlnp | grep :PORT` (older systems)

### Windows Port Cleanup (WSL2)

Uses PowerShell commands from within WSL:
```powershell
# Find processes using port
Get-NetTCPConnection -LocalPort 8025 | Select-Object -ExpandProperty OwningProcess

# Get process name
Get-Process -Id PID | Select-Object -ExpandProperty ProcessName

# Kill process
Stop-Process -Id PID -Force
```

### Safety Features

- **Graceful failures**: Cleanup errors are logged but don't block startup
- **Process verification**: Only kills known mailpit-related processes
- **Fallback support**: Works even if some tools are missing

## Configuration

### Environment Variables

```bash
# Override mailpit container name (default: sting-ce-mailpit)
export MAILPIT_CONTAINER_NAME="my-custom-mailpit"
```

### Email Mode

Mailpit only starts when `EMAIL_MODE` is set to development:

```bash
# In env/app.env or docker-compose.yml
EMAIL_MODE=development  # Starts mailpit
EMAIL_MODE=production   # Skips mailpit
```

## Troubleshooting

### Mailpit Still Won't Start

If automatic cleanup doesn't work:

1. **Check port status**:
   ```bash
   ./lib/mailpit_lifecycle.sh status
   ```

2. **Try nuclear option - restart WSL**:
   ```powershell
   # From Windows PowerShell
   wsl --shutdown
   ```

3. **Restart Docker Desktop** (if using Docker Desktop on WSL2)

4. **Use different ports** (edit `docker-compose.yml`):
   ```yaml
   mailpit:
     ports:
       - "127.0.0.1:1026:1025"  # Changed from 1025
       - "127.0.0.1:8026:8026"  # Changed from 8025
   ```

### Manual Port Cleanup

```bash
# Find what's using port 8025 (Linux)
sudo lsof -i :8025

# Kill the process
sudo kill -9 <PID>

# Find what's using port 8025 (Windows)
powershell.exe "Get-NetTCPConnection -LocalPort 8025"

# Kill from Windows
powershell.exe "Stop-Process -Id <PID> -Force"
```

### Logs

Check STING logs for lifecycle events:
```bash
./manage_sting.sh logs | grep MAILPIT
```

## Future Enhancements

Potential improvements:

1. **Port conflict resolution**: Automatically select alternative ports if defaults are unavailable
2. **Retry logic**: Automatically retry startup after cleanup
3. **Health monitoring**: Continuous monitoring and auto-recovery
4. **Metrics**: Track cleanup frequency to identify persistent issues

## Related Documentation

- [Platform Compatibility Guide](../PLATFORM_COMPATIBILITY_GUIDE.md)
- [WSL2 Custom Domain Solution](./wsl2-custom-domain-solution.md)
- [Docker WSL Fix](../../lib/docker_wsl_fix.sh)

## Credits

This solution addresses the long-standing WSL2 port binding issue that affects:
- Docker containers using localhost port binding on WSL2
- Windows port forwarding via wslrelay.exe
- Docker Desktop's com.docker.backend process

The OS-aware approach ensures STING works seamlessly across all platforms while automatically handling platform-specific quirks.
