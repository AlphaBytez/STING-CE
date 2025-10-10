#!/bin/bash
# Script to create Vault directory structure and configuration files

# Create directory structure
mkdir -p ./vault/{config,policies,scripts}

# Create config/vault.hcl
cat > ./vault/config/vault.hcl << 'EOF'
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

telemetry {
  disable_hostname = true
  prometheus_retention_time = "24h"
}
EOF

# Create policies/app-policy.hcl
cat > ./vault/policies/app-policy.hcl << 'EOF'
# Allow tokens to look up their own properties
path "auth/token/lookup-self" {
    capabilities = ["read"]
}

# Allow tokens to renew themselves
path "auth/token/renew-self" {
    capabilities = ["update"]
}

# Allow tokens to revoke themselves
path "auth/token/revoke-self" {
    capabilities = ["update"]
}

# Allow read access to KV v2 secrets in the sting/ path
path "sting/*" {
    capabilities = ["read"]
}

# Allow read access to database credentials
path "sting/database/*" {
    capabilities = ["read"]
}

# Allow read access to Keycloak credentials
path "sting/keycloak/*" {
    capabilities = ["read"]
}
EOF

# Create policies/admin-policy.hcl
cat > ./vault/policies/admin-policy.hcl << 'EOF'
# Full access to KV v2 secrets in the sting/ path
path "sting/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}

# System health check
path "sys/health" {
    capabilities = ["read", "sudo"]
}

# Manage policies
path "sys/policies/acl/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage token creation
path "auth/token/create" {
    capabilities = ["create", "read", "update", "list"]
}
EOF

# Create initialization script
cat > ./vault/scripts/init-vault.sh << 'EOF'
#!/bin/bash
set -e

# Wait for Vault to start
until curl -fs http://127.0.0.1:8200/v1/sys/health > /dev/null; do
    echo "Waiting for Vault to start..."
    sleep 1
done

# Export Vault address and token
export VAULT_ADDR=${VAULT_ADDR}
export VAULT_TOKEN=${VAULT_TOKEN}

# Enable KV v2 secrets engine
vault secrets enable -path=sting kv-v2

# Create policies
vault policy write app-policy /vault/policies/app-policy.hcl
vault policy write admin-policy /vault/policies/admin-policy.hcl

# Initialize default secrets if they don't exist
if ! vault kv get sting/database/credentials> /dev/null 2>&1; then
    vault kv put sting/database/credentials\
        postgres_user="sting" \
        postgres_password="$(openssl rand -base64 32)"
fi

if ! vault kv get sting/keycloak > /dev/null 2>&1; then
    vault kv put sting/keycloak \
        admin_password="$(openssl rand -base64 32)" \
        db_password="$(openssl rand -base64 32)" \
        client_secret="$(openssl rand -base64 32)" \
        keystore_password="$(openssl rand -base64 32)"
fi

echo "Vault initialization completed successfully"
EOF

# Create rotation script
cat > ./vault/scripts/rotate-secrets.sh << 'EOF'
#!/bin/bash
set -e

export VAULT_ADDR=${VAULT_ADDR}
export VAULT_TOKEN=${VAULT_TOKEN}

# Function to generate a secure password
generate_password() {
    openssl rand -base64 32
}

# Rotate database secrets
echo "Rotating database secrets..."
current_db_user=$(vault kv get -field=postgres_user sting/database)
vault kv put sting/database/credentials\
    postgres_user="$current_db_user" \
    postgres_password="$(generate_password)"

# Rotate Keycloak secrets
echo "Rotating Keycloak secrets..."
vault kv put sting/keycloak \
    admin_password="$(generate_password)" \
    db_password="$(generate_password)" \
    client_secret="$(generate_password)" \
    keystore_password="$(generate_password)"

echo "Secret rotation completed successfully"
EOF

# Create backup script
cat > ./vault/scripts/backup-vault.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/vault/backups"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vault_backup_$TIMESTAMP.snap"

# Export Vault token and address
export VAULT_ADDR=${VAULT_ADDR}
export VAULT_TOKEN=${VAULT_TOKEN}

# Perform backup
vault operator raft snapshot save "$BACKUP_FILE"

# Clean up old backups
find "$BACKUP_DIR" -name "vault_backup_*.snap" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully: $BACKUP_FILE"
EOF

# Set proper permissions
chmod +x ./vault/scripts/init-vault.sh
chmod +x ./vault/scripts/rotate-secrets.sh
chmod +x ./vault/scripts/backup-vault.sh

