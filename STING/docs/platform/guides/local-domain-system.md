# STING Local Domain System

## Overview

STING uses a custom local domain system (`.hive` TLD) to provide:
- Consistent URLs across all services
- WebAuthn passkey compatibility across devices
- Unique machine-specific domains to prevent conflicts
- Zero-configuration network access (where mDNS is supported)

## Why .hive?

We use `.hive` instead of `.local` because:
1. **macOS Compatibility**: `.local` is reserved by Bonjour/mDNS on macOS
2. **Bee Theme**: Fits with STING's bee-themed ecosystem
3. **No Conflicts**: Not a registered TLD, avoiding DNS issues
4. **Memorable**: Easy to remember pattern: `machine-id.sting.hive`

## Domain Structure

```
{machine-id}.sting.hive
     |         |     |
     |         |     └── Custom TLD (avoids .local conflicts)
     |         └────────── Product namespace
     └──────────────────── Unique 8-character machine identifier
```

Examples:
- `mac-a1b2c3d4.sting.hive` (macOS)
- `linux-12345678.sting.hive` (Linux)
- `my-dev.sting.hive` (custom)

## Setup

### Quick Setup

```bash
./setup_local_domain.sh
```

Choose from:
1. **Automatic** (Recommended) - Generates unique domain from hardware
2. **Custom** - Choose your own prefix
3. **Simple** - Use `sting.hive` (may conflict)
4. **Keep Current** - No changes

### How It Works

1. **Domain Generation**:
   - macOS: Uses hardware UUID (first 8 chars)
   - Linux: Uses `/etc/machine-id` (first 8 chars)
   - Fallback: Hostname + MAC address

2. **mDNS Registration** (if available):
   - macOS: Uses native `dns-sd` command
   - Linux: Uses Avahi daemon
   - Automatic network discovery

3. **Configuration Updates**:
   - Updates all service configs
   - Sets WebAuthn RP ID
   - Regenerates environment files
   - Updates CORS origins

## Access Methods

### With mDNS (Automatic Discovery)

Access from any device on your network:
```
https://mac-a1b2c3d4.sting.hive:8443
```

### Without mDNS (Manual Configuration)

Add to `/etc/hosts` on client devices:
```
192.168.1.100    mac-a1b2c3d4.sting.hive
```

## Service URLs

Once configured, access services at:
- Frontend: `https://{domain}:8443`
- API: `https://{domain}:5050`
- Kratos: `https://{domain}:4433`
- Knowledge: `http://{domain}:8090`

## WebAuthn Benefits

Using a custom domain enables:
- ✅ Passkeys work across all devices on your network
- ✅ No more "localhost only" restrictions
- ✅ Consistent authentication experience
- ✅ Cross-device passkey roaming

## Troubleshooting

### Domain Not Resolving

1. **Check mDNS service**:
   ```bash
   # macOS
   dns-sd -B _https._tcp
   
   # Linux
   avahi-browse -a
   ```

2. **Verify hosts file** (if not using mDNS):
   ```bash
   grep sting.hive /etc/hosts
   ```

3. **Test resolution**:
   ```bash
   ping mac-a1b2c3d4.sting.hive
   ```

### Certificate Warnings

Self-signed certificates will show warnings. This is expected. Accept the certificate to proceed.

### Changing Domains

To change your domain later:
```bash
./setup_local_domain.sh
# Select option 2 for custom domain
```

## Technical Details

### Machine ID Generation

```bash
# macOS
ioreg -d2 -c IOPlatformExpertDevice | \
  awk -F\" '/IOPlatformUUID/{print $4}' | \
  tr '[:upper:]' '[:lower:]' | cut -c1-8

# Linux
cat /etc/machine-id | cut -c1-8
```

### mDNS Registration

```bash
# macOS (dns-sd)
dns-sd -R "STING CE" _https._tcp local 8443 \
  "domain=mac-a1b2c3d4.sting.hive"

# Linux (Avahi)
avahi-publish -s "mac-a1b2c3d4" _https._tcp 8443 \
  "domain=mac-a1b2c3d4.sting.hive"
```

### Configuration Files Updated

- `/conf/config.yml` - Base configuration
- `/conf/kratos/kratos.yml` - Authentication RP ID
- `/env/*.env` - Service environment files
- `/.sting_domain` - Domain persistence

## Integration with Install Process

During installation, STING will:
1. Detect if a domain is already configured
2. If not, prompt for domain setup
3. Configure all services automatically
4. Display access URLs at completion

## Best Practices

1. **Use Automatic Mode**: Let STING generate a unique domain
2. **Document Your Domain**: Save it for team members
3. **Network Access**: Ensure devices are on same network
4. **Firewall Rules**: Allow ports 8443, 5050, etc.

## Future Enhancements

- [ ] Automatic certificate generation for domains
- [ ] DNS server integration options
- [ ] Multi-domain support
- [ ] Domain migration tools