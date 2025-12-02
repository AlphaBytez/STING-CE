#!/bin/bash
# docker.sh - Docker-specific operations and utilities

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"
source "${SCRIPT_DIR}/build_logging.sh"

# Source WSL2 Docker fixes if available
if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
    source "${SCRIPT_DIR}/docker_wsl_fix.sh"
    # Apply Docker credential helper fix for WSL2
    fix_docker_credential_helper >/dev/null 2>&1
fi

# Docker wrapper function to handle compose commands
docker() {
    if [ "$1" = "compose" ]; then
        shift
        # On Mac, include the Mac-specific compose file if it exists
        if [[ "$(uname)" == "Darwin" ]] && [ -f "${INSTALL_DIR}/docker-compose.mac.yml" ]; then
            # Use 'command docker' to bypass this function and avoid recursion
            command docker compose -p "${COMPOSE_PROJECT_NAME:-sting-ce}" \
                -f "${INSTALL_DIR}/docker-compose.yml" \
                -f "${INSTALL_DIR}/docker-compose.mac.yml" "$@"
        else
            # Use 'command docker' to bypass this function and avoid recursion
            command docker compose -p "${COMPOSE_PROJECT_NAME:-sting-ce}" "$@"
        fi
    else
        command docker "$@"
    fi
}

# Check if Docker Compose file exists and is valid
check_docker_compose_file() {
    local compose_file="${INSTALL_DIR}/docker-compose.yml"
    log_message "Checking Docker Compose file..."
    if [ ! -f "$compose_file" ]; then
        log_message "ERROR: Docker Compose file not found at $compose_file"
        return 1
    fi
    # log_message "DEBUG: Contents of Docker Compose file:"
    # cat "$compose_file"
    return 0
}

# Build Docker services with optional cache control and verbosity
build_docker_services() {
    local service="$1"
    local no_cache="$2"
    local cache_level="${3:-moderate}"  # full, moderate, minimal for enhanced cache buzzing

    # Use full cache clearing when updating ALL services
    if [ -z "$service" ] && [ "$no_cache" = "true" ]; then
        cache_level="full"
        log_message_verbose "🐝 Updating all services - using FULL cache clearing" "INFO" true
    elif [ "$service" = "frontend" ] && [ "$no_cache" = "true" ]; then
        # Frontend requires extreme service-specific cache clearing due to persistent caching issues
        cache_level="frontend-extreme"
        log_message_verbose "🐝 Updating frontend service - using EXTREME service-specific cache clearing (default for frontend)" "INFO" true
    fi

    show_build_progress "Building ${service:-all} services"

    # Use enhanced cache buzzing if no_cache is true
    if [ "$no_cache" = "true" ]; then
        # Source cache buzzer functions
        if [ -f "$(dirname "${BASH_SOURCE[0]}")/cache_buzzer.sh" ]; then
            source "$(dirname "${BASH_SOURCE[0]}")/cache_buzzer.sh"
            log_message_verbose "🐝 Using enhanced cache buzzer (level: $cache_level)" "INFO"
            build_docker_services_nocache "$service" "$cache_level"
            return $?
        else
            log_message_verbose "Warning: cache_buzzer.sh not found, falling back to standard build" "WARNING" true
        fi
    fi
    
    # Standard build process (original logic)
    # Initialize buildx builder if not exists or recreate if missing DNS config
    local buildkit_config="$SCRIPT_DIR/buildkitd.toml"
    local need_builder_recreate=false

    if ! docker buildx inspect builder &>/dev/null; then
        # Builder doesn't exist, need to create it
        need_builder_recreate=true
    elif [ -f "$buildkit_config" ]; then
        # Builder exists, check if it has DNS config
        if ! docker buildx inspect builder 2>/dev/null | grep -q "nameservers"; then
            log_message_verbose "Existing builder missing DNS config, recreating..." "WARNING" true
            # Clean up refs directory first to avoid .DS_Store issues on macOS
            rm -rf ~/.docker/buildx/refs/builder 2>/dev/null || true
            docker buildx rm builder 2>/dev/null || true
            need_builder_recreate=true
        fi
    fi

    if [ "$need_builder_recreate" = "true" ]; then
        # Use buildkitd.toml for DNS configuration (fixes DNS resolution issues)
        if [ -f "$buildkit_config" ]; then
            log_message_verbose "Creating buildx builder with DNS configuration..." "INFO" true
            docker buildx create --name builder --driver docker-container --config "$buildkit_config" --use
        else
            log_message_verbose "Creating buildx builder (no DNS config found)..." "WARNING" true
            docker buildx create --name builder --driver docker-container --use
        fi
    fi
    
    # If specifically building vault, skip initialization check
    if [ "$service" = "vault" ]; then
        if [ "$no_cache" = "true" ]; then
            docker buildx build --platform linux/amd64,linux/arm64 --no-cache --pull -t vault .
        else
            docker buildx build --platform linux/amd64,linux/arm64 -t vault .
        fi
        return $?
    fi

    # Initialize build logging for Bee Intelligence
    initialize_build_logging

    # Detect if we should use BuildKit or legacy builder
    # BuildKit DNS config doesn't work reliably on macOS, use legacy builder there
    # On Linux/WSL2, BuildKit with DNS config works great
    local builder_arg=""
    if [ "$(uname)" = "Darwin" ]; then
        # macOS: BuildKit DNS doesn't work, always use legacy builder
        log_message_verbose "Using legacy Docker builder (BuildKit DNS issues on macOS)" "INFO" true
        export DOCKER_BUILDKIT=0
    else
        # Linux/WSL2: Use BuildKit with DNS config from buildkitd.toml
        builder_arg="--builder builder"
        log_message_verbose "Using BuildKit builder with DNS configuration for image builds" "INFO" true
    fi

    # Determine if we should skip --pull (OVA mode or images already present)
    local pull_arg="--pull"
    if [ -f "/opt/sting-ce-source/.ova-prebuild" ] || [ "${STING_SKIP_PULL:-}" = "1" ]; then
        pull_arg=""
        log_message_verbose "Skipping --pull (OVA with pre-built images)" "INFO" true
    fi

    if [ -z "$service" ]; then
        # Build all services with verbosity-controlled logging
        local build_cmd
        if [ "$no_cache" = "true" ]; then
            build_cmd="docker compose build --no-cache $pull_arg $builder_arg"
        else
            build_cmd="docker compose build $builder_arg"
        fi

        # Use verbosity-controlled execution
        execute_with_logging "$build_cmd" "Building all services" "docker_build_all"
        return $?
    else
        # Build specific service with verbosity-controlled logging
        local build_cmd

        # Handle special case for utils service which requires profiles
        if [ "$service" = "utils" ]; then
            if [ "$no_cache" = "true" ]; then
                build_cmd="docker compose --profile installation build --no-cache $pull_arg $builder_arg $service"
            else
                build_cmd="docker compose --profile installation build $builder_arg $service"
            fi
        else
            if [ "$no_cache" = "true" ]; then
                build_cmd="docker compose build --no-cache $pull_arg $builder_arg $service"
            else
                build_cmd="docker compose build $builder_arg $service"
            fi
        fi

        # Use verbosity-controlled execution
        execute_with_logging "$build_cmd" "Building $service service" "docker_build_${service}"
        return $?
    fi
}


# Ensure development container is running
ensure_dev_container() {
    # Check if configuration is loaded, if not try to load it
    if [ ! -f "${INSTALL_DIR}/.env" ]; then
        log_message "Loading default configuration via utils container..."
        
        # Load config utils for centralized config generation
        if source "${SCRIPT_DIR}/config_utils.sh" 2>/dev/null; then
            # Generate files using utils container (no local generation)
            if ! generate_config_via_utils "runtime" "config.yml"; then
                log_message "WARNING: Failed to load configuration via utils container, continuing anyway" "WARNING"
            fi
        else
            log_message "WARNING: Config utils module not available, skipping configuration" "WARNING"
        fi
    fi

    if ! docker compose ps dev 2>/dev/null | grep -q "Up"; then
        log_message "Starting development container..."
        # Start dev container without dependencies
        docker compose up -d --no-deps dev
    fi
}

# Run command in development container
run_in_dev_container() {
    local cmd="$*"
    docker compose exec -T dev bash -c "$cmd"
}


# Helper function: Get Docker platform
get_docker_platform() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64)
            echo "linux/amd64"
            ;;
        arm64|aarch64)
            echo "linux/arm64"
            ;;
        *)
            log_message "WARNING: Unknown architecture $arch, defaulting to linux/amd64"
            echo "linux/amd64"
            ;;
    esac
}

# Helper function: Check Docker prerequisites
check_docker_prerequisites() {
    log_message "Checking Docker prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        log_message "ERROR: Docker is not installed" "ERROR"
        return 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log_message "ERROR: Docker daemon is not running" "ERROR"
        return 1
    fi
    
    # Check if Docker Compose is available
    if ! docker compose version >/dev/null 2>&1; then
        log_message "ERROR: Docker Compose is not available" "ERROR"
        return 1
    fi
    
    # Check if buildx is available
    if ! docker buildx version >/dev/null 2>&1; then
        log_message "WARNING: Docker buildx is not available"
    fi
    
    log_message "Docker prerequisites check passed" "SUCCESS"
    return 0
}

# Helper function: Clean up Docker resources
cleanup_docker_resources() {
    local project_name="${COMPOSE_PROJECT_NAME:-sting-ce}"
    
    log_message "Cleaning up Docker resources for project: $project_name"
    
    # Stop and remove containers
    docker compose -p "$project_name" down --remove-orphans 2>/dev/null || true
    
    # Remove unused images
    docker image prune -f --filter "label=project=$project_name" 2>/dev/null || true
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f --filter "label=project=$project_name" 2>/dev/null || true
    
    # Remove unused networks
    docker network prune -f 2>/dev/null || true
    
    log_message "Docker cleanup completed"
}

# Helper function: Get container logs
get_container_logs() {
    local service="$1"
    local lines="${2:-50}"
    
    if [ -z "$service" ]; then
        log_message "ERROR: No service specified for logs" "ERROR"
        return 1
    fi
    
    log_message "Getting logs for service: $service (last $lines lines)"
    docker compose logs --tail="$lines" "$service"
}

# Check or create Docker network
check_or_create_docker_network() {
    local network_name="${DOCKER_NETWORK:-sting_local}"

    if ! docker network inspect "$network_name" &> /dev/null; then
        log_message "Creating Docker network: $network_name"
        if ! docker network create --driver bridge "$network_name"; then
            log_message "Error: Failed to create Docker network"
            return 1
        fi
    fi

    return 0
}

# Check if development container is running
check_dev_container() {
    if ! docker compose ps dev 2>/dev/null | grep -q "Up"; then
        log_message "Development container not running"
        return 1
    fi
    return 0
}

# Helper function: Check container health
check_container_health() {
    local service="$1"
    
    if [ -z "$service" ]; then
        log_message "ERROR: No service specified for health check" "ERROR"
        return 1
    fi
    
    local health_status
    health_status=$(docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep "^$service" | awk '{print $2}')
    
    case "$health_status" in
        *"healthy"*)
            log_message "Service $service is healthy" "SUCCESS"
            return 0
            ;;
        *"unhealthy"*)
            log_message "Service $service is unhealthy" "ERROR"
            return 1
            ;;
        *"Up"*)
            log_message "Service $service is running (health status unknown)"
            return 0
            ;;
        *)
            log_message "Service $service is not running or has unknown status: $health_status" "ERROR"
            return 1
            ;;
    esac
}

# Function to build and start all services
function build_and_start_services() {
    echo "Building and starting services (cache level: ${cache_level:-moderate})..."
    local hostname
    hostname=$(get_hostname | tr -d '[:space:]') # Trim whitespace
    echo "Using HOSTNAME for docker-compose: $hostname"
    update_dotenv "HOSTNAME" "$hostname"
    update_dotenv "COMPOSE_PROJECT_NAME" "sting"

    # Determine if we should use bake or build
    if [ -f "${INSTALL_DIR}/docker-bake.hjson" ]; then
        # Use docker-bake if available
        log_message "Using docker-bake.hjson for build configuration"
        docker compose --profile "${COMPOSE_PROFILE:-default}" --env-file "${INSTALL_DIR}/.env" buildx bake --push --progress=plain
    else
        # Fallback to standard docker-compose build
        log_message "WARNING: docker-bake.hjson not found, falling back to docker-compose build" "WARNING"
        docker compose --profile "${COMPOSE_PROFILE:-default}" --env-file "${INSTALL_DIR}/.env" build
    fi

    # Start services
    docker compose --profile "${COMPOSE_PROFILE:-default}" --env-file "${INSTALL_DIR}/.env" up -d --remove-orphans

    # Wait for services to be healthy
    if [ "$WAIT_FOR_HEALTH" = "true" ]; then
        for service in $(docker compose ps --services); do
            wait_for_service_health "$service"
        done
    fi

    # Show logs
    if [ "$SHOW_LOGS" = "true" ]; then
        for service in $(docker compose ps --services); do
            get_container_logs "$service" 100
        done
    fi
}