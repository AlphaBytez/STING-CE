#!/bin/bash
# Infrastructure Protection Module
# Prevents accidental data loss during updates and reinstalls

# Define infrastructure services that should not be updated/restarted
INFRASTRUCTURE_SERVICES=(
    "db"
    "vault" 
    "redis"
    "mailpit"
    "chroma"
)

# Define data volumes that should be preserved
PROTECTED_VOLUMES=(
    "postgres_data"
    "vault-data"
    "vault-logs"
    "vault-file"
    "redis_data"
    "chroma_data"
    "mailpit_data"
)

# Check if a service is infrastructure
is_infrastructure_service() {
    local service=$1
    for infra in "${INFRASTRUCTURE_SERVICES[@]}"; do
        if [[ "$service" == "$infra" ]]; then
            return 0
        fi
    done
    return 1
}

# Check if a volume should be protected
is_protected_volume() {
    local volume=$1
    for protected in "${PROTECTED_VOLUMES[@]}"; do
        if [[ "$volume" =~ $protected ]]; then
            return 0
        fi
    done
    return 1
}

# Safe update function that skips infrastructure
safe_update_service() {
    local service=$1
    
    if is_infrastructure_service "$service"; then
        log "INFO" "Skipping infrastructure service: $service (data preserved)"
        return 0
    fi
    
    # Proceed with normal update for application services
    return 1
}

# Filter volumes for safe removal (exclude protected data volumes)
get_safe_volumes_to_remove() {
    local all_volumes=$(docker volume ls -q | grep -E "(sting|kratos|chroma|knowledge|postgres)")
    local safe_volumes=""
    
    for volume in $all_volumes; do
        if ! is_protected_volume "$volume"; then
            safe_volumes="$safe_volumes $volume"
        else
            log "INFO" "Preserving data volume: $volume"
        fi
    done
    
    echo "$safe_volumes"
}

# Backup critical data before any destructive operation
backup_critical_data() {
    local backup_dir="${BACKUP_DIR:-/tmp/sting_backup_$(date +%Y%m%d_%H%M%S)}"
    mkdir -p "$backup_dir"
    
    log "INFO" "Backing up critical data to $backup_dir..."
    
    # Backup database
    if docker ps -q -f name=sting-ce-db | grep -q .; then
        docker exec sting-ce-db pg_dump -U postgres sting_app > "$backup_dir/database_backup.sql" 2>/dev/null && \
            log "SUCCESS" "Database backed up successfully" || \
            log "WARNING" "Database backup failed"
    fi
    
    # Backup vault data
    if docker ps -q -f name=sting-ce-vault | grep -q .; then
        docker exec sting-ce-vault vault kv list secret/ > "$backup_dir/vault_keys.txt" 2>/dev/null && \
            log "SUCCESS" "Vault keys listed successfully" || \
            log "WARNING" "Vault backup failed"
    fi
    
    echo "$backup_dir"
}

# Restore data from backup
restore_critical_data() {
    local backup_dir=$1
    
    if [[ ! -d "$backup_dir" ]]; then
        log "ERROR" "Backup directory not found: $backup_dir"
        return 1
    fi
    
    # Restore database
    if [[ -f "$backup_dir/database_backup.sql" ]]; then
        log "INFO" "Restoring database from backup..."
        docker exec -i sting-ce-db psql -U postgres sting_app < "$backup_dir/database_backup.sql" && \
            log "SUCCESS" "Database restored successfully" || \
            log "ERROR" "Database restore failed"
    fi
}

# Export functions for use in other scripts
export -f is_infrastructure_service
export -f is_protected_volume
export -f safe_update_service
export -f get_safe_volumes_to_remove
export -f backup_critical_data
export -f restore_critical_data