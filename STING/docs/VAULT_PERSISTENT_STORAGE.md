# Vault Persistent Storage Configuration

## Overview
As of September 2025, STING has been configured with HashiCorp Vault in production mode with persistent file storage. This replaces the previous dev mode configuration which lost data on restart.

## Configuration Changes

### 1. Vault Dockerfile (`vault/Dockerfile-vault`)
- Changed from dev mode to production mode with config file
- Uses `/vault/scripts/entrypoint.sh` for startup

### 2. Vault Configuration (`vault/config/vault.hcl`)
```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "https://0.0.0.0:8201"
ui = true
disable_mlock = true
```

### 3. Docker Compose Configuration
- Removed `VAULT_DEV_*` environment variables
- Added persistent volumes:
  - `vault_data:/vault/data`
  - `vault_file:/vault/file`
- Updated VAULT_TOKEN to use production token: `hvs.TqEboPUVWPzt9HHXHgaVvMjV`

### 4. Credentials Storage
Vault initialization credentials are stored in:
- `/Users/captain-wolf/.sting-ce/vault/vault-init.json`

**CRITICAL**: These credentials MUST be backed up securely:
```json
{
  "unseal_key": "IPPeoJl7/R/4t37REi/OHDddk/QCM6+4fNTjK+k//Pk=",
  "root_token": "hvs.TqEboPUVWPzt9HHXHgaVvMjV"
}
```

## Operational Procedures

### Initial Setup (Already Completed)
1. Start Vault in production mode
2. Initialize Vault: `vault operator init -key-shares=1 -key-threshold=1`
3. Unseal Vault: `vault operator unseal <unseal_key>`
4. Enable KV v2 engine: `vault secrets enable -path=sting kv-v2`

### After Restart
Vault will need to be unsealed after any restart:
```bash
docker exec sting-ce-vault vault operator unseal IPPeoJl7/R/4t37REi/OHDddk/QCM6+4fNTjK+k//Pk=
```

### Accessing Vault UI
- URL: http://localhost:8200
- Token: `hvs.TqEboPUVWPzt9HHXHgaVvMjV`

## Benefits
1. **Data Persistence**: Files stored in Vault survive container restarts
2. **Production Ready**: No longer using insecure dev mode
3. **Proper Security**: Sealed/unsealed state with encryption at rest
4. **File Storage**: Using file backend at `/vault/file` for persistence

## Migration Notes
- Previous files stored in dev mode Vault are lost
- All new files will be persisted in `/vault/file` volume
- Reports generated after this change will have persistent storage
- Database references to files remain valid as long as Vault data persists

## Future Improvements
1. Implement auto-unseal using AWS KMS or similar
2. Set up Vault backup procedures
3. Implement proper secret rotation
4. Consider migration to Raft storage backend for HA

## Troubleshooting

### Check Vault Status
```bash
docker exec sting-ce-vault vault status
```

### View Vault Logs
```bash
docker logs sting-ce-vault --tail 50
```

### Manually Initialize Vault (if needed)
```bash
docker exec sting-ce-vault vault operator init -key-shares=1 -key-threshold=1
```

### List Files in Vault
```bash
docker exec -e VAULT_TOKEN=hvs.TqEboPUVWPzt9HHXHgaVvMjV sting-ce-vault vault kv list sting/files
```

## Security Considerations
- **NEVER** commit the vault token or unseal key to git
- Store credentials in a secure password manager
- Consider using multiple key shares in production
- Implement proper access policies instead of using root token
- Enable audit logging for compliance

---
*Last Updated: September 24, 2025*
*Configuration tested and working with persistent file storage*