#!/bin/bash
# Gitignore-based Sync Utilities
# Uses .gitignore patterns as rsync exclusion templates to prevent syncing build artifacts

# Convert .gitignore patterns to rsync exclude patterns
convert_gitignore_to_rsync_excludes() {
    local gitignore_file="$1"
    local output_file="$2"
    
    if [[ ! -f "$gitignore_file" ]]; then
        echo "Warning: .gitignore not found at $gitignore_file"
        return 1
    fi
    
    # Process .gitignore and convert to rsync exclude patterns
    grep -v '^#' "$gitignore_file" | grep -v '^$' | while read -r pattern; do
        # Remove leading/trailing whitespace
        pattern=$(echo "$pattern" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Skip empty lines
        [[ -z "$pattern" ]] && continue
        
        # Convert gitignore patterns to rsync exclude patterns
        case "$pattern" in
            # Directory patterns (ending with /)
            */)
                echo "--exclude=${pattern%/}"
                echo "--exclude=${pattern%/}/"
                ;;
            # Leading slash patterns (absolute paths)
            /*)
                echo "--exclude=${pattern#/}"
                ;;
            # Wildcard patterns
            *.*)
                echo "--exclude=$pattern"
                ;;
            # Everything else
            *)
                echo "--exclude=$pattern"
                echo "--exclude=$pattern/"
                ;;
        esac
    done > "$output_file"
}

# Generate rsync exclude arguments from .gitignore
get_gitignore_rsync_excludes() {
    local project_dir="${1:-$(pwd)}"
    local gitignore_file="$project_dir/.gitignore"
    local temp_excludes=$(mktemp)
    
    if [[ -f "$gitignore_file" ]]; then
        convert_gitignore_to_rsync_excludes "$gitignore_file" "$temp_excludes"
        cat "$temp_excludes"
        rm -f "$temp_excludes"
    else
        # Fallback to basic excludes if no .gitignore
        echo "--exclude=node_modules"
        echo "--exclude=build"
        echo "--exclude=dist"
        echo "--exclude=.git"
        echo "--exclude=*.log"
        echo "--exclude=.DS_Store"
    fi
}

# Smart sync using .gitignore patterns
gitignore_aware_sync() {
    local source_dir="$1"
    local dest_dir="$2"
    local additional_excludes="${3:-}"
    
    if [[ ! -d "$source_dir" ]]; then
        echo "Error: Source directory $source_dir does not exist"
        return 1
    fi
    
    echo " Generating rsync excludes from .gitignore..."
    
    # Get excludes from .gitignore
    local excludes_file=$(mktemp)
    get_gitignore_rsync_excludes "$source_dir" > "$excludes_file"
    
    # Add any additional excludes
    if [[ -n "$additional_excludes" ]]; then
        echo "$additional_excludes" | tr ' ' '\n' | while read -r exclude; do
            [[ -n "$exclude" ]] && echo "--exclude=$exclude"
        done >> "$excludes_file"
    fi
    
    # Critical: Add generated files that shouldn't sync (even if not in .gitignore)
    cat >> "$excludes_file" << EOF
--exclude=main.*
--exclude=*.js.map
--exclude=*.css.map
--exclude=config.yml
--exclude=*.env
--exclude=.env.*
EOF
    
    echo "📋 Rsync exclusions ($(wc -l < "$excludes_file") patterns):"
    head -10 "$excludes_file" | sed 's/^/  /'
    [[ $(wc -l < "$excludes_file") -gt 10 ]] && echo "  ... and $(($(wc -l < "$excludes_file") - 10)) more"
    
    # Perform the sync with all exclusions
    echo " Starting gitignore-aware sync: $source_dir -> $dest_dir"
    
    # Use --files-from approach for cleaner handling of many excludes
    local rsync_cmd="rsync -av --delete"
    
    # Add all excludes to the command
    while read -r exclude_arg; do
        [[ -n "$exclude_arg" ]] && rsync_cmd="$rsync_cmd $exclude_arg"
    done < "$excludes_file"
    
    rsync_cmd="$rsync_cmd $source_dir/ $dest_dir/"
    
    echo "📡 Executing: $rsync_cmd"
    eval "$rsync_cmd"
    local sync_result=$?
    
    # Cleanup
    rm -f "$excludes_file"
    
    if [[ $sync_result -eq 0 ]]; then
        echo "[+] Gitignore-aware sync completed successfully"
    else
        echo "[-] Sync failed with exit code $sync_result"
        return $sync_result
    fi
}

# Enhanced sync for specific services
gitignore_service_sync() {
    local service="$1"
    local project_dir="${2:-$(pwd)}"
    local install_dir="${INSTALL_DIR:-$HOME/.sting-ce}"
    
    case "$service" in
        frontend)
            echo "🎨 Frontend gitignore-aware sync..."
            gitignore_aware_sync "$project_dir/frontend" "$install_dir/frontend" \
                "package-lock.json yarn.lock .next .cache"
            ;;
        app|backend)
            echo "🐍 Backend gitignore-aware sync..."
            gitignore_aware_sync "$project_dir/app" "$install_dir/app" \
                "__pycache__ *.pyc *.pyo .pytest_cache"
            ;;
        chatbot)
            echo "🤖 Chatbot gitignore-aware sync..."
            gitignore_aware_sync "$project_dir/chatbot" "$install_dir/chatbot" \
                "__pycache__ *.pyc *.pyo"
            ;;
        knowledge)
            echo "🧠 Knowledge service gitignore-aware sync..."
            gitignore_aware_sync "$project_dir/knowledge_service" "$install_dir/knowledge_service" \
                "__pycache__ *.pyc *.pyo"
            ;;
        *)
            echo "[!] Service $service not recognized, using generic sync..."
            gitignore_aware_sync "$project_dir/$service" "$install_dir/$service"
            ;;
    esac
}

# Export functions for use in other scripts
export -f convert_gitignore_to_rsync_excludes
export -f get_gitignore_rsync_excludes
export -f gitignore_aware_sync
export -f gitignore_service_sync