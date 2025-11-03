# Certificate Management for WebAuthn and Secure Access

## Overview

STING-CE includes comprehensive certificate management automation to ensure WebAuthn/passkey authentication works seamlessly across different machines and network configurations. This is critical for production deployments where users access STING from various devices.

## The Challenge

WebAuthn authentication requires trusted TLS certificates. When STING runs in VMs, containers, or remote servers, clients often encounter certificate errors that break passkey functionality:

- **Certificate Authority not trusted** on client machines
- **Domain mismatch** between certificates and access URLs
- **Self-signed certificate warnings** blocking WebAuthn APIs

## STING's Solution: Automated Certificate Distribution

STING-CE provides a complete certificate automation system that:

1. **Generates trusted certificates** using mkcert for development/internal use
2. **Creates cross-platform installers** for Windows, macOS, and Linux
3. **Automates distribution** to client machines via SCP/rsync
4. **Handles domain configuration** automatically

## 🚀 Quick Start

### Generate Certificate Bundle

```bash
# Export certificates with installation scripts
./manage_sting.sh export-certs ./client-certs

# Files created:
# - sting-ca.pem (Certificate Authority)
# - install-ca-mac.sh (macOS installer)
# - install-ca-linux.sh (Linux installer) 
# - install-ca-windows.ps1 (Windows installer)
```

### Distribute to Client Machines

```bash
# Copy to remote machine
./manage_sting.sh copy-certs user@client-machine /home/user/certs

# Or manually distribute the ./client-certs folder
```

### Client Installation

**On the client machine, run the appropriate installer:**

**macOS:**
```bash
./install-ca-mac.sh
```

**Linux:**
```bash
./install-ca-linux.sh
```

**Windows (as Administrator):**
```powershell
.\install-ca-windows.ps1
```

## 📖 Detailed Guide

### Certificate Generation

The `export-certs` command creates a complete certificate bundle:

```bash
./manage_sting.sh export-certs [output-directory]
```

**What it does:**
- Exports the mkcert Certificate Authority (CA) certificate
- Detects current STING domain and IP configuration
- Generates platform-specific installation scripts
- Creates ready-to-distribute bundle

**Output files:**
- `sting-ca.pem` - The CA certificate file
- `install-ca-mac.sh` - macOS installer script
- `install-ca-linux.sh` - Linux installer script (Ubuntu/Debian/RHEL/CentOS/Fedora)
- `install-ca-windows.ps1` - Windows PowerShell installer

### Remote Distribution

For automated deployment to multiple machines:

```bash
./manage_sting.sh copy-certs user@hostname /remote/path [source-dir]
```

**Parameters:**
- `user@hostname` - SSH target (user and hostname/IP)
- `/remote/path` - Destination directory on remote machine
- `source-dir` - Optional source directory (default: auto-generate)

**Features:**
- Uses rsync when available (with progress), falls back to scp
- Automatically generates certificates if source directory doesn't exist
- Provides clear next-step instructions after transfer

### Cross-Platform Installers

Each installer script:
- **Validates environment** and checks for required permissions
- **Installs CA certificate** to system certificate store
- **Updates hosts file** with domain mapping
- **Provides clear feedback** on success/failure
- **Includes uninstall instructions**

#### macOS Installer Features
- Installs to System Keychain (requires admin password)
- Updates /etc/hosts with domain mapping
- Validates certificate installation
- User-friendly prompts and error messages

#### Linux Installer Features
- Auto-detects distribution (Ubuntu/Debian/RHEL/CentOS/Fedora)
- Uses appropriate certificate store location
- Updates CA certificate trust database
- Handles /etc/hosts modifications with sudo

#### Windows Installer Features
- Requires Administrator privileges (automatic check)
- Installs to LocalMachine certificate store
- Updates Windows hosts file
- PowerShell-based with colored output
- Comprehensive error handling

## 🔧 Integration with STING Configuration

### Domain Configuration

Ensure your STING domain is properly configured for certificate generation:

```yaml
# In conf/config.yml
system:
  hostname: "sting.yourdomain.local"  # or IP address
  domain: "yourdomain.local"
```

**Or using the web wizard:**
1. Navigate to System Configuration
2. Set Hostname/Domain appropriately
3. Complete installation
4. Generate certificates using the configured domain

### WebAuthn Compatibility

Certificate management works seamlessly with WebAuthn:

1. **Domain Consistency**: Certificates use the same domain as WebAuthn RP ID
2. **Cross-Machine Support**: Clients can use passkeys registered on any machine
3. **Trust Chain**: Proper certificate trust eliminates WebAuthn security errors

## 🏢 Production Deployment Scenarios

### VM/Container Deployments

**Scenario**: STING running in VMware/Docker, accessed from host machines

**Solution**:
```bash
# 1. Configure STING with accessible domain/IP
# 2. Generate certificates
./manage_sting.sh export-certs ./vm-client-certs

# 3. Copy to host machine and install
# Host will now trust STING certificates
```

### Multi-User Environments

**Scenario**: Multiple team members accessing shared STING instance

**Solution**:
```bash
# 1. Generate certificate bundle
./manage_sting.sh export-certs ./team-certs

# 2. Distribute via shared storage, email, or direct copy
./manage_sting.sh copy-certs user1@machine1 /home/user1/sting-certs
./manage_sting.sh copy-certs user2@machine2 /home/user2/sting-certs

# 3. Each user runs installer on their machine
```

### Enterprise Deployments

**Scenario**: STING deployed on internal servers, accessed by employee workstations

**Solution**:
```bash
# 1. Generate certificates with internal domain
./manage_sting.sh export-certs ./enterprise-certs

# 2. Package in software deployment system
# 3. Push installers to all employee workstations
# 4. Deploy via group policy, Ansible, or similar
```

## 🛠️ Advanced Usage

### Custom Certificate Bundle

To create certificates for a specific domain/IP:

```bash
# 1. Update STING configuration first
nano conf/config.yml

# 2. Regenerate environment with new domain
./manage_sting.sh regenerate-env

# 3. Regenerate SSL certificates
./manage_sting.sh restart

# 4. Export new certificate bundle
./manage_sting.sh export-certs ./custom-domain-certs
```

### Batch Distribution

For multiple target machines:

```bash
#!/bin/bash
# batch-cert-deploy.sh

MACHINES=(
    "user1@192.168.1.100"
    "user2@192.168.1.101"
    "admin@192.168.1.102"
)

for machine in "${MACHINES[@]}"; do
    echo "Deploying certificates to $machine..."
    ./manage_sting.sh copy-certs "$machine" /home/${machine%@*}/sting-certs
done
```

### Certificate Validation

To verify certificate installation on client machines:

```bash
# Test certificate trust
openssl s_client -connect sting.yourdomain.local:8443 -verify_return_error

# Test WebAuthn compatibility
curl -k https://sting.yourdomain.local:8443/api/health
```

## 🔍 Troubleshooting

### Common Issues

**Certificate Not Trusted After Installation**
- Restart browser completely
- Check certificate store: `security find-certificate -a -c "mkcert"` (macOS)
- Verify hosts file: `cat /etc/hosts | grep sting`

**Permission Denied During Installation**
- Ensure scripts are executable: `chmod +x install-ca-*.sh`
- Run with appropriate privileges (sudo for Linux, admin for Windows)
- Check file permissions in exported directory

**Domain Mismatch Errors**
- Verify STING domain configuration matches certificate
- Check browser URL matches certificate domain exactly
- Regenerate certificates after domain changes

**SCP/Rsync Failures**
- Verify SSH key authentication to target machines
- Check network connectivity and firewall rules
- Ensure destination directory exists and is writable

### Debug Commands

```bash
# Check current STING domain configuration
grep -r "hostname\|domain" conf/config.yml

# Verify certificate generation
ls -la /var/lib/docker/volumes/sting_certs/_data/

# Test mkcert installation
mkcert -version

# Check certificate details
openssl x509 -in ./client-certs/sting-ca.pem -text -noout
```

## 🔗 Related Documentation

- [Passkey Cross-Machine Instructions](PASSKEY_CROSS_MACHINE_INSTRUCTIONS.md)
- [Passkey Quickstart Guide](PASSKEY_QUICKSTART.md)
- [System Configuration Guide](../operations/configuration.md)
- [Security Best Practices](../../SECURITY.md)

## 💡 Tips and Best Practices

1. **Generate certificates after domain changes** - Always regenerate when changing hostnames
2. **Test on one machine first** - Verify certificate installation before mass deployment
3. **Keep certificate bundles updated** - Regenerate periodically or after STING updates
4. **Document your domain strategy** - Ensure all team members use consistent URLs
5. **Automate for large deployments** - Use configuration management for enterprise rollouts

---

*This certificate management system ensures seamless WebAuthn authentication across all your STING deployments, eliminating certificate trust issues that break passkey functionality.*