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
export VAULT_ADDR="${VAULT_ADDR:-'http://0.0.0.0:8200'}"
export VAULT_TOKEN="${VAULT_TOKEN:-'dev-only-token'}"

# Perform backup
vault operator raft snapshot save "$BACKUP_FILE"

# Clean up old backups
find "$BACKUP_DIR" -name "vault_backup_*.snap" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully: $BACKUP_FILE"
