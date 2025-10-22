# WSL2 Fresh Install Checklist

## Overview

This checklist consolidates lessons learned from WSL2-specific issues to ensure clean installations and avoid common pitfalls.

## Pre-Installation Checklist

### Environment Preparation

- [ ] **Verify WSL2 version**
  ```bash
  wsl --status
  # Should show WSL version 2
  ```

- [ ] **Check Docker Desktop WSL2 integration**
  - Open Docker Desktop → Settings → Resources → WSL Integration
  - Enable integration for your WSL2 distro

- [ ] **Verify available disk space**
  ```bash
  df -h /opt
  # Need at least 10GB free for STING installation
  ```

- [ ] **Check port availability**
  ```bash
  # Test that key ports are available
  for port in 5050 8025 8081 8090 8091 4433 5433 6379; do
    nc -z localhost $port && echo "⚠️  Port $port in use" || echo "✅ Port $port available"
  done
  ```

## Configuration Checklist

### docker-compose.yml Port Bindings

**Critical for WSL2:** Use `0.0.0.0` instead of `127.0.0.1` for services you need to access from Windows browser.

- [ ] **Review all port bindings**
  ```bash
  grep -n "127.0.0.1:" docker-compose.yml
  ```

- [ ] **Update services accessible from Windows**
  ```yaml
  # Services that need Windows browser access:
  frontend:
    ports:
      - "0.0.0.0:8443:80"    # Main UI

  mailpit:
    ports:
      - "0.0.0.0:8025:8025"  # Email testing UI
      - "0.0.0.0:1025:1025"  # SMTP

  grafana:
    ports:
      - "0.0.0.0:3000:3000"  # Metrics UI
  ```

- [ ] **Verify internal:external port mappings match**
  ```bash
  # Check each service's actual listening port
  docker logs <container-name> | grep "listening\|starting on"
  ```

### Installation Directory Consistency

- [ ] **Choose ONE installation directory**
  - Development: `/mnt/c/DevWorld/STING-CE/STING`
  - Production: `/opt/sting-ce`

- [ ] **Set INSTALL_DIR environment variable**
  ```bash
  export INSTALL_DIR="/opt/sting-ce"
  echo 'export INSTALL_DIR="/opt/sting-ce"' >> ~/.bashrc
  ```

- [ ] **Verify all config paths use INSTALL_DIR**
  ```bash
  grep -r "INSTALL_DIR" lib/*.sh | grep -v "INSTALL_DIR:-"
  ```

## Post-Installation Verification

### Service Accessibility Tests

- [ ] **Test from WSL localhost**
  ```bash
  curl -I http://localhost:8025  # Mailpit
  curl -I http://localhost:8443  # Frontend
  ```

- [ ] **Test from Windows browser**
  - Open Chrome/Edge
  - Navigate to `http://localhost:8443` (Frontend)
  - Navigate to `http://localhost:8025` (Mailpit)
  - Should see the UIs load (not connection refused)

- [ ] **Test Docker DNS resolution**
  ```bash
  docker exec sting-ce-app curl -s http://mailpit:8025 | head -5
  docker exec sting-ce-app curl -s http://kratos:4433/health/ready
  ```

### Port Binding Verification

- [ ] **Verify containers are listening on 0.0.0.0**
  ```bash
  docker port sting-ce-mailpit
  # Should show: 8025/tcp -> 0.0.0.0:8025
  # NOT: 8025/tcp -> 127.0.0.1:8025
  ```

- [ ] **Check Windows can reach ports**
  ```powershell
  # From PowerShell
  Test-NetConnection -ComputerName localhost -Port 8025
  Test-NetConnection -ComputerName localhost -Port 8443
  # TcpTestSucceeded should be True
  ```

### WSL2-Specific Checks

- [ ] **Verify mailpit lifecycle hooks are installed**
  ```bash
  ls -lh lib/mailpit_lifecycle.sh
  grep -n "mailpit_lifecycle.sh" lib/services.sh
  ```

- [ ] **Test mailpit lifecycle manager**
  ```bash
  ./lib/mailpit_lifecycle.sh status
  ./lib/mailpit_lifecycle.sh health
  ```

- [ ] **Check for zombie port processes**
  ```bash
  ./lib/mailpit_lifecycle.sh ports
  # Should show all ports as available or properly in use
  ```

## Common WSL2 Issues & Quick Fixes

### Issue 1: "Port already in use" on mailpit

**Symptoms:**
```
Error: ports are not available: listen tcp4 127.0.0.1:8025: bind: address already in use
```

**Quick Fix:**
```bash
./lib/mailpit_lifecycle.sh restart
# or
./lib/mailpit_lifecycle.sh cleanup && docker compose up -d mailpit
```

### Issue 2: Services work in WSL but not from Windows browser

**Cause:** Port bound to `127.0.0.1` instead of `0.0.0.0`

**Fix:**
```bash
# 1. Stop services
./manage_sting.sh stop

# 2. Update docker-compose.yml
sed -i 's/127.0.0.1:8025/0.0.0.0:8025/g' docker-compose.yml
sed -i 's/127.0.0.1:8443/0.0.0.0:8443/g' docker-compose.yml

# 3. Restart services
./manage_sting.sh start
```

### Issue 3: Wrong installation directory being used

**Symptoms:** Changes to config don't take effect

**Fix:**
```bash
# Find which directory containers are using
docker inspect sting-ce-app --format='{{index .Config.Labels "com.docker.compose.project.working_dir"}}'

# Stop and restart from correct directory
cd /opt/sting-ce
./manage_sting.sh stop
./manage_sting.sh start
```

### Issue 4: WSL2 IP address changes after restart

**Symptoms:** Saved URLs stop working after WSL restart

**Solutions:**
1. **Use localhost:** Always use `http://localhost:PORT` from Windows (works with 0.0.0.0 binding)
2. **Get current IP:** `hostname -I | awk '{print $1}'`
3. **Fixed IP (advanced):** Configure `.wslconfig` in Windows
   ```ini
   # C:\Users\YourName\.wslconfig
   [wsl2]
   networkingMode=mirrored
   ```

## Best Practices for WSL2 Development

### 1. **Always use 0.0.0.0 for UI services**
Services you'll access from Windows browser should bind to `0.0.0.0`:
- Frontend
- Mailpit
- Grafana
- Any admin UI

### 2. **Use 127.0.0.1 for internal-only services**
Services that should ONLY be accessed within Docker network:
- Database (postgres)
- Redis
- Vault (internal API)

### 3. **Document your installation path**
Create a file to remember which directory is active:
```bash
echo "/opt/sting-ce" > ~/.sting_install_dir
export INSTALL_DIR=$(cat ~/.sting_install_dir)
```

### 4. **Test port forwarding after WSL restart**
WSL restarts can cause port forwarding issues:
```bash
# After WSL restart
./lib/mailpit_lifecycle.sh cleanup
docker compose restart
```

### 5. **Use the lifecycle management tools**
Don't manually kill processes:
```bash
# Use this
./lib/mailpit_lifecycle.sh restart

# Not this
docker stop mailpit && docker start mailpit
```

## Automation: Pre-Flight Check Script

Create this script to run before starting STING:

```bash
#!/bin/bash
# preflight_check.sh

echo "STING WSL2 Pre-Flight Check"
echo "============================"

# Check WSL version
if grep -qi microsoft /proc/version; then
    echo "✅ Running on WSL"
else
    echo "⚠️  Not running on WSL"
fi

# Check Docker
if docker ps >/dev/null 2>&1; then
    echo "✅ Docker is accessible"
else
    echo "❌ Docker is not accessible"
    exit 1
fi

# Check port bindings in docker-compose.yml
if grep -q "127.0.0.1:8025\|127.0.0.1:8443" docker-compose.yml; then
    echo "⚠️  Found 127.0.0.1 port bindings (should be 0.0.0.0 for WSL2)"
    echo "   Run: sed -i 's/127.0.0.0/0.0.0.0/g' docker-compose.yml"
else
    echo "✅ Port bindings look good"
fi

# Check for zombie ports
if lsof -i :8025 >/dev/null 2>&1; then
    echo "⚠️  Port 8025 already in use"
    echo "   Run: ./lib/mailpit_lifecycle.sh cleanup"
fi

# Check INSTALL_DIR
if [[ -z "${INSTALL_DIR}" ]]; then
    echo "⚠️  INSTALL_DIR not set"
    echo "   Run: export INSTALL_DIR=/opt/sting-ce"
else
    echo "✅ INSTALL_DIR: $INSTALL_DIR"
fi

echo ""
echo "Pre-flight check complete!"
```

## Summary of Key Learnings

1. **Port Binding:** `0.0.0.0` for Windows-accessible services on WSL2
2. **Port Accuracy:** External:internal mappings must match actual listening ports
3. **Single Source of Truth:** One installation directory, set via INSTALL_DIR
4. **Lifecycle Management:** Use provided tools for mailpit and other problematic services
5. **Testing:** Always test from both WSL and Windows browser after changes
6. **Documentation:** Keep track of which installation directory is active

## Related Documentation

- [Mailpit WSL2 Auto-Fix](../troubleshooting/MAILPIT_WSL2_AUTO_FIX.md)
- [Platform Compatibility Guide](../PLATFORM_COMPATIBILITY_GUIDE.md)
- [WSL2 Custom Domain Solution](../troubleshooting/wsl2-custom-domain-solution.md)

---

**Note:** This checklist is based on real issues encountered during development. Following these steps will help avoid the most common WSL2 pitfalls.
