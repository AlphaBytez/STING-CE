# Custom Domain Setup for STING

This guide explains how to configure STING to use a custom domain instead of localhost, working within the existing configuration system.

## Overview

STING's domain configuration is managed through:
1. `config.yml` - Main configuration file
2. Environment variables - Override config values
3. `config_loader.py` - Processes configuration
4. `update-env.sh` - Updates frontend environment

## Configuration Steps

### 1. Update config.yml

Edit your `conf/config.yml` file to set your custom domain:

```yaml
# Core Application Settings
application:
  host: sting.local  # Your custom domain (without protocol)
  ssl:
    domain: "${DOMAIN_NAME:-sting.local}"  # Can be overridden by env var
    
# Frontend Configuration  
frontend:
  react:
    api_url: "https://sting.local:5050"  # Update to your domain

# Kratos Authentication
kratos:
  public_url: "https://sting.local:4433"
  cookie_domain: "sting.local"  # Important for session cookies
  
  selfservice:
    default_return_url: "https://sting.local:8443"
    login:
      ui_url: "https://sting.local:8443/login"
    registration:
      ui_url: "https://sting.local:8443/register"
      
  methods:
    webauthn:
      rp_id: "sting.local"  # Must match your domain
      origin: "https://sting.local:8443"
```

### 2. Set Environment Variables

Export these environment variables before starting STING:

```bash
export DOMAIN_NAME="sting.local"
export REACT_APP_API_URL="https://sting.local:5050"
export REACT_APP_KRATOS_PUBLIC_URL="https://sting.local:4433"
export PUBLIC_URL="https://sting.local:8443"
export WEBAUTHN_RP_ID="sting.local"
```

Or add them to your `.env` file:

```bash
DOMAIN_NAME=sting.local
REACT_APP_API_URL=https://sting.local:5050
REACT_APP_KRATOS_PUBLIC_URL=https://sting.local:4433
PUBLIC_URL=https://sting.local:8443
WEBAUTHN_RP_ID=sting.local
```

### 3. Update /etc/hosts (for local custom domains)

Add your custom domain to your hosts file:

```bash
# On macOS/Linux
sudo echo "127.0.0.1 sting.local" >> /etc/hosts

# For network access from other devices
sudo echo "YOUR_LOCAL_IP sting.local" >> /etc/hosts
```

Replace `YOUR_LOCAL_IP` with your machine's local IP (e.g., 192.168.1.100).

### 4. Update Frontend Configuration

The frontend configuration is automatically updated when you start STING with the new environment variables. The `update-env.sh` script will use your environment variables to generate the proper configuration.

To manually update:

```bash
cd frontend
./update-env.sh
```

### 5. SSL Certificates for Custom Domain

For a custom domain, you'll need proper SSL certificates:

#### Option A: Self-Signed (Development)
STING will automatically generate self-signed certificates for your domain.

#### Option B: Let's Encrypt (Production)
1. Ensure your domain points to your server
2. Set the certbot email in config.yml:
   ```yaml
   application:
     ssl:
       email: "your-email@example.com"
   ```
3. STING will attempt to obtain Let's Encrypt certificates automatically

#### Option C: Custom Certificates
Place your certificates in the certs directory:
```bash
cp your-cert.crt ~/.sting-ce/certs/server.crt
cp your-key.key ~/.sting-ce/certs/server.key
```

### 6. Network Access Configuration

To allow access from other devices on your network:

1. **Firewall Rules** - Open required ports:
   ```bash
   # macOS
   sudo pfctl -e
   echo "pass in proto tcp from any to any port {8443,4433,5050}" | sudo pfctl -f -
   
   # Linux (ufw)
   sudo ufw allow 8443/tcp
   sudo ufw allow 4433/tcp
   sudo ufw allow 5050/tcp
   ```

2. **Docker Configuration** - Ensure services bind to all interfaces:
   The default STING configuration already binds to `0.0.0.0` for network access.

3. **CORS Configuration** - Already configured in `app/__init__.py` to accept connections from any IP on port 8443.

## Verification

After configuration:

1. **Test Domain Resolution**:
   ```bash
   ping sting.local
   ```

2. **Test Service Access**:
   ```bash
   curl -k https://sting.local:8443
   curl -k https://sting.local:5050/health
   ```

3. **Browser Access**:
   - Navigate to https://sting.local:8443
   - Accept the self-signed certificate warning (if applicable)

## Troubleshooting

### Session/Cookie Issues
- Ensure `cookie_domain` in kratos config matches your domain
- Check that WebAuthn `rp_id` matches your domain exactly

### Certificate Errors
- For self-signed certs, you must accept them in your browser
- Check certificate validity: `openssl x509 -in ~/.sting-ce/certs/server.crt -text`

### Network Access Issues
- Verify firewall rules are active
- Check Docker is binding to 0.0.0.0, not 127.0.0.1
- Ensure your domain resolves to the correct IP

### Frontend Not Updating
1. Clear browser cache
2. Check env.js was updated: `docker exec sting-ce-frontend cat /app/public/env.js`
3. Restart frontend: `./manage_sting.sh restart frontend`

## Advanced Configuration

### Multiple Domains
You can configure multiple domains by updating CORS settings in `app/__init__.py` and adding them to allowed origins.

### Reverse Proxy Setup
For production, consider using nginx or traefik as a reverse proxy to handle SSL termination and routing.

### Dynamic Domain Configuration
Use environment variable substitution in config.yml for flexible deployment:
```yaml
domain: "${DOMAIN_NAME:-localhost}"
```

This allows different domains for different environments without changing config files.