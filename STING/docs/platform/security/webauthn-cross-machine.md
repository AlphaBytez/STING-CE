# WebAuthn Cross-Machine Passkey Guide

## The Problem

WebAuthn passkeys are bound to a specific "Relying Party ID" (RP ID), which is typically the domain name of your application. When you create a passkey on one machine with `localhost` as the RP ID, it won't work on another machine because:

1. Each machine's `localhost` refers to itself
2. WebAuthn security model prevents passkeys from being used on different domains
3. The RP ID must match exactly between registration and authentication

## The Solution

To use passkeys across multiple machines, all machines must use the **same domain name** to access STING.

### Option 1: Use a Local Domain (Recommended)

1. Choose a consistent domain name (e.g., `sting.local`)
2. Set it up on all machines:

```bash
# Run on each machine where you want to use STING
./set_webauthn_domain.sh
# Enter: sting.local

# Add to /etc/hosts on each machine
echo '192.168.1.100 sting.local' | sudo tee -a /etc/hosts
# Replace 192.168.1.100 with the IP of the machine running STING
```

3. Access STING using: `https://sting.local:8443`

### Option 2: Use IP Address

If machines are on the same network:

```bash
# Find your machine's IP
ipconfig getifaddr en0  # macOS
ip addr show           # Linux

# Set WebAuthn to use the IP
./set_webauthn_domain.sh
# Enter: 192.168.1.100 (your IP)

# Update the app
./manage_sting.sh update app
```

Access STING using: `https://192.168.1.100:8443`

### Option 3: Use a Real Domain

For production or internet-accessible deployments:

```bash
# Set your real domain
./set_webauthn_domain.sh
# Enter: sting.yourdomain.com

# Update DNS to point to your server
# Configure SSL certificates properly
```

## Configuration Details

The WebAuthn RP ID is configured in multiple places:

1. **config.yml**: 
   ```yaml
   security:
     supertokens:
       webauthn:
         rp_id: "${HOSTNAME:-localhost}"
   ```

2. **Environment Variable**: `WEBAUTHN_RP_ID` in `app.env`

3. **Flask Config**: Read from environment in `app/__init__.py`

## Testing Cross-Machine Passkeys

1. Set the same domain on both machines
2. Register a passkey on Machine A
3. Try to login with the passkey on Machine B
4. If it works, your configuration is correct!

## Troubleshooting

### "Passkey not found" on different machine
- Ensure both machines use the exact same domain
- Check `WEBAUTHN_RP_ID` in `~/.sting-ce/env/app.env`
- Verify the domain resolves correctly on both machines

### Browser warnings about invalid certificate
- Self-signed certificates will show warnings
- Add a security exception in your browser
- For production, use proper SSL certificates

### Passkeys work on one machine but not another
- Clear browser cache and cookies
- Re-register the passkey with the new domain
- Ensure time is synchronized between machines

## Security Considerations

- Using IP addresses is less secure than domains
- Local domains (*.local) are suitable for development
- Production deployments should use proper domains with valid SSL
- Never share passkey credentials or private keys

## Quick Setup Script

```bash
# One-liner to set up sting.local domain
STING_IP=$(ipconfig getifaddr en0 || hostname -I | awk '{print $1}') && \
echo "$STING_IP sting.local" | sudo tee -a /etc/hosts && \
./set_webauthn_domain.sh
```

Then enter `sting.local` when prompted.