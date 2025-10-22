# WSL2 Custom Domain Solution for STING

## Overview

This guide explains how using a custom domain can solve WSL2 networking issues and provide a more stable STING installation experience. Custom domains help bypass localhost/127.0.0.1 networking complexities that are common in WSL2 environments.

## Why Custom Domains Help with WSL2

### The Problem

WSL2 uses a virtualized network adapter that can cause issues with:
- **Port binding**: Services bound to localhost in WSL2 aren't always accessible from Windows
- **Cookie domains**: Authentication cookies set for "localhost" may not work correctly
- **Service discovery**: Inter-container communication can fail when using localhost
- **HTTPS certificates**: Self-signed certs for localhost often cause browser warnings

### The Solution

Using a custom domain (e.g., `sting.local`) provides:
- **Consistent addressing**: Same domain works from WSL2, Windows, and containers
- **Better cookie handling**: Cookies work reliably with proper domain names
- **Simplified HTTPS**: Browsers handle self-signed certs better for custom domains
- **Network stability**: Avoids WSL2's localhost forwarding complexities

## Step-by-Step Setup

### 1. Choose Your Domain

Select a domain that won't conflict with real domains:
- Recommended: `sting.local` or `sting.test`
- Avoid: `.com`, `.org`, or other real TLDs
- Custom: `yourcompany-sting.local`

### 2. Configure STING for Custom Domain

#### Option A: Environment Variables (Recommended)

Before installation, set these environment variables:

```bash
# In WSL2 terminal
export DOMAIN_NAME="sting.local"
export REACT_APP_API_URL="https://sting.local:5050"
export REACT_APP_KRATOS_PUBLIC_URL="https://sting.local:4433"
export PUBLIC_URL="https://sting.local:8443"
export WEBAUTHN_RP_ID="sting.local"

# Run installation
./install_sting.sh install
```

#### Option B: Configuration File

Edit `conf/config.yml` before installation:

```yaml
application:
  host: sting.local
  ssl:
    domain: "${DOMAIN_NAME:-sting.local}"
    
frontend:
  react:
    api_url: "https://sting.local:5050"

kratos:
  public_url: "https://sting.local:4433"
  cookie_domain: "sting.local"
  
  selfservice:
    default_return_url: "https://sting.local:8443"
    login:
      ui_url: "https://sting.local:8443/login"
    registration:
      ui_url: "https://sting.local:8443/register"
      
  methods:
    webauthn:
      rp_id: "sting.local"
      origin: "https://sting.local:8443"
```

### 3. Update Windows Hosts File

This is the critical step for WSL2. You must update the Windows hosts file, not just the WSL2 hosts file.

#### Automatic Method (PowerShell as Administrator)

```powershell
# Run in Windows PowerShell as Administrator
$domain = "sting.local"
$hostsPath = "$env:windir\System32\drivers\etc\hosts"

# Add entries
Add-Content -Path $hostsPath -Value "`n# STING WSL2"
Add-Content -Path $hostsPath -Value "127.0.0.1    $domain"
Add-Content -Path $hostsPath -Value "::1          $domain"

# Verify
Get-Content $hostsPath | Select-String $domain
```

#### Manual Method

1. Open Windows Explorer
2. Navigate to `C:\Windows\System32\drivers\etc`
3. Right-click on `hosts` file, select "Open with" → Notepad (as Administrator)
4. Add these lines at the end:
   ```
   # STING WSL2
   127.0.0.1    sting.local
   ::1          sting.local
   ```
5. Save the file

### 4. Configure Services for Network Access

Ensure all STING services bind to all interfaces:

```bash
# Check current bindings
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Services should show 0.0.0.0:PORT->PORT/tcp
# Not 127.0.0.1:PORT->PORT/tcp
```

### 5. Install with Custom Domain Support

Run the enhanced installation:

```bash
# This will detect WSL2 and configure accordingly
./install_sting.sh install

# Or manually trigger WSL2 Ollama setup
./scripts/check_and_install_ollama_wsl2.sh install
./scripts/check_and_install_ollama_wsl2.sh configure-domain sting.local
```

### 6. Verify Installation

After installation, verify all services are accessible:

```bash
# From WSL2
curl -k https://sting.local:8443/health
curl -k https://sting.local:5050/api/health
curl https://localhost:11434/v1/models

# Check Ollama specifically
./scripts/check_and_install_ollama_wsl2.sh check
```

From Windows browser:
- Navigate to https://sting.local:8443
- Accept the self-signed certificate
- Login with default credentials

## Benefits of This Approach

### 1. **Consistent Authentication**
- Kratos cookies work reliably with proper domain
- Session management functions correctly
- WebAuthn/Passkeys work with consistent RP ID

### 2. **Service Communication**
- Frontend can reliably reach backend API
- Inter-container networking is stable
- Ollama API is accessible from all services

### 3. **Development Experience**
- Same URLs work from WSL2 and Windows
- Browser developer tools work normally
- No need for port forwarding tricks

### 4. **HTTPS Handling**
- Self-signed certificates are accepted once
- Browser remembers the exception for the domain
- Consistent SSL/TLS across all services

## Troubleshooting

### Issue: "Cannot reach sting.local"

1. Verify Windows hosts file has the entry
2. Flush DNS cache: `ipconfig /flushdns` (in Windows)
3. Check WSL2 IP: `ip addr show eth0` (might need to use actual IP instead of 127.0.0.1)

### Issue: "Certificate errors persist"

1. Clear browser cache and cookies
2. Regenerate certificates for the custom domain
3. Import the CA certificate to Windows trust store

### Issue: "Services not accessible from Windows"

1. Check Docker Desktop settings - ensure WSL2 integration is enabled
2. Verify services bind to 0.0.0.0, not 127.0.0.1
3. Check Windows Firewall rules

### Issue: "Ollama not accessible"

```bash
# Check Ollama binding
./scripts/check_and_install_ollama_wsl2.sh check

# Ensure OLLAMA_HOST is set correctly
echo $OLLAMA_HOST  # Should be 0.0.0.0:11434
```

## Advanced Configuration

### Using mDNS (Bonjour/Avahi)

For automatic network discovery without hosts file:

```bash
# Install avahi in WSL2
sudo apt-get install avahi-daemon avahi-utils

# Configure service
sudo nano /etc/avahi/avahi-daemon.conf
# Set: enable-dbus=no

# Start service
sudo service avahi-daemon start

# Your service will be available as sting.local via mDNS
```

### Custom SSL Certificates

For production-like setup:

```bash
# Generate certificates for custom domain
cd ~/.sting-ce/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout sting.local.key \
  -out sting.local.crt \
  -subj "/CN=sting.local" \
  -addext "subjectAltName=DNS:sting.local,DNS:*.sting.local"

# Update configuration to use new certs
```

### Multiple Environments

Use different domains for different instances:

- Development: `sting.dev.local`
- Testing: `sting.test.local`
- Demo: `sting.demo.local`

## Conclusion

Using custom domains with STING on WSL2 provides a more stable and production-like development environment. While it requires initial setup of the Windows hosts file, the benefits in terms of reliability and consistency make it worthwhile for WSL2 users.

For automated setup and verification, use the provided WSL2-specific scripts:
- `scripts/check_and_install_ollama_wsl2.sh` - Ollama management
- `lib/ollama_wsl2.sh` - WSL2 integration module
- `docs/custom-domain-setup.md` - General custom domain guide

The custom domain approach effectively sidesteps many WSL2 networking quirks and provides a smoother STING experience.