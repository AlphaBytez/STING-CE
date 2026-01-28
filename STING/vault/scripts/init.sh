#!/bin/bash
set -e

# Wait for Vault to start
until curl -fs http://127.0.0.1:8200/v1/sys/health > /dev/null; do
    echo "Waiting for Vault to start..."
    sleep 1
done

# Export Vault address and token
export VAULT_ADDR="${VAULT_ADDR:-'http://0.0.0.0:8200'}"
export VAULT_TOKEN="${VAULT_TOKEN:-'dev-only-token'}"

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

echo "Vault initialization completed successfully"