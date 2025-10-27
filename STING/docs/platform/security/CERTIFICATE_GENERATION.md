# STING Certificate Generation Guide

## Overview

STING automatically generates SSL/TLS certificates based on your domain configuration. The system intelligently detects your domain type and uses the appropriate certificate generation method.

## Certificate Generation Methods

### 1. **localhost** - Self-Signed Certificates
- **When Used**: Domain is exactly `localhost`
- **Why**: Browsers have built-in exceptions for localhost
- **WebAuthn Support**: ✅ Yes (browsers trust localhost)
- **Setup**: Automatic, no additional tools needed

### 2. **Local Custom Domains** - mkcert (Locally-Trusted)
- **When Used**: Domains like `sting.local`, `queen.hive`, `my-sting.local`, etc.
- **Detection**: Automatically detected by:
  - TLD ending in `.local`, `.localhost`, `.test`, `.internal`, `.lan`
  - Domain listed in `/etc/hosts`
  - Bare hostname without dots
- **Why**: WebAuthn/Passkeys require valid TLS certificates
- **WebAuthn Support**: ✅ Yes (mkcert installs local CA in system trust store)
- **Setup**: Automatic installation of mkcert during STING installation

**mkcert Features:**
- Creates locally-trusted certificates
- Installs CA certificate in system trust store
- Works with all major browsers (Chrome, Firefox, Safari, Edge)
- Certificates are trusted without browser warnings
- Perfect for development and local deployments

### 3. **Public Domains** - Let's Encrypt (Future)
- **When Used**: Real public domains (e.g., `sting.example.com`)
- **Status**: Planned feature (currently falls back to self-signed with warning)
- **WebAuthn Support**: ✅ Yes (once implemented)
- **Requirements**:
  - DNS configured to point to your server
  - Port 80 accessible for ACME challenge
  - Valid email for certificate notifications

## Installation Process

### Automatic Installation

During STING installation, the system will:

1. **Detect your domain** (from wizard or `DOMAIN_NAME` environment variable)
2. **Determine domain type** (localhost, local custom, or public)
3. **Install appropriate tools**:
   - For local custom domains: Install `mkcert` and setup local CA
   - For public domains: Install `certbot` (future)
4. **Generate certificates** using the appropriate method
5. **Install certificates** in Docker volumes and local directories

### Manual mkcert Installation

If automatic installation fails, install mkcert manually:

#### macOS (Homebrew)
```bash
brew install mkcert nss
mkcert -install
```

#### Linux (Ubuntu/Debian)
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y wget libnss3-tools

# Download and install mkcert
wget -O /tmp/mkcert https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
chmod +x /tmp/mkcert
sudo mv /tmp/mkcert /usr/local/bin/mkcert

# Install local CA
mkcert -install
```

#### Linux (RHEL/CentOS)
```bash
# Install dependencies
sudo yum install -y wget nss-tools

# Download and install mkcert
wget -O /tmp/mkcert https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
chmod +x /tmp/mkcert
sudo mv /tmp/mkcert /usr/local/bin/mkcert

# Install local CA
mkcert -install
```

## Domain Configuration

### Setting Domain During Installation

The STING wizard automatically detects your hostname:

1. **FQDN Detection**: Tries `hostname -f` first
2. **Local Suffix**: Adds `.local` to short hostname (e.g., `myvm` → `myvm.local`)
3. **Fallback**: Uses `sting.local` as default

You can override this by setting `DOMAIN_NAME` environment variable:

```bash
export DOMAIN_NAME="my-custom.local"
./install_sting.sh
```

### Updating Domain After Installation

To change your domain after installation:

1. Update `conf/config.yml`:
   ```yaml
   system:
     domain: my-new-domain.local
   ```

2. Regenerate certificates:
   ```bash
   ./manage_sting.sh regenerate-certs
   ```

3. Update `/etc/hosts` if needed:
   ```bash
   sudo bash -c 'echo "127.0.0.1 my-new-domain.local" >> /etc/hosts'
   ```

4. Restart services:
   ```bash
   ./manage_sting.sh restart
   ```

## Troubleshooting

### WebAuthn/Passkeys Not Working

**Error**: `NotAllowedError: WebAuthn is not supported on sites with TLS certificate errors`

**Cause**: Self-signed certificates are being used instead of mkcert

**Solution**:
1. Verify your domain is a local custom domain (ends in `.local`)
2. Check if mkcert is installed: `which mkcert`
3. If not installed, run: `./manage_sting.sh install-mkcert`
4. Regenerate certificates: `./manage_sting.sh regenerate-certs`
5. Clear browser cache and restart browser

### mkcert Installation Failed

**Solution**:
1. Install manually (see "Manual mkcert Installation" above)
2. Verify installation: `mkcert -CAROOT`
3. Ensure CA is installed: `mkcert -install`
4. Regenerate STING certificates

### Browser Still Shows Certificate Warning

**Solution**:
1. Verify mkcert CA is installed: `mkcert -CAROOT`
2. Reinstall CA if needed: `mkcert -install`
3. **Firefox**: May need to set `security.enterprise_roots.enabled` to `true` in `about:config`
4. **Chrome/Safari**: Restart browser completely
5. **Linux**: Ensure `libnss3-tools` is installed

### Certificates Not Updating

**Solution**:
1. Check certificate location:
   ```bash
   ls -la ~/.sting-ce/certs/
   docker run --rm -v sting_certs:/certs alpine ls -la /certs
   ```
2. Manually regenerate:
   ```bash
   cd ~/.sting-ce/certs
   mkcert -cert-file server.crt -key-file server.key sting.local "*.sting.local"
   ```
3. Copy to Docker volume:
   ```bash
   docker run --rm -v sting_certs:/certs -v ~/.sting-ce/certs:/source alpine \
     sh -c "cp /source/server.crt /certs/ && cp /source/server.key /certs/"
   ```
4. Restart services:
   ```bash
   ./manage_sting.sh restart
   ```

## Certificate Locations

- **Host System**: `${INSTALL_DIR}/certs/server.{crt,key}`
  - Default: `~/.sting-ce/certs/` (macOS) or `/opt/sting-ce/certs/` (Linux)
- **Docker Volume**: `sting_certs` volume mounted at `/certs` in containers
- **mkcert CA**: `~/.local/share/mkcert/` (Linux) or `~/Library/Application Support/mkcert/` (macOS)

## Security Notes

### mkcert CA Certificate

- mkcert creates a local Certificate Authority (CA) on your system
- The CA private key is stored in `$(mkcert -CAROOT)/rootCA-key.pem`
- **IMPORTANT**: Keep this file secure! Anyone with this key can create trusted certificates for your system
- The CA is only trusted on your local machine (not other machines)
- Perfect for development/testing, but not for production public domains

### Self-Signed Certificate Limitations

- Browsers show security warnings
- WebAuthn/Passkeys are blocked by browsers
- Users must manually accept certificate exceptions
- Not recommended for production use

### Let's Encrypt Certificates

- Fully trusted by all browsers (no warnings)
- WebAuthn/Passkeys work perfectly
- Free and automated renewal
- Requires public domain and DNS configuration
- **Coming soon** to STING

## References

- [mkcert GitHub](https://github.com/FiloSottile/mkcert)
- [Let's Encrypt](https://letsencrypt.org/)
- [WebAuthn Specification](https://www.w3.org/TR/webauthn/)
- [STING Custom Domain Setup](../guides/custom-domain-setup.md)
