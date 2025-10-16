#!/bin/sh
# Vault production mode entrypoint with auto-unseal and secrets initialization

# Start Vault server in background
vault server -config=/vault/config/vault.hcl &
VAULT_PID=$!

# Wait for Vault server to start
echo "Waiting for Vault server to start..."
sleep 5

# Run auto-init/unseal script
echo "Running auto-init/unseal script..."
if [ -f /vault/scripts/auto-init-vault.sh ]; then
    /bin/sh /vault/scripts/auto-init-vault.sh || {
        echo "WARNING: Auto-init/unseal script failed, Vault may be sealed"
    }
else
    echo "WARNING: Auto-init script not found, Vault may remain sealed"
fi

# Create a marker file to signal that Vault secrets need initialization
# The utils container or installation script will pick this up
echo "Checking for Vault secrets initialization..."
if ! vault kv get sting/database >/dev/null 2>&1; then
    echo "⚠️  Vault secrets not initialized - creating marker file"
    touch /vault/persistent/.vault-needs-secrets
    echo "💡 Run 'docker exec sting-ce-utils python3 /vault/scripts/init_secrets.py' to initialize secrets"
else
    echo "✅ Vault secrets already initialized"
    # Remove marker if secrets exist
    rm -f /vault/persistent/.vault-needs-secrets 2>/dev/null
fi

echo "Vault server started and initialization attempted"

# Keep the container running
wait $VAULT_PID