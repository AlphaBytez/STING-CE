# STING Installation Domain Guide

## Overview

When you install STING, it automatically generates a unique local domain for your installation. This domain:
- Enables WebAuthn passkeys to work across all devices on your network
- Provides consistent URLs for all services
- Prevents conflicts when running multiple STING instances
- Works automatically with mDNS/Bonjour on macOS

## Fresh Installation

### Method 1: Standard Installation (Recommended)

```bash
./install_sting.sh install
```

After installation completes, you'll see:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ STING Installation Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Your STING Domain: mac-c8ba5237.sting.hive

Access STING at:
  Frontend:    https://mac-c8ba5237.sting.hive:8443
  API:         https://mac-c8ba5237.sting.hive:5050
  Auth:        https://mac-c8ba5237.sting.hive:4433

✅ This domain is accessible from any device on your network
```

### Method 2: Installation with Domain Setup

```bash
./install_with_domain.sh install
```

This explicitly handles domain setup during installation.

## Post-Installation

### Finding Your Domain

If you missed the installation message:

```bash
# Check current domain
cat ~/.sting-ce/.sting_domain

# Or run the status command
./manage_sting.sh status
```

### Quick Reference

After installation, check `~/.sting-ce/QUICK_START.txt` for your domain and access URLs.

## Domain Structure

Your domain follows this pattern:
```
{machine-id}.sting.hive
     |         |     |
     |         |     └── Custom TLD (avoids .local conflicts)  
     |         └────────── Product namespace
     └──────────────────── Unique 8-character machine identifier
```

Examples:
- `mac-c8ba5237.sting.hive` (macOS)
- `linux-a1b2c3d4.sting.hive` (Linux)

## Accessing STING

### From This Machine

Simply use the domain shown during installation:
```
https://mac-c8ba5237.sting.hive:8443
```

### From Other Devices on Your Network

#### macOS with Bonjour (Automatic)
The domain works automatically - just enter the URL in any browser on your network.

#### Without mDNS (Manual)
Add to the device's `/etc/hosts`:
```
192.168.1.100    mac-c8ba5237.sting.hive
```

Replace `192.168.1.100` with your STING server's IP address.

## Customizing Your Domain

To change your domain after installation:

```bash
./setup_local_domain.sh
```

Options:
1. **Automatic** - Generate new unique domain
2. **Custom** - Choose your own (e.g., `my-sting.sting.hive`)
3. **Simple** - Use `sting.hive` (may conflict)

## Integration with Installation Scripts

The domain system integrates with STING's installation in several ways:

1. **Automatic Generation**: Domain is generated from hardware ID during first install
2. **Persistence**: Domain is saved in `~/.sting-ce/.sting_domain`
3. **Service Configuration**: All services are configured with the domain
4. **WebAuthn Setup**: RP ID is set to your domain for passkey compatibility

## Troubleshooting

### Domain Not Working

1. **Check domain file exists**:
   ```bash
   ls -la ~/.sting-ce/.sting_domain
   ```

2. **Verify mDNS service** (macOS):
   ```bash
   dns-sd -B _https._tcp
   ```

3. **Test domain resolution**:
   ```bash
   ping mac-c8ba5237.sting.hive
   ```

### Certificate Warnings

You'll see certificate warnings because STING uses self-signed certificates. This is normal - accept the certificate to proceed.

### Can't Access from Other Devices

1. Ensure devices are on the same network
2. Check firewall isn't blocking ports 8443, 5050, etc.
3. If mDNS isn't available, manually add to `/etc/hosts`

## Benefits

Using a custom domain provides:
- ✅ **WebAuthn Compatibility**: Passkeys work across all your devices
- ✅ **Consistent URLs**: Same address from any device
- ✅ **No Conflicts**: Multiple STING instances can coexist
- ✅ **Professional Feel**: Better than `localhost:8443`
- ✅ **Zero Configuration**: Works out of the box with mDNS