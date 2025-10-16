# STING Passkey Authentication Quick Start Guide

## 🚀 Choose Your Setup Mode

Before creating your first user account, decide how you'll access STING:

### Option 1: Single Machine Testing (Default)
- **Access URL**: `https://localhost:8443`
- **Configuration**: No changes needed
- **Best for**: Evaluation, development, single-user testing
- **Limitation**: Passkeys only work on the machine running STING

### Option 2: Multi-Machine/Network Access
- **Access URL**: `https://YOUR-IP:8443` (e.g., `https://192.168.1.100:8443`)
- **Configuration**: Set `WEBAUTHN_RP_ID` BEFORE creating any users
- **Best for**: Team testing, multiple devices, production preparation
- **Benefit**: Passkeys work from any device on your network

## 📋 Initial Setup Instructions

### For Single Machine (Option 1)
```bash
# 1. Install STING (no special configuration needed)
./install_sting.sh

# 2. Access STING
open https://localhost:8443

# 3. Create account and passkeys - they'll work on this machine only
```

### For Multi-Machine Access (Option 2)

**IMPORTANT**: Configure this BEFORE creating any user accounts!

```bash
# 1. Find your server's IP address
ip addr show  # Linux
ifconfig      # macOS

# 2. Edit configuration BEFORE first install
nano env/app.env

# Add or update this line (replace with your actual IP):
WEBAUTHN_RP_ID=192.168.1.100

# 3. Install STING
./install_sting.sh

# 4. Access from ALL devices using the same IP
open https://192.168.1.100:8443
```

## ⚠️ Critical Notes

### Changing Access Method After Setup

If you need to switch from localhost to network access (or vice versa):

1. **Export any important data** (this will delete all users!)
2. **Clear all existing users and passkeys**:
   ```bash
   ./scripts/troubleshooting/clear_dev_users.sh
   ```
3. **Update configuration**:
   ```bash
   # Edit env/app.env
   WEBAUTHN_RP_ID=your-new-domain-or-ip
   ```
4. **Update the app service**:
   ```bash
   ./manage_sting.sh update app
   ```
5. **Clear browser data** for the old domain
6. **Re-create all user accounts** at the new URL

### Why This Matters

WebAuthn passkeys are cryptographically bound to their domain (RP ID):
- A passkey created for `localhost` won't work on `192.168.1.100`
- A passkey created for `192.168.1.100` won't work on `localhost`
- This is a security feature, not a bug!

## 🎯 Best Practices

### For Development/Testing
1. Use `localhost` if you're just evaluating STING
2. Use your machine's IP if you need to test from multiple devices
3. Document which setup you chose for your team

### For Production Preparation
1. Use a proper domain name (e.g., `sting.company.local`)
2. Set up SSL certificates for that domain
3. Configure `WEBAUTHN_RP_ID` to match your domain
4. Test thoroughly before going live

## 🔧 Troubleshooting

### "Passkey not working on other machine"
- Check that `WEBAUTHN_RP_ID` matches the URL you're using
- Ensure all machines access STING using the exact same URL
- Verify no firewall is blocking port 8443

### "Need to change domain/IP"
- You MUST clear all users and start fresh
- Existing passkeys cannot be migrated to a new domain
- This is by design for security

### Browser Warnings
- Accept the self-signed certificate warning
- Or install the STING CA certificate on client machines
- Consider using proper certificates for production

## 📖 Additional Resources

- [Full Passkey Documentation](./PASSKEY_CROSS_MACHINE_INSTRUCTIONS.md)
- [Local Domain Setup](./scripts/setup_local_domain.sh)
- [Troubleshooting Guide](./CLAUDE.md#passkey-cross-machine-issues-july-2025)

---

**Remember**: Choose your access method BEFORE creating users to avoid having to recreate everything later!