# TOTP Persistence Fix - August 2025

## Problem
TOTP (Time-based One-Time Password) settings were being cleared after service restarts, while passkeys remained intact.

## Root Cause Analysis

1. **Missing TOTP Configuration**: The deployed `/conf/kratos/kratos.yml` was missing TOTP configuration
2. **Wrong Database**: Docker Compose was overriding Kratos DSN to use `sting_app` database instead of dedicated `kratos` database
3. **Mixed Storage**: Passkeys use custom implementation in `sting_app.passkeys` table, while TOTP uses Kratos native implementation

## Solution Applied

### 1. Added TOTP Configuration
Updated `/conf/kratos/kratos.yml`:
```yaml
selfservice:
  methods:
    totp:
      enabled: true
      config:
        issuer: "STING Authentication"
```

### 2. Fixed Database Separation
Updated `docker-compose.yml`:
```yaml
kratos:
  environment:
    # Changed from sting_app to kratos database
    - DSN=postgresql://postgres:postgres@db:5432/kratos?sslmode=disable
```

### 3. Applied Changes
```bash
# Create kratos database
docker exec sting-ce-db psql -U postgres -c "CREATE DATABASE kratos;"

# Sync configuration
./manage_sting.sh sync-config

# Recreate Kratos container to apply new DSN
docker stop sting-ce-kratos && docker rm sting-ce-kratos
./manage_sting.sh start kratos
```

## Verification
```bash
# Check credential types in kratos database
docker exec sting-ce-db psql -U postgres -d kratos -c "SELECT name FROM identity_credential_types;"

# Output should include:
# - password
# - totp
# - webauthn
# - lookup_secret
# - code
# - passkey
```

## Impact
- **Users will need to re-setup TOTP** as previous settings weren't persisted
- **Passkeys remain intact** as they use separate custom implementation
- **Future TOTP settings will persist** across restarts

## Prevention
- Ensure configuration changes are synced to deployed files
- Keep authentication methods in separate, dedicated databases
- Test persistence across service restarts during development