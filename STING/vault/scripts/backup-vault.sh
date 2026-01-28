#!/bin/bash
set -e

# Configuration - can be overridden by environment variables
BACKUP_DIR="${VAULT_BACKUP_DIR:-/vault/backups}"
RETENTION_DAYS="${VAULT_BACKUP_RETENTION_DAYS:-7}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vault_backup_$TIMESTAMP.snap"

# Export Vault token and address
export VAULT_ADDR="${VAULT_ADDR:-'http://0.0.0.0:8200'}"
export VAULT_TOKEN="${VAULT_TOKEN:-'dev-only-token'}"

# Perform backup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Vault backup..."
vault operator raft snapshot save "$BACKUP_FILE"

# Clean up old backups
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "vault_backup_*.snap" -mtime +$RETENTION_DAYS -type f 2>/dev/null | wc -l)
if [ "$OLD_BACKUPS" -gt 0 ]; then
    find "$BACKUP_DIR" -name "vault_backup_*.snap" -mtime +$RETENTION_DAYS -type f -delete
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up $OLD_BACKUPS old backups (retention: ${RETENTION_DAYS} days)"
fi

# Show backup info
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "vault_backup_*.snap" -type f 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed: $BACKUP_FILE (${BACKUP_SIZE}, total: $BACKUP_COUNT)"
