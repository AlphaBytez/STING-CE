# Kratos Configuration Files

## ⚠️ IMPORTANT: Use Templates, Not Static Configs

### Primary Configuration File

**`kratos.yml.template`** - This is the ONLY file you should edit for production deployments.

- Contains `__STING_HOSTNAME__` placeholder
- Gets processed during installation to generate `kratos.yml`
- Supports WebAuthn/Passkey authentication with custom hostnames

### How It Works

1. **During Installation:**
   - `kratos.yml.template` is copied to install directory
   - `configure_hostname()` generates `kratos.yml` from template
   - Hostname placeholder is replaced with actual hostname (e.g., `sting.local`, `mycompany.com`)

2. **After Installation:**
   - Use `./update_hostname.sh` to change hostname
   - DO NOT manually edit `kratos.yml` - changes will be overwritten

### Files in This Directory

- **`kratos.yml.template`** ✅ - Production template (EDIT THIS)
- **`kratos.yml.deprecated-use-template`** ❌ - Old static config (DO NOT USE)
- **`minimal.kratos.yml`** - Minimal config for testing
- **`dev.kratos.yml`** - Development-specific config

### Common Tasks

#### Change Hostname After Installation

```bash
cd /opt/sting-ce  # or ~/.sting-ce on macOS
./update_hostname.sh
```

#### Add New Kratos Feature

1. Edit `kratos.yml.template`
2. Use `__STING_HOSTNAME__` for any hostname references
3. Reinstall or run `./update_hostname.sh` to regenerate config

### Why Templates?

WebAuthn/Passkey authentication requires:
- Hostname (not IP address) for Relying Party ID
- Matching origins across CORS, WebAuthn, and session cookies
- Dynamic configuration based on deployment environment

Templates allow STING to work on:
- ✅ VMs with custom hostnames (`sting.local`)
- ✅ Production domains (`sting.company.com`)
- ✅ Local development (`localhost`)
