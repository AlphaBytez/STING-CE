#!/bin/bash
# backup.sh - Backup, restore, and maintenance functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Load backup configuration from config.yml
load_backup_config() {
    # Set INSTALL_DIR if not already set
    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR="$HOME/.sting-ce"
        # If we're in the STING directory, use current directory
        if [ -f "conf/config.yml" ]; then
            INSTALL_DIR="$(pwd)"
        fi
    fi
    
    local config_file="${INSTALL_DIR}/conf/config.yml"
    
    # Default values
    BACKUP_RETENTION_COUNT=5
    BACKUP_MAX_AGE_DAYS=30
    BACKUP_AUTO_CLEANUP=true
    INSTALLATION_RETENTION_COUNT=2
    
    if [ -f "$config_file" ] && command -v python3 >/dev/null 2>&1; then
        # Try to read config using Python
        local config_values=$(cd "$(dirname "$config_file")" && python3 -c "
import yaml
import sys
try:
    with open('$(basename "$config_file")', 'r') as f:
        config = yaml.safe_load(f)
    backup_config = config.get('backup', {})
    retention = backup_config.get('retention', {})
    installation = backup_config.get('installation_backups', {})
    
    print(f\"BACKUP_RETENTION_COUNT={retention.get('count', 5)}\")
    print(f\"BACKUP_MAX_AGE_DAYS={retention.get('max_age_days', 30)}\")
    print(f\"BACKUP_AUTO_CLEANUP={str(retention.get('auto_cleanup', True)).lower()}\")
    print(f\"INSTALLATION_RETENTION_COUNT={installation.get('retention_count', 2)}\")
except Exception as e:
    print(f\"# Error reading config: {e}\", file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$config_values" ]; then
            eval "$config_values"
            log_message "Loaded backup configuration: retention_count=$BACKUP_RETENTION_COUNT, max_age_days=$BACKUP_MAX_AGE_DAYS"
        else
            log_message "Using default backup configuration values"
        fi
    else
        log_message "Config file not found or Python not available, using defaults"
    fi
}

# Initialize backup directory
initialize_backup_directory() {
    log_message "Initializing backup directory..."
    
    # Platform-specific backup directory
    if [[ "$(uname)" == "Darwin" ]]; then
        # Mac: Use user's home directory
        BACKUP_DIR="${HOME}/.sting-ce/backups"
    else
        # Linux: Use standard location with proper permissions
        BACKUP_DIR="/opt/sting-ce/backups"
        if [ "$EUID" -ne 0 ]; then
            sudo mkdir -p "$BACKUP_DIR"
            sudo chown "$USER:$USER" "$BACKUP_DIR"
        else
            mkdir -p "$BACKUP_DIR"
        fi
    fi
    
    mkdir -p "$BACKUP_DIR"
    log_message "Backup directory set to: $BACKUP_DIR"
}

# Pre-flight checks for backup process
backup_preflight_checks() {
    log_message "Running pre-flight checks for backup..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_message "ERROR: Docker is not running or not accessible" "ERROR"
        return 1
    fi
    
    # Check if essential services are running
    local required_services=("db" "vault")
    local missing_services=()
    
    # Change to install directory for docker compose commands
    local original_dir="$(pwd)"
    cd "${INSTALL_DIR}" 2>/dev/null || {
        log_message "WARNING: Could not change to install directory for service checks" "WARNING"
    }
    
    for service in "${required_services[@]}"; do
        # Use docker compose ps to check service status
        if ! docker compose ps --format "{{.Service}}\t{{.Status}}" 2>/dev/null | grep "^${service}" | grep -q "Up\|running"; then
            # Fallback: check by container name pattern
            if ! docker ps --format "{{.Names}}\t{{.Status}}" 2>/dev/null | grep -E "(sting-ce-|sting_ce_)?${service}" | grep -q "Up"; then
                missing_services+=("$service")
            fi
        fi
    done
    
    # Restore original directory
    cd "$original_dir" 2>/dev/null || true
    
    if [ ${#missing_services[@]} -gt 0 ]; then
        log_message "WARNING: Some services not running: ${missing_services[*]}" "WARNING"
        
        # Only fail if database is missing (critical for backup)
        local db_missing=false
        for service in "${missing_services[@]}"; do
            if [[ "$service" == "db" ]]; then
                db_missing=true
                break
            fi
        done
    fi
        if [[ "$db_missing" == "true" ]]; then
    # Check database connectivity (only if db service was found)
    local db_missing=false
    for service in "${missing_services[@]}"; do
        if [[ "$service" == "db" ]]; then
            db_missing=true
            break
        fi
    done
    
    if [[ "$db_missing" == "false" ]]; then
        log_message "Checking database connectivity..."
        cd "${INSTALL_DIR}" 2>/dev/null || true
        if ! docker compose exec -T db pg_isready -U "${POSTGRES_USER:-postgres}" >/dev/null 2>&1; then
            log_message "WARNING: Database connectivity check failed" "WARNING"
            log_message "Backup will continue but database backup may fail" "WARNING"
        else
            log_message "✅ Database connectivity verified"
        fi
        cd "$original_dir" 2>/dev/null || true
    fi
        if ! docker compose exec -T db pg_isready -U "${POSTGRES_USER:-postgres}" >/dev/null 2>&1; then
            log_message "WARNING: Database connectivity check failed" "WARNING"
            log_message "Backup will continue but database backup may fail" "WARNING"
        else
            log_message "✅ Database connectivity verified"
        fi
        cd "$original_dir" 2>/dev/null || true
    fi
    
    # Check available disk space (require at least 1GB free)
    local available_space
    if [[ "$(uname)" == "Darwin" ]]; then
        available_space=$(df -g "${BACKUP_DIR:-${HOME}}" 2>/dev/null | tail -1 | awk '{print $4}' || echo "0")
    else
        available_space=$(df -BG "${BACKUP_DIR:-/opt/sting-ce}" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//' || echo "0")
    fi
    
    if [ "$available_space" -lt 1 ]; then
        log_message "WARNING: Low disk space (${available_space}GB available). Backup may fail." "WARNING"
        log_message "Consider cleaning up old backups or freeing disk space." "WARNING"
    fi
    
    log_message "✅ Pre-flight checks passed"
    return 0
}

# Perform system backup
perform_backup() {
    # Run pre-flight checks first
    if ! backup_preflight_checks; then
        log_message "ERROR: Pre-flight checks failed. Backup aborted." "ERROR"
        return 1
    fi
    
    # Platform-specific setup
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS backup handling
        BACKUP_DIR="${HOME}/.sting-ce/backups"
        # Use gtar if available (from homebrew), fallback to tar
        TAR_CMD=$(command -v gtar || command -v tar)
        # Ensure proper permissions for macOS
        mkdir -p "$BACKUP_DIR"
        chown $(whoami) "$BACKUP_DIR"
    else
        # Linux backup handling
        BACKUP_DIR="/opt/sting-ce/backups"
        TAR_CMD="tar"
        # Ensure proper permissions for Linux
        if [ "$EUID" -ne 0 ]; then
            sudo mkdir -p "$BACKUP_DIR"
            sudo chown "$USER:$USER" "$BACKUP_DIR"
        else
            mkdir -p "$BACKUP_DIR"
        fi
    fi

    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local temp_dir=$(mktemp -d)
    local temp_backup_file="${temp_dir}/sting_backup_${timestamp}.tar.gz"
    local final_backup_file="${BACKUP_DIR}/sting_backup_${timestamp}.tar.gz"
    local db_backup_file="${temp_dir}/db_backup_${timestamp}.sql"

    log_message "Starting backup process..."
    log_message "Using temporary directory: ${temp_dir}"
    
    # Enhanced database backup with validation and retry
    log_message "Creating database backup..."
    local db_backup_success=false
    local max_retries=3
    local retry_delay=5
    
    # Change to install directory for docker compose commands
    local original_backup_dir="$(pwd)"
    cd "${INSTALL_DIR}" || {
        log_message "ERROR: Could not change to install directory for database backup" "ERROR"
        rm -rf "${temp_dir}"
        return 1
    }
    
    for attempt in $(seq 1 $max_retries); do
        log_message "Database backup attempt $attempt/$max_retries"
        
        # Platform-specific database backup
        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS: Use host networking for Docker
            docker compose exec -T --user postgres db pg_dump sting_app > "${db_backup_file}"
        else
            # Linux: Standard approach
            docker compose exec -T db pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DATABASE_NAME:-sting_app}" > "${db_backup_file}"
        fi
        
        if [ $? -eq 0 ] && [ -s "${db_backup_file}" ]; then
            # Validate backup content
            if head -10 "${db_backup_file}" | grep -q "PostgreSQL database dump"; then
                local backup_size=$(du -h "${db_backup_file}" | cut -f1)
                log_message "✅ Database backup successful (${backup_size})"
                db_backup_success=true
                break
            else
                log_message "WARNING: Database backup appears corrupted (attempt $attempt)" "WARNING"
            fi
        else
            log_message "WARNING: Database backup failed or empty (attempt $attempt)" "WARNING"
        fi
        
        if [ $attempt -lt $max_retries ]; then
            log_message "Waiting ${retry_delay}s before retry..."
            sleep $retry_delay
        fi
    done

    # Restore original directory
    cd "$original_backup_dir" || true

    if [ "$db_backup_success" != "true" ]; then
        log_message "ERROR: Database backup failed after $max_retries attempts" "ERROR"
        rm -rf "${temp_dir}"
        return 1
    fi

    # Backup Docker volumes (critical data)
    log_message "Backing up Docker volumes..."
    local volumes_backup_dir="${temp_dir}/docker_volumes"
    mkdir -p "${volumes_backup_dir}"
    
    # List of critical volumes to backup
    local critical_volumes=(
        "config_data"
        "vault_data" 
        "vault_file"
        "vault_logs"
        "sting_logs"
        "sting_certs"
        "llm_logs"
    )
    
    for volume in "${critical_volumes[@]}"; do
        if docker volume inspect "$volume" >/dev/null 2>&1; then
            log_message "Backing up volume: $volume"
            # Create volume backup using a temporary container
            docker run --rm \
                -v "${volume}:/source:ro" \
                -v "${volumes_backup_dir}:/backup" \
                alpine:latest \
                tar czf "/backup/${volume}.tar.gz" -C /source . 2>/dev/null || {
                log_message "Warning: Failed to backup volume $volume" "WARNING"
            }
        else
            log_message "Volume $volume not found, skipping" "WARNING"
        fi
    done

    # Create tar archive with platform-specific handling
    log_message "Creating backup archive..."
    $TAR_CMD czf "${temp_backup_file}" \
        --exclude="./backups" \
        --exclude="*.tmp" \
        --exclude="*.log" \
        --exclude="node_modules" \
        --exclude="venv" \
        --exclude=".venv" \
        --exclude="models" \
        --exclude=".git" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude=".pytest_cache" \
        --exclude="frontend/node_modules" \
        --exclude="frontend-v2/node_modules" \
        --exclude="*.egg-info" \
        -C "${INSTALL_DIR}" . \
        -C "$(dirname ${db_backup_file})" "$(basename ${db_backup_file})" \
        -C "${temp_dir}" docker_volumes

    if [ $? -ne 0 ]; then
        log_message "ERROR: Backup archive creation failed" "ERROR"
        rm -rf "${temp_dir}"
        return 1
    fi
    
    # Verify backup integrity
    log_message "Verifying backup integrity..."
    if ! verify_backup_integrity "${temp_backup_file}"; then
        log_message "ERROR: Backup verification failed" "ERROR"
        rm -rf "${temp_dir}"
        return 1
    fi

    # Move backup to final location with proper permissions
    if [[ "$(uname)" == "Darwin" ]]; then
        mv "${temp_backup_file}" "${final_backup_file}"
        chmod 644 "${final_backup_file}"
    else
        sudo mv "${temp_backup_file}" "${final_backup_file}"
        sudo chown "$USER:$USER" "${final_backup_file}"
        sudo chmod 644 "${final_backup_file}"
    fi

    # Cleanup
    rm -rf "${temp_dir}"
    log_message "Backup completed successfully: ${final_backup_file}"
    
    # Load backup configuration and rotate old backups
    load_backup_config
    rotate_backups "${BACKUP_DIR}"
}

# Enhanced restore with atomic rollback capability
perform_restore() {
    local backup_file="$1"
    local skip_verification="${2:-false}"
    
    if [ ! -f "$backup_file" ]; then
        log_message "ERROR: Backup file not found: $backup_file" "ERROR"
        return 1
    fi

    # Verify backup before attempting restore
    if [ "$skip_verification" != "true" ]; then
        log_message "Verifying backup before restore..."
        if ! verify_backup_integrity "$backup_file"; then
            log_message "ERROR: Backup verification failed. Restore aborted." "ERROR"
            return 1
        fi
    fi

    log_message "Starting atomic restore process..."
    
    # Create atomic restore backup
    local restore_timestamp=$(date +"%Y%m%d_%H%M%S")
    local rollback_backup="${INSTALL_DIR}.pre-restore.${restore_timestamp}"
    
    log_message "Creating rollback point: ${rollback_backup}"
    if [ -d "$INSTALL_DIR" ]; then
        # Create a snapshot for rollback
        cp -r "$INSTALL_DIR" "$rollback_backup" 2>/dev/null || {
            log_message "WARNING: Could not create complete rollback backup" "WARNING"
        }
    fi
    
    # Stop all services with timeout protection
    log_message "Stopping services for restore..."
    timeout 30s docker compose -f "${INSTALL_DIR}/docker-compose.yml" down 2>/dev/null || {
        log_message "WARNING: Service shutdown timed out, forcing stop" "WARNING"
        docker ps -q --filter "name=sting-ce-" | xargs -r docker stop 2>/dev/null || true
    }

    # Create temporary extraction directory for validation
    local temp_extract_dir=$(mktemp -d)
    
    # Extract backup to temporary location first
    log_message "Extracting backup for validation..."
    if ! tar xzf "$backup_file" -C "$temp_extract_dir"; then
        log_message "ERROR: Failed to extract backup file" "ERROR"
        rm -rf "$temp_extract_dir"
        restore_rollback "$rollback_backup"
        return 1
    fi
    
    # Validate extracted contents
    local essential_files=("docker-compose.yml" "conf/config.yml")
    for file in "${essential_files[@]}"; do
        if [ ! -f "${temp_extract_dir}/${file}" ]; then
            log_message "ERROR: Essential file missing in backup: $file" "ERROR"
            rm -rf "$temp_extract_dir"
            restore_rollback "$rollback_backup"
            return 1
        fi
    done

    # Atomic move: replace INSTALL_DIR with extracted backup
    log_message "Performing atomic restore..."
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "${INSTALL_DIR}.old" 2>/dev/null || true
        mv "$INSTALL_DIR" "${INSTALL_DIR}.old"
    fi
    
    mv "$temp_extract_dir" "$INSTALL_DIR" || {
        log_message "ERROR: Atomic restore failed" "ERROR"
        # Restore from old version if possible
        if [ -d "${INSTALL_DIR}.old" ]; then
            mv "${INSTALL_DIR}.old" "$INSTALL_DIR"
        fi
        restore_rollback "$rollback_backup"
        return 1
    }

    # Restore Docker volumes if they exist in backup
    restore_docker_volumes "$INSTALL_DIR"
    
    # Restore database from backup
    restore_database_from_backup "$INSTALL_DIR"

    # Attempt to start services with validation
    log_message "Starting services after restore..."
    cd "$INSTALL_DIR" || {
        log_message "ERROR: Could not change to install directory" "ERROR"
        restore_rollback "$rollback_backup"
        return 1
    }
    
    if ! timeout 60s docker compose up -d; then
        log_message "ERROR: Failed to start services after restore" "ERROR"
        restore_rollback "$rollback_backup"
        return 1
    fi

    # Wait for critical services and validate
    log_message "Validating restore success..."
    sleep 10  # Allow services to start
    
    local critical_services=("db" "app" "frontend")
    local failed_services=()
    
    for service in "${critical_services[@]}"; do
        if ! docker compose ps --format "{{.Name}}\t{{.Status}}" 2>/dev/null | grep "$service" | grep -q "Up"; then
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        log_message "ERROR: Critical services failed to start: ${failed_services[*]}" "ERROR"
        restore_rollback "$rollback_backup"
        return 1
    fi

    # Clean up
    rm -rf "${INSTALL_DIR}.old" 2>/dev/null || true
    rm -rf "$rollback_backup" 2>/dev/null || true
    
    log_message "✅ Restore completed successfully" "SUCCESS"
    return 0
}

# Rollback helper function
restore_rollback() {
    local rollback_backup="$1"
    
    if [ ! -d "$rollback_backup" ]; then
        log_message "ERROR: Cannot rollback - rollback backup not found" "ERROR"
        return 1
    fi
    
    log_message "⚠️  Performing rollback to pre-restore state..." "WARNING"
    
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    mv "$rollback_backup" "$INSTALL_DIR" || {
        log_message "ERROR: Rollback failed" "ERROR"
        return 1
    }
    
    log_message "Rollback completed - system restored to pre-restore state" "WARNING"
    return 0
}

# Helper: Restore Docker volumes
restore_docker_volumes() {
    local install_dir="$1"
    local volumes_backup_dir="${install_dir}/docker_volumes"
    
    if [ ! -d "$volumes_backup_dir" ]; then
        log_message "No Docker volume backups found" "INFO"
        return 0
    fi
    
    log_message "Restoring Docker volumes..."
    
    for volume_backup in "${volumes_backup_dir}"/*.tar.gz; do
        if [ -f "$volume_backup" ]; then
            local volume_name=$(basename "$volume_backup" .tar.gz)
            log_message "Restoring volume: $volume_name"
            
            # Create volume if it doesn't exist
            docker volume create "$volume_name" >/dev/null 2>&1 || true
            
            # Restore volume contents with timeout
            if ! timeout 30s docker run --rm \
                -v "${volume_name}:/target" \
                -v "${volume_backup}:/backup.tar.gz:ro" \
                alpine:latest \
                sh -c "cd /target && tar xzf /backup.tar.gz"; then
                log_message "WARNING: Failed to restore volume $volume_name" "WARNING"
            else
                log_message "✅ Volume $volume_name restored" "SUCCESS"
            fi
        fi
    done
    
    # Clean up extracted volume backups
    rm -rf "$volumes_backup_dir"
    log_message "Docker volumes restore completed"
}

# Helper: Restore database from backup
restore_database_from_backup() {
    local install_dir="$1"
    
    # Find database backup file
    local db_backup_file=$(find "$install_dir" -name "db_backup_*.sql" -type f 2>/dev/null | head -1)
    
    if [ -z "$db_backup_file" ] || [ ! -f "$db_backup_file" ]; then
        log_message "WARNING: No database backup found in restore" "WARNING"
        return 0
    fi
    
    log_message "Restoring database from backup..."
    
    # Start database service if not running
    docker compose up -d db
    sleep 10  # Wait for database to be ready
    
    # Restore database with timeout
    if timeout 60s docker compose exec -T db psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DATABASE_NAME:-sting_app}" < "$db_backup_file"; then
        log_message "✅ Database restored successfully" "SUCCESS"
    else
        log_message "WARNING: Database restore failed or timed out" "WARNING"
    fi
    
    # Clean up database backup file
    rm -f "$db_backup_file"
}

# Rotate old backups to keep only specified number
rotate_backups() {
    local backup_dir="$1"
    local keep_count="${2:-$BACKUP_RETENTION_COUNT}"
    
    # Load configuration if not already loaded
    if [ -z "$BACKUP_RETENTION_COUNT" ]; then
        load_backup_config
        keep_count="$BACKUP_RETENTION_COUNT"
    fi
    
    log_message "Rotating backups in $backup_dir (keeping $keep_count most recent)"
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS version using BSD find and stat
        cd "${backup_dir}" && \
        ls -t *.tar.gz 2>/dev/null | \
        tail -n +$((keep_count + 1)) | \
        xargs -I {} rm -f {}
    else
        # Linux version using GNU find
        find "${backup_dir}" -name '*.tar.gz' -type f -printf '%T@ %p\n' | 
        sort -rn | 
        tail -n +$((keep_count + 1)) | 
        cut -d' ' -f2- | 
        xargs -r rm
    fi
    
    log_message "Old backups rotated, keeping $keep_count most recent"
}

# Clean up installation backups (the .sting-ce.backup.* directories)
cleanup_installation_backups() {
    local retention_count="${1:-$INSTALLATION_RETENTION_COUNT}"
    
    # Load configuration if not already loaded
    if [ -z "$INSTALLATION_RETENTION_COUNT" ]; then
        load_backup_config
        retention_count="$INSTALLATION_RETENTION_COUNT"
    fi
    
    log_message "Cleaning up installation backups (keeping $retention_count most recent)"
    
    # Find all .sting-ce.backup.* directories in user's home
    local backup_dirs=$(find "$HOME" -maxdepth 1 -type d -name ".sting-ce.backup.*" 2>/dev/null | sort -r)
    
    if [ -z "$backup_dirs" ]; then
        log_message "No installation backup directories found"
        return 0
    fi
    
    local count=0
    local total_size_before=0
    local total_size_after=0
    
    # Calculate total size before cleanup
    for dir in $backup_dirs; do
        if [ -d "$dir" ]; then
            local size=$(du -s "$dir" 2>/dev/null | cut -f1)
            total_size_before=$((total_size_before + size))
        fi
    done
    
    # Keep only the most recent ones
    for dir in $backup_dirs; do
        count=$((count + 1))
        if [ $count -le $retention_count ]; then
            log_message "Keeping backup: $(basename "$dir")"
            local size=$(du -s "$dir" 2>/dev/null | cut -f1)
            total_size_after=$((total_size_after + size))
        else
            log_message "Removing old backup: $(basename "$dir")"
            rm -rf "$dir"
        fi
    done
    
    # Convert sizes to human readable format
    local size_freed=$((total_size_before - total_size_after))
    if [ $size_freed -gt 1048576 ]; then
        log_message "Installation backup cleanup completed. Space freed: $((size_freed / 1048576)) GB"
    elif [ $size_freed -gt 1024 ]; then
        log_message "Installation backup cleanup completed. Space freed: $((size_freed / 1024)) MB"
    else
        log_message "Installation backup cleanup completed. Space freed: ${size_freed} KB"
    fi
}

# Enhanced key management functions
get_backup_encryption_key() {
    local key_id="sting_backup_key"
    local key=""
    
    # Try system keychain/keyring first (more secure)
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Use Keychain
        key=$(security find-generic-password -a "$USER" -s "$key_id" -w 2>/dev/null || true)
        if [ -n "$key" ]; then
            echo "$key"
            return 0
        fi
    elif command -v keyctl >/dev/null 2>&1; then
        # Linux: Try kernel keyring
        key=$(keyctl print %user:$key_id 2>/dev/null | base64 -w 0 2>/dev/null || true)
        if [ -n "$key" ]; then
            echo "$key"
            return 0
        fi
    fi
    
    # Fallback: Use file-based key with enhanced security
    local key_file="${CONFIG_DIR}/secrets/backup_key.txt"
    
    if [ -f "$key_file" ]; then
        # Verify file permissions for security
        local perms=$(stat -c "%a" "$key_file" 2>/dev/null || stat -f "%A" "$key_file" 2>/dev/null)
        if [ "$perms" != "600" ]; then
            log_message "WARNING: Fixing backup key file permissions" "WARNING"
            chmod 600 "$key_file"
        fi
        cat "$key_file"
        return 0
    fi
    
    # No key found
    return 1
}

store_backup_encryption_key() {
    local key="$1"
    local key_id="sting_backup_key"
    local stored=false
    
    # Try to store in system keychain/keyring (most secure)
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Store in Keychain
        if security add-generic-password -a "$USER" -s "$key_id" -w "$key" 2>/dev/null; then
            log_message "✅ Backup encryption key stored in macOS Keychain" "SUCCESS"
            stored=true
        fi
    elif command -v keyctl >/dev/null 2>&1; then
        # Linux: Store in kernel keyring
        if echo "$key" | base64 -d | keyctl padd user "$key_id" @u >/dev/null 2>&1; then
            log_message "✅ Backup encryption key stored in Linux keyring" "SUCCESS"
            stored=true
        fi
    fi
    
    # Fallback: Store in file with enhanced security
    if [ "$stored" = false ]; then
        local key_file="${CONFIG_DIR}/secrets/backup_key.txt"
        log_message "Storing backup encryption key in secure file (keychain/keyring not available)"
        
        # Create secure directory
        mkdir -p "$(dirname "$key_file")"
        chmod 700 "$(dirname "$key_file")"
        
        # Store key with strict permissions
        echo "$key" > "$key_file"
        chmod 600 "$key_file"
        
        # Additional security on Linux: set immutable flag if available
        if command -v chattr >/dev/null 2>&1; then
            chattr +i "$key_file" 2>/dev/null || true
        fi
        
        log_message "⚠️  Backup key stored in file: $key_file (consider using system keychain)" "WARNING"
    fi
}

# Enhanced encrypt backup file with secure key management
encrypt_backup() {
    local file="$1"
    local use_keychain="${2:-true}"
    
    if [ ! -f "$file" ]; then
        log_message "ERROR: Backup file not found: $file" "ERROR"
        return 1
    fi
    
    log_message "Encrypting backup with AES-256-CBC..."
    
    # Get or generate encryption key
    local encryption_key=""
    if [ "$use_keychain" = "true" ]; then
        encryption_key=$(get_backup_encryption_key)
    fi
    
    if [ -z "$encryption_key" ]; then
        log_message "Generating new backup encryption key..."
        encryption_key=$(openssl rand -base64 32)
        
        if [ "$use_keychain" = "true" ]; then
            store_backup_encryption_key "$encryption_key"
        fi
    else
        log_message "Using existing backup encryption key from secure storage"
    fi
    
    # Create temporary key file for OpenSSL
    local temp_key_file=$(mktemp)
    echo "$encryption_key" > "$temp_key_file"
    chmod 600 "$temp_key_file"
    
    # Encrypt with stronger algorithm and parameters
    if openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 -in "$file" -out "${file}.enc" -pass file:"$temp_key_file"; then
        # Create checksum for encrypted file
        create_checksum "${file}.enc"
        
        # Secure cleanup
        shred -f "$temp_key_file" 2>/dev/null || rm -f "$temp_key_file"
        rm "$file"  # Remove unencrypted backup
        
        local encrypted_size=$(du -h "${file}.enc" | cut -f1)
        log_message "✅ Backup encrypted successfully: ${file}.enc (${encrypted_size})" "SUCCESS"
        log_message "💡 Keep your encryption key safe - it's required for restore!" "INFO"
        return 0
    else
        log_message "ERROR: Backup encryption failed" "ERROR"
        shred -f "$temp_key_file" 2>/dev/null || rm -f "$temp_key_file"
        return 1
    fi
}

# Enhanced decrypt backup file with secure key management  
decrypt_backup() {
    local file="$1"
    local use_keychain="${2:-true}"
    
    if [ ! -f "$file" ]; then
        log_message "ERROR: Encrypted backup file not found: $file" "ERROR"
        return 1
    fi
    
    # Verify checksum if available
    if [ -f "${file}.checksum" ]; then
        log_message "Verifying encrypted backup integrity..."
        if ! verify_checksum "$file"; then
            log_message "ERROR: Encrypted backup file integrity check failed" "ERROR"
            return 1
        fi
        log_message "✅ Encrypted backup integrity verified"
    fi
    
    log_message "Decrypting backup: $file"
    
    # Get decryption key from secure storage
    local decryption_key=""
    if [ "$use_keychain" = "true" ]; then
        decryption_key=$(get_backup_encryption_key)
    fi
    
    if [ -z "$decryption_key" ]; then
        log_message "ERROR: Backup encryption key not found in secure storage" "ERROR"
        log_message "Try: --no-keychain flag if key is stored in file" "INFO"
        return 1
    fi
    
    # Create temporary key file for OpenSSL
    local temp_key_file=$(mktemp)
    echo "$decryption_key" > "$temp_key_file"
    chmod 600 "$temp_key_file"
    
    # Decrypt with matching algorithm and parameters
    if openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 100000 -in "$file" -out "${file%.enc}" -pass file:"$temp_key_file"; then
        # Secure cleanup
        shred -f "$temp_key_file" 2>/dev/null || rm -f "$temp_key_file"
        
        local decrypted_size=$(du -h "${file%.enc}" | cut -f1)
        log_message "✅ Backup decrypted successfully: ${file%.enc} (${decrypted_size})" "SUCCESS"
        return 0
    else
        log_message "ERROR: Backup decryption failed - wrong key or corrupted file" "ERROR"
        shred -f "$temp_key_file" 2>/dev/null || rm -f "$temp_key_file"
        return 1
    fi
}

# Helper: Export backup encryption key (for backup/transfer)
export_backup_key() {
    local output_file="$1"
    
    if [ -z "$output_file" ]; then
        log_message "ERROR: Output file required for key export" "ERROR"
        return 1
    fi
    
    log_message "⚠️  SECURITY WARNING: Exporting backup encryption key" "WARNING"
    log_message "Keep this key file extremely secure - it can decrypt all your backups!" "WARNING"
    
    local encryption_key=$(get_backup_encryption_key)
    if [ -z "$encryption_key" ]; then
        log_message "ERROR: No backup encryption key found" "ERROR"
        return 1
    fi
    
    # Create secure key export
    {
        echo "# STING Backup Encryption Key"
        echo "# Generated: $(date)"
        echo "# WARNING: Keep this file secure and private!"
        echo "# This key can decrypt all STING backups"
        echo ""
        echo "$encryption_key"
    } > "$output_file"
    
    chmod 600 "$output_file"
    
    log_message "✅ Backup encryption key exported to: $output_file" "SUCCESS"
    log_message "🔐 File permissions set to 600 (owner read/write only)" "INFO"
}

# Helper: Import backup encryption key
import_backup_key() {
    local key_file="$1"
    
    if [ ! -f "$key_file" ]; then
        log_message "ERROR: Key file not found: $key_file" "ERROR"
        return 1
    fi
    
    # Extract key from file (skip comments)
    local encryption_key=$(grep -v '^#' "$key_file" | grep -v '^$' | head -1)
    
    if [ -z "$encryption_key" ]; then
        log_message "ERROR: No valid key found in file" "ERROR"
        return 1
    fi
    
    log_message "Importing backup encryption key..."
    store_backup_encryption_key "$encryption_key"
    
    log_message "✅ Backup encryption key imported successfully" "SUCCESS"
}

# Perform system maintenance
perform_maintenance() {
    log_message "Performing maintenance tasks..."
    
    # Clean up unused Docker resources
    log_message "Cleaning Docker volumes..."
    docker volume prune -f
    
    log_message "Cleaning Docker images..."
    docker image prune -f
    
    log_message "Cleaning Docker containers..."
    docker container prune -f
    
    # Clean up old log files
    if [ -d "${INSTALL_DIR}/logs" ]; then
        log_message "Cleaning old log files..."
        find "${INSTALL_DIR}/logs" -name "*.log" -type f -mtime +30 -delete
    fi
    
    # Clean up temporary files
    if [ -d "${INSTALL_DIR}" ]; then
        log_message "Cleaning temporary files..."
        find "${INSTALL_DIR}" -name "*.tmp" -type f -delete
        find "${INSTALL_DIR}" -name "core" -type f -delete
    fi
    
    # Load backup configuration
    load_backup_config
    
    # Rotate backup files
    initialize_backup_directory
    rotate_backups "$BACKUP_DIR"
    
    # Clean up installation backups
    cleanup_installation_backups
    
    log_message "Maintenance tasks completed." "SUCCESS"
}

# Helper function: List available backups
list_backups() {
    initialize_backup_directory
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_message "No backup directory found"
        return 1
    fi
    
    log_message "Available backups in $BACKUP_DIR:"
    if ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null; then
        return 0
    else
        log_message "No backups found"
        return 1
    fi
}

# Helper function: Get backup size
get_backup_size() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_message "Backup file not found: $backup_file"
        return 1
    fi
    
    local size
    if [[ "$(uname)" == "Darwin" ]]; then
        size=$(stat -f%z "$backup_file")
    else
        size=$(stat -c%s "$backup_file")
    fi
    
    # Convert to human readable format
    if [ $size -gt 1073741824 ]; then
        printf "%.1f GB\n" $(echo "scale=1; $size/1073741824" | bc)
    elif [ $size -gt 1048576 ]; then
        printf "%.1f MB\n" $(echo "scale=1; $size/1048576" | bc)
    elif [ $size -gt 1024 ]; then
        printf "%.1f KB\n" $(echo "scale=1; $size/1024" | bc)
    else
        printf "%d bytes\n" $size
    fi
}

# Enhanced backup integrity verification
verify_backup_integrity() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_message "ERROR: Backup file not found: $backup_file" "ERROR"
        return 1
    fi
    
    log_message "Running comprehensive backup verification..."
    
    # Check file size (should be > 1MB for a valid STING backup)
    local file_size=$(stat -c%s "$backup_file" 2>/dev/null || stat -f%z "$backup_file" 2>/dev/null)
    if [ -z "$file_size" ] || [ "$file_size" -lt 1048576 ]; then
        log_message "ERROR: Backup file is too small (${file_size} bytes)" "ERROR"
        return 1
    fi
    
    # Check if file can be extracted (basic tar integrity)
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        log_message "ERROR: Backup archive is corrupted or invalid" "ERROR"
        return 1
    fi
    
    # Check for essential components in the backup
    local expected_files=(
        "docker-compose.yml"
        "conf/config.yml"
        "docker_volumes/"
    )
    
    for expected_file in "${expected_files[@]}"; do
        if ! tar -tzf "$backup_file" 2>/dev/null | grep -q "$expected_file"; then
            log_message "WARNING: Expected file/directory not found in backup: $expected_file" "WARNING"
        fi
    done
    
    # Check for database backup in archive
    if ! tar -tzf "$backup_file" 2>/dev/null | grep -q "db_backup_.*\.sql"; then
        log_message "ERROR: Database backup not found in archive" "ERROR"
        return 1
    fi
    
    # Create checksum for integrity verification
    create_checksum "$backup_file"
    
    local backup_size_human
    backup_size_human=$(du -h "$backup_file" | cut -f1)
    log_message "✅ Backup verification passed (size: ${backup_size_human})" "SUCCESS"
    return 0
}

# Helper function: Verify backup integrity (legacy compatibility)
verify_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_message "Backup file not found: $backup_file" "ERROR"
        return 1
    fi
    
    log_message "Verifying backup integrity: $backup_file"
    
    # Use enhanced verification if available
    if command -v verify_backup_integrity >/dev/null 2>&1; then
        verify_backup_integrity "$backup_file"
        return $?
    fi
    
    # Fallback: Check if file can be extracted
    if tar -tzf "$backup_file" >/dev/null 2>&1; then
        log_message "Backup file integrity verified" "SUCCESS"
        return 0
    else
        log_message "ERROR: Backup file is corrupted" "ERROR"
        return 1
    fi
}