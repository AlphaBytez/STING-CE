#!/bin/bash
# health.sh - Health checks and monitoring functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Verify database credentials are properly set
verify_db_credentials() {
    log_message "Verifying database credentials..."
    
    # Check if required variables are set
    if [ -z "${POSTGRES_USER}" ] || [ -z "${POSTGRES_PASSWORD}" ] || [ -z "${POSTGRES_DB}" ]; then
        log_message "ERROR: Required database environment variables are not set"
        log_message "POSTGRES_USER: ${POSTGRES_USER:-not set}"
        log_message "POSTGRES_DB: ${POSTGRES_DB:-not set}"
        log_message "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:+is set}"
        return 1
    fi
    
    # Log the values we're using (careful with password)
    log_message "Using database configuration:"
    log_message "Database: ${POSTGRES_DB}"
    log_message "User: ${POSTGRES_USER}"
    log_message "Password is ${POSTGRES_PASSWORD:+set}"
    
    return 0
}

# Verify database schema exists and is populated
verify_db_schema() {
    local db_name="${POSTGRES_DB:-sting_app}"
    local db_user="${POSTGRES_USER:-postgres}"

    # wait for the database to be ready
    sleep 2
    
    log_message "Verifying database schema..."
    
    # First check if database exists
    if ! docker compose exec -T db psql -U "$db_user" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$db_name'" | grep -q 1; then
        log_message "ERROR: Database $db_name does not exist"
        return 1
    fi
    
    # Check tables only if database exists
    local check_tables
    check_tables=$(docker compose exec -T db psql -U "$db_user" -d "$db_name" -tAc "\
        SELECT COUNT(*) FROM information_schema.tables \
        WHERE table_schema = 'public';")
    
    if [ -z "$check_tables" ] || [ "$check_tables" -eq "0" ]; then
        log_message "ERROR: No tables found in database"
        return 1
    fi
    
    log_message "Database schema verification completed successfully"
    return 0
}

# Check and prepare database initialization files
check_db_init_files() {
    log_message "Checking database initialization files..."
    
    # Check if init_db.sql exists in the correct location
    local init_sql="${INSTALL_DIR}/conf/init_db.sql"
    if [ ! -f "$init_sql" ]; then
        log_message "ERROR: init_db.sql not found at $init_sql"
        return 1
    fi
    
    # Check if docker-entrypoint-initdb.d directory exists
    local init_dir="${INSTALL_DIR}/docker-entrypoint-initdb.d"
    if [ ! -d "$init_dir" ]; then
        log_message "Creating docker-entrypoint-initdb.d directory..."
        mkdir -p "$init_dir"
    fi
    
    # Copy init_db.sql to docker-entrypoint-initdb.d
    log_message "Copying init_db.sql to docker-entrypoint-initdb.d..."
    cp "$init_sql" "${init_dir}/init.sql"
    
    # Set proper permissions
    chmod 644 "${init_dir}/init.sql"
    
    log_message "Database initialization files checked and prepared"
    return 0
}

# Helper function: Comprehensive health check
check_system_health() {
    log_message "Running comprehensive system health check..."
    
    local health_status=0
    
    # Check database health
    if ! verify_db_credentials; then
        log_message "Database credentials check failed" "ERROR"
        health_status=1
    fi
    
    # Check if database is responsive
    if ! check_database_connection; then
        log_message "Database connection check failed" "ERROR"
        health_status=1
    fi
    
    # Check LLM models availability 
    if ! check_llm_models; then
        log_message "LLM models check failed" "ERROR"
        health_status=1
    fi
    
    # Check services
    if ! check_services_health; then
        log_message "Services health check failed" "ERROR"
        health_status=1
    fi
    
    if [ $health_status -eq 0 ]; then
        log_message "System health check passed" "SUCCESS"
    else
        log_message "System health check failed" "ERROR"
    fi
    
    return $health_status
}

# Helper function: Check database connection
check_database_connection() {
    log_message "Checking database connection..."
    
    local db_user="${POSTGRES_USER:-postgres}"
    local db_name="${POSTGRES_DB:-sting_app}"
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T db pg_isready -U "$db_user" -d "$db_name" >/dev/null 2>&1; then
            log_message "Database connection successful"
            return 0
        fi
        
        log_message "Waiting for database connection... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "ERROR: Database connection failed after $max_attempts attempts"
    return 1
}

# Helper function: Check all services health
check_services_health() {
    log_message "Checking all services health..."
    
    # Essential services that must be running
    local essential_services=("db" "vault" "kratos" "app" "frontend")
    # Additional important services
    local important_services=("report-worker" "redis" "mailpit")
    # Optional services
    local optional_services=("chroma" "knowledge" "llm-gateway-proxy" "chatbot" "messaging" "external-ai")
    # Utils is a special case - only runs during installation
    
    local failed_essential=()
    local failed_important=()
    local failed_optional=()
    
    # Check essential services
    for service in "${essential_services[@]}"; do
        if ! docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
            failed_essential+=("$service")
        fi
    done
    
    # Check important services
    for service in "${important_services[@]}"; do
        if ! docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
            failed_important+=("$service")
        fi
    done
    
    # Check optional services
    for service in "${optional_services[@]}"; do
        if ! docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
            failed_optional+=("$service")
        fi
    done
    
    # Report results
    if [ ${#failed_essential[@]} -eq 0 ]; then
        log_message "[+] All essential services are running" "SUCCESS"
    else
        log_message "[-] Failed essential services: ${failed_essential[*]}" "ERROR"
    fi
    
    if [ ${#failed_important[@]} -gt 0 ]; then
        log_message "[!]  Failed important services: ${failed_important[*]}" "WARNING"
    fi
    
    if [ ${#failed_optional[@]} -gt 0 ]; then
        log_message "[*]  Optional services not running: ${failed_optional[*]}" "INFO"
    fi
    
    # Return failure only if essential services are down
    if [ ${#failed_essential[@]} -eq 0 ]; then
        return 0
    else
        return 1
    fi
}


# Helper function: Check memory usage
check_memory_usage() {
    log_message "Checking memory usage..."
    
    local available_memory
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        available_memory=$(vm_stat | awk '/free/ {print int($3)*4096/1024/1024}')
    else
        # Linux
        available_memory=$(free -m | awk '/^Mem:/ {print $7}')
    fi
    
    local required_memory=2048  # 2GB minimum
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        log_message "WARNING: Low memory. Available: ${available_memory}MB, Required: ${required_memory}MB"
        return 1
    else
        log_message "Memory check passed: ${available_memory}MB available"
        return 0
    fi
}

# Helper function: Check port availability
check_port_availability() {
    local port="$1"
    local service_name="$2"
    
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        log_message "Port $port is in use by $service_name"
        return 0
    else
        log_message "WARNING: Port $port is not in use (expected for $service_name)"
        return 1
    fi
}

# # Check for pre-downloaded LLM models
# check_llm_models() {
#     local models_dir="${STING_MODELS_DIR:-$HOME/Downloads/llm_models}"
#     local has_models=false
    
#     log_message "Checking for pre-downloaded LLM models in: $models_dir"
    
#     # Check if models directory exists and has any model subdirectories
#     if [ -d "$models_dir" ]; then
#         # Check for any model directories (they typically have names like tinyllama, deepseek-1.5b, etc.)
#         if find "$models_dir" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
#             has_models=true
#             log_message "Found downloaded models in $models_dir"
#         fi
#     fi
    
#     if [ "$has_models" = "false" ]; then
#         echo ""
#         echo "[-] ERROR: No LLM models found!"
#         echo ""
#         echo "The installation REQUIRES pre-downloaded LLM models."
#         echo ""
#         echo "Please run one of the following commands first:"
#         echo "  ./download_small_models.sh     (Recommended - ~5GB total)"
#         echo "  ./download_optimized_models.sh (Better performance - ~15GB total)"
#         echo ""
#         echo "These scripts will download models to: $models_dir"
#         echo ""
#         echo "Why this is required:"
#         echo "  1. Prevents installation from hanging"
#         echo "  2. Avoids network issues during Docker builds"
#         echo "  3. Ensures predictable installation experience"
#         echo ""
#         log_message "Installation cancelled - models must be downloaded first"
#         return 1
#     fi
    
#     return 0
# }

# Check disk space
check_disk_space() {
    log_message "Checking disk space..."
    
    local required_gb=10
    local available_space
    local check_path="$INSTALL_DIR"
    
    # If INSTALL_DIR doesn't exist, check its parent directory
    if [ ! -d "$check_path" ]; then
        check_path=$(dirname "$check_path")
        # If parent doesn't exist, check root
        [ ! -d "$check_path" ] && check_path="/"
    fi
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        available_space=$(df -h "$check_path" 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G.*//')
    else
        # Linux
        available_space=$(df -h "$check_path" 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G.*//')
    fi
    
    # Convert to integer for comparison
    available_space=${available_space%.*}
    
    # Handle case where df output might be empty or invalid
    if [ -z "$available_space" ] || ! [[ "$available_space" =~ ^[0-9]+$ ]]; then
        log_message "WARNING: Could not determine available disk space, skipping check"
        return 0
    fi
    
    if [ "$available_space" -lt "$required_gb" ]; then
        log_message "WARNING: Low disk space. Available: ${available_space}GB, Required: ${required_gb}GB"
        return 1
    else
        log_message "Disk space check passed: ${available_space}GB available"
        return 0
    fi
}

# Helper function: Check individual service health with details
check_service_health_detailed() {
    local service="$1"
    local container_name="sting-ce-${service}"
    
    # Check if container exists
    if ! docker ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
        echo "Container not found"
        return 2
    fi
    
    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        echo "Container stopped"
        return 1
    fi
    
    # Check health status if available
    local health_status=$(docker inspect "$container_name" 2>/dev/null | jq -r '.[0].State.Health.Status // "none"')
    
    case "$health_status" in
        "healthy")
            echo "Healthy"
            return 0
            ;;
        "unhealthy")
            echo "Unhealthy"
            return 1
            ;;
        "starting")
            echo "Starting"
            return 0
            ;;
        "none")
            echo "Running (no health check)"
            return 0
            ;;
        *)
            echo "Unknown status: $health_status"
            return 1
            ;;
    esac
}

# Helper function: List all STING services and their status
list_all_services_status() {
    log_message "STING Services Status Overview:" "INFO"
    log_message "================================" "INFO"
    
    # All known services
    local all_services=("db" "vault" "kratos" "app" "frontend" "report-worker" 
                       "redis" "mailpit" "chroma" "knowledge" "llm-gateway-proxy" 
                       "chatbot" "messaging" "external-ai" "utils")
    
    for service in "${all_services[@]}"; do
        local status=$(check_service_health_detailed "$service")
        local status_code=$?
        
        case $status_code in
            0) log_message "$service: $status" "SUCCESS" ;;
            1) log_message "$service: $status" "ERROR" ;;
            2) log_message "$service: $status" "INFO" ;;
        esac
    done
}

# Helper function: Check required ports
check_required_ports() {
    log_message "Checking required ports..."
    
    local ports=(
        "8443:frontend"
        "5050:backend"
        "5432:database"
        "8200:vault"
        "4433:kratos-public"
        "4434:kratos-admin"
    )
    
    local failed_ports=()
    
    for port_service in "${ports[@]}"; do
        local port="${port_service%:*}"
        local service="${port_service#*:}"
        
        if ! check_port_availability "$port" "$service"; then
            failed_ports+=("$port ($service)")
        fi
    done
    
    if [ ${#failed_ports[@]} -eq 0 ]; then
        log_message "All required ports are active" "SUCCESS"
        return 0
    else
        log_message "Inactive ports: ${failed_ports[*]}" "ERROR"
        return 1
    fi
}

# Export functions for use in other scripts
export -f check_service_health_detailed
export -f list_all_services_status
export -f check_services_health