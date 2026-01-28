#!/bin/bash
#===============================================================================
# STING Backup Monitoring Script
# Checks backup freshness, integrity, and sends alerts
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$(dirname "$SCRIPT_DIR"/../..)}"
CONFIG_FILE="${INSTALL_DIR}/conf/config.yml"
STATUS_FILE="${INSTALL_DIR}/data/backup_status.json"
ALERT_LOG="${INSTALL_DIR}/logs/backup/alerts.log"

# Thresholds (can be overridden by config)
MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-48}"      # Alert if older than this
CRITICAL_BACKUP_AGE_HOURS="${CRITICAL_BACKUP_AGE_HOURS:-168}"  # Critical alert
MIN_BACKUP_SIZE_MB="${MIN_BACKUP_SIZE_MB:-10}"          # Minimum expected size in MB
WARNING_BACKUP_COUNT="${WARNING_BACKUP_COUNT:-2}"      # Warn if fewer than this

# Colors for terminal output
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

#===============================================================================
# Logging functions
#===============================================================================
log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$ALERT_LOG"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1"; }
log_alert() { log "ALERT" "$1"; }

#===============================================================================
# Load configuration
#===============================================================================
load_config() {
    if [ -f "$CONFIG_FILE" ] && command -v python3 >/dev/null 2>&1; then
        local max_age=$(cd "$(dirname "$CONFIG_FILE")" && python3 -c "
import yaml
try:
    with open('$(basename "$CONFIG_FILE}")', 'r') as f:
        config = yaml.safe_load(f)
    retention = config.get('backup', {}).get('retention', {})
    max_hours = retention.get('max_age_days', 30) * 24
    print(int(max_hours))
except:
    print(48)
" 2>/dev/null)

        if [ -n "$max_age" ]; then
            MAX_BACKUP_AGE_HOURS="$max_age"
        fi
    fi
}

#===============================================================================
# Check backup directory exists
#===============================================================================
check_backup_directory() {
    local backup_dir="${1:-/opt/sting-backups}"

    if [ ! -d "$backup_dir" ]; then
        log_alert "BACKUP_DIR_MISSING: Backup directory not found: $backup_dir"
        return 1
    fi

    log_info "Backup directory exists: $backup_dir"
    return 0
}

#===============================================================================
# Check backup freshness
#===============================================================================
check_backup_freshness() {
    local backup_dir="${1:-/opt/sting-backups}"
    local latest_backup
    local backup_age_hours
    local status="OK"

    # Find the latest backup file
    latest_backup=$(find "$backup_dir" -name "sting_backup_*.tar.gz" -o -name "sting_backup_*.enc" -o -name "sting_full_*.tar.gz" 2>/dev/null | sort -r | head -1)

    if [ -z "$latest_backup" ]; then
        log_alert "FRESHNESS_CRITICAL: No backup files found in $backup_dir"
        echo "status=CRITICAL"
        echo "message=No backup files found"
        return 2
    fi

    # Calculate backup age
    local backup_timestamp
    backup_timestamp=$(stat -c %Y "$latest_backup" 2>/dev/null || stat -f %m "$latest_backup" 2>/dev/null)
    local current_timestamp=$(date +%s)
    local age_seconds=$((current_timestamp - backup_timestamp))
    backup_age_hours=$((age_seconds / 3600))

    local backup_size_mb=$(( $(stat -c%s "$latest_backup" 2>/dev/null || stat -f%z "$latest_backup" 2>/dev/null) / 1048576 ))

    log_info "Latest backup: $(basename "$latest_backup")"
    log_info "Backup age: ${backup_age_hours} hours"
    log_info "Backup size: ${backup_size_mb} MB"

    # Check against thresholds
    if [ "$backup_age_hours" -ge "$CRITICAL_BACKUP_AGE_HOURS" ]; then
        log_alert "FRESHNESS_CRITICAL: Backup is ${backup_age_hours} hours old (critical threshold: ${CRITICAL_BACKUP_AGE_HOURS}h)"
        status="CRITICAL"
    elif [ "$backup_age_hours" -ge "$MAX_BACKUP_AGE_HOURS" ]; then
        log_alert "FRESHNESS_WARNING: Backup is ${backup_age_hours} hours old (warning threshold: ${MAX_BACKUP_AGE_HOURS}h)"
        status="WARNING"
    else
        log_info "Backup is fresh (${backup_age_hours}h < ${MAX_BACKUP_AGE_HOURS}h)"
    fi

    # Check backup size
    if [ "$backup_size_mb" -lt "$MIN_BACKUP_SIZE_MB" ]; then
        log_alert "SIZE_WARNING: Backup size ${backup_size_mb}MB is smaller than expected minimum ${MIN_BACKUP_SIZE_MB}MB"
        if [ "$status" = "OK" ]; then
            status="WARNING"
        fi
    fi

    echo "status=$status"
    echo "age_hours=$backup_age_hours"
    echo "size_mb=$backup_size_mb"
    echo "latest_file=$latest_backup"

    return 0
}

#===============================================================================
# Check backup count
#===============================================================================
check_backup_count() {
    local backup_dir="${1:-/opt/sting-backups}"
    local backup_count

    backup_count=$(find "$backup_dir" -name "sting_backup_*.tar.gz" -o -name "sting_backup_*.enc" -o -name "sting_full_*.tar.gz" 2>/dev/null | wc -l)

    log_info "Total backup files: $backup_count"

    if [ "$backup_count" -lt "$WARNING_BACKUP_COUNT" ]; then
        log_alert "COUNT_WARNING: Only $backup_count backup(s) found (expected at least $WARNING_BACKUP_COUNT)"
        echo "count=$backup_count"
        echo "status=WARNING"
        return 1
    fi

    echo "count=$backup_count"
    echo "status=OK"
    return 0
}

#===============================================================================
# Verify backup integrity
#===============================================================================
verify_backup_integrity() {
    local backup_dir="${1:-/opt/sting-backups}"
    local latest_backup
    local verified=0
    local failed=0

    # Find all backup files
    local backup_files=$(find "$backup_dir" -name "sting_backup_*.tar.gz" -o -name "sting_full_*.tar.gz" 2>/dev/null | sort -r | head -5)

    if [ -z "$backup_files" ]; then
        log_alert "INTEGRITY_WARNING: No backup files found to verify"
        echo "status=WARNING"
        echo "message=No files to verify"
        return 1
    fi

    log_info "Verifying recent backup archives..."

    for backup_file in $backup_files; do
        if tar -tzf "$backup_file" >/dev/null 2>&1; then
            log_info "VERIFIED: $(basename "$backup_file")"
            verified=$((verified + 1))
        else
            log_alert "INTEGRITY_FAILED: $(basename "$backup_file") is corrupted!"
            failed=$((failed + 1))
        fi
    done

    log_info "Verification complete: $verified OK, $failed FAILED"

    if [ "$failed" -gt 0 ]; then
        echo "status=FAILED"
        echo "verified=$verified"
        echo "failed=$failed"
        return 2
    fi

    echo "status=OK"
    echo "verified=$verified"
    echo "failed=$failed"
    return 0
}

#===============================================================================
# Check Vault backup status
#===============================================================================
check_vault_backup() {
    local vault_backup_dir="${1:-/vault/backups}"
    local latest_vault_backup
    local vault_age_hours

    if [ ! -d "$vault_backup_dir" ]; then
        log_alert "VAULT_DIR_MISSING: Vault backup directory not found"
        echo "status=WARNING"
        echo "message=Directory not found"
        return 1
    fi

    latest_vault_backup=$(find "$vault_backup_dir" -name "vault_backup_*.snap" 2>/dev/null | sort -r | head -1)

    if [ -z "$latest_vault_backup" ]; then
        log_alert "VAULT_WARNING: No Vault backup files found"
        echo "status=WARNING"
        echo "message=No files found"
        return 1
    fi

    local vault_timestamp
    vault_timestamp=$(stat -c %Y "$latest_vault_backup" 2>/dev/null || stat -f %m "$latest_vault_backup" 2>/dev/null)
    local current_timestamp=$(date +%s)
    vault_age_hours=$(( (current_timestamp - vault_timestamp) / 3600 ))

    log_info "Latest Vault backup: $(basename "$latest_vault_backup") (${vault_age_hours}h old)"

    if [ "$vault_age_hours" -ge 24 ]; then
        log_alert "VAULT_WARNING: Vault backup is ${vault_age_hours} hours old"
        echo "status=WARNING"
        echo "age_hours=$vault_age_hours"
        return 1
    fi

    echo "status=OK"
    echo "age_hours=$vault_age_hours"
    return 0
}

#===============================================================================
# Send notification (webhook/email)
#===============================================================================
send_notification() {
    local level="$1"
    local message="$2"

    # Check if notifications are enabled
    if [ -f "$CONFIG_FILE" ] && command -v python3 >/dev/null 2>&1; then
        local webhook_url=$(cd "$(dirname "$CONFIG_FILE")" && python3 -c "
import yaml
try:
    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)
    print(config.get('backup', {}).get('notifications', {}).get('webhook_url', ''))
except:
    print('')
" 2>/dev/null)

        if [ -n "$webhook_url" ]; then
            log_info "Sending webhook notification..."
            curl -s -X POST "$webhook_url" \
                -H "Content-Type: application/json" \
                -d "{\"level\": \"$level\", \"message\": \"$message\", \"timestamp\": \"$(date -Iseconds)\"}" \
                >/dev/null 2>&1 || log_warn "Failed to send webhook notification"
        fi
    fi
}

#===============================================================================
# Generate status report
#===============================================================================
generate_report() {
    local backup_dir="${1:-/opt/sting-backups}"
    local vault_dir="${2:-/vault/backups}"

    local timestamp
    timestamp=$(date -Iseconds)

    cat << EOF
{
    "timestamp": "$timestamp",
    "summary": {
        "backup_dir": "$backup_dir",
        "vault_dir": "$vault_dir"
    },
    "checks": {
        "directory": $(check_backup_directory "$backup_dir" >/dev/null 2>&1 && echo "{\"status\": \"OK\"}" || echo "{\"status\": \"FAILED\"}"),
        "freshness": $(check_backup_freshness "$backup_dir" 2>/dev/null),
        "count": $(check_backup_count "$backup_dir" 2>/dev/null),
        "integrity": $(verify_backup_integrity "$backup_dir" 2>/dev/null),
        "vault": $(check_vault_backup "$vault_dir" 2>/dev/null)
    }
}
EOF
}

#===============================================================================
# Main check routine
#===============================================================================
run_checks() {
    local backup_dir="${1:-/opt/sting-backups}"
    local vault_dir="${2:-/vault/backups}"
    local overall_status="OK"
    local alert_level="info"

    log_info "=========================================="
    log_info "STING Backup Health Check"
    log_info "=========================================="

    # Run all checks
    if ! check_backup_directory "$backup_dir"; then
        overall_status="CRITICAL"
        alert_level="error"
    fi

    # Check freshness (this also checks size)
    local freshness_result
    freshness_result=$(check_backup_freshness "$backup_dir" 2>&1)
    if echo "$freshness_result" | grep -q "status=CRITICAL"; then
        overall_status="CRITICAL"
        alert_level="error"
    elif echo "$freshness_result" | grep -q "status=WARNING"; then
        if [ "$overall_status" != "CRITICAL" ]; then
            overall_status="WARNING"
        fi
        alert_level="warning"
    fi

    # Check count
    local count_result
    count_result=$(check_backup_count "$backup_dir" 2>&1)
    if echo "$count_result" | grep -q "status=WARNING"; then
        if [ "$overall_status" != "CRITICAL" ]; then
            overall_status="WARNING"
        fi
    fi

    # Check integrity
    local integrity_result
    integrity_result=$(verify_backup_integrity "$backup_dir" 2>&1)
    if echo "$integrity_result" | grep -q "status=FAILED"; then
        overall_status="CRITICAL"
        alert_level="error"
    fi

    # Check Vault
    local vault_result
    vault_result=$(check_vault_backup "$vault_dir" 2>&1)
    if echo "$vault_result" | grep -q "status=WARNING"; then
        if [ "$overall_status" != "CRITICAL" ]; then
            overall_status="WARNING"
        fi
    fi

    # Summary
    log_info "=========================================="
    log_info "Overall Status: $overall_status"
    log_info "=========================================="

    # Send alert if needed
    if [ "$overall_status" != "OK" ]; then
        local alert_message="Backup health check: $overall_status"
        log_alert "$alert_message"
        send_notification "$alert_level" "$alert_message"
    fi

    echo "$overall_status"
    return 0
}

#===============================================================================
# Show help
#===============================================================================
show_help() {
    cat << EOF
STING Backup Monitoring Script

Usage: $0 <command> [options]

Commands:
    check          Run all health checks (default)
    freshness      Check backup freshness only
    count          Check backup count only
    integrity      Verify backup integrity
    vault          Check Vault backup status
    report         Generate JSON report
    help           Show this help

Options:
    --backup-dir DIR    Backup directory (default: /opt/sting-backups)
    --vault-dir DIR     Vault backup directory (default: /vault/backups)
    --max-age HOURS     Warning threshold in hours (default: 48)
    --critical HOURS    Critical threshold in hours (default: 168)

Examples:
    $0 check                    # Run all checks
    $0 check --max-age 24       # Use 24h warning threshold
    $0 freshness                # Check only freshness
    $0 report                   # Generate JSON report

Cron Examples:
    # Daily health check at 6 AM
    0 6 * * * /opt/sting/scripts/backup/backup-monitor.sh check

    # Hourly freshness check
    0 * * * * /opt/sting/scripts/backup/backup-monitor.sh freshness
EOF
}

#===============================================================================
# Main entry point
#===============================================================================
main() {
    local command="check"
    local backup_dir="/opt/sting-backups"
    local vault_dir="/vault/backups"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            check|freshness|count|integrity|vault|report|help)
                command="$1"
                shift
                ;;
            --backup-dir)
                backup_dir="$2"
                shift 2
                ;;
            --vault-dir)
                vault_dir="$2"
                shift 2
                ;;
            --max-age)
                MAX_BACKUP_AGE_HOURS="$2"
                shift 2
                ;;
            --critical)
                CRITICAL_BACKUP_AGE_HOURS="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Initialize
    load_config
    mkdir -p "$(dirname "$ALERT_LOG")"

    # Execute command
    case "$command" in
        check)
            run_checks "$backup_dir" "$vault_dir"
            ;;
        freshness)
            check_backup_freshness "$backup_dir"
            ;;
        count)
            check_backup_count "$backup_dir"
            ;;
        integrity)
            verify_backup_integrity "$backup_dir"
            ;;
        vault)
            check_vault_backup "$vault_dir"
            ;;
        report)
            generate_report "$backup_dir" "$vault_dir"
            ;;
        help)
            show_help
            ;;
        *)
            echo "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
