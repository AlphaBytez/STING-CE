#!/bin/bash
# STING Management Script - Interface Module
# This module provides the command-line interface and argument parsing

# Source required dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/logging.sh"
source "$SCRIPT_DIR/core.sh"
# Don't source services.sh here - it will be loaded on demand
# source "$SCRIPT_DIR/services.sh"

# Function to load modules on demand
load_required_module() {
    local module="$1"
    local module_path="$SCRIPT_DIR/${module}.sh"
    
    if [ -f "$module_path" ] && ! declare -f "${module}_loaded" >/dev/null 2>&1; then
        log_message "Loading required module: $module"
        source "$module_path" || {
            log_message "ERROR: Failed to load required module: $module" "ERROR"
            return 1
        }
        # Mark as loaded
        eval "${module}_loaded() { return 0; }"
    fi
}

# Security function to check for sudo/root privileges
check_admin_creation_privileges() {
    # Check if user is root
    if [[ $EUID -eq 0 ]]; then
        return 0
    fi
    
    # Check if user is in sudo group and can run sudo
    if groups "$USER" | grep -q '\bsudo\b\|wheel\b\|admin\b' 2>/dev/null; then
        # Verify sudo access without prompting for password if possible
        if sudo -n true 2>/dev/null; then
            return 0
        fi
        
        # Prompt for sudo authentication
        log_message "🔐 Admin creation requires sudo privileges for security" "WARNING"
        log_message "Please authenticate to continue..." "INFO"
        if sudo -v; then
            return 0
        fi
    fi
    
    # Access denied
    log_message "❌ SECURITY: Admin creation denied - insufficient privileges" "ERROR"
    log_message "⚠️  This operation requires root or sudo access for security reasons" "ERROR"
    log_message "💡 Solution: Run as root or ensure your user is in the sudo group" "INFO"
    return 1
}

# Function to show help message
show_help() {
    echo "Usage: $0 {start|stop|restart|status|build|update|install|reinstall|uninstall|cleanup|reset|maintenance|download_models|backup|restore|buzz|cache-buzz|build-analytics|install-ollama|ollama-status|llm-status|dev|create|upload-knowledge|help} [options]"
    echo
    echo "Commands:"
    echo "  start, -s [service]           Start all services or specified service"
    echo "  stop, -t [service]            Stop all services or specified service"
    echo "  restart, -r [service...]      Restart all services or specified service(s)"
    echo "  unseal                        Unseal Vault if it's sealed"
    echo "  status, -st [-v] [service]    Show status of all services or specific service"
    echo "                                Use -v or --verbose for detailed diagnostics"
    echo "  debug, -d [--plain] [check]   Comprehensive system diagnostics and troubleshooting"
    echo "                                Options: --plain for text-only output"
    echo "                                Checks: all, services, auth, database, network, ssl, resources, logs"
    echo "  build, -b [service] [-q|-v]   Build all services or specified service"
    echo "                                Use -q/--quiet for minimal output, -v/--verbose for full output"
    echo "  update [service|all] [-q|-v]  Build (--no-cache) then restart specified service or all services"
    echo "                                Use 'all' to update app, frontend, knowledge, chatbot, and more"
    echo "                                Single service updates only clear that service's cache/image"
    echo "                                Use --sync-only for frontend changes without rebuild"
    echo "                                Use --force to override safety checks (risky)"
    echo "                                Use -q/--quiet for minimal output, -v/--verbose for full output"
    echo "  sync-config                   Sync configuration files without rebuilding services"
    echo "  reset-config                  Reset config.yml from template with backup (keeps last 5)"
    echo "  regenerate-env                Regenerate environment files from config.yml changes"
    echo "  install, -i [--start-llm] [--setup-admin] [--no-prompt]  Install the msting command"
    echo "  reinstall, -ri [--fresh] [--llm] [--no-backup]  Reinstall STING with atomic backup/restore"
    echo "                                Use --fresh for complete reinstall with model purge;"
    echo "                                --llm to start LLM service; --no-backup to skip backup"
    echo "  uninstall, -u [--purge] [-l|--llm] [--force]  Uninstall the msting command."
    echo "                                Use --purge to remove all STING Docker resources;"
    echo "                                -l|--llm to also delete downloaded LLM models;"
    echo "                                --force for aggressive cleanup of all STING resources"
    echo "  cleanup, -c                   Clean up Docker resources but preserve configuration"
    echo "  reset, -rs                    Quick reset for development iterations"
    echo "  maintenance, -m               Perform maintenance tasks"
    echo "  download_models, -d           Download models"
    echo "  backup, -ba [--encrypt]       Create a backup of the STING application"
    echo "                                Use --encrypt to encrypt backup with secure key management"
    echo "  restore, -rs <file>           Restore STING application from a backup file"
    echo "                                Automatically detects and decrypts encrypted backups"
    echo ""
    echo "🔐 Backup Key Management:"
    echo "  backup --export-key [file]    Export backup encryption key (default: backup_key.txt)"
    echo "  backup --import-key <file>    Import backup encryption key from file"
    echo "                                Keys stored in system keychain/keyring when available"
    echo "  verbose, -v                   Enable verbose mode"
    echo "  bee support [command]         🐝 AI-Powered Support Assistant - Create intelligent support requests"
    echo "  support tunnel [command]      🔗 Support Tunnel Management - Secure access via Headscale"
    echo "  bundle [list|extract|copy]    📦 Local Bundle Management - Download and share your bundles"
    echo "  buzz [collect|list|clean]     🐝 Hive Diagnostics - Create honey jars for support"
    echo "  cache-buzz, cb [options]      🐝 Cache Buzzer - Clear Docker cache and rebuild"
    echo "  build-analytics [service] [hours]  🐝 Build Intelligence - View Docker build logs & performance"
    echo ""
    echo "📦 Volume Management:"
    echo "  volumes list                  List STING volumes with safety classification"
    echo "  volumes purge <type>          Remove volumes by type (database, config, logs, etc.)"
    echo "  volumes backup [dir]          Backup volumes to directory"
    echo "  volumes help                  Show detailed volume management help"
    echo ""
    echo "🤖 LLM & AI Commands:"
    echo "  install-ollama                Install Ollama for universal LLM support"
    echo "  ollama-status                 Check Ollama installation and running status"
    echo "  llm-status                    Check all LLM services (Ollama, External AI, etc.)"
    echo "  help, -h                      Show this help message"
    echo
    echo "Options:"
    echo "  --no-cache, -nc               Build Docker images without using the cache"
    echo "  --cache                       Use Docker cache during build (overrides default --no-cache for updates)"
    echo "  --sync-only                   Sync code changes without Docker rebuild (faster for frontend)"
    echo "  --force                       Override safety checks and proceed with risky updates"
    echo "  --purge                       Remove all Docker resources during uninstall"
    echo
    echo "Installation Options:"
    echo "  --start-llm                   Automatically start LLM service after installation (macOS only)"
    echo "  --setup-admin                 Force admin user creation prompt (default for fresh installs)"
    echo "  --admin-email=email           Pre-specify admin email for automated setups"
    echo "  --no-admin                    Skip admin user creation entirely"
    echo "  --no-prompt                   Skip interactive prompts during installation"
    echo
    echo "Model Options:"
    echo "  MODEL_MODE=small              Use small models (default): deepseek-1.5b, tinyllama, dialogpt"
    echo "  MODEL_MODE=performance        Use large models: llama3, phi3, zephyr"
    echo "  MODEL_MODE=minimal            Use only tinyllama for minimal setup"
    echo "  DOWNLOAD_MODELS=model1,model2 Custom model list (comma-separated)"
    echo
    echo "Development Options:"
    echo "  dev [command]                 🔥 Development workflow manager (hot reload, sync, build)"
    echo "  cleanup, -c                   Clean Docker resources while preserving configuration"
    echo "  reset, -rs                    Quick development reset"
    echo "  --skip-backup                 Skip backup confirmation prompts"
    echo
    echo "User Management:"
    echo "  create admin --email=<EMAIL>  Create admin user account (PASSWORDLESS by default)"
  echo "  recreate admin --email=<EMAIL> Recreate admin user (delete + create)"
    echo "    [--use-password]            LEGACY: Enable password mode (not recommended)"  
    echo "    [--password=<PASSWORD>]     LEGACY: Set specific password (only with --use-password)"
    echo "  delete admin --email=<EMAIL>  Delete admin user account"
    echo "    [--force]                   Skip confirmation prompts"
    echo "  create user <EMAIL>           Create regular user (future enhancement)"
    echo
    echo "📚 Knowledge Management:"
    echo "  upload-knowledge [options]    Upload STING Platform Knowledge to Honey Jar"
    echo "    --update                    Update existing honey jar instead of creating new"
    echo "    --version <version>         Specify version (default: read from version.txt)"
    echo "    --dry-run                   Show what would be uploaded without actually doing it"
    echo
    echo "🐝 Bee AI Support Assistant:"
    echo "  bee support analyze           Analyze system health and suggest improvements"
    echo "  bee support create \"issue\"     Create AI-guided support ticket with intelligent diagnostics"
    echo "  bee support suggest           Get troubleshooting suggestions for common issues"  
    echo "  bee support list              List existing support tickets"
    echo "  bee support status            Show support system status and configuration"
    echo ""
    echo "  💡 Examples:"
    echo "    bee support create \"login issues after update\""
    echo "    bee support create \"dashboard loading slowly\""
    echo "    bee support create \"ai chat not responding\""
    echo ""
    echo "🔗 Support Tunnel Management (Headscale):"
    echo "  support tunnel create TICKET_ID  Create secure support tunnel (30min default)"
    echo "  support tunnel list              List active support tunnels"
    echo "  support tunnel status TICKET_ID  Show tunnel connection status"
    echo "  support tunnel close TICKET_ID   Close tunnel and revoke access"
    echo "  support tunnel help              Show tunnel management help"
    echo ""
    echo "  💡 Examples:"
    echo "    support tunnel create ST-2025-001      # 30min community tunnel"
    echo "    support tunnel create ST-2025-002 4h   # 4hr enterprise tunnel"
    echo ""
    echo "📦 Local Bundle Management:"
    echo "  bundle list                      List available diagnostic bundles"
    echo "  bundle extract BUNDLE_FILE       Extract bundle for manual review"
    echo "  bundle copy BUNDLE_FILE [DEST]   Copy bundle to location for sharing"
    echo "  bundle inspect BUNDLE_FILE       Preview bundle contents"
    echo "  bundle package TICKET_ID         Create shareable package with docs"
    echo ""
    echo "  💡 Examples:"
    echo "    bundle copy auth-ST-2025-001.tar.gz ~/Desktop   # Copy for email"
    echo "    bundle extract perf-ST-2025-002.tar.gz          # Extract for review"
    echo "    bundle package ST-2025-001                      # Create shareable package"
    echo ""
    echo "🐝 Hive Diagnostics (Buzz Commands):"
    echo "  buzz collect [--hours 24]     Create diagnostic honey jar (default: 24 hours)"
    echo "  buzz collect --auth-focus     Focus on authentication issues"  
    echo "  buzz collect --llm-focus      Focus on LLM service issues"
    echo "  buzz collect --performance    Include performance metrics"
    echo "  buzz collect --ticket ABC123  Tag bundle with support ticket"
    echo "  buzz list                     List existing honey jars"
    echo "  buzz clean [--older-than 7d]  Clean old honey jars"
    echo "  buzz hive-status              Show hive diagnostic status"
    echo "  buzz filter-test              Test data sanitization filters"
    echo ""
    echo "  💡 Need help? Just 'buzz' to create a sanitized diagnostic bundle!"
    echo ""
    echo "🐝 Cache Buzzer Examples:"
    echo "  cache-buzz                    Moderate cache clear and rebuild all services"
    echo "  cache-buzz --full             Full cache clear (removes all STING containers/images)"
    echo "  cache-buzz --minimal          Minimal cache clear (build cache only)"
    echo "  cache-buzz app                Rebuild specific service with cache clear"
    echo "  cache-buzz --clear-only       Clear cache without rebuilding"
    echo "  cache-buzz --validate         Validate container freshness without rebuilding"
    echo ""
    echo "🐳 Docker Troubleshooting:"
    echo "  If Docker containers show old code despite --no-cache builds, use:"
    echo "    ./manage_sting.sh cache-buzz --full    # Complete cache removal"
    echo "  Or manually force remove images:"
    echo "    docker rmi sting-ce-frontend:latest -f  # Force remove specific image"
    echo "    docker-compose build --no-cache frontend # Rebuild specific service"
}



# Main function that handles command parsing and routing
main() {
    local action="$1"
    shift

    # Export COMMAND for check_root function
    export COMMAND="$action"

    # Initialize logging
    if [ ! -f "$LOG_FILE" ]; then
        init_logging
        ensure_log_directory
    fi

    # Only show debug in verbose mode
    [ "$VERBOSE" = true ] && log_message "Debug: Action: $action, Arguments: $*"
    
    # Parse arguments once
    local no_cache=false
    local service=""

    [ "$VERBOSE" = true ] && set -x
    check_root

    # Basic system requirements - load health module for check_disk_space
    load_required_module "health"
    check_disk_space
    # STING_MODELS_DIR will be handled later only when needed (e.g., in Docker compose)
    
    # Check configuration exists before proceeding (except for help command)
    if [[ "$action" != "help" && "$action" != "-h" && "$action" != "--help" ]]; then
        local config_path="${SOURCE_DIR}/conf/config.yml"
        log_message "Checking configuration file: $config_path"
        
        if ! python3 "${SOURCE_DIR}/conf/check_config.py" --config-path="$config_path" --project-root="$SOURCE_DIR" >/dev/null 2>&1; then
            log_message "❌ Configuration check failed!" "ERROR"
            log_message "Run the following to see detailed configuration help:" "INFO"
            log_message "python3 ${SOURCE_DIR}/conf/check_config.py --config-path=\"$config_path\" --project-root=\"$SOURCE_DIR\" --speed-tips"
            return 1
        fi
        log_message "✅ Configuration check passed"
    fi

    # Handle standalone actions that don't need full setup
    case "$action" in
        status|-st)
            # Load required modules
            load_required_module "services"
            load_required_module "docker"
            load_required_module "health"
            
            # Load environment files first to get all variables
            source_service_envs 2>/dev/null || true
            
            # Export critical environment variables for docker compose
            export INSTALL_DIR CONFIG_DIR LOG_DIR SOURCE_DIR
            export POSTGRES_HOST POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
            export DOMAIN FRONTEND_URL KRATOS_PUBLIC_URL KRATOS_ADMIN_URL
            
            # Store current directory and change to install directory
            local original_dir="$(pwd)"
            cd "${INSTALL_DIR}" || {
                log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
                return 1
            }
            
            # Check for verbose flag and service filter
            local verbose=false
            local service_filter=""
            
            for arg in "$@"; do
                case "$arg" in
                    -v|--verbose)
                        verbose=true
                        ;;
                    *)
                        # If not a flag, assume it's a service name
                        if [[ "$arg" != -* ]]; then
                            service_filter="$arg"
                        fi
                        ;;
                esac
            done
            
            # Load enhanced status module if available, otherwise use basic status
            if [ -f "${SOURCE_DIR}/lib/enhanced_status.sh" ]; then
                source "${SOURCE_DIR}/lib/enhanced_status.sh"
                show_enhanced_status "$verbose" "$service_filter"
            else
                # Fallback to basic status
                log_message "STING Services Status:" "INFO"
                echo ""
                
                # Check Docker daemon
                if ! docker info >/dev/null 2>&1; then
                    log_message "Docker is not running or not accessible" "ERROR"
                    return 1
                fi
                
                # Show container status
                docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
                echo ""
                
                # Check critical services health (quick check)
                local services=("sting-ce-db" "sting-ce-vault-1" "sting-ce-kratos-1" "sting-ce-app-1" "sting-ce-frontend-1")
                for service in "${services[@]}"; do
                    if docker compose ps --format "{{.Name}}\t{{.Status}}" 2>/dev/null | grep "$service" | grep -q "Up"; then
                        log_message "$service: Running ✓" "SUCCESS"
                    else
                        log_message "$service: Not running ✗" "ERROR"
                    fi
                done
                
                # Show resource usage
                echo ""
                log_message "Resource Usage:" "INFO"
                docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10 || true
            fi
            
            # Restore original directory
            cd "$original_dir" || true
            return 0
            ;;
        uninstall|-u)
            # Load required modules
            load_required_module "installation"
            
            # Parse uninstall flags
            local purge_flag=""
            local remove_llm_flag=""
            local force_flag=""
            for arg in "$@"; do
                case "$arg" in
                    --purge) purge_flag="--purge" ;; 
                    -l|--llm) remove_llm_flag="--llm" ;;
                    --force) force_flag="--force" ;;
                esac
            done
            
            # If force flag is used, skip confirmation and do aggressive cleanup
            if [ "$force_flag" = "--force" ]; then
                log_message "Force cleanup mode - removing all STING Docker resources..."
                force_cleanup_docker_resources
                if [ -d "${INSTALL_DIR}" ]; then
                    rm -rf "${INSTALL_DIR}"
                fi
                sudo rm -f /usr/local/bin/msting 2>/dev/null || true
                log_message "Force cleanup completed" "SUCCESS"
            else
                uninstall_msting_with_confirmation "$purge_flag" "$remove_llm_flag"
            fi
            return
            ;;
        cleanup|-c)
            load_required_module "development"
            cleanup_development
            return 0
            ;;
        maintenance|-m)
            # Kill any existing Docker compose processes
            pkill -f "docker compose" || true
            # Prune Docker resources
            docker system prune -f --volumes
            docker volume prune -f
            docker network prune -f
            docker image prune -f
            # Clean up temporary directories
            rm -rf /tmp/sting_temp /tmp/sting_download
            log_message "Maintenance completed successfully"
            return 0
            ;;
        download_models|-d)
            load_required_module "model_management"
            load_required_module "configuration"
            check_and_load_config
            download_models
            return 0
            ;;
        install|-i)
            load_required_module "installation"
            load_required_module "environment"
            check_and_install_dependencies || return 1
            verify_environment || return 1
            install_msting "$@"
            return 0
            ;;
        reinstall|-ri)
            load_required_module "installation"
            load_required_module "services"
            # Check if first argument is a flag (starts with --)
            if [ -n "$1" ] && [[ "$1" != --* ]]; then
                # Reinstall specific service
                reinstall_service "$1"
            else
                # Full reinstall (no service specified or flags provided)
                reinstall_msting "$@"
            fi
            return 0
            ;;
        restart|-r)
            load_required_module "services"
            # Load environment variables from generated env files
            source_service_envs
            if [ -n "$1" ]; then
                # Support multiple services: restart service1 service2 service3
                local vault_restarted=false
                while [ -n "$1" ]; do
                    restart_service "$1"
                    # Track if vault was restarted
                    if [ "$1" = "vault" ]; then
                        vault_restarted=true
                    fi
                    shift
                done
                # Auto-unseal vault if it was restarted
                if [ "$vault_restarted" = "true" ]; then
                    sleep 5  # Give vault time to start
                    log_message "Checking if Vault needs unsealing..."
                    if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
                        log_message "Vault is sealed after restart, unsealing..."
                        docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh 2>&1 || {
                            log_message "WARNING: Failed to auto-unseal Vault" "WARNING"
                        }
                    fi
                fi
            else
                restart_all_services
                # Auto-unseal vault after full restart
                sleep 5  # Give vault time to start
                log_message "Checking if Vault needs unsealing after restart..."
                if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
                    log_message "Vault is sealed after restart, unsealing..."
                    docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh 2>&1 || {
                        log_message "WARNING: Failed to auto-unseal Vault" "WARNING"
                    }
                fi
            fi
            return 0
            ;;
        start|-s)
            load_required_module "services"
            load_required_module "environment"
            # Load environment variables from generated env files
            source_service_envs
            if [ -n "$1" ]; then
                start_service "$1"
            else
                start_all_services
            fi
            return 0
            ;;
        stop|-t)
            load_required_module "services"
            if [ -n "$1" ]; then
                stop_service "$1"
            else
                stop_all_services
            fi
            return 0
            ;;
        unseal)
            # Unseal Vault if it's sealed
            log_message "Checking Vault seal status..."
            if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
                log_message "Vault is sealed, attempting to unseal..."
                if docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh 2>&1; then
                    log_message "✅ Vault unsealed successfully" "SUCCESS"
                else
                    log_message "❌ Failed to unseal Vault automatically" "ERROR"
                    log_message "Try manual unseal with: docker exec sting-ce-vault vault operator unseal <key>"
                    return 1
                fi
            else
                log_message "✅ Vault is already unsealed" "SUCCESS"
            fi
            return 0
            ;;
        reset|-rs)
            dev_reset
            return 0
            ;;
        build|-b)
            # Parse flags including verbosity and build options
            local new_args=()
            for arg in "$@"; do
                case "$arg" in
                    --no-cache|-nc)
                        no_cache=true
                        ;;
                    -q|--quiet)
                        setup_verbosity_level "$arg"
                        ;;
                    -v|--verbose)
                        setup_verbosity_level "$arg"
                        ;;
                    *)
                        new_args+=("$arg")
                        ;;
                esac
            done

            # Replace arguments with filtered list
            set -- "${new_args[@]}"

            # Check remaining args for service name
            if [ -n "$1" ]; then
                service="$1"
            fi
            
            load_required_module "docker"
            build_docker_services "$service" "$no_cache"
            return 0
            ;;
        sync-config)
            load_required_module "file_operations"
            sync_config_files
            log_message "💡 Tip: Restart affected services to apply configuration changes" "INFO"
            return 0
            ;;
        reset-config)
            load_required_module "file_operations"
            reset_config_files
            log_message "💡 Tip: Run './manage_sting.sh regenerate-env' to apply the fresh configuration" "INFO"
            return 0
            ;;
        regenerate-env)
            log_message "Regenerating environment files from config.yml..."
            
            # Ensure directories exist
            mkdir -p "${INSTALL_DIR}/env"
            
            # Load services module to start essential services if needed
            load_required_module "services"
            
            # Store current directory and change to install directory for docker compose
            local original_dir="$(pwd)"
            cd "${INSTALL_DIR}" || {
                log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
                return 1
            }
            
            # Check if essential services are running, start them if needed
            if ! docker compose ps vault 2>/dev/null | grep -q "Up"; then
                log_message "Starting essential services for config regeneration..."
                docker compose up -d vault
                sleep 5  # Give Vault time to start
            fi
            
            # Load environment variables from existing env files
            source_service_envs 2>/dev/null || true
            
            # Use config_loader.py directly for better compatibility
            local python_cmd="python3"
            if [ -f "${INSTALL_DIR}/.venv/bin/python3" ]; then
                python_cmd="${INSTALL_DIR}/.venv/bin/python3"
            fi
            
            if [ -f "${SOURCE_DIR}/conf/config_loader.py" ]; then
                # Set INSTALL_DIR environment variable for config_loader.py
                export INSTALL_DIR="${INSTALL_DIR}"
                
                if INSTALL_DIR="${INSTALL_DIR}" $python_cmd "${SOURCE_DIR}/conf/config_loader.py" "${SOURCE_DIR}/conf/config.yml" --mode runtime; then
                    log_message "✅ Environment files regenerated successfully" "SUCCESS"
                    log_message "💡 Tip: Restart affected services to apply configuration changes" "INFO"
                    
                    # List the generated files for confirmation
                    if [ -d "${INSTALL_DIR}/env" ]; then
                        local env_count
                        env_count=$(find "${INSTALL_DIR}/env" -name "*.env" -type f 2>/dev/null | wc -l)
                        log_message "Generated $env_count environment files in ${INSTALL_DIR}/env/" "INFO"
                    fi
                else
                    log_message "❌ Failed to regenerate environment files" "ERROR"
                    log_message "Check if Vault and other essential services are running" "ERROR"
                    cd "$original_dir" || true
                    return 1
                fi
            else
                log_message "❌ config_loader.py not found at ${SOURCE_DIR}/conf/config_loader.py" "ERROR"
                cd "$original_dir" || true
                return 1
            fi
            
            # Restore original directory
            cd "$original_dir" || true
            return 0
            ;;
        update)
            # Load docker module for build_docker_services function
            load_required_module "docker"
            # Load services module for wait_for_service function
            load_required_module "services"
            # Default to --no-cache for update operations (ensures fresh builds)
            no_cache=true
            sync_only=false
            force_update=false

            # Ensure Docker network exists before updating
            if ! docker network inspect sting_local >/dev/null 2>&1; then
                log_message "Creating Docker network: sting_local"
                docker network create sting_local || {
                    log_message "ERROR: Failed to create Docker network" "ERROR"
                    return 1
                }
            fi

            # Parse flags including verbosity
            local new_args=()
            for arg in "$@"; do
                case "$arg" in
                    --cache)
                        no_cache=false
                        ;;
                    --no-cache|-nc)
                        no_cache=true
                        ;;
                    --sync-only)
                        sync_only=true
                        log_message_verbose "🔍 Debug: --sync-only flag detected" "INFO"
                        ;;
                    --force)
                        force_update=true
                        ;;
                    -q|--quiet)
                        setup_verbosity_level "$arg"
                        ;;
                    -v|--verbose)
                        setup_verbosity_level "$arg"
                        ;;
                    *)
                        new_args+=("$arg")
                        ;;
                esac
            done
            
            # Debug output (only shown in verbose mode)
            log_message_verbose "🔍 Debug: sync_only=$sync_only, no_cache=$no_cache, force_update=$force_update, verbosity=$VERBOSITY_LEVEL" "INFO"

            # Replace arguments with filtered list
            set -- "${new_args[@]}"

            # Set PROJECT_DIR to the current working directory (where user runs the command)
            # This ensures we sync FROM the project directory TO the install directory
            PROJECT_DIR="$(pwd)"
            log_message_verbose "🔍 Debug: PROJECT_DIR set to: $PROJECT_DIR" "INFO"
            
            # Load file operations module for config checking and syncing
            load_required_module "file_operations"
            
            # Perform safety checks unless --force is used
            if [ "$force_update" != "true" ]; then
                log_message "🔍 Performing safety checks..."
                check_structural_changes
                local safety_result=$?
                
                case $safety_result in
                    2)
                        # Critical changes - abort unless forced
                        log_message "❌ Update aborted due to critical structural changes" "ERROR"
                        log_message "Use --force to override (not recommended)" "ERROR"
                        return 1
                        ;;
                    1)
                        # Minor changes - warn but continue
                        log_message "⚠️  Proceeding with update despite structural changes" "WARNING"
                        log_message "Monitor closely for issues" "WARNING"
                        ;;
                    0)
                        # No changes - safe to proceed
                        log_message "✅ Safety checks passed"
                        ;;
                esac
            else
                log_message "⚠️  Force mode enabled - skipping safety checks" "WARNING"
            fi
            
            # Check remaining args for service name
            if [ -n "$1" ]; then
                # Update specific service or all services
                service="$1"
                # Load environment variables from generated env files
                source_service_envs
                
                # Check if user wants to update all services
                if [ "$service" = "all" ]; then
                    log_message "🚀 Updating all application services (excluding infrastructure)..."
                    
                    # List of application services to update (excluding infrastructure like vault, db, redis, kratos)
                    # These are safe to update without data loss
                    local services=("app" "frontend" "knowledge" "chatbot" "external-ai" "llm-gateway-proxy" "utils")
                    local failed_services=()
                    
                    for svc in "${services[@]}"; do
                        log_message "📦 Updating $svc service..."
                        
                        # Check service dependencies
                        check_service_dependencies "$svc"
                        
                        # Copy fresh code for the service
                        if [ "$sync_only" = "true" ]; then
                            log_message "🔄 Sync-only mode: Syncing only changed files for $svc..."
                        else
                            log_message "Copying fresh code for $svc from project directory..."
                        fi
                        
                        if ! sync_service_code "$svc"; then
                            failed_services+=("$svc")
                            log_message "⚠️  Failed to sync code for $svc" "WARNING"
                        fi
                        
                        # Build the service
                        if ! build_docker_services "$svc" "$no_cache"; then
                            failed_services+=("$svc")
                            log_message "⚠️  Failed to build $svc" "WARNING"
                        fi
                    done
                    
                    # Report results
                    if [ ${#failed_services[@]} -gt 0 ]; then
                        log_message "⚠️  Some services failed to update: ${failed_services[*]}" "WARNING"
                        return 1
                    else
                        log_message "✅ All services updated successfully!"

                        # Post-update vault unsealing safety net
                        load_required_module "services"
                        ensure_vault_unsealed || log_message "⚠️  Vault unsealing check completed with warnings - manual verification recommended" "WARNING"

                        log_message "💡 Tip: Run './manage_sting.sh restart' to apply changes"
                        return 0
                    fi
                fi
                
                # Single service update (existing code)
                log_message "Updating $service service..."
                
                # Check service dependencies
                check_service_dependencies "$service"
                
                # Copy fresh code for the service
                if [ "$sync_only" = "true" ]; then
                    log_message "🔄 Sync-only mode: Syncing only changed files for $service..."
                else
                    log_message "Copying fresh code for $service from project directory..."
                fi
                sync_service_code "$service"
                
                # Fix execute permissions that may have been stripped (macOS compatibility)
                chmod +x "${INSTALL_DIR}/manage_sting.sh" 2>/dev/null || true
                chmod +x "${INSTALL_DIR}/lib"/*.sh 2>/dev/null || true
                
                # Special handling for utils service - build it first before config generation
                if [ "$service" = "utils" ]; then
                    # For utils service, we need to build it first since it's needed for config generation
                    log_message "🔨 Utils service: Building first to enable config generation..."
                    
                    # Store current directory and change to install directory for docker compose
                    local original_dir="$(pwd)"
                    cd "${INSTALL_DIR}" || {
                        log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
                        return 1
                    }
                    
                    # Stop and remove the service first to avoid conflicts
                    log_message "Stopping utils service..."
                    docker compose --profile installation stop utils 2>/dev/null || true
                    docker compose --profile installation rm -f utils 2>/dev/null || true
                    
                    # Use build_docker_services to get cache-buzz integration
                    log_message "Building utils service..."
                    build_docker_services "$service" "$no_cache"
                    
                    # Start the service
                    log_message "Starting utils service..."
                    docker compose --profile installation up -d utils
                    
                    cd "$original_dir" || true
                fi
                
                # Check if config changed
                if check_config_changes; then
                    # Load config utils for centralized config generation
                    source "${SCRIPT_DIR}/config_utils.sh" || {
                        log_message "Failed to load config utils module" "ERROR"
                        return 1
                    }
                    
                    # Regenerate env files using utils container (no local generation)
                    if ! generate_config_via_utils "runtime" "config.yml"; then
                        log_message "Failed to regenerate configuration files via utils container" "ERROR"
                        return 1
                    fi
                    
                    # Validate generation was successful
                    if ! validate_config_generation; then
                        log_message "Configuration validation failed" "ERROR"
                        return 1
                    fi
                    
                    source_service_envs
                fi
                
                # Store current directory and change to install directory for docker compose
                local original_dir="$(pwd)"
                cd "${INSTALL_DIR}" || {
                    log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
                    return 1
                }
                
                if [ "$sync_only" = "true" ]; then
                    log_message "🚀 Sync-only mode: Skipping Docker rebuild for $service" "INFO"
                    
                    # For frontend, the optimized sync handles container build directly
                    if [ "$service" = "frontend" ]; then
                        # The sync_service_code function already handled the optimized build
                        # Load services module for wait_for_service function
                        load_required_module "services"
                        
                        # Just verify the service is still healthy
                        log_message "Verifying frontend service health..." "INFO"
                        wait_for_service "$service"
                        log_message "✅ $service updated successfully with optimized sync-only mode" "SUCCESS"
                    elif [ "$service" = "app" ]; then
                        # Optimized sync for app service - copy files to running container and restart Python app
                        log_message "🔄 Optimized sync for app service: copying to running container..." "INFO"
                        
                        # Check if container is running
                        if docker ps --format "{{.Names}}" | grep -q "sting-ce-app"; then
                            # Copy changed files directly to running container
                            log_message "📁 Copying app files to running container..." "INFO"
                            docker cp "${INSTALL_DIR}/app/." sting-ce-app:/opt/sting-ce/app/
                            
                            # For Python Flask apps, the file sync is sufficient since Python dynamically imports
                            # No need to restart the process - Flask will pick up the changes automatically
                            log_message "📁 Files synced to running container - Flask will auto-reload modules" "INFO"
                            
                            # Brief wait for module reloads
                            sleep 1
                            
                            # Load services module for wait_for_service function
                            load_required_module "services"
                            
                            # Verify service health
                            log_message "🔍 Verifying app service health..." "INFO"
                            wait_for_service "$service"
                            log_message "✅ $service updated successfully with optimized sync-only mode (container sync)" "SUCCESS"
                        else
                            log_message "⚠️  App container not running, falling back to restart..." "WARNING"
                            docker compose restart "$service"
                        fi
                    else
                        log_message "Restarting $service to pick up file changes..." "INFO"
                        docker compose restart "$service"
                    fi
                else
                    # Skip rebuilding utils service if it was already built in the special handling above
                    if [ "$service" = "utils" ]; then
                        log_message "✅ Utils service already built and started" "SUCCESS"
                    else
                        log_message "🔨 Full rebuild mode for $service" "INFO"
                        # Stop and remove the service first to avoid conflicts
                        log_message "Stopping $service..."
                        docker compose stop "$service"
                        docker compose rm -f "$service"
                        
                        # Extra cleanup for vault to avoid container name conflicts
                        if [ "$service" = "vault" ]; then
                            log_message "Ensuring vault container is fully removed..."
                            docker rm -f sting-ce-vault 2>/dev/null || true
                        fi
                        
                        # Use build_docker_services to get cache-buzz integration
                        log_message "Building $service with cache-buzz support..."
                        build_docker_services "$service" "$no_cache"
                        
                        # Ensure .env file exists before starting
                        if [ ! -f "${INSTALL_DIR}/.env" ]; then
                            log_message "ERROR: .env file not found at ${INSTALL_DIR}/.env" "ERROR"
                            log_message "Run './manage_sting.sh install' to create configuration" "ERROR"
                            return 1
                        fi
                        
                        # Start the service
                        log_message "Starting $service..."
                        docker compose up -d "$service"

                        # Auto-unseal vault if it was updated
                        if [ "$service" = "vault" ]; then
                            sleep 5  # Give vault time to start
                            log_message "Checking if Vault needs unsealing after update..."
                            if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
                                log_message "Vault is sealed after update, unsealing..."
                                docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh 2>&1 || {
                                    log_message "WARNING: Failed to auto-unseal Vault after update" "WARNING"
                                    log_message "Try manual unseal with: msting unseal" "WARNING"
                                }
                            else
                                log_message "✅ Vault is already unsealed" "SUCCESS"
                            fi
                        fi
                    fi
                fi

                # Restore original directory
                cd "$original_dir" || true
                
            else
                # Update all services
                log_message "Updating all services..."
                
                # First, sync all code from project directory to INSTALL_DIR
                log_message "Syncing entire project to INSTALL_DIR..."
                
                # Create critical directories if they don't exist
                mkdir -p "$INSTALL_DIR"/{conf,env,logs,certs}
                
                # Sync with exclusions for critical/generated files
                # Use --no-perms to avoid permission issues with Docker-created directories
                rsync -av "$PROJECT_DIR/" "$INSTALL_DIR/" \
                    --no-perms \
                    --exclude ".git" \
                    --exclude ".gitignore" \
                    --exclude "*.pyc" \
                    --exclude "__pycache__" \
                    --exclude "node_modules" \
                    --exclude "build" \
                    --exclude "dist" \
                    --exclude "*.egg-info" \
                    --exclude ".env" \
                    --exclude "env/" \
                    --exclude "venv/" \
                    --exclude ".venv/" \
                    --exclude "*.log" \
                    --exclude "logs/" \
                    --exclude "backups/" \
                    --exclude "models/" \
                    --exclude "*.tar.gz" \
                    --exclude "*.zip" \
                    --exclude "postgres_data/" \
                    --exclude "vault_data/" \
                    --exclude "*_data/" \
                    --exclude "data/" \
                    --exclude "certs/" \
                    --exclude "secrets/" \
                    --exclude "conf/secrets/" \
                    --exclude "conf/vault/" \
                    --exclude "*.swp" \
                    --exclude ".DS_Store" \
                    --exclude "docker-compose.override.yml" \
                    --exclude "frontend/certs" \
                    --exclude "messaging_service/data" || log_message "Note: Some files could not be synced due to permissions" "WARN"
                
                # Fix execute permissions stripped by --no-perms rsync flag (macOS compatibility)
                log_message "Restoring execute permissions..."
                chmod +x "${INSTALL_DIR}/manage_sting.sh" 2>/dev/null || true
                chmod +x "${INSTALL_DIR}/lib"/*.sh 2>/dev/null || true
                chmod +x "${INSTALL_DIR}/scripts"/*.sh 2>/dev/null || true
                
                # Ensure conf directory is properly synced first
                log_message "Syncing configuration files..."
                # Ensure conf directory exists
                mkdir -p "$INSTALL_DIR/conf"
                
                # Copy critical config files explicitly
                if [ -f "$PROJECT_DIR/conf/config.yml" ]; then
                    cp -f "$PROJECT_DIR/conf/config.yml" "$INSTALL_DIR/conf/config.yml"
                    log_message "Copied config.yml"
                fi
                
                if [ -f "$PROJECT_DIR/conf/config_loader.py" ]; then
                    cp -f "$PROJECT_DIR/conf/config_loader.py" "$INSTALL_DIR/conf/config_loader.py"
                    log_message "Copied config_loader.py"
                fi
                
                # Copy other conf files
                for file in "$PROJECT_DIR/conf"/*.py; do
                    [ -f "$file" ] && cp -f "$file" "$INSTALL_DIR/conf/" || true
                done
                
                for file in "$PROJECT_DIR/conf"/*.yml; do
                    [ -f "$file" ] && cp -f "$file" "$INSTALL_DIR/conf/" || true
                done
                
                for file in "$PROJECT_DIR/conf"/*.txt; do
                    [ -f "$file" ] && cp -f "$file" "$INSTALL_DIR/conf/" || true
                done
                
                for file in "$PROJECT_DIR/conf"/*.in; do
                    [ -f "$file" ] && cp -f "$file" "$INSTALL_DIR/conf/" || true
                done
                
                # Copy subdirectories if they exist
                [ -d "$PROJECT_DIR/conf/kratos" ] && rsync -av "$PROJECT_DIR/conf/kratos/" "$INSTALL_DIR/conf/kratos/" \
                    --exclude='venv' --exclude='**/venv' --exclude='__pycache__' --exclude='*.pyc' || true
                [ -d "$PROJECT_DIR/conf/mailslurper" ] && rsync -av "$PROJECT_DIR/conf/mailslurper/" "$INSTALL_DIR/conf/mailslurper/" \
                    --exclude='venv' --exclude='**/venv' --exclude='__pycache__' --exclude='*.pyc' || true
                
                # Check if config changed and regenerate env files if needed
                if check_config_changes; then
                    # Regenerate env files using config_loader.py (with venv)
                    log_message "Running config_loader.py to regenerate environment files..."
                    if [ -f "${CONFIG_DIR}/config_loader.py" ]; then
                        local python_cmd="python3"
                        if [ -f "${INSTALL_DIR}/.venv/bin/python3" ]; then
                            python_cmd="${INSTALL_DIR}/.venv/bin/python3"
                        fi
                        if ! $python_cmd "${CONFIG_DIR}/config_loader.py" "${CONFIG_DIR}/config.yml"; then
                            log_message "Warning: Failed to regenerate env files" "WARN"
                        fi
                    else
                        log_message "Error: config_loader.py not found at ${CONFIG_DIR}/config_loader.py" "ERROR"
                    fi
                fi
                
                # Load environment variables
                source_service_envs
                
                # Store current directory and change to install directory for docker compose
                local original_dir="$(pwd)"
                cd "${INSTALL_DIR}" || {
                    log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
                    return 1
                }
                
                # Stop all services gracefully (preserves networks and volumes)
                log_message "Stopping all services gracefully..."
                docker compose stop

                # Remove containers to prepare for rebuild
                log_message "Removing old containers..."
                docker compose rm -f

                # Build all services with cache-buzz support
                log_message "Building all services with cache-buzz support..."
                build_docker_services "" "$no_cache"

                # Ensure .env file exists before starting
                if [ ! -f "${INSTALL_DIR}/.env" ]; then
                    log_message "ERROR: .env file not found at ${INSTALL_DIR}/.env" "ERROR"
                    log_message "Run './manage_sting.sh install' to create configuration" "ERROR"
                    return 1
                fi

                # Start services in proper dependency order
                log_message "Starting infrastructure services..."
                docker compose up -d db redis vault

                # Wait for database to be ready
                log_message "Waiting for database to be ready..."
                wait_for_service "db" || {
                    log_message "Database failed to start" "ERROR"
                    return 1
                }

                # Wait for vault to be ready
                log_message "Waiting for Vault to be ready..."
                wait_for_service "vault" || {
                    log_message "Vault failed to start" "ERROR"
                    return 1
                }

                # Start remaining services
                log_message "Starting application services..."
                docker compose up -d
                
                # Wait for critical services to be healthy
                log_message "Waiting for services to start..."
                
                # Wait for database first as many services depend on it
                wait_for_service "db" || log_message "Database health check failed" "WARN"
                
                # Wait for other critical services
                wait_for_service "vault" || log_message "Vault health check failed" "WARN"
                wait_for_service "kratos" || log_message "Kratos health check failed" "WARN"
                wait_for_service "app" || log_message "App health check failed" "WARN"
                
                # Give other services a moment to start
                sleep 5
                
                # Ensure all services are actually started (fix for dependency timing issues)
                source "$INSTALL_DIR/lib/fix_service_startup.sh"
                ensure_all_services_started || log_message "Some services may need manual start" "WARN"
                
                # Show status
                log_message "Services status:"
                docker compose ps
                
                # Restore original directory
                cd "$original_dir" || true
            fi
            return 0
            ;;
        backup|-ba)
            load_required_module "backup"
            
            # Parse backup options
            local encrypt_backup=false
            local backup_args=()
            
            for arg in "$@"; do
                case "$arg" in
                    --encrypt)
                        encrypt_backup=true
                        ;;
                    --export-key)
                        local key_file="${2:-backup_key.txt}"
                        export_backup_key "$key_file"
                        return $?
                        ;;
                    --import-key)
                        local key_file="$2"
                        if [ -z "$key_file" ]; then
                            log_message "ERROR: Key file required for --import-key" "ERROR"
                            return 1
                        fi
                        import_backup_key "$key_file"
                        return $?
                        ;;
                    *)
                        backup_args+=("$arg")
                        ;;
                esac
            done
            
            # Perform backup
            initialize_backup_directory
            if perform_backup; then
                # Get the latest backup file for potential encryption
                local latest_backup=""
                if [[ "$(uname)" == "Darwin" ]]; then
                    # macOS: Use stat with BSD format
                    latest_backup=$(find "$BACKUP_DIR" -name "sting_backup_*.tar.gz" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
                else
                    # Linux: Use GNU find
                    latest_backup=$(find "$BACKUP_DIR" -name "sting_backup_*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
                fi
                
                if [ "$encrypt_backup" = true ] && [ -n "$latest_backup" ]; then
                    log_message "Encrypting backup as requested..."
                    encrypt_backup "$latest_backup"
                fi
                return 0
            else
                return 1
            fi
            ;;
        restore|-re)
            load_required_module "backup"
            if [ -z "$1" ]; then
                log_message "ERROR: Backup file path required for restore" "ERROR"
                show_help
                return 1
            fi
            
            local restore_file="$1"
            
            # Check if backup is encrypted and decrypt if necessary
            if [[ "$restore_file" == *.enc ]]; then
                log_message "Detected encrypted backup, decrypting..."
                if decrypt_backup "$restore_file"; then
                    # Use decrypted file for restore
                    restore_file="${restore_file%.enc}"
                    log_message "Using decrypted backup: $restore_file"
                else
                    log_message "ERROR: Failed to decrypt backup" "ERROR"
                    return 1
                fi
            fi
            
            perform_restore "$restore_file"
            return 0
            ;;
        llm)
            # Pass all arguments to the LLM command handler
            handle_llm_command "$@"
            return 0
            ;;
        chatbot)
            # Pass all arguments to the Chatbot command handler
            handle_chatbot_command "$@"
            return 0
            ;;
        debug|-d)
            # Run debug diagnostics
            load_required_module "debug"
            local format="fancy"
            local check_type="all"
            
            # Parse debug options
            if [[ "$1" == "--plain" ]] || [[ "$1" == "-p" ]]; then
                format="plain"
                shift
            fi
            
            if [[ -n "$1" ]]; then
                check_type="$1"
            fi
            
            run_debug "$format" "$check_type"
            return 0
            ;;
        verbose|-v)
            # Enable verbose mode for the next command
            export VERBOSE=true
            
            if [ -n "$1" ]; then
                # Re-run with the next command in verbose mode
                $0 "$@"
                return $?
            else
                log_message "Verbose mode enabled but no command specified."
                show_help
                return 1
            fi
            ;;
        llm)
            # Load required modules for LLM commands
            load_required_module "services"
            # Call the handle_llm_command from services module
            handle_llm_command "${@:2}"  # Pass remaining arguments
            return 0
            ;;
        buzz)
            # 🐝 Hive Diagnostics - Buzz for Support
            if [ ! -f "${SOURCE_DIR}/lib/hive_diagnostics/honey_collector.sh" ]; then
                log_message "Hive Diagnostics not available - honey collector not found" "ERROR"
                return 1
            fi
            
            log_message "🐝 Starting Hive Diagnostics (Buzzing for Support)..."
            
            # Pass all arguments to the honey collector
            "${SOURCE_DIR}/lib/hive_diagnostics/honey_collector.sh" "$@"
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "🍯 Hive Diagnostics completed successfully" "SUCCESS"
            else
                log_message "❌ Hive Diagnostics failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        cache-buzz|cb)
            # 🐝 Cache Buzzer - Clear Docker cache and rebuild
            log_message "🐝 Starting Cache Buzzer - Enhanced Docker cache clearing..."
            
            if [ ! -f "${SOURCE_DIR}/lib/cache_buzzer.sh" ]; then
                log_message "Cache Buzzer not available - cache_buzzer.sh not found" "ERROR"
                return 1
            fi
            
            # Source the cache buzzer functions
            source "${SOURCE_DIR}/lib/cache_buzzer.sh"
            
            local cache_level="moderate"
            local service=""
            
            # Parse cache buzzer arguments
            while [ $# -gt 0 ]; do
                case "$1" in
                    --full)
                        cache_level="full"
                        log_message "🔥 Full cache clear mode enabled"
                        ;;
                    --moderate)
                        cache_level="moderate"
                        ;;
                    --minimal)
                        cache_level="minimal"
                        ;;
                    --service=*)
                        service="${1#--service=}"
                        ;;
                    --clear-only)
                        log_message "🧹 Clear cache only mode"
                        clear_docker_cache "$cache_level"
                        return $?
                        ;;
                    --validate)
                        log_message "🔍 Running container validation"
                        "${SOURCE_DIR}/lib/validate_containers_simple.sh"
                        return $?
                        ;;
                    *)
                        if [ -z "$service" ]; then
                            service="$1"
                        fi
                        ;;
                esac
                shift
            done
            
            log_message "Cache buzzer level: $cache_level"
            if [ -n "$service" ]; then
                log_message "Target service: $service"
                fresh_rebuild "$service" "$cache_level"
            else
                log_message "Rebuilding all services"
                fresh_rebuild "" "$cache_level"
            fi
            
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "✅ Cache buzzer completed successfully" "SUCCESS"
                log_message "💡 Run 'cache-buzz --validate' to verify freshness" "INFO"
            else
                log_message "❌ Cache buzzer failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        bee)
            # 🐝 Bee AI Support Assistant
            if [ ! -f "${SOURCE_DIR}/lib/bee_support_manager.sh" ]; then
                log_message "Bee Support Manager not available - bee_support_manager.sh not found" "ERROR"
                return 1
            fi
            
            log_message "🐝 Starting Bee AI Support Assistant..."
            
            # Handle bee sub-commands
            local subcommand="$1"
            shift || true
            
            if [ "$subcommand" = "support" ]; then
                # Pass remaining arguments to the bee support manager
                "${SOURCE_DIR}/lib/bee_support_manager.sh" "$@"
            else
                log_message "❌ Unknown bee command: $subcommand" "ERROR"
                log_message "Available: bee support [command]" "INFO"
                "${SOURCE_DIR}/lib/bee_support_manager.sh" help
                return 1
            fi
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "✅ Bee Support operation completed successfully" "SUCCESS"
            else
                log_message "❌ Bee Support operation failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        support)
            # 🔗 Support Tunnel Management (Headscale)
            if [ ! -f "${SOURCE_DIR}/lib/headscale_tunnel_manager.sh" ]; then
                log_message "Support tunnel manager not available - headscale_tunnel_manager.sh not found" "ERROR"
                return 1
            fi
            
            # Handle support sub-commands
            local subcommand="$1"
            shift || true
            
            if [ "$subcommand" = "tunnel" ]; then
                log_message "🔗 Starting Support Tunnel Manager..."
                # Pass remaining arguments to the tunnel manager
                "${SOURCE_DIR}/lib/headscale_tunnel_manager.sh" "$@"
            else
                log_message "❌ Unknown support command: $subcommand" "ERROR"
                log_message "Available: support tunnel [command]" "INFO"
                "${SOURCE_DIR}/lib/headscale_tunnel_manager.sh" help
                return 1
            fi
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "✅ Support tunnel operation completed successfully" "SUCCESS"
            else
                log_message "❌ Support tunnel operation failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        bundle)
            # 📦 Local Bundle Management - Download and share your bundles
            if [ ! -f "${SOURCE_DIR}/lib/local_bundle_manager.sh" ]; then
                log_message "Local bundle manager not available - local_bundle_manager.sh not found" "ERROR"
                return 1
            fi
            
            log_message "📦 Starting Local Bundle Manager..."
            
            # Pass all arguments to the local bundle manager
            "${SOURCE_DIR}/lib/local_bundle_manager.sh" "$@"
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "✅ Bundle operation completed successfully" "SUCCESS"
            else
                log_message "❌ Bundle operation failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        install-ollama|ollama-install)
            log_message "Installing Ollama for STING..."
            if [ -f "${SOURCE_DIR}/scripts/install_ollama.sh" ]; then
                bash "${SOURCE_DIR}/scripts/install_ollama.sh" "$@"
            else
                log_message "Ollama install script not found" "ERROR"
                return 1
            fi
            return $?
            ;;
        ollama-status)
            log_message "Checking Ollama status..."
            if command -v ollama >/dev/null 2>&1; then
                if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                    log_message "✅ Ollama is running" "SUCCESS"
                    ollama list
                else
                    log_message "❌ Ollama is installed but not running" "ERROR"
                    log_message "Start with: ollama serve" "INFO"
                fi
            else
                log_message "❌ Ollama is not installed" "ERROR"
                log_message "Install with: ./manage_sting.sh install-ollama" "INFO"
            fi
            return 0
            ;;
        llm-status)
            log_message "Checking LLM services status..."
            # Check Ollama
            if command -v ollama >/dev/null 2>&1 && curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
                log_message "✅ Ollama: Running" "SUCCESS"
            else
                log_message "❌ Ollama: Not running" "ERROR"
            fi
            # Check External AI service
            if curl -sf http://localhost:8091/health >/dev/null 2>&1; then
                log_message "✅ External AI Service: Running" "SUCCESS"
            else
                log_message "❌ External AI Service: Not running" "ERROR"
            fi
            # Check sting-llm script
            if [ -f "${SOURCE_DIR}/sting-llm" ]; then
                log_message "ℹ️  sting-llm script: Available" "INFO"
                log_message "Run: ./sting-llm status" "INFO"
            fi
            return 0
            ;;
        build-analytics)
            # Build Analytics - View Docker build logs & performance
            log_message "🐝 Build Intelligence & Analytics" "INFO"
            
            # Parse arguments: service and hours
            local target_service="${2:-all}"
            local hours="${3:-24}"
            
            # Source build logging utilities
            if [ -f "${SCRIPT_DIR}/lib/build_logging.sh" ]; then
                source "${SCRIPT_DIR}/lib/build_logging.sh"
            fi
            
            # Run the build logs maintenance script
            if [ -f "${SOURCE_DIR}/scripts/maintenance/build_logs_maintenance.sh" ]; then
                bash "${SOURCE_DIR}/scripts/maintenance/build_logs_maintenance.sh" analytics "$target_service" "$hours"
            else
                # Fallback to basic analytics display
                if command -v get_build_analytics >/dev/null 2>&1; then
                    get_build_analytics "$target_service" "$hours"
                else
                    log_message "Build analytics not available - build logging not initialized" "WARNING"
                    log_message "Try: ./manage_sting.sh update <service> to trigger build logging" "INFO"
                fi
            fi
            return 0
            ;;
        volumes)
            # Volume Management - List, purge, backup Docker volumes
            load_required_module "volume_management"
            manage_volumes "$@"
            return 0
            ;;
        dev)
            # Development workflow management
            local dev_script="${INSTALL_DIR}/scripts/dev_manager.sh"
            if [[ ! -f "$dev_script" ]]; then
                dev_script="${SOURCE_DIR}/scripts/dev_manager.sh"
            fi
            
            if [[ ! -f "$dev_script" ]]; then
                log_message "Development script not found. Run 'msting sync-config' first." "ERROR"
                return 1
            fi
            
            # Export environment variables for dev_manager.sh
            export PROJECT_ROOT="${SOURCE_DIR}"
            export INSTALL_DIR="${INSTALL_DIR}"
            
            # Pass all remaining arguments to dev_manager.sh (dev is already consumed)
            exec "$dev_script" "$@"
            ;;
        create)
            # User and resource creation commands
            local resource_type="$1"
            shift
            
            case "$resource_type" in
                admin)
                    # Parse arguments
                    local email=""
                    local passwordless=true  # PASSWORDLESS BY DEFAULT
                    local password=""
                    local use_password=false
                    
                    for arg in "$@"; do
                        case "$arg" in
                            --email=*)
                                email="${arg#--email=}"
                                ;;
                            --use-password)
                                use_password=true
                                passwordless=false  # Override default
                                ;;
                            --passwordless)
                                passwordless=true  # Explicit passwordless (already default)
                                ;;
                            --password=*)
                                password="${arg#--password=}"
                                # If password provided without --use-password, warn but allow
                                if [[ "$use_password" != "true" ]]; then
                                    log_message "Warning: Password provided but --use-password not specified. Using password mode." "WARNING"
                                    use_password=true
                                    passwordless=false
                                fi
                                ;;
                            *)
                                if [[ -z "$email" && "$arg" != --* ]]; then
                                    email="$arg"
                                fi
                                ;;
                        esac
                    done
                    
                    if [[ -z "$email" ]]; then
                        log_message "Error: Email address is required" "ERROR"
                        log_message "Usage: msting create admin --email=admin@example.com [--use-password] [--password=...]" "INFO"
                        log_message "Note: Admin creation is PASSWORDLESS by default" "INFO"
                        return 1
                    fi
                    
                    # SECURITY CHECK: Verify sudo/root privileges before admin creation
                    if ! check_admin_creation_privileges; then
                        log_message "🛡️ SECURITY PROTECTION: Unauthorized admin creation attempt blocked" "ERROR"
                        log_message "📧 Admin creation for: $email (DENIED)" "WARNING"
                        return 1
                    fi
                    
                    log_message "🔐 Security check passed - proceeding with admin creation" "INFO"
                    
                    # Call the admin creation script (inside Docker container where dependencies exist)
                    local create_script="${SOURCE_DIR}/scripts/create_passwordless_admin.py"
                    if [[ ! -f "$create_script" ]]; then
                        create_script="${INSTALL_DIR}/scripts/create-new-admin.py"
                    fi
                    
                    if [[ ! -f "$create_script" ]]; then
                        log_message "Admin creation script not found" "ERROR"
                        return 1
                    fi
                    
                    # Build command arguments
                    local cmd_args=("--email=$email")
                    if [[ "$use_password" == "true" ]]; then
                        cmd_args+=("--use-password")
                        if [[ -n "$password" ]]; then
                            cmd_args+=("--password=$password")
                        fi
                        log_message "Creating LEGACY password-based admin (not recommended)" "WARNING"
                    else
                        # Default passwordless mode
                        log_message "Creating admin account (email authentication enabled)" "INFO"
                    fi
                    
                    log_message "Creating admin user: $email" "INFO"
                    
                    # Copy script to container and execute it there (where all dependencies exist)
                    docker cp "$create_script" sting-ce-app:/tmp/create_admin.py 2>/dev/null
                    
                    # Execute the script inside the container
                    docker exec sting-ce-app python /tmp/create_admin.py "${cmd_args[@]}"
                    local result=$?
                    
                    # Clean up temporary script
                    docker exec sting-ce-app rm -f /tmp/create_admin.py 2>/dev/null
                    
                    return $result
                    ;;
                user)
                    log_message "Creating regular user: $email" "INFO"
                    
                    # Use the create_user.py script  
                    local create_script="$SCRIPT_DIR/../scripts/troubleshooting/dangerzone/create_user.py"
                    
                    if [[ ! -f "$create_script" ]]; then
                        log_message "User creation script not found: $create_script" "ERROR"
                        return 1
                    fi
                    
                    log_message "Creating user account: $email" "INFO"
                    
                    # Copy script to container and execute it there (where all dependencies exist)
                    docker cp "$create_script" sting-ce-app:/tmp/create_user.py 2>/dev/null
                    
                    # Execute the script inside the container
                    docker exec sting-ce-app python /tmp/create_user.py "${cmd_args[@]}"
                    local result=$?
                    
                    # Clean up temporary script
                    docker exec sting-ce-app rm -f /tmp/create_user.py 2>/dev/null
                    
                    return $result
                    ;;
                *)
                    log_message "Unknown resource type: $resource_type" "ERROR"
                    log_message "Available types: admin, user" "INFO"
                    return 1
                    ;;
            esac
            ;;
        delete)
            # User and resource deletion commands
            local resource_type="$1"
            shift
            
            case "$resource_type" in
                admin)
                    # Parse arguments
                    local email=""
                    local force=false
                    
                    for arg in "$@"; do
                        case "$arg" in
                            --email=*)
                                email="${arg#--email=}"
                                ;;
                            --force)
                                force=true
                                ;;
                            *)
                                if [[ -z "$email" && "$arg" != --* ]]; then
                                    email="$arg"
                                fi
                                ;;
                        esac
                    done
                    
                    if [[ -z "$email" ]]; then
                        log_message "Error: Email address is required" "ERROR"
                        log_message "Usage: msting delete admin --email=user@domain.com [--force]" "INFO"
                        return 1
                    fi
                    
                    # SECURITY CHECK: Verify sudo/root privileges before admin deletion
                    if ! check_admin_creation_privileges; then
                        log_message "🛡️ SECURITY PROTECTION: Unauthorized admin deletion attempt blocked" "ERROR"
                        log_message "📧 Admin deletion for: $email (DENIED)" "WARNING"
                        return 1
                    fi
                    
                    log_message "🔐 Security check passed - proceeding with admin deletion" "INFO"
                    
                    # Call the admin deletion script
                    local delete_script="${SOURCE_DIR}/scripts/delete-admin.py"
                    if [[ ! -f "$delete_script" ]]; then
                        delete_script="${INSTALL_DIR}/scripts/delete-admin.py"
                    fi
                    
                    if [[ ! -f "$delete_script" ]]; then
                        log_message "Admin deletion script not found" "ERROR"
                        return 1
                    fi
                    
                    # Build command arguments
                    local cmd_args=("--email=$email")
                    if [[ "$force" == "true" ]]; then
                        cmd_args+=("--force")
                    fi
                    
                    log_message "Deleting admin user: $email" "INFO"
                    
                    # Follow the same pattern as admin creation: copy script to container then execute
                    docker cp "$delete_script" sting-ce-app:/tmp/delete_admin.py 2>/dev/null
                    
                    # Run script inside container with proper Python environment
                    docker exec sting-ce-app python3 /tmp/delete_admin.py "${cmd_args[@]}"
                    local exit_code=$?
                    
                    # Clean up temporary script
                    docker exec sting-ce-app rm -f /tmp/delete_admin.py 2>/dev/null
                    
                    return $exit_code
                    ;;
                user)
                    log_message "Regular user deletion not yet implemented" "WARNING"
                    log_message "Use: msting delete admin --email=... for admin users" "INFO"
                    return 1
                    ;;
                *)
                    log_message "Unknown resource type: $resource_type" "ERROR"
                    log_message "Available types: admin, user" "INFO"
                    return 1
                    ;;
            esac
            ;;
        recreate)
            # Recreate admin user (delete then create)
            local resource_type="$1"
            shift
            
            if [[ "$resource_type" == "admin" ]]; then
                if [ $# -eq 0 ]; then
                    log_message "Email required for admin recreation" "ERROR"
                    log_message "Usage: ./manage_sting.sh recreate admin --email=admin@example.com" "INFO"
                    return 1
                fi
                
                # Parse email from arguments
                local email=""
                for arg in "$@"; do
                    case $arg in
                        --email=*)
                            email="${arg#*=}"
                            ;;
                    esac
                done
                
                if [ -z "$email" ]; then
                    log_message "Email required for admin recreation" "ERROR"
                    return 1
                fi
                
                log_message "🔄 Recreating admin user: $email" "INFO"
                log_message "Step 1: Attempting to delete existing user..." "INFO"
                
                # Try to delete (ignore failures since user might not exist)
                "${SCRIPT_DIR}/manage_sting.sh" delete admin --email="$email" 2>/dev/null || true
                
                log_message "Step 2: Creating fresh admin user..." "INFO"
                
                # Create the user
                if "${SCRIPT_DIR}/manage_sting.sh" create admin --email="$email"; then
                    log_message "✅ Admin user recreated successfully: $email" "SUCCESS"
                else
                    log_message "❌ Failed to recreate admin user" "ERROR"
                    return 1
                fi
            else
                log_message "Recreate only supports 'admin' resource type" "ERROR"
                return 1
            fi
            ;;
        upload-knowledge)
            # Upload STING Platform Knowledge to Honey Jar
            log_message "📚 Uploading STING Platform Knowledge to Honey Jar..."
            
            # Check if knowledge directory exists on host
            local knowledge_dir="${SOURCE_DIR}/knowledge/sting-platform-docs"
            if [ ! -d "$knowledge_dir" ]; then
                log_message "Knowledge directory not found: $knowledge_dir" "ERROR"
                log_message "Run './manage_sting.sh sync-config' to create knowledge structure" "INFO"
                return 1
            fi
            
            # Check if app container is running
            if ! docker ps | grep -q "sting-ce-app.*Up"; then
                log_message "STING app container is not running" "ERROR"
                log_message "Start services with: ./manage_sting.sh start" "INFO"
                return 1
            fi
            
            # Run the upload script inside the app container where it has proper access
            log_message "Running upload script inside app container with proper authentication..."
            docker exec sting-ce-app python3 /app/scripts/upload_sting_knowledge.py "$@"
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_message "✅ Knowledge upload completed successfully" "SUCCESS"
            else
                log_message "❌ Knowledge upload failed" "ERROR"
            fi
            
            return $exit_code
            ;;
        help|-h|\"\")
            show_help
            return 0
            ;;
        *)
            log_message "Unknown command: $action" "ERROR"
            show_help
            return 1
            ;;
    esac
}