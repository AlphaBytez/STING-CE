# STING Domain Configuration Guide

## Overview
STING now supports custom domains via configuration, with localhost as the fallback. The domain configuration is centrally managed through `config.yml`.

## Implementation Status ✅
1. Domain configuration added to `config.yml` under `system` section
2. `config_loader.py` updated to generate domain-based URLs
3. Kratos configuration dynamically generated with proper domains
4. Frontend receives domain configuration via environment variables
5. `setup-custom-domain.sh` reads domain from config.yml

## Configuration

### 1. Add Domain Configuration to config.yml
```yaml
system:
  domain: queen.hive  # or localhost
  protocol: https
  ports:
    frontend: 8443
    api: 5050
    kratos: 4433
```

### 2. Environment Variable Generation
The config loader should generate:
```bash
# Generated from config.yml
export STING_DOMAIN="queen.hive"
export STING_PROTOCOL="https"
export PUBLIC_URL="${STING_PROTOCOL}://${STING_DOMAIN}:8443"
export KRATOS_PUBLIC_URL="${STING_PROTOCOL}://${STING_DOMAIN}:4433"
export KRATOS_BROWSER_URL="${STING_PROTOCOL}://${STING_DOMAIN}:4433"
```

### 3. Service Configuration Updates

#### Kratos (generated dynamically)
The Kratos configuration is now dynamically generated with proper domain settings:
- Base URLs use the configured domain
- CORS allowed origins include the custom domain
- Session cookies use the domain
- WebAuthn RP ID matches the domain

#### Frontend Environment Variables
```bash
REACT_APP_KRATOS_PUBLIC_URL  # Set to https://[domain]:4433
REACT_APP_KRATOS_BROWSER_URL # Set to https://[domain]:4433
PUBLIC_URL                   # Set to https://[domain]:8443
```

### 4. Implementation Details

The domain configuration system:
1. Reads `system.domain` from config.yml (defaults to localhost)
2. Generates appropriate URLs for all services
3. Updates Kratos configuration dynamically
4. Passes domain settings to frontend via environment variables
5. WebAuthn automatically uses the configured domain

### 5. Fresh Install Flow

```bash
# 1. Configure domain in config.yml
vim conf/config.yml
# Update system section:
# system:
#   domain: queen.hive

# 2. Run setup script (reads domain from config)
sudo ./setup-custom-domain.sh

# 3. Install STING (uses domain from config)
./install.sh

# 4. Access via custom domain
https://queen.hive:8443
```

### 6. Benefits
- Single source of truth for domain configuration
- Works out of the box with localhost
- Easy to switch between domains
- Supports multiple environments (dev/staging/prod)
- WebAuthn/Passkeys work correctly across domains
- No hardcoded URLs in services

### 7. Troubleshooting

If services don't respond on the custom domain:
1. Verify `/etc/hosts` has the domain entry
2. Check that environment files were regenerated: `msting sync-config`
3. Restart services: `msting restart`
4. Clear browser cache and cookies for both localhost and the custom domain