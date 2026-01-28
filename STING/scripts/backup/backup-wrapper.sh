#!/bin/bash
#===============================================================================
# STING Unified Backup Wrapper Script
# cron-ready backup automation with monitoring output
#===============================================================================

set -euo pipefail

# Script directory and configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$(dirname "$SCRIPT_DIR"/../..)}"
CONFIG_FILE="${INSTALL_DIR}/conf/config.yml"
LOG_DIR="${INSTALL_DIR}/logs/backup"
LOG_FILE="${LOG_DIR}/backup_$(date +%Y%m%d).log"
STATUS_FILE="${INSTALL_DIR}/data/backup_status.json"

# Default configuration values
BACKUP_ENABLED="true"
BACKUP_DIR="/opt/sting-backups"
RETENTION_COUNT=5
RETENTION_DAYS=30
COMPRESSION_LEVEL=5
ENCRYPTION_ENABLED="false"
REMOTE_ENABLED="false"
REMOTE_TYPE=""  # s3, rsync, ftp
REMOTE_DEST=""
REMOTE_USER=""
REMOTE_PORT=22
VAULT_BACKUP_ENABLED="true"
VERIFICATION_ENABLED="true"

#===============================================================================
# Logging functions
#===============================================================================
log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1"; }

#===============================================================================
# Load configuration from config.yml
#===============================================================================
load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warn "Config file not found: $CONFIG_FILE"
        return 1
    fi

    if command -v python3 >/dev/null 2>&1; then
        # Read config using Python
        local config_values=$(cd "$(dirname "$CONFIG_FILE")" && python3 -c "
import yaml
import sys
try:
    with open('$(basename "$CONFIG_FILE")', 'r') as f:
        config = yaml.safe_load(f)

    backup = config.get('backup', {})
    remote = backup.get('remote', {})
    vault = backup.get('vault', {})
    retention = backup.get('retention', {})
    encryption = backup.get('encryption', {})
    verification = backup.get('verification', {})

    print(f'BACKUP_ENABLED={str(backup.get(\"enabled\", True)).lower()}')
    print(f'BACKUP_DIR={backup.get(\"default_directory\", \"/opt/sting-backups\")}')
    print(f'RETENTION_COUNT={retention.get(\"count\", 5)}')
    print(f'RETENTION_DAYS={retention.get(\"max_age_days\", 30)}')
    print(f'COMPRESSION_LEVEL={backup.get(\"compression_level\", 5)}')
    print(f'ENCRYPTION_ENABLED={str(encryption.get(\"enabled\", False)).lower()}')
    print(f'REMOTE_ENABLED={str(remote.get(\"enabled\", False)).lower()}')
    print(f'REMOTE_TYPE={remote.get(\"type\", \"\")}')
    print(f'REMOTE_DEST={remote.get(\"destination\", \"\")}')
    print(f'REMOTE_USER={remote.get(\"user\", \"\")}')
    print(f'REMOTE_PORT={remote.get(\"port\", 22)}')
    print(f'REMOTE_PATH={remote.get(\"path\", \"/backups\")}')
    print(f'VAULT_BACKUP_ENABLED={str(vault.get(\"backup_enabled\", True)).lower()}')
    print(f'VERIFICATION_ENABLED={str(verification.get(\"enabled\", True)).lower()}')
    print(f'EXCLUDE_PATTERNS={",".join(backup.get(\"exclude_patterns\", []))}')
except Exception as e:
    print(f'# Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$config_values" ]; then
            eval "$config_values"
            log_info "Configuration loaded from $CONFIG_FILE"
        else
            log_warn "Failed to parse config, using defaults"
            use_defaults
        fi
    else
        log_warn "Python3 not available, using defaults"
        use_defaults
    fi
}

use_defaults() {
    BACKUP_ENABLED="true"
    BACKUP_DIR="/opt/sting-backups"
    RETENTION_COUNT=5
    RETENTION_DAYS=30
    COMPRESSION_LEVEL=5
    ENCRYPTION_ENABLED="false"
    REMOTE_ENABLED="false"
    VAULT_BACKUP_ENABLED="true"
    VERIFICATION_ENABLED="true"
}

#===============================================================================
# Initialize directories and logging
#===============================================================================
initialize() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"

    log_info "=========================================="
    log_info "STING Backup Started"
    log_info "=========================================="
    log_info "Backup directory: $BACKUP_DIR"
    log_info "Retention: $RETENTION_COUNT copies, max $RETENTION_DAYS days"
}

#===============================================================================
# JSON status output for monitoring
#===============================================================================
write_status() {
    local status="$1"
    local backup_file="$2"
    local backup_size="$3"
    local duration="$4"
    local error_msg="${5:-}"

    local timestamp
    timestamp=$(date -Iseconds)

    cat > "$STATUS_FILE" << EOF
{
    "timestamp": "$timestamp",
    "status": "$status",
    "backup_file": "$backup_file",
    "backup_size_bytes": $backup_size,
    "duration_seconds": $duration,
    "error": "${error_msg}",
    "retention": {
        "count": $RETENTION_COUNT,
        "days": $RETENTION_DAYS
    }
}
EOF
    log_info "Status written to $STATUS_FILE"
}

#===============================================================================
# Database backup
#===============================================================================
backup_database() {
    log_info "Starting database backup..."

    local db_backup_file="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
    local db_backup_tmp="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"

    # Get database connection params
    local DB_HOST="${POSTGRES_HOST:-db}"
    local DB_PORT="${POSTGRES_PORT:-5432}"
    local DB_USER="${POSTGRES_USER:-postgres}"
    local DB_NAME="${POSTGRES_DATABASE_NAME:-sting_app}"

    # Create database backup
    if docker compose exec -T "$DB_HOST" pg_dump -U "$DB_USER" -d "$DB_NAME" 2>/dev/null | gzip -"${COMPRESSION_LEVEL}" > "$db_backup_file"; then
        local db_size=$(stat -c%s "$db_backup_file" 2>/dev/null || stat -f%z "$db_backup_file" 2>/dev/null)
        log_info "Database backup completed: $db_backup_file ($(numfmt --to=iec $db_size))"
        rm -f "$db_backup_tmp" 2>/dev/null || true
        echo "$db_backup_file"
    else
        log_error "Database backup failed!"
        return 1
    fi
}

#===============================================================================
# Docker volumes backup
#===============================================================================
backup_volumes() {
    log_info "Starting Docker volumes backup..."

    local volumes_archive="${BACKUP_DIR}/volumes_${TIMESTAMP}.tar.gz"
    local temp_dir=$(mktemp -d)

    # Critical volumes to backup
    local critical_volumes=(
        "config_data"
        "vault_data"
        "vault_file"
        "vault_logs"
        "sting_logs"
        "sting_certs"
        "llm_logs"
        "chroma_data"
    )

    local volumes_count=0
    local volumes_failed=()

    for volume in "${critical_volumes[@]}"; do
        if docker volume inspect "$volume" >/dev/null 2>&1; then
            log_info "Backing up volume: $volume"
            if docker run --rm \
                -v "${volume}:/source:ro" \
                -v "${temp_dir}:/backup" \
                alpine:latest \
                tar czf "/backup/${volume}.tar.gz" -C /source . 2>/dev/null; then
                volumes_count=$((volumes_count + 1))
            else
                volumes_failed+=("$volume")
                log_warn "Failed to backup volume: $volume"
            fi
        fi
    done

    if [ ${#volumes_failed[@]} -eq 0 ]; then
        log_info "All $volumes_count volumes backed up successfully"
    else
        log_warn "${#volumes_failed[@]} volumes failed to backup"
    fi

    # Create consolidated archive
    if [ $volumes_count -gt 0 ]; then
        tar czf "$volumes_archive" -C "$temp_dir" .
        rm -rf "$temp_dir"
        log_info "Volumes archive created: $volumes_archive"
        echo "$volumes_archive"
    else
        rm -rf "$temp_dir"
        return 1
    fi
}

#===============================================================================
# Main backup function
#===============================================================================
perform_backup() {
    local start_time=$(date +%s)
    local backup_files=()
    local final_archive=""
    local overall_status="success"

    log_info "Performing full system backup..."

    # Backup database
    local db_archive
    if db_archive=$(backup_database); then
        backup_files+=("$db_archive")
    else
        log_warn "Database backup failed, continuing..."
    fi

    # Backup volumes
    local volumes_archive
    if volumes_archive=$(backup_volumes); then
        backup_files+=("$volumes_archive")
    else
        log_warn "Volumes backup failed, continuing..."
    fi

    # Create main backup archive (config, scripts, etc.)
    local main_archive="${BACKUP_DIR}/sting_backup_${TIMESTAMP}.tar.gz"

    # Exclude patterns from config
    local exclude_args=()
    IFS=',' read -ra EXCLUDE_PATTERNS <<< "${EXCLUDE_PATTERNS:-*.tmp,*.log,node_modules,.git,__pycache__,*.pyc}"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_args+=("--exclude=$pattern")
    done

    tar czf "$main_archive" \
        -C "$INSTALL_DIR" \
        "${exclude_args[@]}" \
        conf \
        env \
        certs \
        manage_sting.sh \
        docker-compose.yml \
        2>/dev/null

    if [ -f "$main_archive" ]; then
        backup_files+=("$main_archive")
        log_info "Main archive created: $main_archive"
    fi

    # Consolidate into single backup file if multiple parts
    if [ ${#backup_files[@]} -gt 1 ]; then
        final_archive="${BACKUP_DIR}/sting_full_${TIMESTAMP}.tar.gz"
        log_info "Creating consolidated backup..."
        tar czf "$final_archive" -C "$BACKUP_DIR" $(basename ${backup_files[0]}) $(basename ${backup_files[1]}) $(basename ${backup_files[2]}) 2>/dev/null
        rm -f "${backup_files[@]}" 2>/dev/null || true
    elif [ ${#backup_files[@]} -eq 1 ]; then
        final_archive="${backup_files[0]}"
    fi

    if [ -n "$final_archive" ] && [ -f "$final_archive" ]; then
        # Encryption
        if [ "$ENCRYPTION_ENABLED" = "true" ]; then
            log_info "Encrypting backup..."
            if [ -f "$INSTALL_DIR/lib/backup.sh" ]; then
                source "$INSTALL_DIR/lib/backup.sh"
                encrypt_backup "$final_archive" true
                final_archive="${final_archive}.enc"
            fi
        fi

        # Verification
        if [ "$VERIFICATION_ENABLED" = "true" ]; then
            log_info "Verifying backup integrity..."
            if tar -tzf "$final_archive" >/dev/null 2>&1; then
                log_info "Backup verification passed"
            else
                log_error "Backup verification failed!"
                overall_status="verification_failed"
            fi
        fi

        # Rotation
        log_info "Rotating old backups..."
        if [ -f "$INSTALL_DIR/lib/backup.sh" ]; then
            source "$INSTALL_DIR/lib/backup.sh"
            rotate_backups "$BACKUP_DIR" "$RETENTION_COUNT" "$RETENTION_DAYS"
        fi

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local backup_size=$(stat -c%s "$final_archive" 2>/dev/null || stat -f%z "$final_archive" 2>/dev/null)

        log_info "Backup completed successfully!"
        log_info "File: $final_archive"
        log_info "Size: $(numfmt --to=iec $backup_size)"
        log_info "Duration: ${duration}s"

        write_status "$overall_status" "$final_archive" "$backup_size" "$duration"

        # Sync to remote if enabled
        if [ "$REMOTE_ENABLED" = "true" ]; then
            sync_to_remote "$final_archive"
        fi

        return 0
    else
        log_error "No backup files created!"
        write_status "failed" "" 0 0 "No backup files created"
        return 1
    fi
}

#===============================================================================
# Remote sync functions
#===============================================================================
sync_to_remote() {
    local file="$1"
    local filename=$(basename "$file")

    log_info "Syncing backup to remote location..."

    case "$REMOTE_TYPE" in
        s3)
            if command -v aws >/dev/null 2>&1; then
                log_info "Uploading to S3: $REMOTE_DEST/$filename"
                aws s3 cp "$file" "${REMOTE_DEST}/${filename}" --storage-class STANDARD_IA
                log_info "S3 upload completed"
            else
                log_warn "AWS CLI not installed, skipping S3 sync"
            fi
            ;;
        rsync)
            if command -v rsync >/dev/null 2>&1; then
                log_info "Syncing via rsync to: ${REMOTE_USER}@${REMOTE_DEST}:${REMOTE_PATH:-/backups}"
                rsync -avz -e "ssh -p $REMOTE_PORT" "$file" "${REMOTE_USER}@${REMOTE_DEST}:${REMOTE_PATH:-/backups}/"
                log_info "rsync completed"
            else
                log_warn "rsync not installed, skipping remote sync"
            fi
            ;;
        ftp)
            log_warn "FTP sync not yet implemented"
            ;;
        *)
            log_warn "Unknown remote type: $REMOTE_TYPE"
            ;;
    esac
}

#===============================================================================
# Verification function
#===============================================================================
verify_backup() {
    local backup_file="${1:-$BACKUP_DIR/sting_backup_latest.tar.gz}"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi

    log_info "Verifying backup: $backup_file"

    # Check file size
    local file_size=$(stat -c%s "$backup_file" 2>/dev/null || stat -f%z "$backup_file" 2>/dev/null)
    if [ "$file_size" -lt 1048576 ]; then
        log_error "Backup file too small: $(numfmt --to=iec $file_size)"
        return 1
    fi

    # Check archive integrity
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        log_error "Archive is corrupted"
        return 1
    fi

    # Check for essential files
    local essential_files=("docker-compose.yml" "conf/config.yml")
    for file in "${essential_files[@]}"; do
        if ! tar -tzf "$backup_file" 2>/dev/null | grep -q "$file"; then
            log_error "Essential file missing: $file"
            return 1
        fi
    done

    log_info "Backup verification passed"
    log_info "Size: $(numfmt --to=iec $file_size)"
    return 0
}

#===============================================================================
# Status report function
#===============================================================================
show_status() {
    log_info "Backup Status Report"
    log_info "====================="

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "Backup directory not found"
        return 1
    fi

    local total_backups=$(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.enc" 2>/dev/null | wc -l)
    local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    local latest_backup=$(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.enc" 2>/dev/null | sort -r | head -1)
    local latest_age=""

    if [ -n "$latest_backup" ]; then
        latest_age=$(stat -c %Y "$latest_backup" 2>/dev/null || stat -f %m "$latest_backup" 2>/dev/null)
        local age_seconds=$(( $(date +%s) - latest_age ))
        latest_age=$(numfmt --to=human-readable $age_seconds)
    fi

    echo ""
    echo "Backup Directory: $BACKUP_DIR"
    echo "Total Backups: $total_backups"
    echo "Total Size: $total_size"
    echo "Latest Backup: ${latest_backup:-none} (${latest_age:-N/A} old)"
    echo "Retention: $RETENTION_COUNT copies, max $RETENTION_DAYS days"
    echo ""

    if [ -f "$STATUS_FILE" ]; then
        echo "Last Backup Status:"
        cat "$STATUS_FILE"
    fi
}

#===============================================================================
# Help function
#===============================================================================
show_help() {
    cat << EOF
STING Unified Backup Wrapper

Usage: $0 <command> [options]

Commands:
    backup       Perform full system backup (default)
    verify       Verify backup integrity
    status       Show backup status and statistics
    rotate       Rotate old backups
    vault        Backup Vault only
    help         Show this help message

Options:
    --config FILE    Use specific config file (default: conf/config.yml)
    --directory DIR  Backup directory (default: /opt/sting-backups)
    --retention N    Number of backups to keep (default: 5)
    --days N         Maximum age in days (default: 30)
    --encrypt        Enable encryption
    --remote TYPE    Sync to remote (s3, rsync)
    --verbose        Verbose output
    --dry-run        Show what would be done

Examples:
    $0 backup                    # Standard backup
    $0 backup --encrypt          # Backup with encryption
    $0 backup --remote s3        # Backup and sync to S3
    $0 verify                    # Verify last backup
    $0 status                    # Show backup status

Cron Examples:
    # Daily backup at 2 AM
    0 2 * * * /opt/sting/scripts/backup/backup-wrapper.sh backup

    # Backup with S3 sync
    0 2 * * * /opt/sting/scripts/backup/backup-wrapper.sh backup --remote s3

    # Weekly verification
    0 3 * * 0 /opt/sting/scripts/backup/backup-wrapper.sh verify
EOF
}

#===============================================================================
# Main entry point
#===============================================================================
main() {
    local command="backup"
    local verbose="false"
    local dry_run="false"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            backup|verify|status|rotate|vault|help)
                command="$1"
                shift
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --directory)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --retention)
                RETENTION_COUNT="$2"
                shift 2
                ;;
            --days)
                RETENTION_DAYS="$2"
                shift 2
                ;;
            --encrypt)
                ENCRYPTION_ENABLED="true"
                shift
                ;;
            --remote)
                REMOTE_ENABLED="true"
                REMOTE_TYPE="$2"
                shift 2
                ;;
            --verbose)
                verbose="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Initialize
    load_config
    initialize

    # Execute command
    case "$command" in
        backup)
            if [ "$dry_run" = "true" ]; then
                log_info "[DRY RUN] Would perform backup to $BACKUP_DIR"
                log_info "[DRY RUN] Retention: $RETENTION_COUNT copies, $RETENTION_DAYS days"
                if [ "$ENCRYPTION_ENABLED" = "true" ]; then
                    log_info "[DRY RUN] Would encrypt backup"
                fi
                if [ "$REMOTE_ENABLED" = "true" ]; then
                    log_info "[DRY RUN] Would sync to remote: $REMOTE_TYPE"
                fi
            else
                perform_backup
            fi
            ;;
        verify)
            verify_backup
            ;;
        status)
            show_status
            ;;
        rotate)
            if [ -f "$INSTALL_DIR/lib/backup.sh" ]; then
                source "$INSTALL_DIR/lib/backup.sh"
                rotate_backups "$BACKUP_DIR" "$RETENTION_COUNT" "$RETENTION_DAYS"
            fi
            ;;
        vault)
            if [ -f "$INSTALL_DIR/vault/scripts/backup-vault.sh" ]; then
                "$INSTALL_DIR/vault/scripts/backup-vault.sh"
            else
                log_error "Vault backup script not found"
                exit 1
            fi
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
