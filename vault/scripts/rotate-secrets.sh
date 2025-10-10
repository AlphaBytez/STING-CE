#!/bin/bash
set -e

export VAULT_ADDR="${VAULT_ADDR:-'http://0.0.0.0:8200'}"
export VAULT_TOKEN="${VAULT_TOKEN:-'dev-only-token'}"

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


echo "Secret rotation completed successfully"
