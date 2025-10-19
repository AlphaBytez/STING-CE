#!/bin/bash
# STING Management Script - File Operations Module
# This module provides file and directory management utilities

# Source required dependencies
if [[ -z "$SOURCE_DIR" ]]; then
    echo "ERROR: SOURCE_DIR not set. This module must be sourced from manage_sting.sh" >&2
    return 1
fi

# Source logging module if not already loaded
if ! declare -f log_message >/dev/null 2>&1; then
    if [[ -f "$SOURCE_DIR/lib/logging.sh" ]]; then
        source "$SOURCE_DIR/lib/logging.sh"
    else
        echo "ERROR: logging.sh module not found" >&2
        return 1
    fi
fi

# Required environment variables (set in main script)
# INSTALL_DIR - Installation directory
# CONFIG_DIR - Configuration directory  
# SUDO_USER - User for file ownership

# Function to clean up after failed installation
cleanup_failed_installation() {
    log_message "Cleaning up after failed installation..."
    sudo rm -rf ${INSTALL_DIR}
    sudo rm -f /usr/local/bin/msting
    log_message "Cleanup complete. System returned to pre-installation state."
}

# Function to copy files from source to installation directory with comprehensive exclusions
copy_files_to_install_dir() {
    local source_dir="$1"
    local dest_dir="$2"
    local delete_flag="${3:-}"
    
    log_message "Copying files from $source_dir to $dest_dir..."
    
    # Check if source directory exists
    if [ ! -d "$source_dir" ]; then
        log_message "ERROR: Source directory '$source_dir' does not exist."
        return 1
    fi

    # Create the destination directory if it doesn't exist
    # Try without sudo first, then with sudo if needed
    if ! mkdir -p "$dest_dir" 2>/dev/null; then
        if ! sudo mkdir -p "$dest_dir"; then
            log_message "ERROR: Failed to create destination directory '$dest_dir'."
            return 1
        fi
    fi
    
    # Verify destination directory exists and is accessible
    if [ ! -d "$dest_dir" ]; then
        log_message "ERROR: Destination directory '$dest_dir' was not created successfully."
        return 1
    fi
    
    # Build rsync command with standard excludes
    # Check if we need sudo by testing write access
    local rsync_cmd="rsync -a"
    if [ ! -w "$dest_dir" ]; then
        # Use -n flag to avoid password prompts (sudo keepalive should handle this)
        rsync_cmd="sudo -n rsync -a"
    fi
    
    # Add delete flag only if specified (for full reinstall)
    if [ "$delete_flag" = "--delete" ]; then
        rsync_cmd="$rsync_cmd --delete"
        log_message "Using --delete flag: will remove files in destination that don't exist in source"
    else
        log_message "Using efficient sync: will only update changed files"
    fi
    
    # Change to root directory to avoid getcwd() issues with sudo rsync
    # This prevents "No such file or directory" errors when the current directory
    # has restrictive permissions or doesn't exist from rsync's perspective
    pushd / >/dev/null 2>&1 || true
    
    # Copy all files and directories, excluding certain patterns
    if ! $rsync_cmd \
                    --exclude='venv' \
                    --exclude='.venv' \
                    --exclude='.git' \
                    --exclude='node_modules' \
                    --exclude='.gitignore' \
                    --exclude='__pycache__' \
                    --exclude='*.pyc' \
                    --exclude='*.pyo' \
                    --exclude='*.pyd' \
                    --exclude='.DS_Store' \
                    --exclude='/models/' \
                    --exclude='/llm_models' \
                    --exclude='/llm-models' \
                    --exclude='llm_service/models/*' \
                    --exclude='*.log' \
                    --exclude='build' \
                    --exclude='dist' \
                    --exclude='/venv/' \
                    --exclude='*.egg-info' \
                    --exclude='/env/*.env' \
                    --exclude='/conf/*.env' \
                    --exclude='/kratos/kratos.yml' \
                    "$source_dir/" "$dest_dir/"; then
        log_message "ERROR: Failed to copy files to destination directory."
        popd >/dev/null 2>&1 || true
        return 1
    fi
    
    # Return to previous directory
    popd >/dev/null 2>&1 || true
    
    # Set correct ownership for the destination directory
    # Determine the target user (current user if not using sudo, or SUDO_USER if using sudo)
    local target_user="${SUDO_USER:-$USER}"
    local target_group=$(id -gn "$target_user" 2>/dev/null || echo "$target_user")

    log_message "Setting ownership to $target_user:$target_group..."

    # Execute chown with retries and proper error handling
    # On macOS, this operation can be slow and sudo cache might expire
    local max_retries=2
    local retry_count=0
    local chown_success=false

    while [ $retry_count -lt $max_retries ] && [ "$chown_success" = "false" ]; do
        if sudo -n chown -R "$target_user:$target_group" "$dest_dir" 2>/dev/null; then
            chown_success=true
            log_message "✓ Ownership set successfully"
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_message "Ownership change failed (attempt $retry_count/$max_retries), retrying..."
                sleep 2
            fi
        fi
    done

    if [ "$chown_success" = "false" ]; then
        log_message "WARNING: Failed to set ownership after $max_retries attempts (non-critical)"
    fi

    # CRITICAL: Ensure all shell scripts have execute permissions
    # This must happen AFTER chown to avoid permission stripping
    log_message "Setting execute permissions on shell scripts..."
    if ! find "$dest_dir" -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null; then
        # Retry with sudo if needed
        sudo find "$dest_dir" -name "*.sh" -type f -exec chmod +x {} \; || {
            log_message "WARNING: Some shell scripts may not have execute permissions"
        }
    fi

    # Specifically ensure manage_sting.sh is executable (double-check)
    if [ -f "$dest_dir/manage_sting.sh" ]; then
        chmod +x "$dest_dir/manage_sting.sh" 2>/dev/null || sudo chmod +x "$dest_dir/manage_sting.sh" || {
            log_message "ERROR: Failed to set execute permissions on manage_sting.sh"
            return 1
        }
        log_message "✓ manage_sting.sh is executable"
    else
        log_message "ERROR: manage_sting.sh not found at $dest_dir/manage_sting.sh"
        return 1
    fi

    log_message "Files copied successfully."

    # Verify critical directories were copied
    if [ -d "$source_dir/app/models" ] && [ ! -d "$dest_dir/app/models" ]; then
        log_message "ERROR: app/models directory was not copied!" "ERROR"
        log_message "ERROR: Source has models: $source_dir/app/models" "ERROR"
        log_message "ERROR: Destination missing models: $dest_dir/app/models" "ERROR"
        return 1
    fi

    # Verify models/__init__.py exists
    if [ -f "$source_dir/app/models/__init__.py" ] && [ ! -f "$dest_dir/app/models/__init__.py" ]; then
        log_message "ERROR: app/models/__init__.py was not copied!" "ERROR"
        return 1
    fi

    if [ -d "$dest_dir/app/models" ]; then
        local model_count=$(find "$dest_dir/app/models" -name "*.py" -type f 2>/dev/null | wc -l)
        log_message "✓ Verified app/models directory copied ($model_count Python files)"
    fi

    # Ensure the env directory exists (so touch/chmod on vault.env etc. cannot fail)
    mkdir -p "${dest_dir}/env"
    chmod 755 "${dest_dir}/env" || true
    return 0
}

# Function to symlink or copy the .env file to main component folders
symlink_env_to_main_components() {
    local env_file="${INSTALL_DIR}/conf/.env"
    local main_components=("frontend" "app" "authentication")  # Add more components if needed

    for component in "${main_components[@]}"; do
        local component_env="${INSTALL_DIR}/${component}/.env"

        # If .env doesn't already exist in the component folder, create a symlink
        if [ ! -L "$component_env" ] || [ ! -f "$component_env" ]; then
            log_message "Creating symlink for .env in $component..."
            ln -sf "$env_file" "$component_env"
        else
            log_message ".env symlink already exists in $component."
        fi
    done
}

# Function to ensure a directory exists with proper permissions
ensure_directory() {
    local dir_path="$1"
    local permissions="${2:-755}"
    local owner="${3:-$SUDO_USER:$SUDO_USER}"
    
    if [ ! -d "$dir_path" ]; then
        log_message "Creating directory: $dir_path"
        if ! sudo mkdir -p "$dir_path"; then
            log_message "ERROR: Failed to create directory '$dir_path'."
            return 1
        fi
    fi
    
    # Set permissions if specified
    if [ -n "$permissions" ]; then
        sudo chmod "$permissions" "$dir_path"
    fi
    
    # Set ownership if specified and not empty
    if [ -n "$owner" ] && [ "$owner" != ":" ]; then
        sudo chown "$owner" "$dir_path"
    fi
    
    return 0
}

# Function to safely remove directory contents
safe_remove_directory() {
    local dir_path="$1"
    local force="${2:-false}"
    
    if [ ! -d "$dir_path" ]; then
        log_message "Directory does not exist: $dir_path"
        return 0
    fi
    
    if [ "$force" = "true" ]; then
        log_message "Force removing directory: $dir_path"
        sudo rm -rf "$dir_path"
    else
        log_message "Safely removing directory contents: $dir_path"
        # Only remove if directory is not empty and within expected paths
        if [[ "$dir_path" =~ ^(/opt/sting-ce|/home/.*/.sting-ce|$HOME/.sting-ce) ]]; then
            sudo rm -rf "$dir_path"
        else
            log_message "ERROR: Refusing to remove directory outside expected paths: $dir_path"
            return 1
        fi
    fi
    
    return 0
}

# Function to check if config needs regeneration
check_config_changes() {
    local project_dir="${SOURCE_DIR:-$(pwd)}"
    local config_changed=false
    local loader_changed=false
    
    # Check if config.yml has changed
    if ! diff -q "$project_dir/conf/config.yml" "$INSTALL_DIR/conf/config.yml" >/dev/null 2>&1; then
        log_message "config.yml has changed"
        config_changed=true
    fi
    
    # Check if config_loader.py has changed
    if ! diff -q "$project_dir/conf/config_loader.py" "$INSTALL_DIR/conf/config_loader.py" >/dev/null 2>&1; then
        log_message "config_loader.py has changed"
        loader_changed=true
    fi
    
    if [ "$config_changed" = "true" ] || [ "$loader_changed" = "true" ]; then
        log_message "Configuration changes detected. Regenerating environment files..."
        return 0
    else
        return 1
    fi
}

# Function to check for structural changes that require full reinstall
check_structural_changes() {
    local project_dir="${SOURCE_DIR:-$(pwd)}"
    local structural_changes=()
    local dependency_changes=()
    local force_reinstall=false
    
    log_message "Checking for structural changes that may require full reinstall..."
    
    # Check docker-compose.yml changes
    if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
        if ! diff -q "$project_dir/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml" >/dev/null 2>&1; then
            structural_changes+=("docker-compose.yml")
            # Check if it's a major structural change (new services, networks, volumes)
            if diff "$project_dir/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml" | grep -E "^\+.*services:|^\+.*networks:|^\+.*volumes:" >/dev/null 2>&1; then
                force_reinstall=true
            fi
        fi
    fi
    
    # Check Python requirements files
    local python_services=("app" "chatbot" "llm_service" "external_ai_service" "messaging_service" "knowledge_service")
    for service in "${python_services[@]}"; do
        local req_file="$project_dir/$service/requirements.txt"
        local installed_req_file="$INSTALL_DIR/$service/requirements.txt"
        
        if [ -f "$req_file" ] && [ -f "$installed_req_file" ]; then
            if ! diff -q "$req_file" "$installed_req_file" >/dev/null 2>&1; then
                dependency_changes+=("$service/requirements.txt")
            fi
        elif [ -f "$req_file" ] && [ ! -f "$installed_req_file" ]; then
            dependency_changes+=("$service/requirements.txt (new)")
            force_reinstall=true
        fi
    done
    
    # Check package.json for frontend
    if [ -f "$project_dir/frontend/package.json" ] && [ -f "$INSTALL_DIR/frontend/package.json" ]; then
        if ! diff -q "$project_dir/frontend/package.json" "$INSTALL_DIR/frontend/package.json" >/dev/null 2>&1; then
            dependency_changes+=("frontend/package.json")
        fi
    fi
    
    # Check Dockerfile changes
    local dockerfiles=($(find "$project_dir" -name "Dockerfile*" -type f))
    for dockerfile in "${dockerfiles[@]}"; do
        local rel_path="${dockerfile#$project_dir/}"
        local installed_dockerfile="$INSTALL_DIR/$rel_path"
        
        if [ -f "$installed_dockerfile" ]; then
            if ! diff -q "$dockerfile" "$installed_dockerfile" >/dev/null 2>&1; then
                structural_changes+=("$rel_path")
            fi
        fi
    done
    
    # Report findings
    if [ ${#structural_changes[@]} -gt 0 ] || [ ${#dependency_changes[@]} -gt 0 ]; then
        log_message "⚠️  Structural changes detected:" "WARNING"
        
        if [ ${#structural_changes[@]} -gt 0 ]; then
            log_message "📋 Infrastructure changes:" "WARNING"
            for change in "${structural_changes[@]}"; do
                log_message "  - $change" "WARNING"
            done
        fi
        
        if [ ${#dependency_changes[@]} -gt 0 ]; then
            log_message "📦 Dependency changes:" "WARNING"
            for change in "${dependency_changes[@]}"; do
                log_message "  - $change" "WARNING"
            done
        fi
        
        if [ "$force_reinstall" = "true" ]; then
            log_message "🚨 CRITICAL: Major structural changes detected!" "ERROR"
            log_message "These changes require a full reinstall to work properly:" "ERROR"
            log_message "  Recommended: ./manage_sting.sh reinstall" "ERROR"
            log_message "  Alternative: ./manage_sting.sh update --force (risky)" "ERROR"
            return 2  # Critical changes
        else
            log_message "💡 Recommendation: Consider full reinstall for best reliability" "WARNING"
            log_message "  Safe option: ./manage_sting.sh reinstall" "WARNING"
            log_message "  Continue anyway: ./manage_sting.sh update --force" "WARNING"
            return 1  # Minor changes
        fi
    fi
    
    log_message "✅ No structural changes detected - update should be safe"
    return 0  # No changes
}

# Function to check service dependencies
check_service_dependencies() {
    local service="$1"
    local dependencies=()
    
    case "$service" in
        frontend)
            dependencies=("app" "kratos")
            ;;
        app)
            dependencies=("db" "vault" "kratos")
            ;;
        chatbot)
            dependencies=("db" "external-ai")
            ;;
        external-ai)
            # Check if Ollama is running
            if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                log_message "⚠️  Warning: Ollama not running - external-ai service may fail" "WARNING"
                log_message "Start Ollama with: ollama serve" "INFO"
            fi
            ;;
        kratos)
            dependencies=("db")
            ;;
        messaging)
            dependencies=("db")
            ;;
        knowledge)
            dependencies=("db")
            ;;
        nectar-worker)
            dependencies=("app")
            # Check if Ollama is running
            if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                log_message "⚠️  Warning: Ollama not running - nectar-worker may fail" "WARNING"
                log_message "Start Ollama with: ollama serve" "INFO"
            fi
            ;;
    esac
    
    # Check if dependencies are running
    for dep in "${dependencies[@]}"; do
        # Use docker compose with project name to check service status
        if ! docker compose -p "${COMPOSE_PROJECT_NAME:-sting-ce}" ps "$dep" 2>/dev/null | grep -qE "(Up|running)"; then
            log_message "⚠️  Warning: Dependency '$dep' not running for service '$service'" "WARNING"
            log_message "Consider starting dependencies first: ./manage_sting.sh start $dep" "INFO"
        fi
    done
}

# Function to sync code for a specific service
sync_service_code() {
    local service="$1"
    # Determine the correct project directory - use current working directory for updates
    # since that's where the user runs the update command from
    local project_dir
    if [ -n "$PROJECT_DIR" ]; then
        project_dir="$PROJECT_DIR"
    elif [ -f "$(pwd)/manage_sting.sh" ] && [ -d "$(pwd)/frontend" ]; then
        # We're in the project directory
        project_dir="$(pwd)"
    else
        # Fallback to SOURCE_DIR
        project_dir="${SOURCE_DIR:-$(pwd)}"
    fi
    
    log_message "🔍 Debug: Syncing from project_dir: $project_dir to INSTALL_DIR: $INSTALL_DIR" "INFO"
    
    case "$service" in
        frontend)
            # DISABLED: Complex container-based build - use standard approach instead
            # Sync-only mode now uses simple file sync without frontend-builder container
            if [ "$sync_only" = "true" ]; then
                log_message "🚀 Sync-only mode: Simple file sync for frontend..." "INFO"
                
                # Simple file sync - no container building needed
                log_message "📦 Syncing frontend files directly..." "INFO"
                
                # Create temporary staging directory for changed files
                local temp_dir=$(mktemp -d)
                
                # Use gitignore patterns for optimized sync too
                if [[ -f "$project_dir/.gitignore" ]]; then
                    # Use project_dir to find the lib directory reliably
                    local gitignore_sync_path="$project_dir/lib/gitignore_sync.sh"
                    if [[ -f "$gitignore_sync_path" ]]; then
                        source "$gitignore_sync_path"
                        local excludes_file=$(mktemp)
                        get_gitignore_rsync_excludes "$project_dir" > "$excludes_file"
                        
                        # Build rsync command with all excludes
                        local rsync_cmd="rsync -auc"
                        while read -r exclude_arg; do
                            [[ -n "$exclude_arg" ]] && rsync_cmd="$rsync_cmd $exclude_arg"
                        done < "$excludes_file"
                        rsync_cmd="$rsync_cmd $project_dir/frontend/ $temp_dir/"
                        
                        eval "$rsync_cmd"
                        rm -f "$excludes_file"
                    else
                        log_message "⚠️ gitignore_sync.sh not found, using manual excludes" "WARNING"
                        rsync -auc "$project_dir/frontend/" "$temp_dir/" \
                            --exclude node_modules --exclude build --exclude dist \
                            --exclude .git --exclude .gitignore \
                            --exclude '*.log' --exclude '.DS_Store' \
                            --exclude 'main.*' --exclude 'config.yml'
                    fi
                else
                    # Fallback to manual excludes
                    rsync -auc "$project_dir/frontend/" "$temp_dir/" \
                        --exclude node_modules --exclude build --exclude dist \
                        --exclude .git --exclude .gitignore \
                        --exclude '*.log' --exclude '.DS_Store' \
                        --exclude 'main.*' --exclude 'config.yml'
                fi
                
                # Check if the container is running
                if ! docker ps | grep -q "sting-ce-frontend"; then
                    log_message "⚠️ Frontend container not running, falling back to gitignore-aware sync..." "WARNING"
                    rm -rf "$temp_dir"
                    
                    # Clean artifacts and use gitignore sync for fallback too
                    rm -rf "$INSTALL_DIR/frontend/build" "$INSTALL_DIR/frontend/dist"
                    
                    if [[ -f "$project_dir/.gitignore" ]]; then
                        local gitignore_sync_path="$project_dir/lib/gitignore_sync.sh"
                        if [[ -f "$gitignore_sync_path" ]]; then
                            source "$gitignore_sync_path"
                            gitignore_service_sync "frontend" "$project_dir" "$INSTALL_DIR"
                        else
                            rsync -a --delete "$project_dir/frontend/" "$INSTALL_DIR/frontend/" \
                                --exclude node_modules --exclude build --exclude dist \
                                --exclude 'main.*' --exclude 'config.yml' --exclude '*.env'
                        fi
                    else
                        rsync -a --delete "$project_dir/frontend/" "$INSTALL_DIR/frontend/" \
                            --exclude node_modules --exclude build --exclude dist \
                            --exclude 'main.*' --exclude 'config.yml' --exclude '*.env'
                    fi
                    return 0
                fi
                
                # DISABLED: No longer using frontend-builder container
                # Simply sync files directly to install directory
                log_message "📋 Step 2: Direct file sync (frontend-builder disabled)..." "INFO"
                
                # Clean up any existing frontend-builder containers  
                docker rm -f "sting-frontend-builder" >/dev/null 2>&1
                
                # Step 3: Simple file sync to install directory (no build container)
                log_message "🔄 Step 3: Syncing files to install directory..." "INFO"
                rsync -auc "$project_dir/frontend/" "$INSTALL_DIR/frontend/" \
                    --exclude node_modules --exclude build --exclude dist \
                    --exclude .git --exclude .gitignore \
                    --exclude '*.log' --exclude '.DS_Store'
                
                # Step 6: Validate sync completed successfully
                log_message "🔍 Step 6: Validating sync completion..." "INFO"
                local validation_passed=true
                
                # Check that key debugging file was updated with our recent changes
                local debug_file="$INSTALL_DIR/frontend/src/components/auth/EnhancedKratosLogin.jsx"
                if [ -f "$debug_file" ]; then
                    if grep -q "EMAIL CODE SUCCESS" "$debug_file" 2>/dev/null; then
                        log_message "✅ Validation: Recent debugging code found in EnhancedKratosLogin.jsx" "SUCCESS"
                    else
                        log_message "⚠️ Validation: Recent debugging code NOT found in login component" "WARNING"
                        validation_passed=false
                    fi
                else
                    log_message "❌ Validation: Login component file missing after sync" "ERROR"
                    validation_passed=false
                fi
                
                # Check that UnifiedProtectedRoute has bypass logic
                local route_file="$INSTALL_DIR/frontend/src/auth/UnifiedProtectedRoute.jsx"
                if [ -f "$route_file" ]; then
                    if grep -q "TEMPORARY.*bypass" "$route_file" 2>/dev/null; then
                        log_message "✅ Validation: AAL bypass logic found in UnifiedProtectedRoute.jsx" "SUCCESS"
                    else
                        log_message "⚠️ Validation: AAL bypass logic NOT found in route component" "WARNING"
                        validation_passed=false
                    fi
                else
                    log_message "❌ Validation: Route component file missing after sync" "ERROR"
                    validation_passed=false
                fi
                
                # Check file sync timestamps (files modified within last 2 minutes)
                local recent_files=$(find "$INSTALL_DIR/frontend/src" -name "*.jsx" -newermt "2 minutes ago" 2>/dev/null | wc -l)
                if [ "$recent_files" -gt 0 ]; then
                    log_message "✅ Validation: $recent_files React files updated in last 2 minutes" "SUCCESS"
                else
                    log_message "⚠️ Validation: No recent file modifications detected" "WARNING"
                fi
                
                # Check container build success
                if docker ps | grep -q "sting-ce-frontend" && [ $? -eq 0 ]; then
                    log_message "✅ Validation: Frontend container is running" "SUCCESS"
                else
                    log_message "⚠️ Validation: Frontend container not running (may be expected)" "WARNING"
                fi
                
                # Report validation results
                if [ "$validation_passed" = "true" ]; then
                    log_message "🎉 Code validation: All key changes verified in sync target" "SUCCESS"
                else
                    log_message "⚠️ Code validation: Some expected changes not found - check sync process" "WARNING"
                fi
                
                log_message "✅ Frontend optimized sync completed successfully" "SUCCESS"
                return 0
            else
                log_message "🔨 Full sync mode: Syncing all frontend files..." "INFO"
                # Clean build artifacts first to prevent corruption
                rm -rf "$INSTALL_DIR/frontend/build" "$INSTALL_DIR/frontend/dist"
                rm -rf "$project_dir/frontend/build" "$project_dir/frontend/dist"
                
                # Use gitignore-aware sync for comprehensive exclusions
                if [[ -f "$project_dir/.gitignore" ]]; then
                    log_message "📋 Using .gitignore patterns for sync exclusions..." "INFO"
                    local gitignore_sync_path="$project_dir/lib/gitignore_sync.sh"
                    if [[ -f "$gitignore_sync_path" ]]; then
                        source "$gitignore_sync_path"
                        gitignore_service_sync "frontend" "$project_dir" "$INSTALL_DIR"
                    else
                        log_message "⚠️ gitignore_sync.sh not found, using manual excludes" "WARNING"
                        rsync -a --delete "$project_dir/frontend/" "$INSTALL_DIR/frontend/" \
                            --filter='P node_modules/**' \
                            --filter='P node_modules' \
                            --exclude node_modules --exclude build --exclude dist \
                            --exclude 'main.*' --exclude '*.js.map' --exclude '*.css.map' \
                            --exclude '.git' --exclude '*.log' --exclude '.DS_Store' \
                            --exclude 'config.yml' --exclude '*.env'
                    fi
                else
                    # Fallback to manual excludes if no .gitignore
                    rsync -a --delete "$project_dir/frontend/" "$INSTALL_DIR/frontend/" \
                        --filter='P node_modules/**' \
                        --filter='P node_modules' \
                        --exclude node_modules --exclude build --exclude dist \
                        --exclude 'main.*' --exclude '*.js.map' --exclude '*.css.map' \
                        --exclude '.git' --exclude '*.log' --exclude '.DS_Store' \
                        --exclude 'config.yml' --exclude '*.env'
                fi
            fi
            
            # IMPORTANT: Sync theme files from src/theme to public/theme
            log_message "🎨 Syncing theme files from src/theme to public/theme..." "INFO"
            mkdir -p "$INSTALL_DIR/frontend/public/theme"
            if [ -d "$INSTALL_DIR/frontend/src/theme" ]; then
                # Sync all theme CSS files
                cp -f "$INSTALL_DIR/frontend/src/theme"/*-theme.css "$INSTALL_DIR/frontend/public/theme/" 2>/dev/null || true
                log_message "✅ Theme files synced to public directory ($(ls -1 "$INSTALL_DIR/frontend/public/theme/" 2>/dev/null | wc -l | tr -d ' ') files)" "INFO"
            fi
            
            # Also sync themes in the project directory for consistency
            mkdir -p "$project_dir/frontend/public/theme"
            if [ -d "$project_dir/frontend/src/theme" ]; then
                cp -f "$project_dir/frontend/src/theme"/*-theme.css "$project_dir/frontend/public/theme/" 2>/dev/null || true
            fi
            ;;
        chatbot)
            rsync -a "$project_dir/chatbot/" "$INSTALL_DIR/chatbot/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            # Also copy llm_service/chat for shared code
            mkdir -p "$INSTALL_DIR/llm_service"
            rsync -a "$project_dir/llm_service/chat/" "$INSTALL_DIR/llm_service/chat/" \
                --exclude='venv' --exclude='**/venv' --exclude='__pycache__' --exclude='*.pyc'
            rsync -a "$project_dir/llm_service/filtering/" "$INSTALL_DIR/llm_service/filtering/" \
                --exclude='venv' --exclude='**/venv' --exclude='__pycache__' --exclude='*.pyc'
            ;;
        nectar-worker)
            rsync -a "$project_dir/nectar_worker/" "$INSTALL_DIR/nectar_worker/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            ;;
        llm-gateway)
            mkdir -p "$INSTALL_DIR/llm_service"
            rsync -a "$project_dir/llm_service/" "$INSTALL_DIR/llm_service/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='models' --exclude='*.bin' --exclude='*.safetensors'
            ;;
        app)
            rsync -a "$project_dir/app/" "$INSTALL_DIR/app/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='instance' --exclude='flask_session' --exclude='*.egg-info'
            ;;
        messaging)
            rsync -a "$project_dir/messaging_service/" "$INSTALL_DIR/messaging_service/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            ;;
        kratos)
            rsync -a "$project_dir/kratos/" "$INSTALL_DIR/kratos/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            ;;
        vault)
            rsync -a "$project_dir/vault/" "$INSTALL_DIR/vault/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            ;;
        database)
            rsync -a "$project_dir/database/" "$INSTALL_DIR/database/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            rsync -a "$project_dir/docker-entrypoint-initdb.d/" "$INSTALL_DIR/docker-entrypoint-initdb.d/" \
                --exclude='venv' --exclude='**/venv' --exclude='*.pyc'
            ;;
        web-server)
            rsync -a "$project_dir/web-server/" "$INSTALL_DIR/web-server/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            ;;
        external-ai)
            rsync -a "$project_dir/external_ai_service/" "$INSTALL_DIR/external_ai_service/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='*.egg-info'
            ;;
        knowledge)
            rsync -a "$project_dir/knowledge_service/" "$INSTALL_DIR/knowledge_service/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='*.egg-info' --exclude='data' --exclude='chroma_data'
            ;;
        loki)
            rsync -a "$project_dir/observability/loki/" "$INSTALL_DIR/observability/loki/" \
                --exclude='data' --exclude='*.log'
            ;;
        promtail)
            rsync -a "$project_dir/observability/promtail/" "$INSTALL_DIR/observability/promtail/" \
                --exclude='*.log'
            ;;
        grafana)
            rsync -a "$project_dir/observability/grafana/" "$INSTALL_DIR/observability/grafana/" \
                --exclude='data' --exclude='*.log' --exclude='grafana.db'
            ;;
        utils)
            # Utils service shares app code and Dockerfile.utils
            rsync -a "$project_dir/app/" "$INSTALL_DIR/app/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='instance' --exclude='flask_session' --exclude='*.egg-info'
            # Also sync utils-specific files if they exist
            if [ -f "$project_dir/Dockerfile.utils" ]; then
                cp "$project_dir/Dockerfile.utils" "$INSTALL_DIR/Dockerfile.utils"
            fi
            ;;
        report-worker)
            # Report worker shares app code
            rsync -a "$project_dir/app/" "$INSTALL_DIR/app/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='instance' --exclude='flask_session' --exclude='*.egg-info'
            ;;
        db|database)
            rsync -a "$project_dir/database/" "$INSTALL_DIR/database/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
            rsync -a "$project_dir/docker-entrypoint-initdb.d/" "$INSTALL_DIR/docker-entrypoint-initdb.d/" \
                --exclude='venv' --exclude='**/venv' --exclude='*.pyc'
            ;;
        llm-gateway-proxy|llm-gateway)
            mkdir -p "$INSTALL_DIR/llm_service"
            rsync -a "$project_dir/llm_service/" "$INSTALL_DIR/llm_service/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='models' --exclude='*.bin' --exclude='*.safetensors'
            # Also sync nginx config if it exists
            if [ -f "$project_dir/nginx-llm-proxy.conf" ]; then
                cp "$project_dir/nginx-llm-proxy.conf" "$INSTALL_DIR/nginx-llm-proxy.conf"
            fi
            ;;
        public-bee)
            mkdir -p "$INSTALL_DIR/public_bee"
            rsync -a "$project_dir/public_bee/" "$INSTALL_DIR/public_bee/" \
                --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
                --exclude='*.egg-info' --exclude='instance' --exclude='.pytest_cache'
            log_message "Public Bee service synchronized successfully"
            ;;
        manage-script)
            # Sync the main management script and lib directory
            if [ -f "$project_dir/manage_sting.sh" ]; then
                cp "$project_dir/manage_sting.sh" "$INSTALL_DIR/manage_sting.sh"
                # Ensure execute permissions are set and clear extended attributes (macOS)
                chmod +x "$INSTALL_DIR/manage_sting.sh" || {
                    log_message "WARNING: Failed to set execute permissions on manage_sting.sh"
                }
                # Clear extended attributes that can prevent execution on macOS
                if [[ "$(uname)" == "Darwin" ]]; then
                    xattr -c "$INSTALL_DIR/manage_sting.sh" 2>/dev/null || true
                fi
                log_message "Management script synchronized successfully"
            else
                log_message "WARNING: manage_sting.sh not found in source directory"
            fi
            
            # Sync the lib directory with all modules
            if [ -d "$project_dir/lib" ]; then
                rsync -a "$project_dir/lib/" "$INSTALL_DIR/lib/" \
                    --exclude='venv' --exclude='**/venv' --exclude='.venv' \
                    --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc'
                # Ensure execute permissions on shell scripts
                chmod +x "$INSTALL_DIR/lib"/*.sh 2>/dev/null || true
                log_message "Management script lib directory synchronized successfully"
            else
                log_message "WARNING: lib directory not found in source directory"
            fi
            ;;
        headscale)
            # Headscale uses official image but has configuration files
            mkdir -p "$INSTALL_DIR/conf/headscale"
            rsync -a "$project_dir/conf/headscale/" "$INSTALL_DIR/conf/headscale/" \
                --exclude='*.tmp' --exclude='*.log'
            log_message "Headscale configuration files synchronized successfully"
            ;;
        *)
            log_message "Warning: No specific sync rules for service $service" "WARNING"
            log_message "Available services: frontend, app, chatbot, external-ai, knowledge, messaging, kratos, vault, database, web-server, utils, report-worker, db, llm-gateway-proxy, public-bee, loki, promtail, grafana, headscale, manage-script" "INFO"
            return 1
            ;;
    esac
}

# Function to sync configuration and infrastructure files only
sync_config_files() {
    local project_dir="${SOURCE_DIR:-$(pwd)}"
    local install_dir="${INSTALL_DIR}"
    
    log_message "Syncing configuration and infrastructure files..."
    
    # Sync docker-compose files
    log_message "Syncing Docker Compose files..."
    for compose_file in "$project_dir"/docker-compose*.yml; do
        if [ -f "$compose_file" ]; then
            local filename=$(basename "$compose_file")
            cp -f "$compose_file" "$install_dir/$filename"
            log_message "  ✓ $filename"
        fi
    done
    
    # Sync conf directory
    log_message "Syncing configuration directory..."
    if [ -d "$project_dir/conf" ]; then
        rsync -a "$project_dir/conf/" "$install_dir/conf/" \
            --exclude='secrets/' \
            --exclude='vault/' \
            --exclude='*.swp' \
            --exclude='.DS_Store' \
            --exclude='__pycache__' \
            --exclude='*.pyc'
        log_message "  ✓ conf/ directory"
    fi
    
    # Sync management scripts
    log_message "Syncing management scripts..."
    if [ -f "$project_dir/manage_sting.sh" ]; then
        cp -f "$project_dir/manage_sting.sh" "$install_dir/manage_sting.sh"
        chmod +x "$install_dir/manage_sting.sh"
        log_message "  ✓ manage_sting.sh"
    fi
    
    # Sync lib directory
    if [ -d "$project_dir/lib" ]; then
        rsync -a "$project_dir/lib/" "$install_dir/lib/" \
            --exclude='__pycache__' \
            --exclude='*.pyc'
        chmod +x "$install_dir/lib"/*.sh 2>/dev/null || true
        log_message "  ✓ lib/ directory"
    fi
    
    # Sync scripts directory if exists
    if [ -d "$project_dir/scripts" ]; then
        rsync -a "$project_dir/scripts/" "$install_dir/scripts/" \
            --exclude='__pycache__' \
            --exclude='*.pyc'
        chmod +x "$install_dir/scripts"/*.sh 2>/dev/null || true
        log_message "  ✓ scripts/ directory"
    fi
    
    # Sync .env.example if exists
    if [ -f "$project_dir/.env.example" ]; then
        cp -f "$project_dir/.env.example" "$install_dir/.env.example"
        log_message "  ✓ .env.example"
    fi
    
    # Sync msting wrapper command if it exists
    if [ -f "/usr/local/bin/msting" ]; then
        log_message "Syncing msting wrapper command..."
        local wrapper_content="#!/bin/bash
# msting - STING Community Edition Management Command
# This wrapper calls the installed manage_sting.sh script

# Determine install directory
if [[ \"\$(uname)\" == \"Darwin\" ]]; then
    INSTALL_DIR=\"\${INSTALL_DIR:-\$HOME/.sting-ce}\"
else
    INSTALL_DIR=\"\${INSTALL_DIR:-${install_dir}}\"
fi

# Call the actual script
exec \"\$INSTALL_DIR/manage_sting.sh\" \"\$@\"
"
        if echo "$wrapper_content" > /tmp/msting_wrapper 2>/dev/null; then
            if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
                sudo cp /tmp/msting_wrapper /usr/local/bin/msting
                sudo chmod +x /usr/local/bin/msting
                rm -f /tmp/msting_wrapper
                log_message "  ✓ msting wrapper command"
            else
                log_message "  ⚠  msting wrapper update requires sudo" "WARN"
                rm -f /tmp/msting_wrapper
            fi
        fi
    fi

    # Check if config changed and regenerate env files if needed
    if check_config_changes; then
        log_message "Configuration changes detected, regenerating environment files..."
        local python_cmd="python3"
        if [ -f "${install_dir}/.venv/bin/python3" ]; then
            python_cmd="${install_dir}/.venv/bin/python3"
        fi
        if [ -f "${install_dir}/conf/config_loader.py" ]; then
            if ! $python_cmd "${install_dir}/conf/config_loader.py" "${install_dir}/conf/config.yml"; then
                log_message "Warning: Failed to regenerate env files" "WARN"
            else
                log_message "  ✓ Environment files regenerated"
            fi
        fi
    fi
    
    log_message "✅ Configuration sync completed successfully" "SUCCESS"
    return 0
}

# Function to reset config.yml from config.yml.default with backup
reset_config_files() {
    local install_dir="${INSTALL_DIR}"
    local config_file="$install_dir/conf/config.yml"
    local default_config="$install_dir/conf/config.yml.default"
    
    log_message "Resetting configuration from template with backup..."
    
    # Check if install directory exists
    if [ ! -d "$install_dir" ]; then
        log_message "❌ Install directory not found: $install_dir" "ERROR"
        log_message "Run installation first or check INSTALL_DIR path" "ERROR"
        return 1
    fi
    
    # Ensure conf directory exists
    mkdir -p "$install_dir/conf"
    
    # Check if config.yml.default exists
    if [ ! -f "$default_config" ]; then
        log_message "❌ Template file not found: $default_config" "ERROR"
        log_message "Run './manage_sting.sh sync-config' first to sync template files" "ERROR"
        return 1
    fi
    
    # Backup existing config.yml if it exists
    if [ -f "$config_file" ]; then
        log_message "📦 Backing up existing config.yml..."
        
        # Find next available backup number
        local backup_num=1
        while [ -f "$config_file.$backup_num" ]; do
            backup_num=$((backup_num + 1))
        done
        
        # Create backup
        cp "$config_file" "$config_file.$backup_num"
        log_message "  ✓ Backed up to config.yml.$backup_num"
        
        # Clean up old backups (keep last 5)
        local backup_count
        backup_count=$(find "$(dirname "$config_file")" -name "config.yml.*" -type f | wc -l)
        if [ "$backup_count" -gt 5 ]; then
            log_message "🧹 Cleaning up old backups (keeping last 5)..."
            find "$(dirname "$config_file")" -name "config.yml.*" -type f -print0 | \
                xargs -0 ls -t | tail -n +6 | xargs rm -f
            log_message "  ✓ Cleaned up old backups"
        fi
    else
        log_message "📝 No existing config.yml found, creating fresh from template"
    fi
    
    # Copy fresh config from template
    log_message "🔄 Resetting config.yml from template..."
    cp "$default_config" "$config_file"
    log_message "  ✓ Fresh config.yml created from config.yml.default"
    
    # Verify the file was created successfully
    if [ ! -f "$config_file" ] || [ ! -s "$config_file" ]; then
        log_message "❌ Failed to create config.yml or file is empty" "ERROR"
        return 1
    fi
    
    log_message "✅ Configuration reset completed successfully" "SUCCESS"
    log_message "📋 Next steps:" "INFO"
    log_message "  1. Edit $config_file as needed" "INFO"
    log_message "  2. Run './manage_sting.sh regenerate-env' to apply changes" "INFO"
    log_message "  3. Restart services: './manage_sting.sh restart <service>'" "INFO"
    
    return 0
}

# Function to preserve env files during reinstall
preserve_env_files() {
    local install_dir="$1"
    local backup_suffix=".preserved.$(date +%Y%m%d_%H%M%S)"
    
    log_message "Preserving existing env files..."
    
    # Check if env directory exists
    if [ ! -d "$install_dir/env" ]; then
        log_message "No env directory found, nothing to preserve"
        return 0
    fi
    
    # Count env files
    local env_file_count=$(find "$install_dir/env" -name "*.env" 2>/dev/null | wc -l)
    if [ "$env_file_count" -eq 0 ]; then
        log_message "No env files found to preserve"
        return 0
    fi
    
    # Create backup of env files
    local preserved_count=0
    for env_file in "$install_dir/env"/*.env "$install_dir/conf"/*.env; do
        if [ -f "$env_file" ]; then
            cp "$env_file" "${env_file}${backup_suffix}"
            ((preserved_count++))
        fi
    done
    
    log_message "Preserved $preserved_count env files with suffix: $backup_suffix"
    return 0
}

# Function to restore preserved env files
restore_env_files() {
    local install_dir="$1"
    
    log_message "Checking for preserved env files to restore..."
    
    # Find most recent preserved files
    local restored_count=0
    for preserved_file in "$install_dir/env"/*.env.preserved.* "$install_dir/conf"/*.env.preserved.*; do
        if [ -f "$preserved_file" ]; then
            # Extract original filename
            local original_file="${preserved_file%%.preserved.*}"
            
            # Only restore if original doesn't exist (wasn't copied from source)
            if [ ! -f "$original_file" ]; then
                mv "$preserved_file" "$original_file"
                log_message "Restored: $(basename "$original_file")"
                ((restored_count++))
            else
                # Remove preserved file if original exists
                rm -f "$preserved_file"
            fi
        fi
    done
    
    if [ "$restored_count" -gt 0 ]; then
        log_message "Restored $restored_count env files"
    else
        log_message "No env files needed restoration"
    fi
    
    return 0
}

log_message "File operations module loaded successfully"