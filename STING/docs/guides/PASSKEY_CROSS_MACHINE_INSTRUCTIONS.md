# Instructions for Using Passkeys Across Different Machines

## The Issue
You experienced a 500 error when trying to use a passkey created on Machine A to login on Machine B. This is because WebAuthn passkeys are cryptographically bound to their Relying Party ID (RP ID), which was set to 'localhost' by default.

## Recent Updates (July 2025)
The following improvements have been made to support cross-machine passkey authentication:
- Cookie domain now dynamically uses WEBAUTHN_RP_ID for consistency
- Removed hardcoded 'localhost' domain from Kratos session cookies
- WebAuthn origins are dynamically built based on the RP ID

## Solution Steps

### On the Machine Running STING:

1. **Determine the access method** - How will other machines access STING?
   - Via IP address (e.g., 192.168.1.100)
   - Via hostname (e.g., sting-server.local)
   - Via domain name (e.g., sting.yourdomain.com)

2. **Update the configuration**:
   ```bash
   # Edit the app environment file
   nano env/app.env
   
   # Add or update this line (replace with your chosen access method):
   WEBAUTHN_RP_ID=192.168.1.100  # Example using IP address
   ```

3. **Apply the changes**:
   ```bash
   ./manage_sting.sh update app
   ```

4. **Verify the update**:
   - Check logs: `docker logs sting-ce-app | grep "WebAuthn RP ID"`
   - You should see: `WebAuthn RP ID: 192.168.1.100` (or your chosen value)

### On ALL Client Machines (including the server):

1. **Access STING using the same URL** that matches the WEBAUTHN_RP_ID:
   - If RP ID is `192.168.1.100`, access via: `https://192.168.1.100:8443`
   - If RP ID is `sting.local`, access via: `https://sting.local:8443`

2. **Clear browser data** for the old localhost URLs

3. **Re-register passkeys**:
   - Login with your password
   - Go to Security Settings
   - Delete old passkeys (they won't work with the new RP ID)
   - Add new passkeys

## Important Notes

- **All passkeys must be re-registered** after changing the RP ID
- **All machines must use the exact same URL** to access STING
- The URL domain/IP must match the WEBAUTHN_RP_ID exactly
- Using 'localhost' will only work on the local machine

## Diagnostic Tool

Run this on any machine to check the current configuration:
```bash
python diagnose_passkey_issue.py
```

## Example Scenarios

### Home Network Setup
```bash
# In env/app.env
WEBAUTHN_RP_ID=192.168.1.100

# Access from all devices:
https://192.168.1.100:8443
```

### Local Development with Multiple Machines
```bash
# In env/app.env
WEBAUTHN_RP_ID=sting.local

# Add to /etc/hosts on all machines:
192.168.1.100 sting.local

# Access from all devices:
https://sting.local:8443
```

### Production Setup
```bash
# In env/app.env
WEBAUTHN_RP_ID=sting.yourdomain.com

# Access from all devices:
https://sting.yourdomain.com:8443
```

## Troubleshooting

If you still get errors after following these steps:

1. Check that the RP ID matches exactly what you're using in the browser
2. Ensure all old passkeys are deleted
3. Clear all browser cookies and cache
4. Check app logs: `docker logs sting-ce-app --tail 100`
5. Verify WebAuthn origins are correctly set in the logs