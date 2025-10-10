#!/bin/sh
# Vault production mode entrypoint with auto-unseal

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

echo "Vault server started and initialization attempted"

# Keep the container running
wait $VAULT_PID