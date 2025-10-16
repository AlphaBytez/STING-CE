# Passkey Cross-Machine Authentication Issue

## Problem
Passkeys created on one machine cannot be used on another machine because the RP ID (Relying Party ID) is hardcoded to 'localhost'. WebAuthn passkeys are bound to their RP ID domain.

## Root Cause
In `app/__init__.py`, the WebAuthn configuration is set as:
```python
'WEBAUTHN_RP_ID': os.environ.get('WEBAUTHN_RP_ID', 'localhost'),
```

When you create a passkey on machine A with RP ID 'localhost', it can only be used on domains that match 'localhost'. If machine B accesses the app using a different hostname (e.g., IP address or hostname), the passkey won't work.

## Solutions

### Option 1: Use a Consistent Domain (Recommended for Production)
1. Set up a proper domain (e.g., `sting.local` or `sting.yourdomain.com`)
2. Configure all machines to use this domain
3. Set the environment variable: `WEBAUTHN_RP_ID=sting.local`

### Option 2: Use IP Address (For Local Network)
1. Use the server's IP address consistently across all machines
2. Set: `WEBAUTHN_RP_ID=192.168.1.100` (replace with your server IP)
3. Access the app using: `https://192.168.1.100:8443`

### Option 3: Configure Each Installation
Add to your `.env` file or environment:
```bash
# For local development
WEBAUTHN_RP_ID=localhost

# For network access
WEBAUTHN_RP_ID=your-server-ip-or-hostname
```

### Option 4: Dynamic RP ID Based on Request (Not Recommended)
This would require modifying the WebAuthn implementation to dynamically set RP ID based on the request host, but this breaks the security model of WebAuthn.

## Implementation Steps

1. **Update app.env**:
   ```bash
   echo "WEBAUTHN_RP_ID=your-domain-or-ip" >> env/app.env
   ```

2. **Restart the app service**:
   ```bash
   ./manage_sting.sh restart app
   ```

3. **Re-register passkeys** on the new domain (old passkeys won't work with a different RP ID)

## Important Notes
- Passkeys are cryptographically bound to their RP ID
- Changing the RP ID invalidates all existing passkeys
- For production, use a proper domain name
- For development across multiple machines, consider using a local DNS solution or consistent IP addresses