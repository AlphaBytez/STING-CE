# Configuration Template Behavior Documentation

## Overview
This document explains how configuration files are managed during STING installation, uninstallation, and backup restoration processes.

## Configuration File Lifecycle

### 1. Fresh Installation
When `/opt/sting-ce/conf/config.yml` doesn't exist:
- The installation script checks for existing config.yml
- If not found, it copies from the appropriate template:
  - On macOS: `config.yml.default.mac` (if exists and on Mac)
  - Otherwise: `config.yml.default`
- This happens in `lib/configuration.sh` (lines 96-99)

### 2. Uninstallation
- The uninstall process removes `/opt/sting-ce/` directory entirely
- This includes the generated `config.yml` file
- Configuration templates in the source directory remain untouched

### 3. Backup Restoration
- If restoring from backup and config.yml doesn't exist
- The system will create a new one from the default template
- Any custom configurations in the backup would override the default

## Port 3000 Issue Resolution

### Problem
Frontend port kept reverting to 3000 during fresh installations despite commits changing it to 8443.

### Root Cause
The configuration templates (`config.yml.default`, `config.yml.default.mac`, `config.yml.minimal`) contained hardcoded port 3000 values.

### Solution
Updated all configuration templates to use port 8443:
- `conf/config.yml.default` - All port references changed to 8443
- `conf/config.yml.default.mac` - All port references changed to 8443  
- `conf/config.yml.minimal` - REACT_PORT changed to 8443

### Why This Matters
1. **Fresh installs** always use the template files
2. **Uninstall/reinstall** cycles will use templates
3. **Backup restoration** without config.yml uses templates
4. **Development environments** may regenerate from templates

## Best Practices

### For Developers
1. When changing default ports or configurations, update ALL template files:
   - `config.yml.default`
   - `config.yml.default.mac`
   - `config.yml.minimal`
2. Test fresh installations to verify changes persist
3. Consider template files as the "source of truth" for defaults

### For System Administrators
1. Always backup custom `config.yml` before uninstalling
2. Review template changes after updates
3. Consider maintaining custom templates for your environment

## Configuration Loading Process

The configuration is loaded by `conf/config_loader.py`:
1. Checks if `config.yml` exists
2. If not, uses `check_config_exists()` to create from template
3. Platform detection chooses optimal template (Mac vs general)
4. Generates environment files based on loaded configuration

## Port 3000 Issue - Additional Findings

### Multiple Configuration Sources
The port 3000 issue can persist even after updating templates due to multiple configuration sources:

1. **Environment Files**
   - `/opt/sting-ce/env/frontend.env` - Generated with port value
   - `/opt/sting-ce/.env` - Main docker-compose environment
   - `/opt/sting-ce/conf/.env.template` - Template file

2. **Configuration Cache**
   - `/opt/sting-ce/conf/.config_state` - JSON cache of configuration
   - This cache can retain old values even after config.yml is updated

3. **Docker Compose Port Mapping**
   - Uses `${REACT_PORT:-8443}:80` in docker-compose.yml
   - Reads REACT_PORT from environment at container creation time
   - Container must be recreated (not just restarted) for port changes

### Complete Fix Process
1. Update all template files (done)
2. Remove configuration cache: `rm /opt/sting-ce/conf/.config_state`
3. Add REACT_PORT to main .env: `echo 'REACT_PORT=8443' >> /opt/sting-ce/.env`
4. Update frontend.env: `sed -i 's/REACT_PORT="3000"/REACT_PORT="8443"/' /opt/sting-ce/env/frontend.env`
5. Recreate frontend container: `docker-compose rm -f frontend && docker-compose up -d frontend`

## Related Files
- `/lib/configuration.sh` - Handles config file creation
- `/conf/config_loader.py` - Loads config and generates env files
- `/conf/config.yml.default` - Default template for general systems
- `/conf/config.yml.default.mac` - Mac-optimized template
- `/conf/config.yml.minimal` - Minimal configuration template
- `/conf/.env.template` - Environment variable template
- `/conf/.config_state` - Configuration cache (JSON)