#!/bin/bash
# Honey Reserve Maintenance Script
# This script handles routine maintenance tasks for the Honey Reserve storage system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/sting/maintenance"
LOG_FILE="${LOG_DIR}/honey-reserve-maintenance-$(date +%Y%m%d).log"
CONFIG_FILE="/etc/sting/honey-reserve.conf"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file not found at $CONFIG_FILE" >&2
    exit 1
fi

# Default values if not in config
: ${RETENTION_HOURS:=48}
: ${MAX_FILE_SIZE:=104857600}  # 100MB
: ${STORAGE_PATH:="/var/sting/honey-reserve"}
: ${TEMP_PATH:="/var/sting/temp-uploads"}
: ${DB_CONNECTION:="postgresql://sting:password@localhost/sting_app"}

# Logging function
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR" "$1"
    exit 1
}

# Function to clean expired temporary files
clean_expired_temp_files() {
    log "INFO" "Starting cleanup of expired temporary files"
    
    local expired_count=0
    local freed_space=0
    
    # Find and remove files older than retention period
    while IFS= read -r file; do
        if [[ -f "$file" ]]; then
            local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
            
            if rm -f "$file"; then
                ((expired_count++))
                ((freed_space += file_size))
                log "DEBUG" "Removed expired file: $file ($(numfmt --to=iec $file_size))"
            else
                log "WARN" "Failed to remove expired file: $file"
            fi
        fi
    done < <(find "$TEMP_PATH" -type f -mmin +$((RETENTION_HOURS * 60)) 2>/dev/null)
    
    log "INFO" "Cleaned up $expired_count expired files, freed $(numfmt --to=iec $freed_space)"
}

# Function to enforce storage quotas
enforce_storage_quotas() {
    log "INFO" "Enforcing storage quotas"
    
    # Query database for users exceeding quota
    local query="
    SELECT 
        u.email,
        u.id,
        COALESCE(SUM(f.size), 0) as total_usage,
        u.honey_reserve_quota
    FROM users u
    LEFT JOIN user_files f ON u.id = f.user_id
    GROUP BY u.id, u.email, u.honey_reserve_quota
    HAVING COALESCE(SUM(f.size), 0) > u.honey_reserve_quota * 0.9
    ORDER BY total_usage DESC;
    "
    
    # Execute query and process results
    psql "$DB_CONNECTION" -t -A -F"|" -c "$query" | while IFS='|' read -r email user_id usage quota; do
        local usage_percent=$((usage * 100 / quota))
        log "WARN" "User $email is at ${usage_percent}% of quota ($(numfmt --to=iec $usage) / $(numfmt --to=iec $quota))"
        
        # If over 100%, clean oldest temp files
        if [[ $usage_percent -ge 100 ]]; then
            clean_user_temp_files "$user_id" "$email"
        fi
    done
}

# Function to clean user's oldest temp files
clean_user_temp_files() {
    local user_id="$1"
    local email="$2"
    
    log "INFO" "Cleaning temporary files for user $email (over quota)"
    
    # Remove oldest temporary files until under 95% quota
    local query="
    DELETE FROM user_files
    WHERE id IN (
        SELECT id FROM user_files
        WHERE user_id = '$user_id'
        AND file_type = 'temporary'
        ORDER BY created_at ASC
        LIMIT 10
    )
    RETURNING id, filename, size;
    "
    
    psql "$DB_CONNECTION" -t -A -F"|" -c "$query" | while IFS='|' read -r file_id filename size; do
        local file_path="${TEMP_PATH}/${user_id}/${file_id}"
        if [[ -f "$file_path" ]]; then
            rm -f "$file_path"
            log "INFO" "Removed temp file for $email: $filename ($(numfmt --to=iec $size))"
        fi
    done
}

# Function to generate storage report
generate_storage_report() {
    log "INFO" "Generating storage usage report"
    
    local report_file="${LOG_DIR}/storage-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
Honey Reserve Storage Report
Generated: $(date)
================================

Overall Statistics:
EOF
    
    # Total storage usage
    local total_usage=$(du -sb "$STORAGE_PATH" 2>/dev/null | cut -f1)
    echo "Total Storage Usage: $(numfmt --to=iec $total_usage)" >> "$report_file"
    
    # User statistics
    psql "$DB_CONNECTION" -t -A -F"|" >> "$report_file" << EOF

User Storage Summary:
--------------------
SELECT 
    u.email,
    COUNT(f.id) as file_count,
    COALESCE(SUM(f.size), 0) as total_usage,
    u.honey_reserve_quota as quota,
    ROUND(COALESCE(SUM(f.size), 0)::numeric / u.honey_reserve_quota * 100, 2) as usage_percent
FROM users u
LEFT JOIN user_files f ON u.id = f.user_id
GROUP BY u.id, u.email, u.honey_reserve_quota
ORDER BY total_usage DESC
LIMIT 20;
EOF
    
    # File type distribution
    echo -e "\nFile Type Distribution:" >> "$report_file"
    psql "$DB_CONNECTION" -t -A -F"|" >> "$report_file" << EOF
SELECT 
    file_type,
    COUNT(*) as count,
    SUM(size) as total_size
FROM user_files
GROUP BY file_type
ORDER BY total_size DESC;
EOF
    
    log "INFO" "Storage report generated: $report_file"
}

# Function to verify file integrity
verify_file_integrity() {
    log "INFO" "Starting file integrity verification"
    
    local corrupted_count=0
    local missing_count=0
    
    # Check files in database exist on disk
    psql "$DB_CONNECTION" -t -A -F"|" -c "SELECT id, user_id, filename, checksum FROM user_files WHERE checksum IS NOT NULL LIMIT 1000" | \
    while IFS='|' read -r file_id user_id filename checksum; do
        local file_path="${STORAGE_PATH}/${user_id}/${file_id}"
        
        if [[ ! -f "$file_path" ]]; then
            ((missing_count++))
            log "ERROR" "Missing file: $file_path ($filename)"
            # Mark as missing in database
            psql "$DB_CONNECTION" -c "UPDATE user_files SET status = 'missing' WHERE id = '$file_id'"
        else
            # Verify checksum
            local actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
            if [[ "$actual_checksum" != "$checksum" ]]; then
                ((corrupted_count++))
                log "ERROR" "Checksum mismatch for $file_path ($filename)"
                # Mark as corrupted in database
                psql "$DB_CONNECTION" -c "UPDATE user_files SET status = 'corrupted' WHERE id = '$file_id'"
            fi
        fi
    done
    
    log "INFO" "Integrity check complete. Missing: $missing_count, Corrupted: $corrupted_count"
}

# Function to optimize storage
optimize_storage() {
    log "INFO" "Starting storage optimization"
    
    # Find and remove orphaned files (on disk but not in database)
    local orphaned_count=0
    local orphaned_size=0
    
    find "$STORAGE_PATH" -type f -name "*" | while read -r file_path; do
        local file_id=$(basename "$file_path")
        local exists=$(psql "$DB_CONNECTION" -t -A -c "SELECT 1 FROM user_files WHERE id = '$file_id' LIMIT 1")
        
        if [[ -z "$exists" ]]; then
            local file_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo 0)
            ((orphaned_count++))
            ((orphaned_size += file_size))
            
            # Move to orphaned directory for manual review
            mkdir -p "${STORAGE_PATH}/orphaned"
            mv "$file_path" "${STORAGE_PATH}/orphaned/"
            log "WARN" "Moved orphaned file: $file_path ($(numfmt --to=iec $file_size))"
        fi
    done
    
    log "INFO" "Optimization complete. Orphaned files: $orphaned_count ($(numfmt --to=iec $orphaned_size))"
}

# Main execution
main() {
    log "INFO" "Starting Honey Reserve maintenance"
    
    # Check if another instance is running
    local lockfile="/var/run/honey-reserve-maintenance.lock"
    exec 200>"$lockfile"
    
    if ! flock -n 200; then
        error_exit "Another maintenance process is already running"
    fi
    
    # Run maintenance tasks
    clean_expired_temp_files
    enforce_storage_quotas
    verify_file_integrity
    optimize_storage
    
    # Generate report if it's the scheduled time (e.g., 3 AM)
    if [[ $(date +%H) -eq 3 ]]; then
        generate_storage_report
    fi
    
    log "INFO" "Honey Reserve maintenance completed successfully"
    
    # Release lock
    flock -u 200
}

# Run main function
main "$@"