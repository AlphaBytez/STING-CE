#!/bin/bash
# Vault initialization and unsealing script for production mode

VAULT_ADDR="${VAULT_ADDR:-http://0.0.0.0:8200}"
VAULT_INIT_FILE="/vault/file/.vault_init"

# Wait for Vault to be ready
echo "Waiting for Vault to be ready..."
while ! vault status 2>/dev/null; do
  sleep 1
done

# Check if Vault is already initialized
if vault status 2>/dev/null | grep -q "Initialized.*true"; then
  echo "Vault is already initialized"

  # Check if we have the unseal keys stored
  if [ -f "$VAULT_INIT_FILE" ]; then
    echo "Found stored unseal keys, attempting to unseal..."

    # Extract unseal keys from file (first 3 keys for threshold of 3)
    for i in 1 2 3; do
      UNSEAL_KEY=$(grep "Unseal Key $i:" "$VAULT_INIT_FILE" | cut -d':' -f2 | tr -d ' ')
      if [ -n "$UNSEAL_KEY" ]; then
        vault operator unseal "$UNSEAL_KEY"
      fi
    done

    # Extract and export root token
    export VAULT_TOKEN=$(grep "Initial Root Token:" "$VAULT_INIT_FILE" | cut -d':' -f2 | tr -d ' ')
    echo "Vault unsealed successfully"
  else
    echo "WARNING: Vault is initialized but no unseal keys found in $VAULT_INIT_FILE"
    echo "Please manually unseal Vault or restore the init file"
  fi
else
  echo "Initializing Vault..."

  # Initialize with 5 key shares and threshold of 3
  vault operator init -key-shares=5 -key-threshold=3 | tee "$VAULT_INIT_FILE"

  if [ $? -eq 0 ]; then
    echo "Vault initialized successfully. Keys stored in $VAULT_INIT_FILE"
    echo "IMPORTANT: Back up this file securely!"

    # Auto-unseal with the first 3 keys
    for i in 1 2 3; do
      UNSEAL_KEY=$(grep "Unseal Key $i:" "$VAULT_INIT_FILE" | cut -d':' -f2 | tr -d ' ')
      if [ -n "$UNSEAL_KEY" ]; then
        vault operator unseal "$UNSEAL_KEY"
      fi
    done

    # Export root token
    export VAULT_TOKEN=$(grep "Initial Root Token:" "$VAULT_INIT_FILE" | cut -d':' -f2 | tr -d ' ')

    # Enable KV secrets engine for STING
    vault login "$VAULT_TOKEN"
    vault secrets enable -path=sting kv-v2

    echo "Vault setup complete"
  else
    echo "ERROR: Failed to initialize Vault"
    exit 1
  fi
fi