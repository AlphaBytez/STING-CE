#!/bin/bash
# installation.sh - Installation and dependency management functions

# Dependencies should be loaded by the main script
# No need to source them again here

# Main installation function
install_msting() {
    local start_llm=false
    local interactive_prompt=true
    local setup_admin=true  # Default to true for fresh installs
    local admin_email=""
    local cache_level="${CACHE_LEVEL:-moderate}"  # Accept cache level from environment or default
    
    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --start-llm)
                start_llm=true
                interactive_prompt=false
                ;;
            --setup-admin)
                setup_admin=true
                ;;
            --admin-email=*)
                admin_email="${arg#*=}"
                setup_admin=true
                ;;
            --no-admin)
                setup_admin=false
                ;;
            --no-prompt)
                interactive_prompt=false
                ;;
        esac
    done
    
    log_message "Starting STING installation..."

    # Note: Existing installation check is performed earlier in install_sting.sh
    # before wizard/keepalive starts, to avoid unnecessary sudo prompts

    # Set fresh install flag for extended timeouts
    export FRESH_INSTALL=true
    
    # Create install directory
    log_message "Creating installation directory at ${INSTALL_DIR}..."
    
    # Detect if we're running with sudo privileges
    local is_sudo=false
    if [ "$EUID" -eq 0 ] || [ -n "$SUDO_USER" ]; then
        is_sudo=true
        log_message "Running with elevated privileges"
    fi
    
    # Create directory with appropriate method
    if [ "$is_sudo" = true ]; then
        # Already have sudo - create directly and set proper ownership
        mkdir -p "${INSTALL_DIR}" || {
            log_message "Failed to create installation directory" "ERROR"
            return 1
        }
        # Set ownership to the original user if running via sudo
        if [ -n "$SUDO_USER" ]; then
            chown -R "$SUDO_USER:$(id -gn $SUDO_USER)" "${INSTALL_DIR}"
        fi
    else
        # Try without sudo first, then with sudo if needed
        if ! mkdir -p "${INSTALL_DIR}" 2>/dev/null; then
            if command -v sudo >/dev/null 2>&1; then
                log_message "Need elevated permissions to create ${INSTALL_DIR}"
                # Use -n flag to avoid password prompts (keepalive should handle this)
                if ! sudo -n mkdir -p "${INSTALL_DIR}" 2>/dev/null; then
                    log_message "Failed to create installation directory (sudo not available)" "ERROR"
                    log_message "Ensure sudo keepalive is running or run installer with sudo" "ERROR"
                    return 1
                fi
                # Set ownership to current user
                sudo -n chown -R "$USER:$(id -gn)" "${INSTALL_DIR}" 2>/dev/null || {
                    log_message "Warning: Could not set ownership on ${INSTALL_DIR}" "WARNING"
                }
            else
                log_message "Cannot create ${INSTALL_DIR} - permission denied and sudo not available" "ERROR"
                return 1
            fi
        fi
    fi
    
    # Check prerequisites
    if ! check_and_install_dependencies; then
        log_message "Failed to install dependencies" "ERROR"
        return 1
    fi
    
    # Apply WSL2 Docker fixes if needed
    if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
        source "${SCRIPT_DIR}/docker_wsl_fix.sh"
        fix_docker_credential_helper
    fi
    
    # Pull base Docker images
    log_message "Pulling base Docker images..."
    docker pull postgres:16-alpine
    docker pull node:20-alpine
    docker pull python:3.11-slim
    
    # Initialize STING using the master initialization function
    if ! initialize_sting; then
        log_message "Failed to initialize STING" "ERROR"
        return 1
    fi
    
    # Note: Python dependency verification skipped - using containerized approach
    
    # Install msting command
    install_msting_command
    
    log_message "STING installation completed successfully!" "SUCCESS"
    log_message "You can now use 'msting' command to manage STING"
    
    # Check for potential PATH conflicts
    check_msting_path_conflicts
    
    # Cross-platform permission notice
    echo ""
    log_message "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:" "WARNING"
    log_message "   Please run the permission fix script after installation:"
    log_message "   ./fix_permissions.sh"
    log_message ""
    log_message "   This is required on both macOS and PC to ensure proper script permissions."
    echo ""
    
    # Handle admin setup - enhanced with scenario detection
    if [ "$setup_admin" = true ] && [ "$interactive_prompt" = false ]; then
        # Non-interactive: setup admin with provided email
        log_message "Setting up admin user as requested..."
        create_admin_user_with_verification "$admin_email"
    else
        # Smart admin setup based on installation scenario
        smart_admin_setup
    fi
    
    # Handle LLM service startup based on flags only (no interactive prompts)
    if [[ "$(uname)" == "Darwin" ]] && [ "$start_llm" = true ]; then
        log_message "Starting LLM service as requested..."
        start_llm_service_post_install
    else
        # Always show LLM startup notice instead of prompting
        # show_llm_startup_notice  # Deprecated - LLM service is no longer used
        true  # no-op
    fi
    
    return 0
}

# Uninstall STING
# Force cleanup all STING Docker resources
force_cleanup_docker_resources() {
    log_message "Performing aggressive Docker cleanup for STING resources..."
    
    # Stop and remove all containers with STING-related names (including utils)
    docker ps -a --format "{{.Names}}" | grep -E "(sting|kratos|chroma|knowledge|utils)" | xargs -r docker rm -f 2>/dev/null || true
    
    # Remove all STING-related images
    docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "(sting|kratos)" | xargs -r docker rmi -f 2>/dev/null || true
    
    # Remove all STING-related volumes
    # FIXED: Only remove non-data volumes
    for vol in $(docker volume ls -q | grep -E "(sting|kratos|chroma|knowledge)"); do
        if [[ ! "$vol" =~ (postgres_data|vault-data|redis_data|chroma_data|mailpit_data) ]]; then
            docker volume rm -f "$vol" 2>/dev/null || true
        fi
    done 2>/dev/null || true
    
    # Remove STING networks
    docker network ls --format "{{.Name}}" | grep sting | xargs -r docker network rm 2>/dev/null || true

    # Remove buildx builder (used for local builds)
    if docker buildx inspect builder &>/dev/null; then
        log_message "Removing buildx builder..."
        # Clean up refs directory first to avoid .DS_Store issues on macOS
        rm -rf ~/.docker/buildx/refs/builder 2>/dev/null || true
        docker buildx rm builder 2>/dev/null || true
    fi

    # Clean up any orphaned containers, networks, and volumes
    docker system prune -f 2>/dev/null || true
    
    # Remove any stale .venv directories that could cause command conflicts
    if [ -d "${INSTALL_DIR}/.venv" ]; then
        log_message "Removing stale .venv directory to prevent command conflicts..."
        rm -rf "${INSTALL_DIR}/.venv"
    fi
    
    # Also check for .venv in the source directory (project dir) if different from install dir
    if [ -n "${SOURCE_DIR}" ] && [ "${SOURCE_DIR}" != "${INSTALL_DIR}" ] && [ -d "${SOURCE_DIR}/.venv" ]; then
        log_message "Removing stale .venv from source directory to prevent command conflicts..."
        rm -rf "${SOURCE_DIR}/.venv"
    fi
    
    log_message "Aggressive Docker cleanup completed"
}

uninstall_msting() {
    local purge_models="$1"
    
    log_message "Starting STING uninstallation..."
    
    # Stop all services including all profiles
    if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
        cd "${INSTALL_DIR}" || return 1
        
        log_message "Stopping any STING containers (with timeout protection)..."
        
        # Use timeout for all Docker commands to prevent hanging
        # Stop all containers with STING-related names (bypass label filtering)
        timeout 10s docker ps -a --format "{{.Names}}" 2>/dev/null | grep -E "(sting|STING)" | xargs -r timeout 5s docker stop 2>/dev/null || true
        timeout 10s docker ps -a --format "{{.Names}}" 2>/dev/null | grep -E "(sting|STING)" | xargs -r timeout 5s docker kill 2>/dev/null || true
        
        # Alternative: stop by container name patterns directly (including utils, headscale, etc.)
        timeout 5s docker stop sting-ce-vault sting-ce-db sting-ce-app sting-ce-frontend sting-ce-kratos sting-ce-mailpit sting-ce-messaging sting-ce-redis sting-ce-llm-gateway sting-ce-external-ai sting-ce-utils sting-ce-headscale sting-ce-knowledge sting-ce-chatbot sting-ce-profile sting-ce-public-bee sting-ce-nectar-worker 2>/dev/null || true
        timeout 5s docker kill sting-ce-vault sting-ce-db sting-ce-app sting-ce-frontend sting-ce-kratos sting-ce-mailpit sting-ce-messaging sting-ce-redis sting-ce-llm-gateway sting-ce-external-ai sting-ce-utils sting-ce-headscale sting-ce-knowledge sting-ce-chatbot sting-ce-profile sting-ce-public-bee sting-ce-nectar-worker 2>/dev/null || true
        
        log_message "Container stop attempts completed (may have timed out)"
    fi
    
    # Remove containers and images with timeout protection
    log_message "Removing Docker containers and images..."
    
    # Remove all STING-related containers with timeout (comprehensive patterns)
    local container_patterns=("sting" "sting-ce" "sting_ce")
    for pattern in "${container_patterns[@]}"; do
        if timeout 30s docker ps -a --filter "name=${pattern}" --format "{{.ID}}" 2>/dev/null | xargs -r docker rm -f 2>/dev/null; then
            log_message "Containers matching '${pattern}' removed"
        else
            log_message "Container removal for '${pattern}' timed out or failed - continuing..." "WARNING"
        fi
    done
    
    # Additional: Remove containers by explicit naming patterns to catch edge cases
    log_message "Removing containers by explicit naming patterns..."
    docker ps -a --format "{{.Names}}" 2>/dev/null | grep -E "(sting|utils|headscale|kratos|chroma|knowledge|chatbot|profile)" | xargs -r docker rm -f 2>/dev/null || true
    
    # Remove STING images with timeout - comprehensive cleanup
    log_message "Removing STING Docker images..."
    
    # Use consistent Docker Compose project naming
    local project_name="${COMPOSE_PROJECT_NAME:-sting-ce}"
    
    # Multiple patterns to catch all STING-related images
    local image_patterns=(
        "*sting*"           # Any image with sting in name
        "*${project_name}*" # Images with project name (sting-ce)
        "sting-ce-*"        # Explicit STING-CE images  
        "${project_name}_*" # Docker Compose naming: sting-ce_app, sting-ce_frontend
        "${project_name}-*" # Alternative naming: sting-ce-app, sting-ce-frontend
    )
    
    local images_removed=false
    
    for pattern in "${image_patterns[@]}"; do
        local image_ids=$(timeout 15s docker images --filter "reference=${pattern}" --format "{{.ID}}" 2>/dev/null | sort -u)
        if [ -n "$image_ids" ]; then
            if echo "$image_ids" | xargs -r timeout 15s docker rmi -f 2>/dev/null; then
                log_message "Removed images matching pattern: ${pattern}"
                images_removed=true
            else
                log_message "Failed to remove some images matching: ${pattern}" "WARNING"
            fi
        fi
    done
    
    # Additional cleanup: remove dangling images created during build
    if timeout 15s docker image prune -f 2>/dev/null; then
        log_message "Removed dangling build images"
        images_removed=true
    fi
    
    if [ "$images_removed" = true ]; then
        log_message "STING images cleanup completed" "SUCCESS"
    else
        log_message "No STING images found to remove" "INFO"
    fi
    
    # Remove installation directory (but preserve backups and .venv unless --purge)
    if [ -d "${INSTALL_DIR}" ]; then
        log_message "Removing installation directory..."
        
        # Preserve important directories unless purging
        local preserve_dirs=()
        if [ -d "${INSTALL_DIR}/backups" ]; then
            local backup_temp="/tmp/sting_backups_$(date +%s)"
            mv "${INSTALL_DIR}/backups" "$backup_temp"
            log_message "Backups preserved at: $backup_temp"
        fi
        
        # IMPORTANT: Do NOT preserve .venv directory as it can contain outdated msting commands
        # that conflict with the proper system installation. Always remove .venv to prevent
        # PATH conflicts where old Python CLI versions shadow the correct shell script.
        if [ -d "${INSTALL_DIR}/.venv" ]; then
            log_message "Removing .venv directory to prevent command conflicts..."
            rm -rf "${INSTALL_DIR}/.venv"
            log_message "Virtual environment removed (prevents outdated msting command conflicts)"
        fi

        # Remove the installation directory (handle permission issues)
        if ! rm -rf "${INSTALL_DIR}" 2>/dev/null; then
            # If that fails, try with sudo for Docker-owned files
            log_message "Normal removal failed, trying with elevated permissions..."
            sudo rm -rf "${INSTALL_DIR}" || {
                log_message "WARNING: Could not fully remove ${INSTALL_DIR}, some files may remain"
            }
        fi

        # Restore preserved directories (excluding .venv which was intentionally removed)
        # Note: .venv directories are never restored to prevent command conflicts
    fi
    
    # Always clean up sensitive files that could cause security issues
    log_message "Cleaning up sensitive files and state..."
    # Note: admin_password.txt no longer used in passwordless system
    rm -f "${INSTALL_DIR}/.admin_initialized" 2>/dev/null || true
    rm -f "${INSTALL_DIR}/.installation_id" 2>/dev/null || true
    rm -rf "${INSTALL_DIR}/.sessions" 2>/dev/null || true
    
    # Remove models if purge flag is set
    if [ "$purge_models" = "--purge" ]; then
        log_message "PURGE MODE: Aggressive cleanup of all STING resources..." "WARNING"
        
        # Source model_management.sh to get ensure_models_dir function
        source "${SCRIPT_DIR}/model_management.sh"
        local models_dir
        models_dir=$(ensure_models_dir)
        if [ -d "$models_dir" ]; then
            log_message "Removing LLM models from $models_dir..."
            rm -rf "$models_dir"
        fi
        
        # Also remove Docker volume on macOS
        if [[ "$(uname)" == "Darwin" ]]; then
            docker volume rm llm_model_data 2>/dev/null || true
        fi
        
        # Remove ALL persistent state when purging
        log_message "Purging all persistent state and configuration..."
        rm -rf "${INSTALL_DIR}/env" 2>/dev/null || true
        rm -rf "${INSTALL_DIR}/logs" 2>/dev/null || true
        rm -rf "${INSTALL_DIR}/certs" 2>/dev/null || true
        rm -rf "${INSTALL_DIR}/backups" 2>/dev/null || true
        
        # Extra aggressive Docker cleanup for purge mode
        log_message "PURGE: Performing aggressive Docker cleanup..."
        
        # Remove ALL unused images (not just STING ones)
        docker image prune -af 2>/dev/null || true
        
        # Remove ALL unused volumes
        docker volume prune -f 2>/dev/null || true
        
        # Remove ALL unused networks  
        docker network prune -f 2>/dev/null || true
        
        # Remove build cache
        docker builder prune -af 2>/dev/null || true
        
        log_message "PURGE: Aggressive Docker cleanup completed" "WARNING"
    fi
    
    # Remove msting command
    if [ -L "/usr/local/bin/msting" ]; then
        log_message "Removing msting command..."
        sudo rm -f /usr/local/bin/msting 2>/dev/null || \
            log_message "Please manually remove /usr/local/bin/msting with sudo"
    fi
    
    # Remove user data only if --purge flag is set
    if [ "$purge_models" = "--purge" ]; then
        log_message "Purging user data (admin password, etc.)..."
        # Check multiple possible locations
        local user_data_dirs=(
            "${HOME}/.sting-ce"
            "/opt/sting-ce/.admin_initialized"
        )
        
        for data_path in "${user_data_dirs[@]}"; do
            if [ -e "$data_path" ]; then
                log_message "Removing user data: $data_path"
                rm -rf "$data_path"
            fi
        done
    else
        # Preserve user data for reinstalls
        if [ -d "${HOME}/.sting-ce" ]; then
            log_message "Preserving user data - use --purge to remove"
        fi
    fi
    
    # Wait for all services to fully terminate before removing volumes (avoids race condition)
    log_message "Waiting for services to fully terminate before removing volumes..."
    sleep 5
    
    # Double-check all STING containers are stopped
    local remaining_containers=$(docker ps -q --filter "name=sting" --filter "name=kratos" 2>/dev/null || true)
    if [ -n "$remaining_containers" ]; then
        log_message "Force stopping remaining containers..." "WARNING"
        docker stop $remaining_containers 2>/dev/null || true
        docker rm -f $remaining_containers 2>/dev/null || true
        sleep 3
    fi
    
    # Remove Docker networks and remaining volumes
    log_message "Cleaning up Docker networks and volumes..."
    docker network rm sting_local 2>/dev/null || true
    
    # Remove STING-related volumes - use docker-compose down -v for proper cleanup
    # First, try docker-compose down with volume removal if docker-compose.yml exists
    if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
        log_message "Using docker-compose to remove volumes..."
        cd "${INSTALL_DIR}" 2>/dev/null && docker-compose down -v 2>/dev/null || true
        cd - >/dev/null 2>&1
    fi
    
    # List of known STING volume names from docker-compose.yml
    local known_volumes=(
        "config_data"
        "postgres_data" 
        "vault_data"
        "vault_file"
        "vault_logs"
##        "supertokens_logs"  # DEPRECATED  # DEPRECATED
        "sting_logs"
        "sting_certs"
        "llm_logs"
        "mailpit_data"
        "messaging_data"
        "redis_data"
        "chroma_data"
        "knowledge_data"
        "knowledge_uploads"
        "profile_logs"
        "loki_data"
        "grafana_data"
        "container_logs"
        "build_logs"
        "build_analytics"
        "public_bee_logs"
    )
    
    # Also check for volumes with sting-ce_ prefix and other patterns
    local volumes_to_remove=$(docker volume ls -q | grep -E "(sting|kratos|sting-ce)" || true)
    
    # Add known volumes to removal list
    for vol in "${known_volumes[@]}"; do
        if docker volume ls -q | grep -q "^${vol}$"; then
            volumes_to_remove="$volumes_to_remove $vol"
        fi
    done
    
    # Remove duplicates from the list
    volumes_to_remove=$(echo "$volumes_to_remove" | tr ' ' '\n' | sort -u | tr '\n' ' ')
    
    if [ -n "$volumes_to_remove" ]; then
        # When purging, remove ALL volumes including data volumes
        if [ "$purge_models" = "--purge" ]; then
            log_message "PURGE: Removing ALL STING volumes including persistent data..." "WARNING"
            for vol in $volumes_to_remove; do
                docker volume rm -f "$vol" >/dev/null 2>&1 || {
                    log_message "Failed to remove volume: $vol (may be in use)" "WARNING"
                }
            done
        else
            # Without purge, preserve data volumes but always reset Vault for fresh installs
            log_message "Removing non-data Docker volumes..."
            for vol in $volumes_to_remove; do
                # Always remove Vault volumes for fresh installs (secrets shouldn't persist)
                # Skip other data volumes unless purging
                if [[ "$vol" =~ (vault_data|vault_file) ]] || [[ ! "$vol" =~ (postgres_data|redis_data|chroma_data|mailpit_data|messaging_data|knowledge_data) ]]; then
                    docker volume rm -f "$vol" >/dev/null 2>&1 || true
                    if [[ "$vol" =~ vault ]]; then
                        log_message "Removed Vault volume for fresh initialization: $vol"
                    fi
                fi
            done
        fi
        log_message "Removed Docker volumes"
    fi
    
    # Additional cleanup for orphaned containers
    docker container prune -f >/dev/null 2>&1 || true
    
    # If there are still STING containers running, do aggressive cleanup
    if docker ps --format "{{.Names}}" | grep -q -E "(sting|kratos|chroma|knowledge)"; then
        log_message "Some STING containers still detected, performing aggressive cleanup..." "WARNING"
        force_cleanup_docker_resources
    fi
    
    log_message "STING uninstallation completed" "SUCCESS"
    return 0
}

# Uninstall with confirmation
uninstall_msting_with_confirmation() {
    echo "⚠️  WARNING: This will remove STING installation!"
    echo "   - Installation directory: ${INSTALL_DIR}"
    echo "   - Docker containers, images, and volumes"
    echo ""
    echo "   ℹ️  User data (admin password, etc.) will be PRESERVED"
    echo "   Add --purge to remove ALL data including:"
    echo "     - User data and admin credentials"
    echo "     - All configuration files"
    echo ""
    read -p "Are you sure you want to uninstall STING? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        uninstall_msting "$@"
    else
        log_message "Uninstall cancelled"
        return 1
    fi
}

# Atomic Reinstall STING with rollback capability
reinstall_msting() {
    local fresh_install=false
    local install_llm=false
    local no_backup=false
    local lean_backup=true  # Default to lean backup
    local cache_level="moderate"  # Default cache buzzer level
    local backup_dir="${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --fresh)
                fresh_install=true
                cache_level="full"  # Fresh install uses full cache clear
                ;;
            --llm)
                install_llm=true
                ;;
            --no-backup)
                no_backup=true
                ;;
            --full-backup)
                lean_backup=false
                ;;
            --cache-minimal)
                cache_level="minimal"
                ;;
            --cache-moderate)
                cache_level="moderate"
                ;;
            --cache-full)
                cache_level="full"
                ;;
        esac
    done
    
    
    log_message "Starting atomic STING reinstallation..."
    
    # Phase 1: Create backup of existing installation (unless --no-backup is specified)
    if [ "$no_backup" = false ] && [ -d "${INSTALL_DIR}" ]; then
        # First preserve env files
        if declare -f preserve_env_files >/dev/null 2>&1; then
            preserve_env_files "${INSTALL_DIR}"
        fi
        
        # Source backup utilities
        source "${SCRIPT_DIR}/backup_utils.sh" 2>/dev/null || {
            # Fallback to full backup if backup_utils.sh not available
            log_message "backup_utils.sh not found, using full backup"
            lean_backup=false
        }
        
        if [ "$lean_backup" = true ] && command -v create_lean_backup >/dev/null 2>&1; then
            log_message "Creating lean backup of essential files..."
            if ! create_lean_backup "${INSTALL_DIR}" "${backup_dir}"; then
                log_message "Failed to create lean backup - aborting reinstall for safety" "ERROR"
                return 1
            fi
        else
            log_message "Creating full backup of installation..."
            if ! rsync -a --delete "${INSTALL_DIR}/" "${backup_dir}/"; then
                log_message "Failed to create backup - aborting reinstall for safety" "ERROR"
                return 1
            fi
            log_message "Full backup created at: ${backup_dir}"
        fi
    elif [ "$no_backup" = true ]; then
        log_message "Skipping backup creation (--no-backup flag specified)" "WARNING"
    fi
    
    # Phase 2: Test if we can install (dry run check)
    log_message "Performing pre-install validation..."
    if ! check_and_install_dependencies; then
        log_message "System dependencies check failed - cannot proceed with reinstall" "ERROR"
        if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
            restore_from_backup "${backup_dir}"
        fi
        return 1
    fi
    
    # Save credentials if not fresh install
    local saved_creds=""
    if [ "$fresh_install" = false ] && [ -f "${INSTALL_DIR}/conf/secrets/hf_token.txt" ]; then
        saved_creds=$(cat "${INSTALL_DIR}/conf/secrets/hf_token.txt")
        log_message "Preserving existing credentials..."
    fi
    
    # Phase 3: Uninstall existing installation
    log_message "Removing existing installation..."
    if [ "$fresh_install" = true ]; then
        # For fresh installs, ensure ALL state is cleaned
        log_message "Fresh install requested - purging all data including admin credentials..."
        if ! uninstall_msting --purge; then
            log_message "Uninstall failed - restoring from backup" "ERROR"
            if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
                restore_from_backup "${backup_dir}"
            fi
            return 1
        fi
    else
        if ! uninstall_msting; then
            log_message "Uninstall failed - restoring from backup" "ERROR"
            if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
                restore_from_backup "${backup_dir}"
            fi
            return 1
        fi
    fi
    
    # Wait a moment for cleanup
    sleep 2
    
    # Phase 4: Attempt new installation
    log_message "Installing fresh STING..."
    # Export cache level for install_msting to use
    export CACHE_LEVEL="$cache_level"
    if ! install_msting; then
        log_message "Installation failed - restoring from backup" "ERROR"
        if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
            restore_from_backup "${backup_dir}"
        fi
        return 1
    fi
    
    # Restore preserved env files after successful installation
    if declare -f restore_env_files >/dev/null 2>&1; then
        restore_env_files "${INSTALL_DIR}"
    fi
    
    # Phase 5: Verify installation health
    log_message "Verifying installation health..."
    if ! verify_installation_health; then
        log_message "Installation health check failed - restoring from backup" "ERROR"
        if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
            restore_from_backup "${backup_dir}"
        fi
        return 1
    fi
    
    # Phase 6: Restore credentials if saved
    if [ -n "$saved_creds" ] && [ "$fresh_install" = false ]; then
        log_message "Restoring saved credentials..."
        save_hf_token "$saved_creds"
    fi
    
    # Phase 7: Cleanup successful - remove backup (if one was created)
    if [ "$no_backup" = false ] && [ -d "${backup_dir}" ]; then
        log_message "Reinstall successful - cleaning up backup..."
        rm -rf "${backup_dir}"
        
        # Clean up old installation backups according to retention policy
        if command -v cleanup_installation_backups >/dev/null 2>&1; then
            cleanup_installation_backups
        fi
    fi
    
    log_message "STING atomic reinstallation completed successfully!" "SUCCESS"
    
    # Cross-platform permission notice
    echo ""
    log_message "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:" "WARNING"
    log_message "   Please run the permission fix script after installation:"
    log_message "   STING/fix_permissions.sh"
    echo ""
    
    return 0
}

# Helper function to restore from backup
restore_from_backup() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        log_message "No valid backup directory provided" "ERROR"
        return 1
    fi
    
    log_message "Restoring installation from backup..." "WARNING"
    
    # Remove any partial installation (handle permission issues)
    if [ -d "${INSTALL_DIR}" ]; then
        # Try normal removal first
        if ! rm -rf "${INSTALL_DIR}" 2>/dev/null; then
            # If that fails, try with sudo for Docker-owned files
            log_message "Normal removal failed, trying with elevated permissions..."
            sudo rm -rf "${INSTALL_DIR}" || {
                log_message "WARNING: Could not fully remove ${INSTALL_DIR}, some files may remain"
            }
        fi
    fi
    
    # Save current directory before restore
    local current_dir="$(pwd 2>/dev/null || echo "$HOME")"
    
    # Restore from backup
    if cd "$HOME" && rsync -a --delete "${backup_dir}/" "${INSTALL_DIR}/"; then
        # Return to original directory if it still exists
        [ -d "$current_dir" ] && cd "$current_dir"
        # Ensure manage_sting.sh has execute permissions after restore
        if [ -f "${INSTALL_DIR}/manage_sting.sh" ]; then
            if ! chmod +x "${INSTALL_DIR}/manage_sting.sh" 2>/dev/null; then
                log_message "WARNING: Failed to set execute permissions on manage_sting.sh after restore" "WARNING"
                log_message "Services may still work, but 'msting' command requires: chmod +x ${INSTALL_DIR}/manage_sting.sh" "WARNING"
            else
                log_message "Execute permissions set on manage_sting.sh"
            fi
        fi
        log_message "Installation restored from backup successfully"
        log_message "Backup directory preserved at: ${backup_dir}"
        return 0
    else
        log_message "Failed to restore from backup!" "ERROR"
        log_message "Manual recovery required from: ${backup_dir}" "ERROR"
        return 1
    fi
}

# Helper function to verify installation health
verify_installation_health() {
    log_message "Checking critical files..."
    
    # Check for essential files
    local critical_files=(
        "${INSTALL_DIR}/manage_sting.sh"
        "${INSTALL_DIR}/lib/installation.sh"
        "${INSTALL_DIR}/lib/services.sh"
        "${INSTALL_DIR}/conf/config.yml"
        "${INSTALL_DIR}/conf/config_loader.py"
    )
    
    for file in "${critical_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_message "Critical file missing: $file" "ERROR"
            return 1
        fi
    done
    
    # Check that manage_sting.sh is executable - auto-fix if not
    if [ ! -x "${INSTALL_DIR}/manage_sting.sh" ]; then
        log_message "manage_sting.sh is not executable - attempting to fix permissions..." "WARNING"
        if chmod +x "${INSTALL_DIR}/manage_sting.sh" 2>/dev/null; then
            log_message "Successfully fixed manage_sting.sh permissions" "SUCCESS"
        else
            log_message "Failed to fix manage_sting.sh permissions - may need manual intervention" "WARNING"
            # Don't fail installation for permission issues - user can fix later
        fi
    fi
    
    # Test basic functionality only if file is executable
    if [ -x "${INSTALL_DIR}/manage_sting.sh" ]; then
        if ! "${INSTALL_DIR}/manage_sting.sh" help >/dev/null 2>&1; then
            log_message "manage_sting.sh help command failed - script may have issues" "WARNING"
            # Don't fail for help command - core services might still work
        fi
    else
        log_message "Skipping manage_sting.sh functionality test due to permission issues" "WARNING"
    fi
    
    log_message "Installation health check passed"
    return 0
}

# Check and install system dependencies
# Check and fix Docker IPv6 connectivity issues
check_docker_ipv6() {
    log_message "Checking Docker networking configuration..."

    # Test if Docker can reach registry via IPv6
    local test_result=$(docker run --rm busybox:latest wget --spider --timeout=5 https://registry-1.docker.io 2>&1)

    if echo "$test_result" | grep -q "network is unreachable\|Connection refused"; then
        log_message "⚠️  Docker IPv6 connectivity issue detected" "WARNING"
        log_message "Configuring Docker to use IPv4..." "INFO"

        # Backup existing daemon.json if it exists
        if [ -f /etc/docker/daemon.json ]; then
            sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%s) 2>/dev/null || true
            log_message "Existing Docker config backed up"
        fi

        # Create/update daemon.json to disable IPv6 and add registry mirrors
        sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "ipv6": false,
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"],
  "registry-mirrors": [
    "https://mirror.gcr.io",
    "https://dockerhub.azk8s.cn"
  ],
  "max-concurrent-downloads": 10
}
EOF

        log_message "Restarting Docker daemon..."
        sudo systemctl restart docker
        sleep 3

        # Verify fix
        if docker run --rm busybox:latest wget --spider --timeout=5 https://registry-1.docker.io >/dev/null 2>&1; then
            log_message "✅ Docker networking fixed" "SUCCESS"
        else
            log_message "⚠️  Docker networking may still have issues, but continuing..." "WARNING"
        fi
    else
        log_message "✅ Docker networking is working correctly" "SUCCESS"
    fi
}

# Pre-pull all required Docker images with retry logic and fallback registries
prepull_docker_images() {
    log_message "Pre-pulling required Docker images..."

    # Define images with fallback registries
    # Format: "primary_image|fallback_image|description"
    local images=(
        "oryd/kratos:v1.3.0|ghcr.io/ory/kratos:v1.3.0|Kratos"
        "hashicorp/vault:1.13||Vault"
        "postgres:16||PostgreSQL"
        "redis:7-alpine||Redis"
        "axllent/mailpit:latest|ghcr.io/axllent/mailpit:latest|Mailpit"
        "chromadb/chroma:0.5.20||Chroma"
    )

    local pull_failed=0

    for image_spec in "${images[@]}"; do
        IFS='|' read -r primary_image fallback_image description <<< "$image_spec"

        log_message "Pulling $description ($primary_image)..."

        # Try pulling primary image with 2 retries
        local retries=2
        local success=false

        for ((i=1; i<=retries; i++)); do
            if docker pull "$primary_image" >/dev/null 2>&1; then
                log_message "  ✓ $description from primary registry" "SUCCESS"
                success=true
                break
            else
                if [ $i -lt $retries ]; then
                    log_message "  Retry $i/$retries for $primary_image..." "WARNING"
                    sleep 2
                fi
            fi
        done

        # If primary failed and fallback exists, try fallback
        if [ "$success" = false ] && [ -n "$fallback_image" ]; then
            log_message "  Trying fallback registry for $description..." "WARNING"
            if docker pull "$fallback_image" >/dev/null 2>&1; then
                # Tag fallback image as primary for docker-compose compatibility
                docker tag "$fallback_image" "$primary_image" >/dev/null 2>&1
                log_message "  ✓ $description from fallback registry (tagged as $primary_image)" "SUCCESS"
                success=true
            fi
        fi

        if [ "$success" = false ]; then
            log_message "  ✗ Failed to pull $description after trying all registries" "ERROR"
            pull_failed=1
        fi
    done

    if [ $pull_failed -eq 1 ]; then
        log_message "Some images failed to pull. Installation may fail." "WARNING"
        log_message "Check your internet connection and Docker configuration." "WARNING"
        return 1
    fi

    log_message "✅ All Docker images pulled successfully" "SUCCESS"
    return 0
}

check_and_install_dependencies() {
    log_message "Checking system dependencies..."

    log_message "DEBUG: Starting dependency checks..."
    local critical_deps=()
    local optional_deps=()

    # Check and fix Docker IPv6 issues first
    check_docker_ipv6 || log_message "Docker networking check had warnings, continuing..." "WARNING"

    # Pre-pull Docker images to catch connectivity issues early
    prepull_docker_images || log_message "Image pre-pull had warnings, continuing..." "WARNING"

    # Note: Python dependencies removed - using utils container for all Python operations
    log_message "DEBUG: Skipping Python dependency checks (using containerized approach)"

    # Check for python3 (CRITICAL - required for setup wizard)
    # On macOS, Python should be installed via Homebrew
    # On Linux, we can install via apt-get/yum
    if ! command -v python3 >/dev/null 2>&1; then
        if [[ "$(uname)" == "Darwin" ]]; then
            log_message "python3 not found on macOS" "ERROR"
            log_message "Please install Python via Homebrew: brew install python3" "ERROR"
            return 1
        else
            # Linux - can auto-install
            critical_deps+=("python3")
            log_message "python3 not found - CRITICAL for setup wizard" "WARNING"
        fi
    fi

    # Check for python3-venv (CRITICAL - required for setup wizard)
    # On Ubuntu 24.10+, need version-specific package (e.g., python3.12-venv)
    # On macOS, venv is included with Homebrew Python
    # Note: Test actual venv creation, not just --help
    local test_venv_dir="/tmp/sting-venv-test-$$"
    if ! python3 -m venv "$test_venv_dir" >/dev/null 2>&1; then
        # Clean up failed test venv
        rm -rf "$test_venv_dir" 2>/dev/null || true

        if [[ "$(uname)" == "Darwin" ]]; then
            # macOS - venv should be included with Homebrew Python
            log_message "python3 venv not working on macOS" "ERROR"
            log_message "Please reinstall Python via Homebrew: brew reinstall python3" "ERROR"
            return 1
        else
            # Linux - need to install venv package
            # Get Python version (e.g., 3.12)
            local py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3")

            # Note: We add both version-specific and generic packages
            # On Ubuntu 24.10+: python3.12-venv exists, python3-venv may not
            # On Ubuntu 20.04/22.04: python3-venv exists, python3.X-venv may not
            # We'll try version-specific first, then fall back to generic
            critical_deps+=("python${py_version}-venv")
            critical_deps+=("python3-venv")
            log_message "python3-venv not working - CRITICAL for setup wizard" "WARNING"
            log_message "Will try python${py_version}-venv, then fallback to python3-venv" "INFO"
        fi
    else
        # Clean up successful test venv
        rm -rf "$test_venv_dir" 2>/dev/null || true
        log_message "python3-venv is working" "INFO"
    fi

    # Check for python3-pip (CRITICAL - required for setup wizard)
    if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
        if [[ "$(uname)" == "Darwin" ]]; then
            log_message "pip not found on macOS" "ERROR"
            log_message "Please reinstall Python via Homebrew: brew reinstall python3" "ERROR"
            return 1
        else
            critical_deps+=("python3-pip")
            log_message "python3-pip not found - CRITICAL for setup wizard" "WARNING"
        fi
    fi

    # Check for jq (helpful for status checks and JSON parsing, but not critical)
    if ! command -v jq >/dev/null 2>&1; then
        optional_deps+=("jq")
        log_message "jq not found - optional dependency" "INFO"
    fi
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_message "Docker is not installed. Installing Docker..."
        if ! install_docker; then
            log_message "Failed to install Docker" "ERROR"
            return 1
        fi
    else
        # Docker is installed - check if it's snap version
        if detect_snap_docker; then
            log_message "Detected snap-based Docker installation" "WARNING"
            log_message "Snap Docker has limitations with /opt directory access"
            log_message "Automatically replacing with native apt-based Docker..." "INFO"

            if ! fix_snap_docker; then
                log_message "Failed to replace snap Docker" "ERROR"
                log_message "Manual fix: sudo snap remove docker && sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin" "ERROR"
                return 1
            fi

            log_message "Docker successfully upgraded from snap to apt version" "SUCCESS"
        fi
    fi

    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        log_message "Docker Compose is not available" "ERROR"
        return 1
    fi
    
    # Install CRITICAL dependencies first (fail hard if these don't install)
    if [ ${#critical_deps[@]} -gt 0 ]; then
        log_message "Installing CRITICAL dependencies: ${critical_deps[*]}"

        if command -v apt-get >/dev/null 2>&1; then
            # Retry apt-get update up to 3 times with backoff
            local update_success=false
            for attempt in 1 2 3; do
                log_message "Updating package lists (attempt $attempt/3)..."
                if sudo apt-get update 2>&1 | tee /tmp/apt-update.log; then
                    update_success=true
                    break
                else
                    log_message "apt-get update failed (attempt $attempt/3)" "WARNING"
                    if [ $attempt -lt 3 ]; then
                        log_message "Retrying in 5 seconds..."
                        sleep 5
                    fi
                fi
            done

            if [ "$update_success" = false ]; then
                log_message "Failed to update package lists after 3 attempts" "ERROR"
                log_message "Cannot proceed without installing critical dependencies" "ERROR"
                log_message "Please check your network connection and /etc/apt/sources.list" "ERROR"
                return 1
            fi

            # Separate python-venv packages for special handling (they have fallbacks)
            local venv_deps=()
            local other_deps=()
            for dep in "${critical_deps[@]}"; do
                if [[ "$dep" =~ venv ]]; then
                    venv_deps+=("$dep")
                else
                    other_deps+=("$dep")
                fi
            done

            # Install non-venv critical deps first
            if [ ${#other_deps[@]} -gt 0 ]; then
                log_message "Installing critical dependencies: ${other_deps[*]}"
                if ! sudo apt-get install -y "${other_deps[@]}" 2>&1 | tee /tmp/apt-install-critical.log; then
                    log_message "Failed to install CRITICAL dependencies: ${other_deps[*]}" "ERROR"
                    log_message "Installation cannot continue without these packages" "ERROR"
                    log_message "Check /tmp/apt-install-critical.log for details" "ERROR"
                    return 1
                fi
            fi

            # Install venv packages with fallback logic
            if [ ${#venv_deps[@]} -gt 0 ]; then
                log_message "Installing Python venv packages with fallback..."
                local venv_installed=false

                # Try each venv package until one succeeds
                for venv_pkg in "${venv_deps[@]}"; do
                    log_message "Trying to install $venv_pkg..."
                    if sudo apt-get install -y "$venv_pkg" 2>&1 | tee -a /tmp/apt-install-critical.log; then
                        log_message "$venv_pkg installed successfully" "SUCCESS"
                        venv_installed=true
                        break
                    else
                        log_message "$venv_pkg not available, trying next option..." "WARNING"
                    fi
                done

                if [ "$venv_installed" = false ]; then
                    log_message "Failed to install any Python venv package" "ERROR"
                    log_message "Tried: ${venv_deps[*]}" "ERROR"
                    return 1
                fi
            fi

            # Verify Python is now available if it was in critical deps
            if [[ " ${critical_deps[*]} " =~ " python3 " ]]; then
                if ! command -v python3 >/dev/null 2>&1; then
                    log_message "Python3 installation failed - command not available" "ERROR"
                    return 1
                fi
            fi

            log_message "Critical dependencies installed successfully" "SUCCESS"
        elif command -v yum >/dev/null 2>&1; then
            if ! sudo yum install -y "${critical_deps[@]}"; then
                log_message "Failed to install critical dependencies" "ERROR"
                return 1
            fi
        else
            log_message "Unable to install dependencies automatically. Please install: ${critical_deps[*]}" "ERROR"
            return 1
        fi
    fi

    # Install OPTIONAL dependencies (non-fatal if these fail)
    if [ ${#optional_deps[@]} -gt 0 ]; then
        log_message "Installing optional dependencies: ${optional_deps[*]}"

        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get install -y "${optional_deps[@]}" 2>&1 | tee /tmp/apt-install-optional.log || {
                log_message "Failed to install some optional dependencies: ${optional_deps[*]}" "WARNING"
                log_message "This may limit some functionality but installation will continue" "INFO"
            }
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y "${optional_deps[@]}" || log_message "Optional dependencies installation failed" "WARNING"
        fi
    fi
    
    # Check for libmagic (required for knowledge service)
    log_message "Checking libmagic for knowledge service..."
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Use Homebrew
        if ! command -v brew >/dev/null 2>&1; then
            log_message "Homebrew not found. Please install Homebrew first." "ERROR"
            log_message "Visit: https://brew.sh" "ERROR"
            return 1
        fi
        
        # Tell Homebrew to use non-interactive sudo (avoid TouchID prompts)
        # This works because we've already authenticated sudo in install_sting.sh
        export HOMEBREW_NO_INTERACTIVE=1
        export HOMEBREW_NO_ENV_HINTS=1
        
        # Check and install libmagic
        if ! brew list libmagic >/dev/null 2>&1; then
            log_message "Installing libmagic via Homebrew..."
            # Ensure we're in a valid directory for brew to work
            local original_dir="$(pwd)"
            cd /tmp || cd "$HOME" || cd /
            export PWD="$(pwd)"
            
            if ! brew install libmagic; then
                log_message "Failed to install libmagic" "ERROR"
                # Try to restore original directory if it exists
                [ -d "$original_dir" ] && cd "$original_dir" || true
                return 1
            fi
            
            # Try to restore original directory if it exists
            [ -d "$original_dir" ] && cd "$original_dir" || true
        else
            log_message "libmagic already installed"
        fi
        
        # Check and install jq
        if ! brew list jq >/dev/null 2>&1; then
            log_message "Installing jq via Homebrew..."
            local original_dir="$(pwd)"
            cd /tmp || cd "$HOME" || cd /
            export PWD="$(pwd)"
            
            if ! brew install jq; then
                log_message "Failed to install jq" "ERROR"
                [ -d "$original_dir" ] && cd "$original_dir" || true
                return 1
            fi
            
            [ -d "$original_dir" ] && cd "$original_dir" || true
        else
            log_message "jq already installed"
        fi
    else
        # Linux: Use system package manager
        if command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            # Check if libmagic-dev is installed (which is what we actually need)
            if ! dpkg -l libmagic-dev 2>/dev/null | grep -q "^ii"; then
                log_message "libmagic-dev not found, attempting installation..."

                # Retry apt-get update up to 3 times
                local update_success=false
                for attempt in 1 2 3; do
                    log_message "Updating package lists for libmagic (attempt $attempt/3)..."
                    if sudo apt-get update 2>&1 | tee /tmp/apt-update-libmagic.log; then
                        update_success=true
                        break
                    else
                        log_message "apt-get update failed (attempt $attempt/3)" "WARNING"
                        if [ $attempt -lt 3 ]; then
                            sleep 5
                        fi
                    fi
                done

                if [ "$update_success" = false ]; then
                    log_message "Failed to update package lists for libmagic" "WARNING"
                    log_message "Skipping libmagic installation - knowledge service may not work properly" "WARNING"
                    log_message "You can install it later with: sudo apt-get install libmagic-dev" "INFO"
                    return 0  # Non-fatal, continue installation
                fi

                # Try to install libmagic-dev
                if sudo apt-get install -y libmagic-dev 2>&1 | tee /tmp/apt-install-libmagic.log; then
                    log_message "libmagic-dev installation completed successfully" "SUCCESS"
                else
                    log_message "Failed to install libmagic-dev" "WARNING"
                    log_message "Knowledge service may not work properly without it" "WARNING"
                    log_message "You can install it later with: sudo apt-get install libmagic-dev" "INFO"
                    # Non-fatal - continue installation
                fi
            else
                log_message "libmagic already installed" "SUCCESS"
            fi
        elif command -v yum >/dev/null 2>&1; then
            # RHEL/CentOS/Fedora
            if ! rpm -q file-libs >/dev/null 2>&1; then
                log_message "Installing libmagic via yum..."
                if ! sudo yum install -y file-libs file-devel; then
                    log_message "Failed to install libmagic" "ERROR"
                    return 1
                fi
            else
                log_message "libmagic already installed"
            fi
        elif command -v dnf >/dev/null 2>&1; then
            # Modern Fedora
            if ! rpm -q file-libs >/dev/null 2>&1; then
                log_message "Installing libmagic via dnf..."
                if ! sudo dnf install -y file-libs file-devel; then
                    log_message "Failed to install libmagic" "ERROR"
                    return 1
                fi
            else
                log_message "libmagic already installed"
            fi
        else
            log_message "Unsupported package manager. Please install libmagic manually." "WARNING"
            log_message "Required packages: libmagic1, libmagic-dev (Debian/Ubuntu) or file-libs, file-devel (RHEL/CentOS)" "WARNING"
        fi
    fi
    
    log_message "All dependencies are satisfied" "SUCCESS"
    return 0
}

# Install Node.js
install_nodejs() {
    log_message "Checking Node.js installation..."
    
    # Check if Node.js is already installed
    if command -v node >/dev/null 2>&1; then
        local node_version
        node_version=$(node -v)
        log_message "Node.js is already installed: $node_version"
        
        # Check if npm is installed
        if command -v npm >/dev/null 2>&1; then
            local npm_version
            npm_version=$(npm -v)
            log_message "npm is already installed: $npm_version"
            return 0
        fi
    fi
    
    log_message "Installing Node.js..."
    
    # Determine if we need sudo
    local SUDO=""
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
    fi
    
    if command -v apt-get >/dev/null 2>&1; then
        # Install Node.js on Debian/Ubuntu
        curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
        $SUDO apt-get install -y nodejs
    elif command -v yum >/dev/null 2>&1; then
        # Install Node.js on RHEL/CentOS
        curl -fsSL https://rpm.nodesource.com/setup_20.x | $SUDO bash -
        $SUDO yum install -y nodejs
    else
        log_message "Unable to install Node.js automatically. Please install Node.js 20.x manually." "ERROR"
        return 1
    fi
    
    # Verify installation
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        log_message "Node.js installed successfully: $(node -v)" "SUCCESS"
        log_message "npm installed successfully: $(npm -v)" "SUCCESS"
        return 0
    else
        log_message "Node.js installation failed" "ERROR"
        return 1
    fi
}

# Detect if Docker is installed via snap
detect_snap_docker() {
    # Check if docker command is from snap
    if command -v docker >/dev/null 2>&1; then
        local docker_path=$(which docker)
        if [[ "$docker_path" == *"/snap/"* ]]; then
            return 0  # Is snap Docker
        fi

        # Also check snap list
        if command -v snap >/dev/null 2>&1; then
            if snap list 2>/dev/null | grep -q "^docker "; then
                return 0  # Is snap Docker
            fi
        fi
    fi

    return 1  # Not snap Docker
}

# Fix snap Docker by replacing with apt version
fix_snap_docker() {
    log_message "Removing snap Docker installation..."

    # Stop any running containers first
    docker ps -q 2>/dev/null | xargs -r docker stop 2>/dev/null || true

    # Remove snap Docker
    if command -v snap >/dev/null 2>&1; then
        sudo snap remove --purge docker 2>/dev/null || true
    fi

    # Small delay to ensure snap cleanup completes
    sleep 2

    # Install proper Docker via apt
    log_message "Installing native Docker from apt repository..."
    if ! install_docker; then
        log_message "Failed to install apt-based Docker" "ERROR"
        return 1
    fi

    # Verify new installation is not snap
    if detect_snap_docker; then
        log_message "Docker is still snap-based after fix attempt" "ERROR"
        return 1
    fi

    log_message "Docker successfully replaced with apt version" "SUCCESS"
    log_message "NOTE: You may need to restart your session for Docker group changes to take effect"

    return 0
}

# Install Docker
install_docker() {
    log_message "Installing Docker Engine..."

    # This installation is for Debian/Ubuntu systems
    if ! command -v apt-get >/dev/null 2>&1; then
        log_message "Docker installation script only supports Debian/Ubuntu systems" "ERROR"
        log_message "Please install Docker manually from https://docs.docker.com/get-docker/"
        return 1
    fi

    # Update package index with retry
    local update_success=false
    for attempt in 1 2 3; do
        log_message "Updating package lists for Docker install (attempt $attempt/3)..."
        if sudo apt-get update 2>&1 | tee /tmp/apt-update-docker.log; then
            update_success=true
            break
        else
            log_message "apt-get update failed (attempt $attempt/3)" "WARNING"
            if [ $attempt -lt 3 ]; then
                sleep 5
            fi
        fi
    done

    if [ "$update_success" = false ]; then
        log_message "Failed to update package lists after 3 attempts" "ERROR"
        log_message "Please check your network connection and /etc/apt/sources.list" "ERROR"
        log_message "You can install Docker manually later with the official script:" "INFO"
        log_message "  curl -fsSL https://get.docker.com | sh" "INFO"
        return 1
    fi

    # Install prerequisites
    log_message "Installing Docker prerequisites..."
    if ! sudo apt-get install -y ca-certificates curl gnupg lsb-release 2>&1 | tee /tmp/apt-install-docker-prereqs.log; then
        log_message "Failed to install prerequisites" "WARNING"
        log_message "Attempting to continue anyway..." "INFO"
    fi

    # Add Docker's official GPG key
    log_message "Adding Docker GPG key..."
    sudo mkdir -p /etc/apt/keyrings
    if ! curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null; then
        log_message "Failed to add Docker GPG key" "WARNING"
        log_message "Trying alternative method..." "INFO"
        # Try without dearmor if gpg fails
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.gpg > /dev/null || {
            log_message "Failed to add Docker GPG key - cannot continue" "ERROR"
            return 1
        }
    fi

    # Set up the repository
    log_message "Setting up Docker repository..."
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Update package index again with retry
    update_success=false
    for attempt in 1 2 3; do
        log_message "Updating package lists with Docker repo (attempt $attempt/3)..."
        if sudo apt-get update 2>&1 | tee -a /tmp/apt-update-docker.log; then
            update_success=true
            break
        else
            if [ $attempt -lt 3 ]; then
                sleep 5
            fi
        fi
    done

    if [ "$update_success" = false ]; then
        log_message "Failed to update with Docker repository" "ERROR"
        return 1
    fi

    # Install Docker Engine and Docker Compose plugin
    log_message "Installing Docker packages..."
    if ! sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>&1 | tee /tmp/apt-install-docker.log; then
        log_message "Failed to install Docker packages" "ERROR"
        log_message "Check /tmp/apt-install-docker.log for details" "ERROR"
        return 1
    fi

    # Add current user to docker group
    sudo usermod -aG docker "$USER" || log_message "Warning: Failed to add user to docker group" "WARNING"

    # Verify installation
    if docker --version >/dev/null 2>&1; then
        log_message "Docker installed successfully" "SUCCESS"
        log_message "You may need to log out and back in for group changes to take effect" "INFO"
        return 0
    else
        log_message "Docker installation failed - docker command not available" "ERROR"
        return 1
    fi
}

# Install frontend dependencies
install_frontend_dependencies() {
    log_message "Installing frontend dependencies..."
    
    if [ ! -d "${INSTALL_DIR}/frontend" ]; then
        log_message "Frontend directory not found" "ERROR"
        return 1
    fi
    
    cd "${INSTALL_DIR}/frontend" || return 1
    
    if [ -f "package.json" ]; then
        log_message "Running npm install..."
        npm install
        return $?
    else
        log_message "package.json not found in frontend directory" "ERROR"
        return 1
    fi
}

# Install development dependencies
install_dev_dependencies() {
    log_message "Installing development dependencies..."
    
    # Wait for utils container to be ready
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker compose ps utils 2>/dev/null | grep -q "Up"; then
            break
        fi
        log_message "Waiting for utilities container... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Install Python development dependencies
    if docker compose exec -T utils pip install -r requirements-dev.txt 2>/dev/null; then
        log_message "Development dependencies installed successfully" "SUCCESS"
        return 0
    else
        log_message "Failed to install development dependencies" "ERROR"
        return 1
    fi
}

# Install msting command
install_msting_command() {
    log_message "Installing msting command..."
    
    # Remove any stale .venv directories that could cause command conflicts
    if [ -d "${INSTALL_DIR}/.venv" ]; then
        log_message "Removing existing .venv directory to prevent command conflicts..."
        rm -rf "${INSTALL_DIR}/.venv"
    fi
    
    local target_path="/usr/local/bin/msting"
    local source_path="${INSTALL_DIR}/manage_sting.sh"
    
    # Create a wrapper script that calls the installed version
    local wrapper_content="#!/bin/bash
# msting - STING Community Edition Management Command
# This wrapper calls the installed manage_sting.sh script

# Determine install directory
if [[ \"\$(uname)\" == \"Darwin\" ]]; then
    INSTALL_DIR=\"\${INSTALL_DIR:-\$HOME/.sting-ce}\"
else
    INSTALL_DIR=\"\${INSTALL_DIR:-/opt/sting-ce}\"
fi

# Call the actual script using bash explicitly (doesn't require execute perms)
exec bash \"\$INSTALL_DIR/manage_sting.sh\" \"\$@\"
"
    
    # Ensure /usr/local/bin exists
    # Note: This should have been created during pre-installation sudo setup
    # Use -n flag to avoid password prompts (keepalive should handle this)
    if [ ! -d "/usr/local/bin" ]; then
        if ! sudo -n mkdir -p /usr/local/bin 2>/dev/null; then
            log_message "Failed to create /usr/local/bin directory (sudo not available)" "WARNING"
            log_message "The msting command may not be accessible system-wide" "WARNING"
            # Don't fail - user can still use full path
            return 0
        fi
    fi

    # Try to create wrapper without sudo first (since user owns /usr/local/bin on macOS)
    if echo "$wrapper_content" > "$target_path" 2>/dev/null && chmod +x "$target_path" 2>/dev/null; then
        log_message "msting command installed successfully" "SUCCESS"
    elif echo "$wrapper_content" | sudo -n tee "$target_path" >/dev/null 2>&1; then
        sudo -n chmod +x "$target_path" 2>/dev/null
        log_message "msting command installed successfully with sudo" "SUCCESS"
    else
        log_message "Could not create /usr/local/bin/msting (non-interactive sudo)" "WARNING"
        log_message "You can still use STING with the full path:" "INFO"
        log_message "  ${INSTALL_DIR}/manage_sting.sh" "INFO"
        # Don't fail - installation can continue
    fi
}

# Install Python packages with progress indicator
pip_install_with_progress() {
    local package="$1"
    local pip_args="${2:-}"
    
    echo -n "Installing $package"
    
    # Run pip install in background
    pip install --prefer-binary $pip_args "$package" > /tmp/pip_install_$$.log 2>&1 &
    local pip_pid=$!
    
    # Show progress spinner
    local spin='-\|/'
    local i=0
    while kill -0 $pip_pid 2>/dev/null; do
        i=$(( (i+1) %4 ))
        printf "\rInstalling $package ${spin:$i:1}"
        sleep 0.1
    done
    
    # Check if installation succeeded
    wait $pip_pid
    local result=$?
    
    if [ $result -eq 0 ]; then
        printf "\rInstalling $package... done\n"
    else
        printf "\rInstalling $package... failed\n"
        cat /tmp/pip_install_$$.log
    fi
    
    rm -f /tmp/pip_install_$$.log
    return $result
}


# Helper function: Check for LLM models
check_llm_models() {
    log_message "Checking for LLM models..."
    
    local models_dir
    models_dir=$(ensure_models_dir)
    
    # Check if any model files exist
    if [ -d "$models_dir" ] && find "$models_dir" -name "*.bin" -o -name "*.gguf" | grep -q .; then
        log_message "LLM models found in $models_dir"
        return 0
    else
        log_message "No LLM models found"
        return 1
    fi
}

# Helper function: Ensure HuggingFace CLI is available
ensure_hf_cli() {
    if ! command -v huggingface-cli >/dev/null 2>&1; then
        log_message "Installing HuggingFace CLI..."
        pip_install_with_progress "huggingface-hub[cli]"
        return $?
    fi
    return 0
}

# Helper function: Ensure HuggingFace authentication
ensure_hf_auth() {
    if [ -n "$HF_TOKEN" ]; then
        log_message "HuggingFace token configured (authentication will happen in containers)"
        # Authentication will be handled by the containers using the HF_TOKEN environment variable
        return 0
    fi
    log_message "No HuggingFace token available" "WARNING"
    return 1
}

# Helper function: Ensure models directory
# ensure_models_dir() {
#     if [[ "$(uname)" == "Darwin" ]]; then
#         # macOS: Use user's home directory
#         echo "$HOME/.sting/models"
#     else
#         # Linux: Use system directory
#         echo "/opt/sting-ce/models"
#     fi
# }

# Wait for Vault service to be ready
wait_for_vault() {
    log_message "Waiting for Vault to initialize..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Use docker exec directly to avoid docker compose warnings
        if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Initialized.*true"; then
            log_message "Vault is initialized"
            return 0
        fi
        log_message "Waiting for Vault... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Vault failed to initialize" "ERROR"
    return 1
}

# Validate database initialization and setup required databases/users
validate_database_initialization() {
    log_message "Validating database initialization..."
    
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_message "Database validation attempt $attempt/$max_attempts"
        
        # Check if required databases exist
        local missing_databases=()
        for db in kratos sting_app sting_messaging; do
            if ! docker exec sting-ce-db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw "$db"; then
                missing_databases+=("$db")
            fi
        done
        
        # Check if required users exist
        local missing_users=()
        for user in kratos_user app_user messaging_user; do
            if ! docker exec sting-ce-db psql -U postgres -c "\du" | grep -qw "$user"; then
                missing_users+=("$user")
            fi
        done
        
        if [ ${#missing_databases[@]} -eq 0 ] && [ ${#missing_users[@]} -eq 0 ]; then
            # Verify permissions by testing a simple CREATE operation
            if docker exec sting-ce-db psql -U kratos_user -d kratos -c "SELECT 1;" >/dev/null 2>&1; then
                log_message "Database validation successful - all databases and users properly configured" "SUCCESS"
                return 0
            else
                log_message "Database users exist but lack proper permissions" "WARNING"
            fi
        fi
        
        # Report what's missing
        if [ ${#missing_databases[@]} -gt 0 ]; then
            log_message "Missing databases: ${missing_databases[*]}" "WARNING"
        fi
        if [ ${#missing_users[@]} -gt 0 ]; then
            log_message "Missing database users: ${missing_users[*]}" "WARNING"
        fi
        
        # Attempt automatic repair
        log_message "Attempting to repair database initialization..."
        if repair_database_initialization; then
            log_message "Database repair attempted, retrying validation..."
        else
            log_message "Database repair failed" "ERROR"
        fi
        
        attempt=$((attempt + 1))
        [ $attempt -le $max_attempts ] && sleep 5
    done
    
    log_message "Database validation failed after $max_attempts attempts" "ERROR"
    return 1
}

# Repair database initialization by creating missing databases and users
repair_database_initialization() {
    log_message "Repairing database initialization..."
    
    # Create missing databases (ignore errors if they already exist)
    docker exec sting-ce-db psql -U postgres -c "CREATE DATABASE kratos;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -c "CREATE DATABASE sting_app;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -c "CREATE DATABASE sting_messaging;" 2>/dev/null || true
    
    # Create missing users with proper passwords (ignore errors if they already exist)
    docker exec sting-ce-db psql -U postgres -c "CREATE USER kratos_user WITH PASSWORD 'kratos_secure_password_change_me';" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -c "CREATE USER app_user WITH PASSWORD 'app_secure_password_change_me';" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -c "CREATE USER messaging_user WITH PASSWORD 'messaging_secure_password_change_me';" 2>/dev/null || true

    # Ensure postgres user has full schema permissions (critical for migrations)
    docker exec sting-ce-db psql -U postgres -d sting_app -c "GRANT ALL ON SCHEMA public TO postgres;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_app -c "ALTER SCHEMA public OWNER TO postgres;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d kratos -c "GRANT ALL ON SCHEMA public TO postgres;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d kratos -c "ALTER SCHEMA public OWNER TO postgres;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT ALL ON SCHEMA public TO postgres;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "ALTER SCHEMA public OWNER TO postgres;" 2>/dev/null || true
    
    # Grant proper permissions for kratos database
    docker exec sting-ce-db psql -U postgres -d kratos -c "GRANT ALL PRIVILEGES ON DATABASE kratos TO kratos_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d kratos -c "GRANT ALL PRIVILEGES ON SCHEMA public TO kratos_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d kratos -c "GRANT CREATE ON SCHEMA public TO kratos_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d kratos -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO kratos_user;" 2>/dev/null || true
    
    # Grant proper permissions for sting_app database  
    docker exec sting-ce-db psql -U postgres -d sting_app -c "GRANT ALL PRIVILEGES ON DATABASE sting_app TO app_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_app -c "GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_app -c "GRANT CREATE ON SCHEMA public TO app_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_app -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;" 2>/dev/null || true
    
    # Grant proper permissions for sting_messaging database
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO messaging_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT ALL PRIVILEGES ON SCHEMA public TO messaging_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT CREATE ON SCHEMA public TO messaging_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO messaging_user;" 2>/dev/null || true
    
    # Also grant app_user access to messaging database for cross-service operations
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;" 2>/dev/null || true
    docker exec sting-ce-db psql -U postgres -d sting_messaging -c "GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;" 2>/dev/null || true
    
    return 0
}

# Apply database migrations from database/migrations directory
apply_database_migrations() {
    log_message "Applying database migrations..."
    
    # Check if migrations directory exists
    local migrations_dir="${SOURCE_DIR}/database/migrations"
    if [ ! -d "$migrations_dir" ]; then
        log_message "No migrations directory found at $migrations_dir, skipping"
        return 0
    fi
    
    # Check if database container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^sting-ce-db$"; then
        log_message "Database container is not running, cannot apply migrations" "ERROR"
        return 1
    fi
    
    # Find all migration files (Python scripts and SQL files)
    local migration_files=()
    if [ -d "$migrations_dir" ]; then
        # Add Python migration files
        while IFS= read -r -d '' file; do
            migration_files+=("$file")
        done < <(find "$migrations_dir" -name "*.py" -print0 | sort -z)
        
        # Add SQL migration files
        while IFS= read -r -d '' file; do
            migration_files+=("$file")
        done < <(find "$migrations_dir" -name "*.sql" -print0 | sort -z)
    fi
    
    if [ ${#migration_files[@]} -eq 0 ]; then
        log_message "No migration files found, skipping"
        return 0
    fi
    
    log_message "Found ${#migration_files[@]} migration file(s) to apply"
    
    # Apply each migration
    local applied_count=0
    local failed_count=0
    
    for migration_file in "${migration_files[@]}"; do
        local migration_name=$(basename "$migration_file")
        log_message "Applying migration: $migration_name"
        
        if [[ "$migration_file" == *.py ]]; then
            # Apply Python migration
            if apply_python_migration "$migration_file"; then
                log_message "✅ Applied $migration_name"
                ((applied_count++))
            else
                log_message "❌ Failed to apply $migration_name" "WARNING"
                ((failed_count++))
            fi
        elif [[ "$migration_file" == *.sql ]]; then
            # Apply SQL migration
            if apply_sql_migration "$migration_file"; then
                log_message "✅ Applied $migration_name"
                ((applied_count++))
            else
                log_message "❌ Failed to apply $migration_name" "WARNING"
                ((failed_count++))
            fi
        else
            log_message "⏭️  Skipping unknown file type: $migration_name" "WARNING"
        fi
    done
    
    log_message "Migration summary: $applied_count applied, $failed_count failed"
    
    if [ $failed_count -gt 0 ]; then
        log_message "Some migrations failed - you may need to apply them manually" "WARNING"
        return 1
    fi
    
    return 0
}

# Apply a Python migration file
apply_python_migration() {
    local migration_file="$1"
    
    # Copy the migration file to a temporary location in the database container
    local temp_migration="/tmp/$(basename "$migration_file")"
    
    if docker cp "$migration_file" "sting-ce-db:$temp_migration" >/dev/null 2>&1; then
        # Run the Python migration inside the database container
        if docker exec sting-ce-db python3 "$temp_migration" >/dev/null 2>&1; then
            # Clean up
            docker exec sting-ce-db rm -f "$temp_migration" >/dev/null 2>&1 || true
            return 0
        else
            # Clean up on failure
            docker exec sting-ce-db rm -f "$temp_migration" >/dev/null 2>&1 || true
            return 1
        fi
    else
        return 1
    fi
}

# Apply a SQL migration file
apply_sql_migration() {
    local migration_file="$1"
    
    # Apply the SQL migration directly
    if docker exec -i sting-ce-db psql -U postgres -d sting_app < "$migration_file" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Verify LLM service is ready to serve requests
verify_llm_service_ready() {
    log_message "Verifying LLM service readiness..."
    local max_attempts=30
    local attempt=1
    local llm_port=8085  # Native LLM service port on macOS
    
    if [[ "$(uname)" != "Darwin" ]]; then
        llm_port=8086  # Docker LLM gateway port on Linux
    fi
    
    while [ $attempt -le $max_attempts ]; do
        # Check if service responds to health check
        if curl -s -f "http://localhost:${llm_port}/health" >/dev/null 2>&1; then
            log_message "LLM service health check passed"
            
            # Test basic functionality with a simple request
            if curl -s -f -X POST "http://localhost:${llm_port}/generate" \
                -H "Content-Type: application/json" \
                -d '{"prompt": "test", "max_tokens": 5}' >/dev/null 2>&1; then
                log_message "LLM service is ready and responding to requests" "SUCCESS"
                return 0
            else
                log_message "LLM service health OK but not responding to requests, attempt $attempt/$max_attempts"
            fi
        else
            log_message "LLM service health check failed, attempt $attempt/$max_attempts"
        fi
        
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_message "LLM service failed to become ready after $max_attempts attempts" "ERROR"
    return 1
}

# Start LLM services based on platform and configuration
start_llm_services() {
    log_message "Starting universal LLM gateway and external AI services..."
    
    # Start the universal LLM gateway proxy (works on all platforms)
    docker compose up -d llm-gateway-proxy
    
    # Start external AI service (connects to Ollama)
    docker compose up -d external-ai
    
    log_message "Universal LLM services started successfully"
    log_message "External AI service will connect to Ollama when available"
    
    return 0
}

# Show status of all services
show_status() {
    log_message "Service Status:"
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
}

# Check if all core services are healthy before starting LLM
check_core_services_health() {
    log_message "Checking core services health before LLM startup..."
    local max_attempts=30
    local attempt=1
    local failed_services=()
    
    # Essential services that must be healthy
    local essential_services=("db" "vault" "app" "frontend")
    
    for service in "${essential_services[@]}"; do
        attempt=1
        while [ $attempt -le $max_attempts ]; do
            if docker compose ps --format "{{.Name}}\t{{.Status}}" 2>/dev/null | grep "sting-ce-${service}" | grep -q "Up"; then
                # Service is up, check if it's healthy
                if docker compose exec -T "$service" echo "health check" >/dev/null 2>&1; then
                    log_message "✅ Service $service is healthy"
                    break
                fi
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                log_message "❌ Service $service failed health check after $max_attempts attempts" "ERROR"
                failed_services+=("$service")
                break
            fi
            
            log_message "⏳ Waiting for $service to be healthy... attempt $attempt/$max_attempts"
            sleep 5
            attempt=$((attempt + 1))
        done
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        log_message "❌ Failed services: ${failed_services[*]}" "ERROR"
        log_message "LLM service startup aborted due to unhealthy core services" "ERROR"
        return 1
    fi
    
    log_message "✅ All core services are healthy" "SUCCESS"
    return 0
}

# Start LLM service after installation with health checks
start_llm_service_post_install() {
    if [[ "$(uname)" != "Darwin" ]]; then
        log_message "LLM service auto-start is only supported on macOS" "WARNING"
        return 1
    fi
    
    # Check core services health first
    if ! check_core_services_health; then
        log_message "Cannot start LLM service due to unhealthy core services" "ERROR"
        return 1
    fi
    
    # Load native LLM module
    if ! source "${SCRIPT_DIR}/native_llm.sh"; then
        log_message "Failed to load native LLM module" "ERROR"
        return 1
    fi
    
    # Start the native LLM service
    log_message "🚀 Starting native LLM service..."
    if start_native_llm_service; then
        log_message "✅ LLM service started successfully!" "SUCCESS"
        
        # Verify the service is responding
        if verify_llm_service_ready; then
            log_message "🐝 Bee chatbot is now ready to use!" "SUCCESS"
            
            # Set up knowledge base with STING documentation
            setup_knowledge_base
        else
            log_message "⚠️  LLM service started but may not be fully ready" "WARNING"
        fi
    else
        log_message "❌ Failed to start LLM service" "ERROR"
        # show_llm_startup_notice  # Deprecated - LLM service is no longer used
        return 1
    fi
}

# Interactive prompt for LLM service startup
prompt_llm_service_startup() {
    if [[ "$(uname)" != "Darwin" ]]; then
        # show_llm_startup_notice  # Deprecated - LLM service is no longer used
        return
    fi
    
    echo ""
    echo -e "\033[1;33m🐝 STING installation completed successfully! \033[0m"
    echo ""
    echo -e "\033[1;36mWould you like to start the LLM service now to enable the Bee chatbot?\033[0m"
    echo ""
    echo "  This will:"
    echo "  • Check that all core services are healthy"
    echo "  • Start the native LLM service with Metal Performance Shaders (MPS)"
    echo "  • Enable the Bee chatbot for immediate use"
    echo ""
    echo "  ⚠️  Note: This uses significant memory/CPU resources"
    echo ""
    
    local choice
    while true; do
        read -p "Start LLM service now? (y/n): " choice
        case "$choice" in
            [Yy]* )
                echo ""
                start_llm_service_post_install
                break
                ;;
            [Nn]* )
                echo ""
                log_message "LLM service startup skipped - you can start it later with: ./sting-llm start"
                # show_llm_startup_notice  # Deprecated - LLM service is no longer used
                
                # Still set up knowledge base even without LLM service
                echo ""
                echo "Setting up knowledge base for future Bee Chat use..."
                setup_knowledge_base
                break
                ;;
            * )
                echo "Please answer yes (y) or no (n)."
                ;;
        esac
    done
}

# Show prominent notice about starting LLM service on macOS
# Setup comprehensive knowledge base for fresh installations
setup_knowledge_base() {
    echo ""
    echo -e "\033[1;33m🍯 Setting up STING knowledge base...\033[0m"
    echo ""
    
    # Wait a moment for services to be fully ready
    sleep 5
    
    # Run the setup script
    if [ -f "${PROJECT_DIR}/scripts/setup_default_honey_jars.py" ]; then
        echo "  📚 Populating honey jars with STING documentation..."
        
        # Use Python to run the setup script
        if command -v python3 >/dev/null 2>&1; then
            cd "${PROJECT_DIR}"
            python3 scripts/setup_default_honey_jars.py
            setup_result=$?
            
            if [ $setup_result -eq 0 ]; then
                echo ""
                echo -e "\033[1;32m✅ Knowledge base setup completed!\033[0m"
                echo ""
                echo "  🐝 Bee Chat is now ready with comprehensive STING knowledge!"
                echo ""
                echo "  💡 Try these test queries:"
                echo "     • 'What is STING and how does it work?'"
                echo "     • 'How can STING help my law firm?'"
                echo "     • 'What are STING's enterprise security features?'"
                echo ""
            else
                echo ""
                echo -e "\033[1;33m⚠️  Knowledge base setup encountered issues\033[0m"
                echo "  🔧 You can run it manually later:"
                echo "     python3 scripts/setup_default_honey_jars.py"
                echo ""
            fi
        else
            echo -e "\033[1;33m⚠️  Python3 not found, skipping knowledge base setup\033[0m"
            echo "  🔧 You can run it manually after installing Python3:"
            echo "     python3 scripts/setup_default_honey_jars.py"
            echo ""
        fi
    else
        echo -e "\033[1;33m⚠️  Setup script not found at: ${PROJECT_DIR}/scripts/setup_default_honey_jars.py\033[0m"
        echo ""
    fi
}

show_llm_startup_notice() {
    if [[ "$(uname)" == "Darwin" ]]; then
        echo ""
        echo -e "\033[1;36m╔═══════════════════════════════════════════════════════════════════════════════╗\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;33m🐝 IMPORTANT: Native LLM Service Setup Required for Bee Chatbot 🐝\033[1;36m        ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;37mThe native LLM service was not started during installation to prevent\033[1;36m      ║\033[0m"
        echo -e "\033[1;36m║  \033[1;37mDocker crashes. To enable the Bee chatbot, start it manually:\033[1;36m           ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;32m📋 Start LLM Service:\033[1;36m                                                   ║\033[0m"
        echo -e "\033[1;36m║     \033[1;97m./sting-llm start\033[1;36m                                                     ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;32m📋 Check LLM Status:\033[1;36m                                                    ║\033[0m"
        echo -e "\033[1;36m║     \033[1;97m./sting-llm status\033[1;36m                                                    ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;32m📋 Stop LLM Service:\033[1;36m                                                    ║\033[0m"
        echo -e "\033[1;36m║     \033[1;97m./sting-llm stop\033[1;36m                                                     ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;33m💡 Features:\033[1;36m                                                             ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Metal Performance Shaders (MPS) GPU acceleration\033[1;36m                    ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Phi-3 and TinyLlama models from HuggingFace\033[1;36m                       ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Dynamic context system support\033[1;36m                                    ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Automatic model downloading on first use\033[1;36m                          ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;31m⚠️  Note: Starting the LLM service uses significant memory/CPU.\033[1;36m          ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37mConsider stopping Docker services if you experience issues.\033[1;36m          ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m║  \033[1;32m💡 Quick Start Options:\033[1;36m                                              ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Install with LLM: ./install_sting.sh install --start-llm\033[1;36m           ║\033[0m"
        echo -e "\033[1;36m║     \033[1;37m• Install without prompts: ./install_sting.sh install --no-prompt\033[1;36m   ║\033[0m"
        echo -e "\033[1;36m║                                                                               ║\033[0m"
        echo -e "\033[1;36m╚═══════════════════════════════════════════════════════════════════════════════╝\033[0m"
        echo ""
    fi
}

# Install Ollama if enabled in configuration
install_ollama_if_enabled() {
    log_message \"Checking Ollama configuration...\"
    
    # Check for WSL2-specific handling first
    if [ -f \"${SOURCE_DIR}/lib/ollama_wsl2.sh\" ]; then
        source \"${SOURCE_DIR}/lib/ollama_wsl2.sh\"
        if is_wsl2_environment; then
            log_message \"WSL2 environment detected - using enhanced Ollama installation\"
            if ollama_wsl2_integration_check; then
                return 0
            else
                log_message \"WSL2 Ollama integration failed, falling back to standard method\" \"WARNING\"
            fi
        fi
    fi
    
    # Standard Ollama installation flow
    # Check if Ollama is enabled in config
    local ollama_enabled=\"true\"  # Default to true for new installations
    local ollama_auto_install=\"true\"
    
    # Try to read from config if available
    if [ -f \"${INSTALL_DIR}/env/llm-gateway.env\" ]; then
        if grep -q \"OLLAMA_ENABLED=false\" \"${INSTALL_DIR}/env/llm-gateway.env\" 2>/dev/null; then
            ollama_enabled=\"false\"
        fi
        if grep -q \"OLLAMA_AUTO_INSTALL=false\" \"${INSTALL_DIR}/env/llm-gateway.env\" 2>/dev/null; then
            ollama_auto_install=\"false\"
        fi
    fi
    
    if [ \"$ollama_enabled\" = \"false\" ]; then
        log_message \"Ollama is disabled in configuration, skipping installation\"
        return 0
    fi
    
    if [ \"$ollama_auto_install\" = \"false\" ]; then
        log_message \"Ollama auto-install is disabled, skipping installation\"
        log_message \"You can install manually with: ./manage_sting.sh install-ollama\"
        return 0
    fi
    
    # Check if Ollama is already installed
    if command -v ollama >/dev/null 2>&1; then
        log_message \"Ollama is already installed, checking status...\"
        if curl -sf http://localhost:11434/v1/models >/dev/null 2>&1; then
            log_message \"✅ Ollama is running and ready\"
            return 0
        else
            log_message \"Ollama is installed but not running, attempting to start...\"
            # Try to start Ollama
            if [ -f \"${SOURCE_DIR}/scripts/install_ollama.sh\" ]; then
                bash \"${SOURCE_DIR}/scripts/install_ollama.sh\" --start-only
            fi
        fi
    else
        log_message \"Installing Ollama for universal LLM support...\"
        if [ -f \"${SOURCE_DIR}/scripts/install_ollama.sh\" ]; then
            # Set environment variables for the install script
            export OLLAMA_AUTO_INSTALL=\"true\"
            export OLLAMA_MODELS_TO_INSTALL=\"phi3:mini,deepseek-r1:latest\"
            
            if bash \"${SOURCE_DIR}/scripts/install_ollama.sh\"; then
                log_message \"✅ Ollama installation completed successfully\"
            else
                log_message \"❌ Ollama installation failed\" \"ERROR\"
                log_message \"You can install manually later with: ./manage_sting.sh install-ollama\" \"INFO\"
                return 1
            fi
        else
            log_message \"Ollama install script not found, skipping\" \"WARNING\"
            return 1
        fi
    fi
    
    return 0
}

# Generate env.js files from templates with actual host IP
generate_env_js_files() {
    log_message "Generating environment configuration files for frontend..."

    # Get host IP (prioritize STING_HOST_IP, fallback to detected IP)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

    # Fallback to localhost if no IP detected
    if [ -z "$host_ip" ] || [ "$host_ip" = "127.0.0.1" ]; then
        host_ip="localhost"
    fi

    log_message "Using host IP for frontend: $host_ip"

    # Generate env.js for frontend build (used during build time)
    if [ -f "${INSTALL_DIR}/frontend/public/env.js.template" ]; then
        sed "s/__HOST_IP__/$host_ip/g" "${INSTALL_DIR}/frontend/public/env.js.template" > "${INSTALL_DIR}/frontend/public/env.js"
        log_message "✅ Generated frontend/public/env.js"
    else
        log_message "⚠️ frontend/public/env.js.template not found, skipping" "WARNING"
    fi

    # Generate env.js for app static files (served by Flask)
    if [ -f "${INSTALL_DIR}/app/static/env.js.template" ]; then
        sed "s/__HOST_IP__/$host_ip/g" "${INSTALL_DIR}/app/static/env.js.template" > "${INSTALL_DIR}/app/static/env.js"
        log_message "✅ Generated app/static/env.js"
    else
        log_message "⚠️ app/static/env.js.template not found, skipping" "WARNING"
    fi
}

# Validate authentication configuration consistency
# This catches hostname/RP ID mismatches BEFORE Docker build starts
validate_auth_config_consistency() {
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_message "🔍 Validating authentication configuration consistency..."
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Trim whitespace from hostname to avoid comparison issues
    local hostname=$(echo "$STING_HOSTNAME" | xargs)
    local errors=()
    local warnings=()

    # 1. Verify Kratos config exists
    if [ ! -f "${INSTALL_DIR}/kratos/kratos.yml" ]; then
        errors+=("❌ Kratos config not found at ${INSTALL_DIR}/kratos/kratos.yml")
        log_message "❌ CRITICAL: Kratos configuration validation failed!"
        for error in "${errors[@]}"; do
            log_message "   $error"
        done
        return 1
    fi

    # 2. Check for unsubstituted placeholders (critical error)
    if grep -q "__STING_HOSTNAME__" "${INSTALL_DIR}/kratos/kratos.yml"; then
        errors+=("❌ Kratos config still contains __STING_HOSTNAME__ placeholder!")
        errors+=("   Template substitution may have failed")
    fi

    # 3. Verify WebAuthn RP ID matches configured hostname
    # Use more specific pattern to match webauthn rp: section only, trim all whitespace
    local rp_id=$(grep -A20 "webauthn:" "${INSTALL_DIR}/kratos/kratos.yml" | grep -A10 "rp:" | grep "id:" | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'" | xargs)
    if [ -z "$rp_id" ]; then
        errors+=("❌ WebAuthn RP ID not found in Kratos config")
    elif [ "$rp_id" != "$hostname" ]; then
        errors+=("❌ WebAuthn RP ID mismatch!")
        errors+=("   Expected: '$hostname'")
        errors+=("   Got: '$rp_id'")
        errors+=("   This WILL cause passkey/WebAuthn failures!")
    else
        log_message "   ✅ WebAuthn RP ID: $rp_id"
    fi

    # 4. Verify WebAuthn origins include the hostname
    if ! grep -A20 "webauthn:" "${INSTALL_DIR}/kratos/kratos.yml" | grep -A10 "rp:" | grep "origins:" -A5 | grep -q "$hostname"; then
        errors+=("❌ WebAuthn origins don't include hostname '$hostname'")
    else
        log_message "   ✅ WebAuthn origins configured correctly"
    fi

    # 5. Verify CORS allowed_origins match hostname
    if ! grep -A5 "allowed_origins:" "${INSTALL_DIR}/kratos/kratos.yml" | grep -q "$hostname"; then
        errors+=("❌ CORS allowed_origins doesn't include '$hostname'")
    else
        log_message "   ✅ CORS origins configured correctly"
    fi

    # 6. Check frontend env.js (non-critical - might not exist yet)
    if [ -f "${INSTALL_DIR}/frontend/public/env.js" ]; then
        if ! grep -q "$hostname" "${INSTALL_DIR}/frontend/public/env.js"; then
            warnings+=("⚠️  Frontend env.js doesn't contain hostname '$hostname'")
        else
            log_message "   ✅ Frontend configuration matches hostname"
        fi
    fi

    # 7. Check for URL consistency (all should use same hostname)
    local unique_hosts=$(grep -E "https?://" "${INSTALL_DIR}/kratos/kratos.yml" | grep -o "https\?://[^:]*" | sort -u | wc -l)
    if [ "$unique_hosts" -gt 2 ]; then  # Allow both http:// and https:// variants
        warnings+=("⚠️  Multiple different hostnames found in Kratos config")
        warnings+=("   This may cause redirect/CORS issues")
    fi

    # 8. Special check for localhost (common misconfiguration)
    if [ "$hostname" != "localhost" ] && grep -q "localhost" "${INSTALL_DIR}/kratos/kratos.yml"; then
        # Count localhost occurrences (excluding comments)
        local localhost_count=$(grep -v "^#" "${INSTALL_DIR}/kratos/kratos.yml" | grep -c "localhost" || true)
        if [ "$localhost_count" -gt 0 ]; then
            warnings+=("⚠️  Found 'localhost' in config despite hostname being '$hostname'")
            warnings+=("   This may cause issues with remote access")
        fi
    fi

    # 9. DNS Resolution Check (for non-localhost/non-IP hostnames)
    if [ "$hostname" != "localhost" ] && [[ ! "$hostname" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_message "   🔍 Checking DNS resolution for '$hostname'..."

        # Try multiple resolution methods for best compatibility
        local dns_resolved=false

        # Method 1: getent hosts (most reliable, uses system resolver)
        if command -v getent &>/dev/null; then
            if getent hosts "$hostname" &>/dev/null; then
                dns_resolved=true
                local resolved_ip=$(getent hosts "$hostname" | head -1 | awk '{print $1}')
                log_message "   ✅ DNS resolution successful via getent: $resolved_ip"
            fi
        fi

        # Method 2: ping (fallback for systems without getent)
        if [ "$dns_resolved" = false ] && command -v ping &>/dev/null; then
            if ping -c 1 -W 2 "$hostname" &>/dev/null 2>&1; then
                dns_resolved=true
                log_message "   ✅ DNS resolution successful via ping"
            fi
        fi

        # Method 3: host/nslookup (alternative DNS lookup)
        if [ "$dns_resolved" = false ] && command -v host &>/dev/null; then
            if host "$hostname" &>/dev/null 2>&1; then
                dns_resolved=true
                log_message "   ✅ DNS resolution successful via host"
            fi
        fi

        if [ "$dns_resolved" = false ]; then
            warnings+=("⚠️  Hostname '$hostname' does not currently resolve via DNS")
            warnings+=("   This is OK if you plan to add it to /etc/hosts on client machines")

            # Special warning for .local domains
            if [[ "$hostname" =~ \.local$ ]]; then
                warnings+=("   Note: .local domains require mDNS/Avahi or manual /etc/hosts entry")
            fi
        fi
    fi

    # 10. .local domain special checks (mDNS/Avahi requirements)
    if [[ "$hostname" =~ \.local$ ]]; then
        log_message "   🔍 Checking .local domain mDNS support..."

        local mdns_available=false

        # Check for systemd-resolved (Linux)
        if command -v resolvectl &>/dev/null && systemctl is-active --quiet systemd-resolved 2>/dev/null; then
            mdns_available=true
            log_message "   ✅ systemd-resolved active (supports .local via mDNS)"
        # Check for Avahi (Linux alternative)
        elif command -v avahi-daemon &>/dev/null || systemctl is-active --quiet avahi-daemon 2>/dev/null; then
            mdns_available=true
            log_message "   ✅ Avahi daemon detected (supports .local via mDNS)"
        # macOS always supports .local via Bonjour
        elif [[ "$(uname)" == "Darwin" ]]; then
            mdns_available=true
            log_message "   ✅ macOS detected (native .local support via Bonjour)"
        fi

        if [ "$mdns_available" = false ]; then
            warnings+=("⚠️  .local hostname used but mDNS/Avahi not detected")
            warnings+=("   .local domains may not resolve without:")
            warnings+=("   - systemd-resolved (usually enabled by default on Ubuntu)")
            warnings+=("   - Avahi daemon (install: sudo apt install avahi-daemon)")
            warnings+=("   - OR manual /etc/hosts entries on all client machines")
        fi
    fi

    # 11. Cookie domain compatibility check
    # Ensure session cookies will work with the configured hostname
    local cookie_domain=$(grep -A5 "session:" "${INSTALL_DIR}/kratos/kratos.yml" | grep "domain:" | awk '{print $2}')
    if [ -n "$cookie_domain" ] && [ "$cookie_domain" != "$hostname" ]; then
        warnings+=("⚠️  Session cookie domain '$cookie_domain' differs from hostname '$hostname'")
        warnings+=("   This may cause session/login issues")
    else
        log_message "   ✅ Session cookie configuration compatible with hostname"
    fi

    # 12. SSL/TLS hostname validation check
    if [ "$hostname" != "localhost" ]; then
        log_message "   ℹ️  SSL certificates will be self-signed for hostname: $hostname"
        log_message "   ℹ️  Browsers will show security warnings until you install custom certs"
    fi

    # Report results
    log_message ""
    if [ ${#errors[@]} -eq 0 ]; then
        log_message "✅ Authentication configuration validation PASSED"
        log_message "   Configured hostname: $hostname"
        log_message "   WebAuthn RP ID: $rp_id"
        log_message "   All critical checks passed"

        if [ ${#warnings[@]} -gt 0 ]; then
            log_message ""
            log_message "⚠️  Warnings (non-critical):"
            for warning in "${warnings[@]}"; do
                log_message "   $warning"
            done
        fi

        log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_message ""
        return 0
    else
        log_message "❌ Authentication configuration validation FAILED"
        log_message ""
        log_message "Critical errors found:"
        for error in "${errors[@]}"; do
            log_message "   $error"
        done

        if [ ${#warnings[@]} -gt 0 ]; then
            log_message ""
            log_message "Warnings:"
            for warning in "${warnings[@]}"; do
                log_message "   $warning"
            done
        fi

        log_message ""
        log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_message "⚠️  These configuration issues WILL cause authentication failures!"
        log_message "   - Passkeys/WebAuthn will not work"
        log_message "   - Login/registration may fail"
        log_message "   - CORS errors may occur"
        log_message ""
        log_message "Recommended action: Fix configuration and retry installation"
        log_message "You can run './update_hostname.sh' after installation to fix hostname issues"
        log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_message ""

        # Don't fail installation, but warn heavily
        # Return 1 to signal validation failure (caller can decide whether to continue)
        return 1
    fi
}

# Configure hostname for WebAuthn/Passkey compatibility
configure_hostname() {
    log_message "Configuring hostname for WebAuthn/Passkey support..."

    # Source hostname detection library
    local script_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$script_lib_dir/hostname_detection.sh" ]; then
        source "$script_lib_dir/hostname_detection.sh"
    else
        log_message "⚠️ hostname_detection.sh not found, using localhost as fallback" "WARNING"
        export STING_HOSTNAME="localhost"
        return 0
    fi

    # Get hostname (interactive mode if not already set via env var)
    if [ -z "$STING_HOSTNAME" ]; then
        log_message "Detecting hostname for STING configuration..."
        STING_HOSTNAME=$(get_sting_hostname true)
    fi

    if [ -z "$STING_HOSTNAME" ]; then
        log_message "⚠️ No hostname detected, defaulting to localhost" "WARNING"
        STING_HOSTNAME="localhost"
    fi

    export STING_HOSTNAME
    log_message "Using hostname: $STING_HOSTNAME"

    # Generate kratos.yml from template
    if [ -f "${INSTALL_DIR}/kratos/kratos.yml.template" ]; then
        log_message "Generating kratos/kratos.yml from template..."
        sed "s/__STING_HOSTNAME__/$STING_HOSTNAME/g" \
            "${INSTALL_DIR}/kratos/kratos.yml.template" > \
            "${INSTALL_DIR}/kratos/kratos.yml"
        log_message "✅ Generated kratos/kratos.yml with hostname: $STING_HOSTNAME"
    else
        log_message "⚠️ kratos/kratos.yml.template not found, skipping Kratos config generation" "WARNING"
    fi

    # Update env.js files with hostname instead of IP for WebAuthn compatibility
    log_message "Updating frontend configuration with hostname..."

    # Detect OS for sed -i compatibility (macOS requires '', Linux doesn't)
    local sed_inplace_arg=""
    if [[ "$(uname)" == "Darwin" ]]; then
        sed_inplace_arg="-i ''"
    else
        sed_inplace_arg="-i"
    fi

    # Update frontend/public/env.js
    if [ -f "${INSTALL_DIR}/frontend/public/env.js" ]; then
        # Replace any existing hostname/IP with the configured hostname
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "${INSTALL_DIR}/frontend/public/env.js"
            sed -i '' "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "${INSTALL_DIR}/frontend/public/env.js"
            sed -i '' "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "${INSTALL_DIR}/frontend/public/env.js"
        else
            sed -i "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "${INSTALL_DIR}/frontend/public/env.js"
            sed -i "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "${INSTALL_DIR}/frontend/public/env.js"
            sed -i "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "${INSTALL_DIR}/frontend/public/env.js"
        fi
        log_message "✅ Updated frontend/public/env.js with hostname"
    fi

    # Update app/static/env.js
    if [ -f "${INSTALL_DIR}/app/static/env.js" ]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "${INSTALL_DIR}/app/static/env.js"
            sed -i '' "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "${INSTALL_DIR}/app/static/env.js"
            sed -i '' "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "${INSTALL_DIR}/app/static/env.js"
        else
            sed -i "s|PUBLIC_URL: '[^']*'|PUBLIC_URL: 'https://$STING_HOSTNAME:8443'|g" "${INSTALL_DIR}/app/static/env.js"
            sed -i "s|REACT_APP_API_URL: '[^']*'|REACT_APP_API_URL: 'https://$STING_HOSTNAME:5050'|g" "${INSTALL_DIR}/app/static/env.js"
            sed -i "s|REACT_APP_KRATOS_PUBLIC_URL: '[^']*'|REACT_APP_KRATOS_PUBLIC_URL: 'https://$STING_HOSTNAME:4433'|g" "${INSTALL_DIR}/app/static/env.js"
        fi
        log_message "✅ Updated app/static/env.js with hostname"
    fi

    # Update config.yml domain setting
    log_message "Updating config.yml with hostname..."
    if [ -f "${INSTALL_DIR}/conf/config.yml" ]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i '' "s/^  domain: .*/  domain: $STING_HOSTNAME/" "${INSTALL_DIR}/conf/config.yml"
        else
            sed -i "s/^  domain: .*/  domain: $STING_HOSTNAME/" "${INSTALL_DIR}/conf/config.yml"
        fi
        log_message "✅ Updated config.yml domain to: $STING_HOSTNAME"
    else
        log_message "⚠️ config.yml not found, skipping domain update" "WARNING"
    fi

    # Save hostname to .sting_domain file for future reference
    if [ "$STING_HOSTNAME" != "localhost" ]; then
        echo "$STING_HOSTNAME" > "${INSTALL_DIR}/.sting_domain"
        echo "https://${STING_HOSTNAME}:8443" > "${INSTALL_DIR}/.sting_url"
        log_message "✅ Saved hostname to .sting_domain file"
    fi

    # CRITICAL: Validate auth configuration consistency BEFORE Docker build
    # This catches hostname/RP ID mismatches early, saving time
    log_message ""
    validate_auth_config_consistency || {
        log_message "⚠️  Authentication validation failed, but continuing installation..."
        log_message "   You may need to run './update_hostname.sh' after installation to fix issues"
        log_message ""
    }

    # Show setup instructions
    log_message ""
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ "$STING_HOSTNAME" = "localhost" ]; then
        log_message "✅ Using localhost - WebAuthn will work on this machine only"
        log_message "   For remote access with passkeys, run: ./update_hostname.sh"
    else
        log_message "✅ Hostname configured: $STING_HOSTNAME"
        log_message ""
        log_message "📝 For remote access, add to /etc/hosts on client machines:"
        log_message "   <SERVER_IP>  $STING_HOSTNAME"
        log_message ""
        log_message "   Example: 192.168.1.100  $STING_HOSTNAME"
    fi
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_message ""

    return 0
}

# Master initialization function that orchestrates the entire setup process
initialize_sting() {
    local source_dir="${SOURCE_DIR:-$(pwd)}"
    log_message "Initializing STING environment..."

    # Load required modules (ensure they're available)
    local script_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Load file_operations.sh first (required for copy_files_to_install_dir)
    if [ -f "$script_lib_dir/file_operations.sh" ]; then
        source "$script_lib_dir/file_operations.sh"
    else
        log_message "ERROR: file_operations.sh not found in $script_lib_dir" "ERROR"
        return 1
    fi
    
    # Load other modules with error checking
    if [ -f "$script_lib_dir/configuration.sh" ]; then
        source "$script_lib_dir/configuration.sh"
    fi

    # Note: services.sh is sourced globally in install_sting.sh, not here
    # This ensures all functions (including build_and_start_services) can access wait_for_service

    # 1. Create basic directory structure and Docker resources
    if ! prepare_basic_structure; then
        log_message "Failed to prepare basic environment structure" "ERROR"
        return 1
    fi
    
    # Restore any preserved env files from previous installation
    if declare -f restore_env_files >/dev/null 2>&1; then
        restore_env_files "${INSTALL_DIR}"
    fi
    

    # 2. Skip HF token setup - using Ollama/External AI instead
    # Legacy HF token support has been deprecated
    log_message "Skipping HuggingFace token setup (using modern AI stack)"
    
    # 3. Build and run the configuration container to generate initial env files
    # Note: Using utils container for config generation (no host Python needed)
    generate_initial_configuration
    
    # 4.3. Fix env file permissions to ensure they're readable by docker-compose
    if [ -d "${INSTALL_DIR}/env" ]; then
        log_message "Fixing environment file permissions..."

        # Ensure env directory is accessible (755) while keeping files secure (644)
        chmod 755 "${INSTALL_DIR}/env" 2>/dev/null || true

        # Make env files readable by docker-compose but secure
        find "${INSTALL_DIR}/env" -name "*.env" -type f -exec chmod 644 {} \; 2>/dev/null || true

        # Fix the main .env file
        [ -f "${INSTALL_DIR}/.env" ] && chmod 644 "${INSTALL_DIR}/.env" 2>/dev/null || true

        # Determine the correct user for ownership
        local target_user="${SUDO_USER:-$USER}"
        local target_group="$(id -gn ${SUDO_USER:-$USER} 2>/dev/null || echo 'root')"

        # Ensure env directory and files are owned by correct user
        # This allows both root and the user to access files
        if [ -n "$target_user" ] && [ "$target_user" != "root" ]; then
            chown -R "$target_user:$target_group" "${INSTALL_DIR}/env" 2>/dev/null || true
            [ -f "${INSTALL_DIR}/.env" ] && chown "$target_user:$target_group" "${INSTALL_DIR}/.env" 2>/dev/null || true
            log_message "Environment files owned by: $target_user:$target_group"
        fi
    fi
    
    # 4.5. Validate that all critical env files were generated
    if ! validate_env_files; then
        log_message "Installation cannot proceed without critical environment files" "ERROR"
        log_message "Please fix the configuration issues and try again" "ERROR"
        return 1
    fi
    
    # 5. Now load the generated configuration into the shell
    load_env_files
    
    # 5.5. Install Ollama for universal LLM support
    install_ollama_if_enabled || {
        log_message \"Ollama installation failed or skipped\" \"WARNING\"
    }
    
    # 6. Setup complete environment with loaded variables
    setup_environment

    # 6.5. Generate env.js files for frontend with actual host IP
    generate_env_js_files

    # 6.6. Configure hostname for WebAuthn/Passkey compatibility
    configure_hostname

    # 7. Install services
    if ! build_and_start_services "$cache_level"; then
        log_message "Service startup failed during installation!" "ERROR"
        
        # Offer automatic cleanup on failure
        if [ "$is_reinstall" != "true" ]; then
            echo ""
            log_message "Installation failed. Would you like to automatically clean up the partial installation?" "WARNING"
            read -p "Clean up failed installation? (y/n): " cleanup_choice
            
            if [ "$cleanup_choice" = "y" ] || [ "$cleanup_choice" = "yes" ]; then
                log_message "Cleaning up failed installation..." "INFO"
                # Stop any running containers
                if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
                    cd "${INSTALL_DIR}" || true
                    docker compose down -v 2>/dev/null || true
                fi
                
                # Remove partial installation directory  
                if [ -d "${INSTALL_DIR}" ] && [ "${INSTALL_DIR}" != "/" ]; then
                    rm -rf "${INSTALL_DIR}" 2>/dev/null || true
                    log_message "Partial installation cleaned up" "INFO"
                fi
                
                # Clean up Docker resources
                docker system prune -f 2>/dev/null || true
                log_message "Docker cleanup completed" "INFO"
            else
                log_message "Partial installation left for debugging. Clean up manually with: ./manage_sting.sh uninstall --purge" "INFO"
            fi
        fi
        
        if [ "$is_reinstall" = "true" ]; then
            log_message "Try running a clean install with: ./manage_sting.sh reinstall --fresh" "WARNING"
        else
            log_message "If problems persist, check logs and try troubleshooting scripts in ./troubleshooting/" "WARNING"
        fi
        return 1
    fi
}

# Creates basic directory structure and Docker resources
prepare_basic_structure() {
    log_message "Preparing basic environment structure..."

    # Create Docker network
    if ! docker network inspect sting_local >/dev/null 2>&1; then
        log_message "Creating Docker network: sting_local"
        if ! docker network create sting_local; then
            log_message "ERROR: Failed to create Docker network sting_local" "ERROR"
            return 1
        fi
        log_message "Docker network sting_local created successfully"
    else
        log_message "Docker network sting_local already exists"
    fi

    # Create Docker volumes
    local volumes=("config_data" "postgres_data" "vault_data" "vault_file" "vault_persistent" "vault_logs" "sting_certs" "sting_uploads" "sting_logs" "llm_logs" "llm_model_data")
    for volume in "${volumes[@]}"; do
        docker volume create "$volume"
    done

    # Create basic directory structure
    mkdir -p "${INSTALL_DIR}/logs" "${INSTALL_DIR}/conf" "${INSTALL_DIR}/env" "${INSTALL_DIR}/certs"
    chmod 755 "${INSTALL_DIR}/logs"
    chmod 755 "${INSTALL_DIR}/conf"
    chmod 755 "${INSTALL_DIR}/env"  # Changed from 700 to 755 to allow Docker Compose access

    # Copy essential files and directories from source
    # For initial installation, use --delete flag to ensure a clean install
    # For reinstalls, skip --delete to preserve unchanged files (faster)
    # Note: delete_flag is not set by default, preserving env files during reinstall
    local delete_flag="${DELETE_FLAG:-}"
    if ! declare -f copy_files_to_install_dir >/dev/null 2>&1; then
        log_message "ERROR: copy_files_to_install_dir function not available" "ERROR"
        log_message "ERROR: Ensure file_operations.sh is properly loaded" "ERROR"
        return 1
    fi
    copy_files_to_install_dir "$source_dir" "$INSTALL_DIR" "$delete_flag"
    
    # Ensure manage_sting.sh is executable after copying
    if [ -f "${INSTALL_DIR}/manage_sting.sh" ]; then
        if ! chmod +x "${INSTALL_DIR}/manage_sting.sh" 2>/dev/null; then
            log_message "WARNING: Failed to set execute permissions on manage_sting.sh" "WARNING"
            log_message "Installation will continue, but 'msting' command may require manual fix" "WARNING"
            log_message "Fix with: chmod +x ${INSTALL_DIR}/manage_sting.sh" "WARNING"
        else
            log_message "Execute permissions successfully set on manage_sting.sh"
        fi
    fi
    
    # Ensure Kratos identity schema is present for config
    kratos_schema_src="$source_dir/kratos/identity.schema.json"
    kratos_schema_dest="${INSTALL_DIR}/conf/kratos/identity.schema.json"
    mkdir -p "$(dirname "$kratos_schema_dest")"
    if [ -f "$kratos_schema_src" ]; then
        cp "$kratos_schema_src" "$kratos_schema_dest"
        chmod 600 "$kratos_schema_dest"
    fi
    

    log_message "Basic environment structure prepared successfully"
    return 0
}

# Builds and starts all Docker services with retry logic
build_and_start_services() {
    local cache_level="${1:-moderate}"  # Accept cache level parameter, default to moderate
    log_message "Building and starting services (cache level: $cache_level)..."
    
    # CRITICAL: Ensure Docker network exists FIRST before ANY docker compose operations
    if ! docker network inspect sting_local >/dev/null 2>&1; then
        log_message "Creating Docker network: sting_local"
        docker network create sting_local || {
            log_message "ERROR: Failed to create Docker network" "ERROR"
            return 1
        }
    fi
    
    # Load all generated environment variables, including kratos.env
    source_service_envs

    # Export HOSTNAME for docker-compose environment variable substitution
    # CRITICAL: Use STING_HOSTNAME (not IP!) for WebAuthn/Passkey compatibility
    # The hostname must match Kratos RP ID for WebAuthn to work
    export HOSTNAME="${STING_HOSTNAME:-localhost}"
    log_message "Using HOSTNAME for docker-compose: $HOSTNAME"

    # Persist HOSTNAME to .env file for future container recreations
    if [ -f "${INSTALL_DIR}/.env" ]; then
        # Remove existing HOSTNAME line if present
        sed -i.backup '/^HOSTNAME=/d' "${INSTALL_DIR}/.env" 2>/dev/null || \
            sed -i '' '/^HOSTNAME=/d' "${INSTALL_DIR}/.env" 2>/dev/null
        # Append new HOSTNAME
        echo "HOSTNAME=${HOSTNAME}" >> "${INSTALL_DIR}/.env"
        log_message "Persisted HOSTNAME=${HOSTNAME} to .env file"
    fi

    # Change to installation directory for Docker operations
    cd "${INSTALL_DIR}" || {
        log_message "Failed to change to installation directory" "ERROR"
        return 1
    }

    # Install frontend dependencies for local development
    # This ensures node_modules exists for local testing/development
    log_message "Installing frontend dependencies for local development..."
    install_frontend_dependencies || {
        log_message "WARNING: Failed to install frontend dependencies. Docker build will still work." "WARNING"
        # Don't fail the installation - Docker build has its own npm install
    }
    
    # Legacy LLM building removed - using Ollama/External AI instead
    log_message "Skipping legacy LLM image building - using modern Ollama/External AI stack"
    
    log_message "llm-base image built successfully"
    
    # Build all services except those that depend on llm-base
    log_message "Building core service images..."
    
    # Split build strategy: Core services first, then observability
    log_message "🏗️ Building services in phases for improved reliability..."
    
    # Phase 1: Core Standard Services (essential for basic operation)
    log_message "📦 Phase 1: Building core standard services..."
    local core_services="vault db app frontend report-worker kratos messaging"
    
    if [ "$FRESH_INSTALL" = "true" ]; then
        # Fresh install: standard build for core services
        if ! docker compose build --no-cache $core_services; then
            log_message "Failed to build core standard services" "ERROR"
            return 1
        fi
    elif [ -f "${SOURCE_DIR}/lib/docker.sh" ]; then
        # Update/reinstall: use cache buzzer if available
        source "${SOURCE_DIR}/lib/docker.sh"
        log_message "🐝 Using cache buzzer for core services (level: ${cache_level:-moderate})"
        if ! build_docker_services "$core_services" "true" "${cache_level:-moderate}"; then
            log_message "Cache buzzer build failed for core services, falling back to standard build" "WARNING"
            if ! docker compose build --no-cache $core_services; then
                log_message "Failed to build core standard services" "ERROR"
                return 1
            fi
        fi
    else
        # Standard build for core services
        if ! docker compose build --no-cache $core_services; then
            log_message "Failed to build core standard services" "ERROR"
            return 1
        fi
    fi
    
    # Phase 2: AI and Knowledge Services (can be optional)
    log_message "🤖 Phase 2: Building AI and knowledge services..."
    local ai_services="chroma knowledge external-ai chatbot llm-gateway-proxy profile-sync-worker public-bee"
    
    if ! docker compose build --no-cache $ai_services; then
        log_message "⚠️  Failed to build some AI services - continuing installation" "WARNING"
        log_message "You may need to manually rebuild AI services later with: msting update" "WARNING"
        # Don't fail installation for AI services
    else
        log_message "✅ AI and knowledge services built successfully"
    fi
    
    # Phase 3: Observability Services (optional, can fail without breaking installation)
    log_message "📊 Phase 3: Building observability services..."
    local observability_services="loki promtail grafana"
    
    if ! docker compose build --no-cache $observability_services; then
        log_message "⚠️  Failed to build observability services - continuing installation" "WARNING"
        log_message "Observability features will be disabled. You can enable them later with: msting update" "WARNING"
        log_message "This is common on resource-constrained systems and won't affect core functionality" "INFO"
        # Don't fail installation for observability services
    else
        log_message "✅ Observability services built successfully"
    fi
    
    # Build utils service with installation profile
    if ! docker compose --profile installation build --no-cache utils; then
        log_message "Failed to build utils service" "WARNING"
        # Don't fail installation if utils service fails to build
    fi
    
    # Modern LLM stack - no legacy services to build
    log_message "Using modern Ollama/External AI stack - no legacy LLM services to build"

    
    # Sequential service startup with verification
    log_message "Starting Vault service..."
    docker compose up -d vault

    # Start utils container needed for Vault initialization
    log_message "Starting utils service for Vault initialization..."
    # Remove existing utils container if present (handles restart scenarios)
    docker rm -f sting-ce-utils 2>/dev/null || true
    docker compose up -d utils
    sleep 3  # Give containers a moment to start

    # Wait for Vault to be ready before initializing
    log_message "Waiting for Vault to be ready..."
    if ! wait_for_service "vault"; then
        log_message "⚠️ Vault service is not responding, continuing with initialization attempt..."
    fi

    # Initialize Vault automatically using the dedicated script
    log_message "Initializing Vault with enhanced error handling..."
    # Don't redirect output so we can see what's happening
    if docker exec sting-ce-vault /vault/scripts/auto-init-vault.sh; then
        log_message "✅ Vault initialized successfully"
    else
        log_message "⚠️ Vault auto-initialization failed, will try config_loader as fallback..."
        # Fallback to config_loader method
        if docker exec sting-ce-utils sh -c "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode initialize" >/dev/null 2>&1; then
            log_message "✅ Vault initialized via config_loader"
        else
            log_message "⚠️ Both initialization methods failed, checking if already initialized..."
        fi
    fi

    wait_for_vault || return 1

    # CRITICAL: Regenerate env files after Vault initialization to pick up the new token
    log_message "Regenerating environment files with Vault token..."
    if docker exec sting-ce-utils sh -c "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode runtime" >/dev/null 2>&1; then
        log_message "✅ Environment files regenerated with Vault token"
    else
        log_message "⚠️ Failed to regenerate env files - services may have incorrect tokens" "WARNING"
    fi

    # Force recreate utils service to pick up new environment variables
    # Docker compose restart doesn't reload env_file, we need to recreate
    log_message "Recreating utils service to load new Vault token..."
    docker compose stop utils >/dev/null 2>&1
    docker compose rm -f utils >/dev/null 2>&1
    docker compose up -d utils >/dev/null 2>&1
    sleep 3  # Give it a moment to start
    
    log_message "Starting database service..."
    docker compose up -d db
    wait_for_service "db" || return 1
    
    # Validate database initialization and create missing databases/users
    log_message "Validating database setup for database separation architecture..."
    if ! validate_database_initialization; then
        log_message "Database validation failed - this may cause service startup failures" "ERROR"
        log_message "Continuing with installation, but you may need to manually fix database issues"
    fi

    # Apply database migrations after database validation
    log_message "Applying database migrations..."
    if ! apply_database_migrations; then
        log_message "Database migrations failed - some features may not work properly" "WARNING"
        log_message "You can apply them manually later with: scripts/apply-db-migrations.sh"
    fi

    # Start mail service for email verification
    log_message "Starting mail service..."
    docker compose --profile development up -d mailpit

##    # Start Kratos service (replacing SuperTokens)  # DEPRECATED  # DEPRECATED
    if [ "$SKIP_KRATOS" != "true" ]; then
        log_message "Starting Kratos service..."
        docker compose up -d kratos
        wait_for_service "kratos" || return 1
    else
        log_message "SKIP_KRATOS=true; skipping Kratos startup and healthcheck"
    fi
    
##    # Skipping SuperTokens service startup (migrating to Kratos)  # DEPRECATED  # DEPRECATED
    # log_message "Starting authentication service..."
##    # verify_supertokens_env  # DEPRECATED  # DEPRECATED
##    # docker compose up -d supertokens  # DEPRECATED  # DEPRECATED
##    # wait_for_service "supertokens" || return 1  # DEPRECATED  # DEPRECATED
    
    log_message "Starting core application services..."

    # Ensure Vault is unsealed before starting app services that depend on it
    log_message "Verifying Vault is unsealed for application services..."
    if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
        log_message "Vault is sealed, attempting to unseal..."
        if docker exec sting-ce-vault /vault/scripts/auto-init-vault.sh >/dev/null 2>&1; then
            log_message "✅ Vault unsealed for application services"
        else
            log_message "⚠️ Could not unseal Vault - app services may fail to start" "WARNING"
        fi
    else
        log_message "✅ Vault is already unsealed"
    fi

    # Start Redis before app since app depends on it for session storage
    log_message "Starting Redis..."
    docker compose up -d redis

    # Start core application services
    log_message "Starting app, frontend, and workers..."
    docker compose up -d app frontend report-worker profile-sync-worker
    # Wait for core services to become healthy
    wait_for_service utils       || return 1
    wait_for_service app       || return 1
    wait_for_service frontend  || return 1
    wait_for_service report-worker || log_message "Report worker service is taking longer to start..." "WARNING"
    wait_for_service profile-sync-worker || log_message "Profile sync worker service is taking longer to start..." "WARNING"
    
    log_message "Starting knowledge system services..."
    docker compose up -d chroma knowledge public-bee
    
    # Make knowledge system non-critical for installation success
    if ! wait_for_service knowledge; then
        log_message "WARNING: Knowledge system failed to start. Installation will continue without it." "WARNING"
        log_message "You can start it later with: ./manage_sting.sh start knowledge"
        # Don't return failure - allow installation to continue
    fi

    # Start observability stack if enabled in config
    log_message "Starting observability services (if enabled)..."
    # Check if observability is enabled in the config
    if [ -f "${INSTALL_DIR}/env/observability.env" ]; then
        source "${INSTALL_DIR}/env/observability.env" 2>/dev/null || true
        if [ "${OBSERVABILITY_ENABLED}" = "true" ]; then
            log_message "Starting observability stack..."
            # Start observability services
            docker compose up -d loki promtail grafana log-forwarder
            
            # Make observability non-critical for installation success
            if ! wait_for_service loki; then
                log_message "WARNING: Loki failed to start. Observability will be limited." "WARNING"
            fi
            if ! wait_for_service grafana; then
                log_message "WARNING: Grafana failed to start. Dashboard will not be available." "WARNING"
            fi
            
            log_message "Observability stack startup completed"
        else
            log_message "Observability disabled in configuration, skipping observability services"
        fi
    else
        log_message "No observability configuration found, skipping observability services"
    fi

    # Start headscale support tunnel service if enabled in config
    log_message "Starting support tunnel services (if enabled)..."
    if [ -f "${INSTALL_DIR}/env/headscale.env" ]; then
        source "${INSTALL_DIR}/env/headscale.env" 2>/dev/null || true
        if [ "${HEADSCALE_ENABLED}" = "true" ]; then
            # Check if headscale service exists in compose file
            if [ -f "${INSTALL_DIR}/docker-compose.full.yml" ] && \
               docker compose -f "${INSTALL_DIR}/docker-compose.full.yml" config --services 2>/dev/null | grep -q "^headscale$"; then
                log_message "Starting Headscale support tunnel service..."
                docker compose -f "${INSTALL_DIR}/docker-compose.full.yml" --profile support-tunnels up -d headscale

                # Make headscale non-critical for installation success
                if ! wait_for_service headscale; then
                    log_message "WARNING: Headscale failed to start. Support tunnels will not be available." "WARNING"
                    log_message "You can start it later with: ./manage_sting.sh start headscale"
                fi
            else
                log_message "Headscale service not available in this edition (requires docker-compose.full.yml)" "INFO"
                log_message "This is expected for Community Edition installs using standard compose file"
            fi
        else
            log_message "Headscale disabled in configuration, skipping support tunnel service"
        fi
    else
        log_message "No headscale configuration found, skipping support tunnel service"
    fi

    log_message "Loading environment variables..."
    
    # Skip HF_TOKEN handling - using Ollama/External AI instead
    # Legacy HF token support has been deprecated
    
    # Start messaging and chatbot services
    log_message "Starting auxiliary services..."
    docker compose up -d messaging chatbot

    # Optionally start LLM services unless explicitly skipped
    if [ "${SKIP_LLM_STARTUP}" != "true" ]; then
        log_message "Starting LLM services..."
        start_llm_services
    else
        log_message "Skipping LLM services startup as requested."
    fi
    
    # Final verification
    log_message "Verifying all services are running..."
    sleep 5
    show_status
    
    log_message "All services started successfully"
    return 0
}

# Admin Setup Functions for Post-Installation

# Get environment-aware curl SSL options
get_curl_ssl_options() {
    local config_file="conf/config.yml"
    if [ -f "$config_file" ]; then
        local env=$(grep "env:" "$config_file" | awk '{print $2}' | head -1)
        if [ "$env" = "development" ]; then
            echo "-k"  # Skip SSL verification in development
        else
            echo ""   # Use proper SSL verification in production
        fi
    else
        echo "-k"  # Default to skip SSL verification if config not found
    fi
}

# Verify that core services are healthy for admin setup
verify_services_for_admin() {
    log_message "Verifying services are ready for admin setup..."
    
    # Get SSL options based on environment
    local ssl_options=$(get_curl_ssl_options)
    
    # Check Kratos health
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl $ssl_options -s https://localhost:4434/admin/health/ready >/dev/null 2>&1; then
            log_message "✅ Kratos service is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_message "❌ Kratos service not ready after $max_attempts attempts" "ERROR"
            return 1
        fi
        
        log_message "⏳ Waiting for Kratos to be ready... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Check STING app health
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl $ssl_options -s https://localhost:5050/health >/dev/null 2>&1; then
            log_message "✅ STING app service is healthy"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_message "❌ STING app service not ready after $max_attempts attempts" "ERROR"
            return 1
        fi
        
        log_message "⏳ Waiting for STING app to be ready... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
}

# Setup admin user automatically after installation
setup_admin_user_post_install() {
    local admin_email="$1"
    
    log_message "🐝 Setting up admin user..." "INFO"
    
    # Verify services are ready
    if ! verify_services_for_admin; then
        log_message "Cannot setup admin user - core services not ready" "ERROR"
        return 1
    fi
    
    # Call the setup script with appropriate flags
    if [ -n "$admin_email" ]; then
        log_message "Creating admin user with provided email: $admin_email"
        echo -e "$admin_email\n1" | "${INSTALL_DIR}/setup_first_admin.sh"
    else
        log_message "Prompting for admin user details..."
        "${INSTALL_DIR}/setup_first_admin.sh"
    fi
    
    return $?
}

# Smart admin setup that detects installation scenarios
smart_admin_setup() {
    local scenario=""
    local has_existing_admin=false
    local has_admin_marker=false
    local has_installation_id=false
    
    # Detect installation scenario
    if [ "$FRESH_INSTALL" = "true" ]; then
        scenario="fresh"
    elif [ "$is_reinstall" = "true" ]; then
        scenario="reinstall"
    elif [ -f "${INSTALL_DIR}/.installation_id" ]; then
        scenario="upgrade"
        has_installation_id=true
    else
        scenario="fresh"
    fi
    
    # Check if admin already exists in the system
    if [ -f "${INSTALL_DIR}/.admin_initialized" ]; then
        has_admin_marker=true
    fi
    
    # Check if admin exists in Kratos and capture the detailed status
    local admin_check_result
    admin_check_result=$(docker exec sting-ce-app python -c "
import sys, requests, urllib3
sys.path.insert(0, '/app')
from app.utils.default_admin_setup import KRATOS_ADMIN_URL, DEFAULT_ADMIN_EMAIL

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    response = requests.get(f'{KRATOS_ADMIN_URL}/admin/identities', verify=False, timeout=5)
    if response.status_code == 200:
        identities = response.json()
        for identity in identities:
            if identity.get('traits', {}).get('email') == DEFAULT_ADMIN_EMAIL:
                # Check if has valid credentials
                creds = identity.get('credentials', {})
                if 'password' in creds:
                    print('ADMIN_EXISTS_WITH_CREDS')
                else:
                    print('ADMIN_EXISTS_NO_CREDS')
                sys.exit(0)
        print('NO_ADMIN')
    else:
        print('KRATOS_ERROR')
except Exception:
    print('KRATOS_UNAVAILABLE')
" 2>/dev/null)
    
    local admin_has_valid_creds=false
    case "$admin_check_result" in
        "ADMIN_EXISTS_WITH_CREDS")
            has_existing_admin=true
            admin_has_valid_creds=true
            ;;
        "ADMIN_EXISTS_NO_CREDS")
            has_existing_admin=true
            admin_has_valid_creds=false
            log_message "Admin user exists but has no password credentials - needs to be recreated"
            ;;
        "NO_ADMIN")
            has_existing_admin=false
            ;;
        *)
            log_message "Could not determine admin status: $admin_check_result" "WARNING"
            has_existing_admin=false
            ;;
    esac
    
    # Handle different scenarios
    case "$scenario" in
        "fresh")
            if [ "$has_existing_admin" = "false" ]; then
                log_message "Fresh installation detected - offering admin setup"
                prompt_admin_setup
            elif [ "$admin_has_valid_creds" = "true" ]; then
                log_message "Fresh installation with valid admin detected - skipping admin setup"
                show_existing_admin_notice
            else
                log_message "Fresh installation with broken admin detected - recreating admin"
                recreate_broken_admin
            fi
            ;;
        "reinstall")
            if [ "$has_existing_admin" = "true" ] && [ "$admin_has_valid_creds" = "true" ]; then
                log_message "Reinstall detected with valid admin - preserving existing setup"
                show_reinstall_admin_notice
            elif [ "$has_existing_admin" = "true" ] && [ "$admin_has_valid_creds" = "false" ]; then
                log_message "Reinstall detected with broken admin - recreating admin"
                recreate_broken_admin
            else
                log_message "Reinstall detected without admin - offering recovery options"
                prompt_admin_recovery_setup
            fi
            ;;
        "upgrade")
            if [ "$has_existing_admin" = "true" ] && [ "$admin_has_valid_creds" = "true" ]; then
                log_message "Upgrade detected - preserving existing admin setup"
                show_upgrade_admin_notice
            elif [ "$has_existing_admin" = "true" ] && [ "$admin_has_valid_creds" = "false" ]; then
                log_message "Upgrade detected with broken admin - recreating admin"
                recreate_broken_admin
            else
                log_message "Upgrade detected without admin - offering setup"
                prompt_admin_setup
            fi
            ;;
        *)
            log_message "Unknown installation scenario - offering admin setup"
            prompt_admin_setup
            ;;
    esac
}

# Get the appropriate STING URL based on installation environment
get_sting_url() {
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

    # Check if it's a network IP (VM/remote server)
    if [[ "$host_ip" =~ ^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.) ]]; then
        echo "https://${host_ip}:8443"
    elif [[ -n "$host_ip" ]] && [[ "$host_ip" != "127.0.0.1" ]] && [[ "$host_ip" != "localhost" ]]; then
        # Has an IP but not private network - show both
        echo "https://${host_ip}:8443 or https://localhost:8443"
    else
        # Localhost installation
        echo "https://localhost:8443"
    fi
}

# Show notice for existing admin during fresh install
show_existing_admin_notice() {
    local sting_url=$(get_sting_url)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
    local mailpit_url="http://${host_ip:-localhost}:8025"

    echo ""
    echo "🐝 STING installation completed successfully!"
    echo ""
    echo "✅ Admin user already configured"
    echo ""
    echo "Your existing admin user has been preserved."
    echo "🔗 Access STING at: $sting_url"
    echo ""
    echo "🚀 PASSWORDLESS LOGIN: Enter your admin email to receive a login code"
    echo "📧 Check magic links at: $mailpit_url"
    echo ""
    echo "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:"
    echo "   Please run: ./fix_permissions.sh"
    echo ""
}

# Show notice for reinstall with existing admin
show_reinstall_admin_notice() {
    local sting_url=$(get_sting_url)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
    local mailpit_url="http://${host_ip:-localhost}:8025"

    echo ""
    echo -e "🐝 STING reinstallation completed successfully!"
    echo ""
    echo -e "✅ Your existing admin user has been preserved"
    echo ""
    echo "All your admin settings and credentials remain intact."
    echo "🔗 Access STING at: $sting_url"
    echo ""
    echo "🚀 PASSWORDLESS LOGIN: Enter your admin email to receive a login code"
    echo "📧 Check magic links at: $mailpit_url"
    echo ""
    echo "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:"
    echo "   Please run: ./fix_permissions.sh"
    echo ""
}

# Show notice for upgrade scenario
show_upgrade_admin_notice() {
    local sting_url=$(get_sting_url)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
    local mailpit_url="http://${host_ip:-localhost}:8025"

    echo ""
    echo -e "\033[1;33m🐝 STING upgrade completed successfully! \033[0m"
    echo ""
    echo -e "\033[1;32m✅ Your admin user has been preserved during upgrade\033[0m"
    echo ""
    echo "You can continue using your existing credentials."
    echo "Login at: \033[1;97m${sting_url}/login\033[0m"
    echo "📧 Check magic links at: $mailpit_url"
    echo ""
}

# Prompt for admin recovery during reinstall
prompt_admin_recovery_setup() {
    echo ""
    echo -e "\033[1;33m🐝 STING reinstallation completed! \033[0m"
    echo ""
    echo "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:"
    echo "   Please run: ./fix_permissions.sh"
    echo ""
    echo -e "\033[1;33m⚠️  Admin Recovery Needed\033[0m"
    echo ""
    echo "Your admin user appears to be missing or corrupted."
    echo "This can happen if:"
    echo "  • The admin user was manually deleted"
    echo "  • Kratos data was reset"
    echo "  • There was a database issue"
    echo ""
    
    local choice
    while true; do
        read -p "Would you like to create a new admin user? (y/n): " choice
        case "$choice" in
            [Yy]* )
                echo ""
                echo -e "\033[1;36m🔧 Creating new admin user...\033[0m"
                setup_admin_user_interactive
                break
                ;;
            [Nn]* )
                echo ""
                log_message "Admin recovery skipped - you can create one later manually"
                echo "To create an admin later, use the interactive tools or contact support."
                break
                ;;
            * )
                echo "Please answer yes (y) or no (n)."
                ;;
        esac
    done
}

# Interactive prompt for passwordless admin setup

# Recreate broken admin user (admin exists but has no password credentials)
recreate_broken_admin() {
    log_message "Recreating broken admin user..."
    
    # First, try to delete the existing broken admin user
    if docker exec sting-ce-app python -c "
import sys, requests, urllib3
sys.path.insert(0, '/app')
from app.utils.default_admin_setup import KRATOS_ADMIN_URL, DEFAULT_ADMIN_EMAIL

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    # Get the admin user ID
    response = requests.get(f'{KRATOS_ADMIN_URL}/admin/identities', verify=False, timeout=5)
    if response.status_code == 200:
        identities = response.json()
        for identity in identities:
            if identity.get('traits', {}).get('email') == DEFAULT_ADMIN_EMAIL:
                admin_id = identity.get('id')
                if admin_id:
                    # Delete the broken admin user
                    delete_response = requests.delete(f'{KRATOS_ADMIN_URL}/admin/identities/{admin_id}', verify=False, timeout=5)
                    if delete_response.status_code in [200, 204, 404]:
                        print('ADMIN_DELETED')
                    else:
                        print('DELETE_FAILED')
                    sys.exit(0)
        print('ADMIN_NOT_FOUND')
    else:
        print('KRATOS_ERROR')
except Exception as e:
    print(f'DELETE_ERROR: {e}')
" 2>/dev/null; then
        log_message "Broken admin user removed successfully" "SUCCESS"
    else
        log_message "Could not remove broken admin user - proceeding anyway" "WARNING"
    fi
    
    # Now create a fresh admin user
    log_message "Creating fresh admin user..."
    create_admin_user_with_verification "admin@sting.local"

    local sting_url=$(get_sting_url)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
    local mailpit_url="http://${host_ip:-localhost}:8025"

    echo ""
    echo "🐝 STING installation completed successfully!"
    echo ""
    echo "✅ Admin user recreated successfully"
    echo ""
    echo "Your broken admin user has been replaced with a fresh one."
    echo "You can log in at: ${sting_url}/login"
    echo "📧 Check magic links at: $mailpit_url"
    echo ""
    echo "The UI will display your admin credentials on first visit."
    echo ""
    echo "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:"
    echo "   Please run: ./fix_permissions.sh"
    echo ""
}

prompt_admin_setup() {
    local sting_url=$(get_sting_url)
    local host_ip="${STING_HOST_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
    local mailpit_url="http://${host_ip:-localhost}:8025"

    echo ""
    echo -e "\033[1;33m🐝 STING installation completed successfully! \033[0m"
    echo ""
    echo "🔗 Access STING at: $sting_url"
    echo "📧 Check magic links at: $mailpit_url"
    echo ""
    echo "📌 IMPORTANT: If you encounter permission errors with 'msting' commands:"
    echo "   Please run: ./fix_permissions.sh"
    echo ""
    echo -e "\033[1;36mWould you like to create an admin user now?\033[0m"
    echo ""
    echo "  This will:"
    echo "  • Create a Kratos identity for the admin user"
    echo "  • Generate a secure temporary password"
    echo "  • Set email verification requirement"
    echo "  • Force password change on first login"
    echo "  • Enable access to 🐝 admin features and LLM Settings"
    echo ""
    echo "  💡 Note: You can also create admin users later with manual setup"
    echo ""
    
    local choice
    while true; do
        read -p "Create admin user now? (y/n): " choice
        case "$choice" in
            [Yy]* )
                echo ""
                setup_admin_user_interactive
                break
                ;;
            [Nn]* )
                echo ""
                log_message "Admin user setup skipped - you can create one later"
                show_admin_setup_notice
                break
                ;;
            * )
                echo "Please answer yes (y) or no (n)."
                ;;
        esac
    done
}

# Interactive admin setup with email prompting and verification
setup_admin_user_interactive() {
    echo -e "\033[1;32m📋 Admin User Setup\033[0m"
    echo ""
    
    # Get admin email
    local admin_email
    while true; do
        read -p "Enter admin email address [admin@sting.local]: " admin_email
        admin_email=${admin_email:-admin@sting.local}
        
        # Basic email validation
        if [[ "$admin_email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
            break
        else
            echo "❌ Invalid email format. Please enter a valid email address."
        fi
    done
    
    # Confirmation
    echo ""
    echo "Creating admin user with:"
    echo "  📧 Email: $admin_email"
    echo "  🚀 Authentication: Passwordless (email verification)"
    echo "  📧 Login process: Enter email → Receive verification → Complete login"
    echo "  🔧 Next steps: Passkey setup (primary), then TOTP backup (admin only)"
    echo ""
    
    read -p "Proceed with admin user creation? (y/n): " confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        log_message "Admin user creation cancelled"
        return 0
    fi
    
    # Call the passwordless admin creation function
    create_passwordless_admin_user "$admin_email"
}

# Create passwordless admin user - creates identity only, no password
create_passwordless_admin_user() {
    local email="${1:-admin@sting.local}"
    
    log_message "Creating passwordless admin user: $email"
    
    # Wait for services to be ready
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec sting-ce-app python -c "
import requests
import urllib3
import sys
sys.path.insert(0, '/app')

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    # Check if Kratos is accessible
    response = requests.get('https://kratos:4434/admin/health/ready', verify=False, timeout=5)
    if response.status_code == 200:
        print('Kratos is ready')
        sys.exit(0)
    else:
        print(f'Kratos not ready: {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Kratos check failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log_message "Services are ready, proceeding with passwordless admin creation..."
            break
        fi
        
        log_message "Waiting for services to be ready... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_message "❌ Services failed to become ready within timeout" "ERROR"
        return 1
    fi
    
    # Create passwordless admin identity (no password, only email)
    local result
    result=$(docker exec sting-ce-app python -c "
import requests
import json
import sys
import os
sys.path.insert(0, '/app')

admin_email = '$email'
kratos_admin_url = 'https://kratos:4434'

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    # Create identity with only email and admin role - no password credentials
    create_data = {
        'schema_id': 'default',
        'traits': {
            'email': admin_email,
            'role': 'admin'
        }
        # Note: No credentials block - this creates a passwordless identity
    }
    
    create_response = requests.post(
        f'{kratos_admin_url}/admin/identities',
        headers={'Content-Type': 'application/json'},
        json=create_data,
        verify=False,
        timeout=10
    )
    
    if create_response.status_code == 201:
        identity = create_response.json()
        identity_id = identity['id']
        
        print(f'SUCCESS:{admin_email}:{identity_id}:passwordless')
    else:
        print(f'ERROR: Failed to create passwordless admin: {create_response.status_code} - {create_response.text}')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: Exception during admin creation: {e}')
    sys.exit(1)
")
    
    if [[ "$result" == SUCCESS:* ]]; then
        IFS=':' read -r status email identity_id auth_type <<< "$result"
        local sting_url=$(get_sting_url)

        echo ""
        echo -e "\033[1;37m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo -e "\033[1;32m                            🐝 ADMIN USER CREATED                             \033[0m"
        echo -e "\033[1;37m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo ""
        echo -e "\033[1;36m📧 Email:      \033[1;97m$email\033[0m"
        echo -e "\033[1;36m🚀 Auth Type:  \033[1;97mPasswordless (Email Code)\033[0m"
        echo -e "\033[1;36m🔗 Login URL:  \033[1;97m$sting_url\033[0m"
        echo ""
        echo -e "\033[1;33m🔧 NEXT STEPS:\033[0m"
        echo -e "\033[1;97m   1. Visit $sting_url\033[0m"
        echo -e "\033[1;97m   2. Enter your email: $email\033[0m"
        echo -e "\033[1;97m   3. Check your email for the verification link/code\033[0m"
        echo -e "\033[1;97m   4. Complete passwordless login\033[0m"
        echo -e "\033[1;97m   5. Set up passkey (primary authentication)\033[0m"
        echo -e "\033[1;97m   6. Set up TOTP (admin backup/recovery)\033[0m"
        echo ""
        echo -e "\033[1;31m⚠️  IMPORTANT:\033[0m"
        echo -e "\033[1;97m   • Check your email (including spam folder) for login verification\033[0m"
        echo -e "\033[1;97m   • No password needed - fully passwordless + hardware security\033[0m"
        echo -e "\033[1;97m   • Passkeys provide phishing-resistant primary authentication\033[0m"
        echo -e "\033[1;97m   • TOTP serves as backup/recovery for admin accounts\033[0m"
        echo -e "\033[1;37m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo ""
        log_message "Passwordless admin user created: $email" "SUCCESS"
    else
        log_message "❌ Passwordless admin user creation failed: $result" "ERROR"
        return 1
    fi
}

# Legacy function - Create admin user with email verification and forced password change
create_admin_user_with_verification() {
    local email="${1:-admin@sting.local}"
    
    log_message "Creating admin user with email verification: $email"
    
    # Wait for services to be ready
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec sting-ce-app python -c "
import requests
import urllib3
import sys
sys.path.insert(0, '/app')

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    # Check if Kratos is accessible
    response = requests.get('https://kratos:4434/admin/health/ready', verify=False, timeout=5)
    if response.status_code == 200:
        print('Kratos is ready')
        sys.exit(0)
    else:
        print(f'Kratos health check failed: {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Kratos not accessible: {e}')
    sys.exit(1)
" 2>/dev/null; then
            break
        fi
        
        log_message "Waiting for Kratos to be ready... (attempt $attempt/$max_attempts)"
        sleep 3
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_message "❌ Kratos is not ready. Admin user creation failed." "ERROR"
        return 1
    fi
    
    # Create the admin user with enhanced security
    local result=$(docker exec sting-ce-app python -c "
import sys, requests, json, secrets, string
import urllib3
sys.path.insert(0, '/app')

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits + '!@#$%&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Configuration
KRATOS_ADMIN_URL = 'https://kratos:4434'
admin_email = '$email'
password = generate_secure_password()

try:
    # Check if admin already exists
    response = requests.get(f'{KRATOS_ADMIN_URL}/admin/identities', verify=False)
    if response.status_code == 200:
        identities = response.json()
        for identity in identities:
            if identity.get('traits', {}).get('email') == admin_email:
                print(f'ERROR: Admin user with email {admin_email} already exists')
                sys.exit(1)
    
    # Create new admin with enhanced security
    identity_data = {
        'schema_id': 'default',
        'state': 'active',
        'traits': {
            'email': admin_email,
            'name': {
                'first': 'Admin',
                'last': 'User'
            },
            'role': 'admin',
            'force_password_change': True,
            'email_verified': False
        },
        'credentials': {
            'password': {
                'config': {
                    'password': password
                }
            }
        }
    }
    
    create_response = requests.post(
        f'{KRATOS_ADMIN_URL}/admin/identities',
        json=identity_data,
        verify=False
    )
    
    if create_response.status_code == 201:
        # Save password to file
        import os
        from pathlib import Path
        
        # Determine install directory
        install_dir = os.getenv('STING_INSTALL_DIR', '/opt/sting-ce')
        password_file = Path(install_dir) / 'admin_password.txt'
        
        # Create directory if needed
        password_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write password with restricted permissions
        with open(password_file, 'w') as f:
            f.write(password)
        os.chmod(password_file, 0o600)
        
        print(f'SUCCESS:{admin_email}:{password}:{password_file}')
    else:
        print(f'ERROR: Failed to create admin user: {create_response.status_code} - {create_response.text}')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
")
    
    # Parse the result
    if echo "$result" | grep -q "^SUCCESS:"; then
        local email=$(echo "$result" | cut -d: -f2)
        local password=$(echo "$result" | cut -d: -f3)
        local password_file=$(echo "$result" | cut -d: -f4)
        local sting_url=$(get_sting_url)

        echo ""
        echo -e "\033[1;32m✅ Admin user created successfully!\033[0m"
        echo ""
        echo -e "\033[1;33m📋 ADMIN CREDENTIALS\033[0m"
        echo -e "\033[1;37m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo -e "\033[1;36m📧 Email:    \033[1;97m$email\033[0m"
        echo -e "\033[1;36m🔑 Password: \033[1;97m$password\033[0m"
        echo -e "\033[1;36m🔗 Login:    \033[1;97m${sting_url}/login\033[0m"
        echo -e "\033[1;37m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo ""
        log_message "Admin user created: $email" "SUCCESS"
        
        # The password file was created inside the container, so copy it to host
        log_message "Copying admin password file from container to host..."
        
        # Try to copy to the standard location first
        local actual_password_location=""
        if docker cp sting-ce-app:/opt/sting-ce/admin_password.txt /opt/sting-ce/admin_password.txt 2>/dev/null; then
            log_message "Password file copied to /opt/sting-ce/admin_password.txt" "SUCCESS"
            chmod 600 /opt/sting-ce/admin_password.txt 2>/dev/null
            actual_password_location="/opt/sting-ce/admin_password.txt"
        else
            # If that fails, try copying to user's home directory
            log_message "Failed to copy to /opt/sting-ce, trying user home directory..." "WARNING"
            local user_dir="${HOME}/.sting-ce"
            mkdir -p "$user_dir" 2>/dev/null
            if docker cp sting-ce-app:/opt/sting-ce/admin_password.txt "${user_dir}/admin_password.txt" 2>/dev/null; then
                log_message "Password file copied to ${user_dir}/admin_password.txt" "SUCCESS"
                chmod 600 "${user_dir}/admin_password.txt" 2>/dev/null
                actual_password_location="${user_dir}/admin_password.txt"
            else
                log_message "Failed to copy password file to host - password only visible in container" "WARNING"
                actual_password_location="(stored in container at $password_file)"
            fi
        fi
        
        echo -e "\033[1;33m⚠️  SECURITY NOTES:\033[0m"
        echo -e "   • Password saved to: \033[1;97m$actual_password_location\033[0m"
        echo -e "   • \033[1;31mPassword change REQUIRED on first login\033[0m"
        echo -e "   • \033[1;31mEmail verification REQUIRED before full access\033[0m"
        echo -e "   • Keep credentials secure and change password immediately"
        echo ""
        
        # The container already has the password file at /opt/sting-ce/admin_password.txt
        # but the UI expects it at /.sting-ce/admin_password.txt, so copy it there too
        docker exec sting-ce-app cp /opt/sting-ce/admin_password.txt /.sting-ce/admin_password.txt 2>/dev/null || true
    else
        log_message "❌ Admin user creation failed: $result" "ERROR"
        return 1
    fi
}

# Show prominent notice about admin setup
show_admin_setup_notice() {
    echo ""
    echo -e "\033[1;36m╔═══════════════════════════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;33m🐝 IMPORTANT: Admin User Setup Required for Full STING Access 🐝\033[1;36m        ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;37mTo access admin features like LLM Settings, you need an admin user.\033[1;36m      ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;32m📋 Create Admin User:\033[1;36m                                                   ║\033[0m"
    echo -e "\033[1;36m║     \033[1;97m./setup_first_admin.sh\033[1;36m                                               ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;32m📋 Create Admin with Custom Email:\033[1;36m                                      ║\033[0m"
    echo -e "\033[1;36m║     \033[1;97mmsting create admin <EMAIL>\033[1;36m ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;32m📋 Check Admin Status:\033[1;36m                                                  ║\033[0m"
    echo -e "\033[1;36m║     \033[1;97mpython3 check_admin.py\033[1;36m                                               ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;33m💡 Admin Features:\033[1;36m                                                      ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• 🐝 LLM Settings tab in Settings page\033[1;36m                              ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• Model management with progress tracking\033[1;36m                           ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• User management capabilities\033[1;36m                                     ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• System administration features\033[1;36m                                   ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;31m⚠️  Security Note: Use temporary passwords for initial admin setup.\033[1;36m      ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37mAdmins should change passwords on first login.\033[1;36m                      ║\033[0m"
    echo -e "\033[1;36m║                                                                               ║\033[0m"
    echo -e "\033[1;36m║  \033[1;32m💡 Quick Setup Options:\033[1;36m                                              ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• Install with admin: ./install_sting.sh install --setup-admin\033[1;36m      ║\033[0m"
    echo -e "\033[1;36m║     \033[1;37m• Install without prompts: ./install_sting.sh install --no-prompt\033[1;36m   ║\033[0m"
    echo -e "\\033[1;36m║                                                                               ║\\033[0m"
    echo -e "\\033[1;36m╚═══════════════════════════════════════════════════════════════════════════════╝\\033[0m"
    echo ""
}

# Verify Python dependencies are properly installed
verify_python_dependencies() {
    log_message "Verifying Python dependencies installation..."
    
    # Check if utils container is running
    if ! docker compose ps utils 2>/dev/null | grep -q "Up"; then
        log_message "Starting utils container for dependency verification..."
        docker compose up -d utils
        
        # Wait for container to be ready
        local max_attempts=30
        local attempt=1
        while [ $attempt -le $max_attempts ]; do
            if docker compose ps utils 2>/dev/null | grep -q "Up"; then
                break
            fi
            log_message "Waiting for utils container... attempt $attempt/$max_attempts"
            sleep 2
            attempt=$((attempt + 1))
        done
    fi
    
    # Test critical imports that were failing
    log_message "Testing critical Python imports..."
    
    local test_imports=(
        "flask_cors"
        "app.services.user_service"
        "app.models.user_models"
        "sqlalchemy"
        "cryptography"
        "requests"
    )
    
    local failed_imports=()
    
    for import_name in "${test_imports[@]}"; do
        if ! docker compose exec -T utils python3 -c "import $import_name; print('✓ $import_name')" 2>/dev/null; then
            failed_imports+=("$import_name")
            log_message "Failed to import: $import_name" "WARNING"
        fi
    done
    
    if [ ${#failed_imports[@]} -eq 0 ]; then
        log_message "All critical Python dependencies verified successfully" "SUCCESS"
        return 0
    else
        log_message "Failed imports detected. Installing missing dependencies..." "WARNING"
        
        # Try to install missing dependencies
        if docker compose exec -T utils pip install -r /app/app/requirements.txt 2>/dev/null; then
            log_message "Additional dependencies installed successfully" "SUCCESS"
            
            # Re-test failed imports
            local still_failed=()
            for import_name in "${failed_imports[@]}"; do
                if ! docker compose exec -T utils python3 -c "import $import_name" 2>/dev/null; then
                    still_failed+=("$import_name")
                fi
            done
            
            if [ ${#still_failed[@]} -eq 0 ]; then
                log_message "All dependencies now working after installation" "SUCCESS"
                return 0
            else
                log_message "Some dependencies still failing: ${still_failed[*]}" "ERROR"
                return 1
            fi
        else
            log_message "Failed to install additional dependencies" "ERROR"
            return 1
        fi
    fi
}

# Function to check for and warn about msting command PATH conflicts
check_msting_path_conflicts() {
    log_message "Checking for potential msting command PATH conflicts..."
    
    # Check if there are multiple msting commands in PATH
    local msting_locations=($(which -a msting 2>/dev/null || true))
    
    if [ ${#msting_locations[@]} -gt 1 ]; then
        log_message "⚠️  WARNING: Multiple msting commands found in PATH!" "WARNING"
        log_message "This can cause confusion about which version is being used:" "WARNING"
        for loc in "${msting_locations[@]}"; do
            log_message "  - $loc" "WARNING"
        done
        log_message ""
        log_message "To resolve conflicts:" "WARNING"
        log_message "1. Remove stale .venv directories: rm -rf ~/.local/*/bin/msting" "WARNING"
        log_message "2. Or deactivate virtual environments when using msting" "WARNING"
        log_message "3. Use full path: /usr/local/bin/msting for system version" "WARNING"
        log_message ""
    fi
    
    # Check if current msting is from a virtual environment
    local current_msting=$(which msting 2>/dev/null || true)
    if [[ "$current_msting" == *".venv"* ]] || [[ "$current_msting" == *"venv"* ]]; then
        log_message "⚠️  NOTICE: Current msting command is from a virtual environment" "WARNING"
        log_message "Location: $current_msting" "WARNING"
        log_message "This may be an outdated version. Consider using: /usr/local/bin/msting" "WARNING"
        log_message ""
    fi

     # Detect if we're running with sudo privileges
    local is_sudo=false
    if [ "$EUID" -eq 0 ] || [ -n "$SUDO_USER" ]; then
        is_sudo=true
        log_message "Running with elevated privileges"
    fi

    # Run fix_permissions.sh after sudo is confirmed (non-fatal)
    if [ "$is_sudo" = true ]; then
        log_message "Running permission fix script..."

        local fix_script=""
        if [ -f "${INSTALL_DIR}/fix_permissions.sh" ]; then
            fix_script="${INSTALL_DIR}/fix_permissions.sh"
        elif [ -f "${SOURCE_DIR}/fix_permissions.sh" ]; then
            fix_script="${SOURCE_DIR}/fix_permissions.sh"
        fi

        if [ -n "$fix_script" ]; then
            # Copy to tmp if on WSL mount to avoid permission issues
            if echo "$fix_script" | grep -q "/mnt/"; then
                local tmp_script="/tmp/fix_permissions_$$.sh"
                cp "$fix_script" "$tmp_script"
                chmod +x "$tmp_script"
                # Run with sudo to ensure permission commands work
                if sudo bash "$tmp_script" 2>&1; then
                    log_message "✅ Permission fixes applied successfully" "SUCCESS"
                else
                    log_message "⚠️  WARNING: Permission fix script failed (non-fatal)" "WARNING"
                fi
                rm -f "$tmp_script"
            else
                # Run with sudo to ensure permission commands work
                if sudo bash "$fix_script" 2>&1; then
                    log_message "✅ Permission fixes applied successfully" "SUCCESS"
                else
                    log_message "⚠️  WARNING: Permission fix script failed (non-fatal)" "WARNING"
                fi
            fi
        else
            log_message "⚠️  WARNING: fix_permissions.sh not found (non-fatal)" "WARNING"
        fi
    fi
    
    # Verify the current msting command has the update subcommand
    if command -v msting >/dev/null 2>&1; then
        # Try the msting command with a timeout to avoid hanging
        if timeout 10 msting --help 2>&1 | grep -q "update.*service"; then
            log_message "✅ msting command appears to be working correctly" "SUCCESS"
        else
            log_message "⚠️  WARNING: msting command may need permission fixes or PATH adjustment" "WARNING"
            log_message "This is common on macOS installations." "WARNING"
            log_message "" 
            log_message "To fix msting command issues:" "WARNING"
            log_message "1. Run: ./fix_permissions.sh (fixes permissions)" "WARNING"
            log_message "2. Or try: /usr/local/bin/msting --help (use full path)" "WARNING" 
            log_message "3. Or reload shell: source ~/.bashrc or source ~/.zshrc" "WARNING"
            log_message ""
            log_message "This warning can be safely ignored if installation completed successfully." "WARNING"
        fi
    else
        log_message "⚠️  msting command not found in PATH" "WARNING"
        log_message "You may need to run ./fix_permissions.sh after installation" "WARNING"
    fi
}