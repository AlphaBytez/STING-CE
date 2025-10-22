#!/bin/bash
# backup_utils.sh - Lean backup utilities for STING

# Create a lean backup of essential STING files
create_lean_backup() {
    local install_dir="${1:-$HOME/.sting-ce}"
    local backup_dir="${2:-${install_dir}.backup.$(date +%Y%m%d_%H%M%S)}"
    
    log_message "Creating lean backup of essential files..."
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Essential directories and files to backup
    local essential_items=(
        # Configuration files
        "env"                    # Environment variables
        "conf/secrets"           # Secrets (API keys, tokens)
        "conf/*.yml"             # YAML configs
        "conf/*.yaml"            
        "conf/*.json"            # JSON configs
        
        # SSL certificates
        "certs"                  # SSL certificates
        
        # User data
        "data"                   # User data directory (if exists)
        
        # Kratos configuration
        "kratos/kratos.yml"      # Generated Kratos config
        "kratos/identity.schema.json"
        
        # Installation state
        ".env"                   # Main environment file
        "manage_sting.sh"        # Management script
        
        # Docker volumes list (for reference)
        "docker_volumes.txt"     # We'll create this
    )
    
    # Create docker volumes list for reference
    docker volume ls --format "{{.Name}}" | grep -E "(sting|kratos)" > "$backup_dir/docker_volumes.txt" 2>/dev/null || true
    
    # Backup each essential item
    for item in "${essential_items[@]}"; do
        if [[ "$item" == *"*"* ]]; then
            # Handle wildcards
            local base_dir=$(dirname "$item")
            local pattern=$(basename "$item")
            if [ -d "$install_dir/$base_dir" ]; then
                mkdir -p "$backup_dir/$base_dir"
                find "$install_dir/$base_dir" -maxdepth 1 -name "$pattern" -exec cp -p {} "$backup_dir/$base_dir/" \; 2>/dev/null || true
            fi
        elif [ -e "$install_dir/$item" ]; then
            # Create parent directory in backup
            local parent_dir=$(dirname "$item")
            [ "$parent_dir" != "." ] && mkdir -p "$backup_dir/$parent_dir"
            
            # Copy item preserving permissions
            cp -rp "$install_dir/$item" "$backup_dir/$item" 2>/dev/null || {
                log_message "Warning: Could not backup $item" "WARNING"
            }
        fi
    done
    
    # Save backup metadata
    cat > "$backup_dir/backup_metadata.txt" << EOF
Backup created: $(date)
STING version: $(cd "$install_dir" && git describe --tags 2>/dev/null || echo "unknown")
Backup type: lean
Original location: $install_dir
EOF
    
    # Calculate backup size
    local backup_size=$(du -sh "$backup_dir" | cut -f1)
    log_message "Lean backup created at: $backup_dir (size: $backup_size)"
    
    return 0
}

# Restore from lean backup
restore_lean_backup() {
    local backup_dir="$1"
    local install_dir="${2:-$HOME/.sting-ce}"
    
    if [ ! -d "$backup_dir" ]; then
        log_message "Backup directory not found: $backup_dir" "ERROR"
        return 1
    fi
    
    log_message "Restoring from lean backup..."
    
    # Restore essential items
    for item in env conf/secrets certs data kratos .env manage_sting.sh; do
        if [ -e "$backup_dir/$item" ]; then
            # Create parent directory if needed
            local parent_dir=$(dirname "$item")
            [ "$parent_dir" != "." ] && mkdir -p "$install_dir/$parent_dir"
            
            # Restore item
            rsync -a "$backup_dir/$item" "$install_dir/$parent_dir/" || {
                log_message "Warning: Could not restore $item" "WARNING"
            }
        fi
    done
    
    # Restore execute permissions on scripts
    [ -f "$install_dir/manage_sting.sh" ] && chmod +x "$install_dir/manage_sting.sh"
    
    log_message "Lean backup restored successfully"
    return 0
}

# List what would be backed up
list_backup_contents() {
    local install_dir="${1:-$HOME/.sting-ce}"
    
    echo "Essential items that will be backed up:"
    echo "======================================="
    
    # Check sizes of essential directories
    for dir in env conf/secrets certs data kratos; do
        if [ -d "$install_dir/$dir" ]; then
            local size=$(du -sh "$install_dir/$dir" 2>/dev/null | cut -f1)
            echo "  $dir/ ($size)"
        fi
    done
    
    # Check essential files
    for file in .env manage_sting.sh; do
        if [ -f "$install_dir/$file" ]; then
            local size=$(ls -lh "$install_dir/$file" 2>/dev/null | awk '{print $5}')
            echo "  $file ($size)"
        fi
    done
    
    echo ""
    echo "Items NOT backed up (can be regenerated):"
    echo "========================================="
    echo "  - Application code (app/, frontend/, etc.)"
    echo "  - Documentation (docs/)"
    echo "  - Test files (tests/)"
    echo "  - Virtual environments (.venv/)"
    echo "  - Archive directories"
    echo "  - Log files"
    echo ""
    
    # Estimate total backup size
    local total_size=0
    for dir in env conf certs data kratos; do
        if [ -d "$install_dir/$dir" ]; then
            local dir_size=$(du -sk "$install_dir/$dir" 2>/dev/null | cut -f1)
            total_size=$((total_size + dir_size))
        fi
    done
    
    echo "Estimated backup size: $((total_size / 1024))MB"
}