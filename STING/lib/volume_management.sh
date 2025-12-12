#!/bin/bash
# Volume Management Module for STING CE
# Provides safe volume management with data classification
# Compatible with bash 3.2+ (macOS default)

# Volume type lookup function - compatible with bash 3.2+
get_volume_type() {
    local volume="$1"
    case "$volume" in
        postgres_data) echo "database" ;;
        vault_data|vault_file) echo "secrets" ;;
        config_data) echo "config" ;;
        vault_logs|sting_logs) echo "logs" ;;
        sting-ce_chroma_data|sting-ce_redis_data|sting-ce_mailpit_data) echo "service" ;;
        sting-ce_temp) echo "temp" ;;
        *) echo "unknown" ;;
    esac
}

# Volume description lookup function
get_volume_description() {
    local volume="$1"
    case "$volume" in
        postgres_data) echo "PostgreSQL database - Contains all user data, identities, and app data" ;;
        vault_data) echo "HashiCorp Vault data - Contains encrypted secrets and API keys" ;;
        vault_file) echo "Vault file storage - Additional vault data storage" ;;
        vault_logs) echo "Vault logs - Audit and operational logs" ;;
        config_data) echo "Configuration data - System configs and certificates" ;;
        sting_logs) echo "STING logs - Application and service logs" ;;
        sting-ce_chroma_data) echo "Vector database - Document embeddings (expensive to regenerate)" ;;
        sting-ce_redis_data) echo "Redis cache - Session data and temporary storage" ;;
        sting-ce_mailpit_data) echo "Email testing data - Development email messages" ;;
        sting-ce_temp) echo "Temporary storage - Safe to remove" ;;
        *) echo "Unknown volume" ;;
    esac
}

# Volume color lookup function
get_volume_color() {
    local type="$1"
    case "$type" in
        database) echo "31" ;;  # Red
        secrets) echo "33" ;;   # Yellow  
        config) echo "36" ;;    # Cyan
        logs) echo "32" ;;      # Green
        service) echo "35" ;;   # Magenta
        temp) echo "37" ;;      # White
        *) echo "37" ;;         # White default
    esac
}

list_volumes() {
    local show_all=${1:-false}
    
    log_message "📊 STING Volume Analysis" "INFO"
    echo ""
    
    # Get all Docker volumes
    local all_volumes=$(docker volume ls -q)
    local sting_volumes=""
    
    # Find STING-related volumes
    for volume in $all_volumes; do
        if echo "$volume" | grep -E "(sting|postgres|vault|config)" >/dev/null || [ "$(get_volume_type "$volume")" != "unknown" ]; then
            sting_volumes="$sting_volumes $volume"
        fi
    done
    
    if [ -z "$sting_volumes" ]; then
        echo "[+] No STING volumes found"
        return 0
    fi
    
    # Group volumes by type using temporary files (bash 3.2 compatible)
    local tmpdir="$(mktemp -d)"
    for volume in $sting_volumes; do
        local type=$(get_volume_type "$volume")
        echo "$volume" >> "$tmpdir/$type"
    done
    
    # Display volumes by safety category
    for type in database secrets config service logs temp unknown; do
        if [ -f "$tmpdir/$type" ]; then
            local color=$(get_volume_color "$type")
            echo -e "\\033[${color}m=== $(echo $type | tr '[:lower:]' '[:upper:]') VOLUMES ===\\033[0m"
            
            while read volume; do
                [ -z "$volume" ] && continue
                local size=$(docker system df -v --format "table {{.Name}}\t{{.Size}}" 2>/dev/null | grep "^$volume" | awk '{print $2}' || echo "unknown")
                local desc=$(get_volume_description "$volume")
                
                printf "   %-20s %8s - %s\\n" "$volume" "($size)" "$desc"
            done < "$tmpdir/$type"
            echo ""
        fi
    done
    
    # Cleanup
    rm -rf "$tmpdir"
}

purge_volumes() {
    local purge_type="$1"
    local confirm="$2"
    
    case "$purge_type" in
        "database"|"db")
            purge_volumes_by_type "database" "$confirm"
            ;;
        "config")
            purge_volumes_by_type "config" "$confirm"
            ;;
        "logs")
            purge_volumes_by_type "logs" "$confirm"
            ;;
        "service")
            purge_volumes_by_type "service" "$confirm"
            ;;
        "temp")
            purge_volumes_by_type "temp" "$confirm"
            ;;
        "safe")
            log_message "🧹 Purging safe volumes (logs, temp)" "INFO"
            purge_volumes_by_type "logs" "$confirm"
            purge_volumes_by_type "temp" "$confirm"
            ;;
        "all"|"nuclear")
            if [ "$confirm" != "--force" ]; then
                echo "🚨 DANGER: This will delete ALL STING data!"
                echo "   - All databases (users, identities, application data)"
                echo "   - All secrets (API keys, certificates)" 
                echo "   - All service data (embeddings, cache)"
                echo "   - All configurations"
                echo ""
                echo "This action is IRREVERSIBLE!"
                echo ""
                echo "To confirm, run: $0 volumes purge all --force"
                return 1
            fi
            
            log_message "☢️  NUCLEAR PURGE: Removing ALL STING volumes" "WARNING"
            for type in database secrets config service logs temp unknown; do
                purge_volumes_by_type "$type" "--force"
            done
            ;;
        *)
            log_message "[-] Invalid purge type: $purge_type" "ERROR"
            echo "Valid types: database, config, logs, service, temp, safe, all"
            echo "Example: $0 volumes purge database"
            return 1
            ;;
    esac
}

purge_volumes_by_type() {
    local target_type="$1"
    local confirm="$2"
    
    local volumes_to_remove=""
    
    # Find volumes of the specified type
    local all_volumes=$(docker volume ls -q)
    for volume in $all_volumes; do
        local type=$(get_volume_type "$volume")
        if [ "$type" = "$target_type" ] || ([ "$target_type" = "unknown" ] && [ "$type" = "unknown" ] && echo "$volume" | grep -E "(sting|postgres|vault|config)" >/dev/null); then
            volumes_to_remove="$volumes_to_remove $volume"
        fi
    done
    
    if [ -z "$volumes_to_remove" ]; then
        log_message "[+] No $target_type volumes found" "INFO"
        return 0
    fi
    
    # Show what will be removed
    local color=$(get_volume_color "$target_type")
    echo -e "\\033[${color}m🗑️  Removing $target_type volumes:\\033[0m"
    for volume in $volumes_to_remove; do
        local desc=$(get_volume_description "$volume")
        echo "    $volume - $desc"
    done
    echo ""
    
    # Require confirmation for dangerous types
    if [[ "$target_type" =~ ^(database|secrets)$ ]] && [ "$confirm" != "--force" ]; then
        echo "[!]  WARNING: Removing $target_type volumes will cause data loss!"
        echo "To confirm, add --force: $0 volumes purge $target_type --force"
        return 1
    fi
    
    # Remove volumes
    for volume in $volumes_to_remove; do
        if docker volume inspect "$volume" >/dev/null 2>&1; then
            log_message "Removing volume: $volume" "INFO"
            if docker volume rm "$volume" 2>/dev/null; then
                echo "[+] Removed: $volume"
            else
                echo "[-] Failed to remove: $volume (may be in use)"
            fi
        else
            echo "[!]  Volume not found: $volume"
        fi
    done
}

backup_volumes() {
    local backup_dir="${1:-$HOME/.sting-ce/backups/$(date +%Y%m%d_%H%M%S)}"
    
    log_message "💾 Creating volume backups in: $backup_dir" "INFO"
    mkdir -p "$backup_dir"
    
    # Get all STING volumes
    local all_volumes=$(docker volume ls -q)
    local backed_up=0
    
    for volume in $all_volumes; do
        if echo "$volume" | grep -E "(sting|postgres|vault|config)" >/dev/null || [ "$(get_volume_type "$volume")" != "unknown" ]; then
            local type=$(get_volume_type "$volume")
            
            # Skip temp volumes
            if [ "$type" = "temp" ]; then
                continue
            fi
            
            log_message "Backing up volume: $volume ($type)" "INFO"
            
            # Create tar backup of volume
            if docker run --rm -v "$volume":/data -v "$backup_dir":/backup alpine tar czf "/backup/${volume}.tar.gz" -C /data .; then
                echo "[+] Backed up: $volume"
                ((backed_up++))
            else
                echo "[-] Failed to backup: $volume"
            fi
        fi
    done
    
    # Create backup manifest
    cat > "$backup_dir/manifest.txt" <<EOF
STING Volume Backup
Created: $(date)
Total volumes backed up: $backed_up

Volume Information:
$(list_volumes)

Restore Instructions:
1. Create volume: docker volume create <volume_name>
2. Restore data: docker run --rm -v <volume_name>:/data -v $(pwd):/backup alpine tar xzf /backup/<volume_name>.tar.gz -C /data
EOF
    
    log_message "[+] Backup complete: $backed_up volumes backed up to $backup_dir" "INFO"
    echo "📄 Backup manifest: $backup_dir/manifest.txt"
}

volume_usage() {
    echo "Volume Management Commands:"
    echo ""
    echo "  $0 volumes list                    - List all STING volumes with classification"
    echo "  $0 volumes purge <type>            - Remove volumes by type"
    echo "  $0 volumes backup [dir]            - Backup volumes to directory"
    echo ""
    echo "Volume Types:"
    echo "  database    - Database volumes (DANGEROUS - contains all user data)"
    echo "  secrets     - Vault and secret storage (DANGEROUS - contains API keys)"
    echo "  config      - Configuration data (MEDIUM RISK)"
    echo "  service     - Service data like embeddings (EXPENSIVE to regenerate)"
    echo "  logs        - Log files (SAFE to remove)"
    echo "  temp        - Temporary data (SAFE to remove)"
    echo "  safe        - Logs + temp volumes (SAFE combination)"
    echo "  all         - ALL volumes (NUCLEAR OPTION - requires --force)"
    echo ""
    echo "Examples:"
    echo "  $0 volumes list                    # Show all volumes"
    echo "  $0 volumes purge safe              # Remove logs and temp (safe)"
    echo "  $0 volumes purge config            # Remove config (medium risk)"
    echo "  $0 volumes purge database --force  # Remove database (DANGEROUS)"
    echo "  $0 volumes backup                  # Backup all volumes"
    echo "  $0 volumes purge all --force       # Nuclear option"
}

# Main volume management function
manage_volumes() {
    local action="$1"
    shift
    
    case "$action" in
        "list"|"ls")
            list_volumes "$@"
            ;;
        "purge"|"remove"|"rm")
            purge_volumes "$@"
            ;;
        "backup")
            backup_volumes "$@"
            ;;
        "help"|"--help"|"")
            volume_usage
            ;;
        *)
            log_message "[-] Unknown volume action: $action" "ERROR"
            volume_usage
            return 1
            ;;
    esac
}