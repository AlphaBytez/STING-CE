#!/bin/bash
# Automated Vault initialization script for production mode
# This script handles both fresh initialization and restart unsealing

VAULT_ADDR="${VAULT_ADDR:-http://0.0.0.0:8200}"

# Primary storage locations (in order of preference)
VAULT_INIT_FILE="/vault/file/.vault-init.json"                    # Vault's file storage
VAULT_PERSISTENT_FILE="/vault/persistent/.vault-init.json"        # Dedicated persistent volume (survives updates)
VAULT_CONFIG_FILE="/.sting-ce/vault/vault-init.json"              # Host mount backup
VAULT_SHARED_FILE="/app/conf/.vault-auto-init.json"                # Shared config volume

# Backup locations for maximum resilience (POSIX-compliant)
VAULT_BACKUP_FILE_1="/vault/persistent/.vault-backup.json"
VAULT_BACKUP_FILE_2="/vault/persistent/.vault-backup-$(date +%Y%m%d).json"
VAULT_BACKUP_FILE_3="/.sting-ce/vault/.vault-backup.json"

# Function to wait for Vault to be ready
wait_for_vault() {
    echo "Waiting for Vault to be ready..."
    local max_attempts=60  # 60 seconds timeout
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        vault status >/dev/null 2>&1
        exit_code=$?
        # Exit code 0 = unsealed, 2 = sealed but initialized, both are "ready"
        if [ $exit_code -eq 0 ] || [ $exit_code -eq 2 ]; then
            echo "Vault is ready (attempt $attempt)"
            return 0
        fi
        echo "Waiting... (attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "❌ Vault did not become ready within $max_attempts seconds"
    return 1
}

# Function to save vault init data to multiple resilient locations
save_vault_init_data() {
    local init_output="$1"
    local success_count=0
    local total_locations=0

    echo "💾 Saving vault initialization data to multiple resilient locations..."

    # Ensure persistent directories exist
    mkdir -p "/vault/persistent" 2>/dev/null
    mkdir -p "/.sting-ce/vault" 2>/dev/null
    mkdir -p "/app/conf" 2>/dev/null

    # Save to primary locations (POSIX-compliant)
    save_to_location() {
        local file="$1"
        total_locations=$((total_locations + 1))
        if echo "$init_output" > "$file" 2>/dev/null; then
            echo "✅ Saved to $file"
            success_count=$((success_count + 1))
        else
            echo "⚠️  Failed to save to $file"
        fi
    }

    # Save to all primary locations
    save_to_location "$VAULT_INIT_FILE"
    save_to_location "$VAULT_PERSISTENT_FILE"
    save_to_location "$VAULT_CONFIG_FILE"
    save_to_location "$VAULT_SHARED_FILE"

    # Save to backup locations
    save_to_location "$VAULT_BACKUP_FILE_1"
    save_to_location "$VAULT_BACKUP_FILE_2"
    save_to_location "$VAULT_BACKUP_FILE_3"

    echo "📊 Vault keys saved to $success_count/$total_locations locations"

    # Require at least 2 successful saves
    if [ $success_count -ge 2 ]; then
        echo "✅ Sufficient redundancy achieved ($success_count locations)"
        return 0
    else
        echo "❌ Insufficient redundancy! Only $success_count locations succeeded"
        return 1
    fi
}

# Function to initialize Vault
initialize_vault() {
    echo "🔐 Initializing Vault for the first time..."

    # Initialize with simple settings for automation
    INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json)

    if [ $? -eq 0 ]; then
        # Save to multiple resilient locations
        if ! save_vault_init_data "$INIT_OUTPUT"; then
            echo "❌ Failed to achieve sufficient key storage redundancy"
            return 1
        fi

        # Extract unseal key and root token
        UNSEAL_KEY=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[0]')
        ROOT_TOKEN=$(echo "$INIT_OUTPUT" | jq -r '.root_token')

        echo "Vault initialized successfully"
        echo "Unsealing Vault..."
        vault operator unseal "$UNSEAL_KEY"

        # Login and enable KV v2 for STING
        export VAULT_TOKEN="$ROOT_TOKEN"
        vault login "$ROOT_TOKEN"
        vault secrets enable -path=sting kv-v2

        echo "✅ Vault setup complete"
        return 0
    else
        echo "❌ Failed to initialize Vault"
        return 1
    fi
}

# Function to find and load vault init data from any available location (POSIX-compliant)
find_vault_init_data() {
    echo "🔍 Searching for vault initialization data..." >&2

    # Function to check a single location
    check_vault_file() {
        local file="$1"
        if [ -f "$file" ] && [ -r "$file" ]; then
            # Validate the file contains valid JSON
            if jq -e '.unseal_keys_b64[0]' "$file" >/dev/null 2>&1; then
                echo "✅ Found valid vault data: $file" >&2
                echo "$file"  # This is the only stdout output - the actual return value
                return 0
            else
                echo "⚠️  Found invalid vault data: $file (corrupted JSON)" >&2
            fi
        fi
        return 1
    }

    # Check locations in order of preference
    check_vault_file "$VAULT_PERSISTENT_FILE" && return 0
    check_vault_file "$VAULT_INIT_FILE" && return 0
    check_vault_file "$VAULT_CONFIG_FILE" && return 0
    check_vault_file "$VAULT_SHARED_FILE" && return 0

    # Check backup locations
    check_vault_file "$VAULT_BACKUP_FILE_1" && return 0
    check_vault_file "$VAULT_BACKUP_FILE_2" && return 0
    check_vault_file "$VAULT_BACKUP_FILE_3" && return 0

    echo "❌ No valid vault initialization data found in any location" >&2
    return 1
}

# Function to unseal Vault using stored keys
unseal_vault() {
    echo "🔓 Vault is sealed, attempting to unseal..."

    # Find vault initialization data from any available location
    local vault_data_file
    vault_data_file=$(find_vault_init_data)
    local find_result=$?

    if [ $find_result -ne 0 ] || [ -z "$vault_data_file" ]; then
        echo "❌ No unseal keys found. Manual intervention required."
        echo "💡 Hint: Check if vault keys exist in /vault/persistent/ directory"
        return 1
    fi

    # Load keys from the found file
    UNSEAL_KEY=$(jq -r '.unseal_keys_b64[0]' "$vault_data_file")
    ROOT_TOKEN=$(jq -r '.root_token' "$vault_data_file")

    echo "📋 Using vault data from: $vault_data_file"

    if [ -n "$UNSEAL_KEY" ]; then
        vault operator unseal "$UNSEAL_KEY"
        if [ $? -eq 0 ]; then
            echo "✅ Vault unsealed successfully"
            export VAULT_TOKEN="$ROOT_TOKEN"
            return 0
        else
            echo "❌ Failed to unseal Vault"
            return 1
        fi
    else
        echo "❌ Invalid unseal key"
        return 1
    fi
}

# Main execution
wait_for_vault

# Check Vault status - handle both sealed and unsealed states
vault status -format=json >/tmp/vault_status.json 2>/dev/null
vault_exit_code=$?

if [ $vault_exit_code -eq 0 ] || [ $vault_exit_code -eq 2 ]; then
    # Exit code 0 = unsealed, 2 = sealed but initialized
    STATUS=$(cat /tmp/vault_status.json)
    INITIALIZED=$(echo "$STATUS" | jq -r '.initialized // false')
    SEALED=$(echo "$STATUS" | jq -r '.sealed // true')
else
    # Exit code 1 = not initialized
    INITIALIZED="false"
    SEALED="true"
fi

if [ "$INITIALIZED" = "false" ]; then
    initialize_vault
elif [ "$SEALED" = "true" ]; then
    unseal_vault
else
    echo "✅ Vault is already initialized and unsealed"
fi

# Export token for use by other services
vault_data_file=$(find_vault_init_data 2>/dev/null)
find_result=$?
if [ $find_result -eq 0 ] && [ -n "$vault_data_file" ]; then
    ROOT_TOKEN=$(jq -r '.root_token' "$vault_data_file")
    echo "export VAULT_TOKEN=$ROOT_TOKEN" > /vault/token.env
    echo "🔑 Token exported from: $vault_data_file"
else
    echo "⚠️  Could not export vault token - no valid vault data found"
fi