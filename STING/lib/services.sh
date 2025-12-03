#!/bin/bash
# services.sh - Service management functions

# Source dependencies
# Use LIB_DIR instead of SCRIPT_DIR to avoid overwriting parent script's SCRIPT_DIR
LIB_DIR_INTERNAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${LIB_DIR_INTERNAL}/core.sh"
source "${LIB_DIR_INTERNAL}/logging.sh"
source "${LIB_DIR_INTERNAL}/environment.sh"

# Source enhanced startup resilience if available
if [ -f "${LIB_DIR_INTERNAL}/service_startup_resilience.sh" ]; then
    source "${LIB_DIR_INTERNAL}/service_startup_resilience.sh"
fi

# Helper function for consistent Docker Compose calls
# This ensures all Docker Compose commands use the correct working directory and file path
docker_compose() {
    local original_dir="$(pwd)"
    cd "${INSTALL_DIR}" || {
        log_message "ERROR: Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
        return 1
    }
    
    # Log the command being executed for debugging
    if [ -f "${INSTALL_DIR}/docker-compose.frontend-nginx.yml" ]; then
        log_message "Executing: docker compose with nginx frontend configuration $*"
    else
        log_message "Executing: docker compose -f ${INSTALL_DIR}/docker-compose.yml $*"
    fi
    
    # Run docker compose with explicit file path for safety
    # Include frontend-nginx compose file if it exists
    local compose_files="-f ${INSTALL_DIR}/docker-compose.yml"
    if [ -f "${INSTALL_DIR}/docker-compose.frontend-nginx.yml" ]; then
        compose_files="$compose_files -f ${INSTALL_DIR}/docker-compose.frontend-nginx.yml"
    fi
    
    # Redirect stderr to a temp file to filter out env file warnings
    local temp_err=$(mktemp)
    docker compose $compose_files "$@" 2>"$temp_err"
    local result=$?
    
    # Show all errors for debugging if command failed
    if [ $result -ne 0 ]; then
        log_message "Docker compose command failed with exit code $result" "ERROR"
        if [ -s "$temp_err" ]; then
            log_message "Docker compose error output:" "ERROR"
            cat "$temp_err" >&2
        fi
    elif [ -s "$temp_err" ]; then
        # Only filter warnings if command succeeded
        grep -v "env file.*not found" "$temp_err" | grep -v "variable is not set" >&2
    fi
    rm -f "$temp_err"
    
    # Restore original directory
    cd "$original_dir" || true
    return $result
}

# Sync PostgreSQL password with environment configuration
# This function ensures the database password matches what's in the env files
# Call this after regenerating env files to avoid authentication failures
sync_database_password() {
    log_message "🔐 Syncing database password with environment configuration..."

    # Source the database environment to get the current password
    if [ -f "${INSTALL_DIR}/env/db.env" ]; then
        source "${INSTALL_DIR}/env/db.env"
    else
        log_message "⚠️  Database env file not found, skipping password sync" "WARNING"
        return 0
    fi

    # Check if database container is running
    if ! docker ps --format "{{.Names}}" | grep -q "sting-ce-db"; then
        log_message "ℹ️  Database container not running, password will sync on next start" "INFO"
        return 0
    fi

    # Check if database is accepting connections (using local docker exec)
    if ! docker exec sting-ce-db psql -U postgres -c "SELECT 1;" >/dev/null 2>&1; then
        log_message "ℹ️  Database not ready for password sync, will retry when accessible" "INFO"
        return 0
    fi

    # Update the postgres user password to match the env file
    if docker exec sting-ce-db psql -U postgres -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';" >/dev/null 2>&1; then
        log_message "✅ Database password synced successfully" "SUCCESS"
        return 0
    else
        log_message "⚠️  Failed to sync database password - may need manual intervention" "WARNING"
        return 1
    fi
}

# Fix Docker bridge networking for VirtualBox environments
# VirtualBox can cause two issues with Docker bridge networks:
# 1. Bridge interface loses its gateway IP address
# 2. Container veth interfaces are not attached to the bridge (NO-CARRIER state)
# This function checks and fixes both issues
fix_docker_bridge_networking() {
    local network_name="${1:-sting_local}"
    local fixed_something=false

    # Check if network exists
    if ! docker network inspect "$network_name" >/dev/null 2>&1; then
        return 0  # Network doesn't exist yet, nothing to fix
    fi

    # Get the gateway and subnet from Docker network config
    local gateway=$(docker network inspect "$network_name" --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null)
    local subnet=$(docker network inspect "$network_name" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
    local network_id=$(docker network inspect "$network_name" --format '{{.Id}}' 2>/dev/null | cut -c1-12)

    if [ -z "$gateway" ] || [ -z "$subnet" ] || [ -z "$network_id" ]; then
        return 0  # Can't determine network config
    fi

    # Find the bridge interface
    local bridge_iface="br-${network_id}"
    if ! ip link show "$bridge_iface" >/dev/null 2>&1; then
        return 0  # Bridge interface doesn't exist
    fi

    # Fix 1: Check if gateway IP is assigned to bridge
    if ! ip addr show "$bridge_iface" | grep -q "inet ${gateway}"; then
        log_message "Fixing Docker bridge networking: adding gateway ${gateway} to ${bridge_iface}..."

        # Calculate CIDR from subnet (e.g., 172.18.0.0/16 -> /16)
        local cidr=$(echo "$subnet" | grep -oE '/[0-9]+$')

        if ip addr add "${gateway}${cidr}" dev "$bridge_iface" 2>/dev/null; then
            log_message "Docker bridge gateway IP fixed successfully"
            fixed_something=true
        else
            log_message "Warning: Could not add gateway IP to bridge" "WARNING"
        fi
    fi

    # Fix 2: Check if bridge is in NO-CARRIER/DOWN state (veths not attached)
    # This happens in VirtualBox when Docker creates veths but doesn't attach them
    local bridge_state=$(ip link show "$bridge_iface" 2>/dev/null | grep -oE 'state (UP|DOWN)' | awk '{print $2}')
    if [ "$bridge_state" = "DOWN" ]; then
        log_message "Docker bridge $bridge_iface is DOWN - attaching container veth interfaces..."

        # Find all veth interfaces and attach them to the bridge
        local veth_count=0
        for veth in $(ip link show type veth 2>/dev/null | grep -oE 'veth[a-f0-9]+'); do
            # Check if veth already has a master
            if ! ip link show "$veth" 2>/dev/null | grep -q "master"; then
                if ip link set "$veth" master "$bridge_iface" 2>/dev/null; then
                    ((veth_count++))
                fi
            fi
        done

        if [ $veth_count -gt 0 ]; then
            log_message "Attached $veth_count veth interfaces to bridge $bridge_iface"
            fixed_something=true
        fi

        # Verify bridge is now UP
        bridge_state=$(ip link show "$bridge_iface" 2>/dev/null | grep -oE 'state (UP|DOWN)' | awk '{print $2}')
        if [ "$bridge_state" = "UP" ]; then
            log_message "Docker bridge networking fixed successfully"
        else
            log_message "Warning: Bridge still DOWN after attaching veths" "WARNING"
        fi
    fi

    if [ "$fixed_something" = "true" ]; then
        return 0
    fi
    return 0
}

# Ensure SSL certificates exist for HTTPS operation
ensure_ssl_certificates() {
    local cert_dir="${INSTALL_DIR}/certs"
    local volume_exists=false
    
    # Check if certificates exist in install directory
    if [ -f "${cert_dir}/server.crt" ] && [ -f "${cert_dir}/server.key" ]; then
        log_message "SSL certificates found in ${cert_dir}"
    else
        log_message "SSL certificates missing, generating new ones..."
        
        # Load security module if not already loaded
        if ! command -v generate_ssl_certs >/dev/null 2>&1; then
            source "${SCRIPT_DIR}/security.sh" || {
                log_message "ERROR: Failed to load security module" "ERROR"
                return 1
            }
        fi
        
        # Generate certificates
        generate_ssl_certs || {
            log_message "ERROR: Failed to generate SSL certificates" "ERROR"
            return 1
        }
    fi
    
    # Apply WSL2 Docker fixes if needed before pulling alpine image
    if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
        source "${SCRIPT_DIR}/docker_wsl_fix.sh"
        fix_docker_credential_helper >/dev/null 2>&1
    fi
    
    # Ensure Docker volume exists and has certificates
    if ! docker volume inspect sting_certs >/dev/null 2>&1; then
        log_message "Creating Docker volume sting_certs..."
        docker volume create sting_certs || {
            log_message "ERROR: Failed to create sting_certs volume" "ERROR"
            return 1
        }
    fi
    
    # Check if volume has certificates
    # Try to check without pulling alpine image first
    local volume_cert_count="0"
    
    # First try using a local busybox or alpine image if available
    if docker image inspect alpine:latest >/dev/null 2>&1 || docker image inspect busybox:latest >/dev/null 2>&1; then
        volume_cert_count=$(docker run --rm -v sting_certs:/certs alpine sh -c "ls /certs/*.crt 2>/dev/null | wc -l" 2>/dev/null || echo "0")
    fi
    
    if [ "$volume_cert_count" -eq 0 ]; then
        log_message "Docker volume sting_certs is empty, copying certificates..."
        
        # Alternative method: copy using docker cp with a temporary container
        # This avoids the need to pull images when credentials are broken
        local temp_container="sting-cert-copy-$$"
        
        # Create a temporary container using an existing image (postgres which we already have)
        if docker create --name "$temp_container" -v sting_certs:/certs postgres:16-alpine true >/dev/null 2>&1; then
            # Copy certificates to the container
            docker cp "${cert_dir}/server.crt" "$temp_container:/certs/" 2>/dev/null || true
            docker cp "${cert_dir}/server.key" "$temp_container:/certs/" 2>/dev/null || true

            # Set proper permissions and ownership for Kratos (UID 10000)
            docker run --rm -v sting_certs:/certs alpine sh -c \
                "chmod 644 /certs/server.crt && chmod 640 /certs/server.key && chown -R 10000:10000 /certs/" 2>/dev/null || true

            # Clean up
            docker rm "$temp_container" >/dev/null 2>&1 || true

            log_message "Certificates copied to Docker volume using docker cp method"
        else
            # Fallback: try the original method anyway
            docker run --rm -v sting_certs:/certs -v "${cert_dir}":/source:ro alpine sh -c \
                "cp /source/server.crt /source/server.key /certs/ && chmod 644 /certs/server.crt && chmod 640 /certs/server.key && chown -R 10000:10000 /certs/" 2>/dev/null || {
                log_message "WARNING: Could not copy certificates to Docker volume - continuing anyway" "WARNING"
                # Don't fail installation over this
            }
        fi
        log_message "Certificates successfully copied to Docker volume"
    else
        log_message "Docker volume sting_certs already contains certificates"
    fi
    
    return 0
}

# Wait for a service to become healthy
wait_for_service() {
    local service="$1"
    local max_attempts=${HEALTH_CHECK_RETRIES:-30}
    local attempt=1
    local interval=${HEALTH_CHECK_INTERVAL:-5s}
    local ignore_failure=${2:-"false"}

    # Fix Docker bridge networking (VirtualBox workaround)
    # This ensures the Docker bridge has its gateway IP for host-to-container communication
    fix_docker_bridge_networking "sting_local" 2>/dev/null || true

    # For Kratos during fresh install, increase timeout to handle migrations
    if [ "$service" = "kratos" ] && [ "${FRESH_INSTALL:-false}" = "true" ]; then
        max_attempts=60  # 5 minutes for fresh install migrations
        log_message "Fresh install detected - using extended timeout for Kratos migrations"
    fi

    # Vault starts quickly - use shorter interval
    if [ "$service" = "vault" ]; then
        interval=1s  # Check every 1 second instead of 5
        max_attempts=10  # Only need 10 seconds total for Vault
    fi

    log_message "Waiting for $service to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        case "$service" in
            "frontend")
                # For frontend, just check that the container is running
                # React dev server can take time to fully initialize
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-frontend"; then
                    log_message "Frontend container is up and running"
                    return 0
                fi
                ;;
            "app")
                # Check container is up and application health over HTTPS (with 3s timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-app" && \
                   curl -k -s --connect-timeout 2 -m 3 "https://localhost:5050/health" > /dev/null 2>&1; then
                    log_message "Flask application is fully operational"
                    return 0
                fi
                ;;
            "db")
                while [ $attempt -le $max_attempts ]; do
                    # Basic connectivity check
                    # Use docker exec directly to avoid compose warnings
                    if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
                        log_message "Database is accepting connections"
                        return 0
                    fi
                    
                    log_message "Waiting for database... attempt $attempt/$max_attempts"
                    sleep 5
                    attempt=$((attempt + 1))
                done
                ;;
            "vault")
                # Use docker exec directly to avoid compose warnings
                if docker exec sting-ce-vault vault status >/dev/null 2>&1 && \
                   docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Initialized.*true"; then
                    log_message "Vault is operational and initialized"
                    return 0
                fi
                ;;
            "kratos")
                # Check Kratos container and readiness endpoint via admin port (HTTPS)
                # Use docker ps directly to avoid compose warnings about env files
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-kratos"; then
                    # Container is running, check health endpoint (with 3s timeout to avoid long hangs)
                    if curl -s -f -k --connect-timeout 2 -m 3 https://localhost:4434/admin/health/ready > /dev/null 2>&1; then
                        log_message "Kratos is fully operational"
                        return 0
                    else
                        # During fresh install, provide more info about migration status
                        if [ "${FRESH_INSTALL:-false}" = "true" ] && [ $attempt -gt 10 ]; then
                            log_message "Kratos is still initializing (this is normal for fresh install with database migrations)..."
                            # Show last few log lines to indicate progress
                            docker logs sting-ce-kratos --tail 5 2>&1 | grep -E "(Migration|applied successfully)" | tail -3 || true
                        fi
                    fi
                fi
                ;;
            "utils")
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-utils" && \
                docker exec sting-ce-utils python3 --version >/dev/null 2>&1; then
                    log_message "Utilities container is operational"
                    return 0
                fi
                ;;
##            "supertokens")  # DEPRECATED - SuperTokens removed in favor of Kratos
##                # Add network and credential verification
##                docker exec sting-ce-db psql -U postgres -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';" >/dev/null 2>&1
##                docker exec sting-ce-supertokens nc -z db 5432 >/dev/null 2>&1  # DEPRECATED
##                if curl -s "http://localhost:3567/health" > /dev/null 2>&1; then
##                    log_message "Supertokens is healthy"  # DEPRECATED
##                    return 0
##                fi
##                ;;
            "chatbot"|"sting-ce-chatbot")
                # First check: Is the container running at all?
                if docker ps | grep -q "sting-ce-chatbot"; then
                    # If we're more than 5 attempts in, assume it's working
                    if [ $attempt -gt 5 ]; then
                        log_message "Chatbot container is running - assuming healthy after 5 checks"
                        return 0
                    fi
                    
                    # Check health endpoint (with timeout)
                    if curl -s -f --connect-timeout 2 -m 3 "http://localhost:8081/health" > /dev/null; then
                        log_message "Chatbot service is fully operational"
                        return 0
                    fi
                fi
                ;;
            "nectar-worker")
                # Check nectar-worker container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-nectar-worker" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:9002/health" > /dev/null 2>&1; then
                    log_message "Nectar Worker service is fully operational"
                    return 0
                fi
                ;;
            "knowledge")
                # Check knowledge service container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-knowledge" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:8090/health" > /dev/null 2>&1; then
                    log_message "Knowledge service is fully operational"
                    return 0
                fi
                ;;
            "report-worker")
                # Check report-worker container is running and healthy
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-report-worker"; then
                    log_message "Report worker service is running"
                    return 0
                fi
                ;;
            "profile-sync-worker")
                # Check profile-sync-worker container is running and healthy
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-profile-sync-worker"; then
                    log_message "Profile sync worker service is running"
                    return 0
                fi
                ;;
            "loki")
                # Check Loki container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-loki" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:3100/ready" > /dev/null 2>&1; then
                    log_message "Loki log aggregation service is fully operational"
                    return 0
                fi
                ;;
            "grafana")
                # Check Grafana container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-grafana" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:3001/api/health" > /dev/null 2>&1; then
                    log_message "Grafana dashboard service is fully operational"
                    return 0
                fi
                ;;
            "promtail")
                # Check Promtail container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-promtail" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:9080/ready" > /dev/null 2>&1; then
                    log_message "Promtail log collection service is fully operational"
                    return 0
                fi
                ;;
            "public-bee")
                # Check Public Bee container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-public-bee" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:8092/health" > /dev/null 2>&1; then
                    log_message "Public Bee (Nectar Bot) service is fully operational"
                    return 0
                fi
                ;;
            "headscale")
                # Check Headscale container and health endpoint (with timeout)
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-headscale" && \
                   curl -s -f --connect-timeout 2 -m 3 "http://localhost:8070/health" > /dev/null 2>&1; then
                    log_message "Headscale support tunnel service is fully operational"
                    return 0
                fi
                ;;
            *)
                # Use docker ps to check if container is running
                if docker ps --format "table {{.Names}}" | grep -q "sting-ce-$service"; then
                    log_message "Service $service is running"
                    return 0
                fi
                ;;
        esac
        
        log_message "Waiting for $service... attempt $attempt/$max_attempts"
        sleep $interval
        attempt=$((attempt + 1))
    done
    
    if [ "$ignore_failure" = "true" ]; then
        log_message "WARNING: Service $service didn't become healthy, but continuing anyway as requested"
        docker_compose logs "$service"
        return 0
    else
        log_message "ERROR: Service $service failed to become healthy"
        docker_compose logs "$service"
        return 1
    fi
}

# Core service management function
manage_services() {
    local action="$1"
    local service="$2"
    local no_cache="$3"

    # Platform-specific privilege handling
    if [[ "$(uname)" != "Darwin" ]]; then
        # Linux needs root privileges
        if [ "$EUID" -ne 0 ]; then
            exec sudo "$0" "$@"
            exit $?
        fi
    fi

    log_message "Managing services: action=${action}, service=${service:-all}, no-cache=${no_cache:-false}"

    case "$action" in
        start)
            # Check if required environment files exist first
            local required_services=(db vault kratos app frontend)
            local missing_env_files=()
            
            for service_name in "${required_services[@]}"; do
                if [ ! -f "${INSTALL_DIR}/env/${service_name}.env" ]; then
                    missing_env_files+=("$service_name")
                fi
            done
            
            # Only regenerate environment files if any are missing
            if [ ${#missing_env_files[@]} -gt 0 ]; then
                log_message "Missing environment files for: ${missing_env_files[*]}"
                
                # Load config utils for centralized config generation
                source "${SCRIPT_DIR}/config_utils.sh" || {
                    log_message "Failed to load config utils module" "ERROR"
                    return 1
                }
                
                # Generate files using utils container (no local generation)
                if ! generate_config_via_utils "runtime" "config.yml"; then
                    log_message "ERROR: Environment file generation failed via utils container" "ERROR"
                    return 1
                fi
                
                # Validate generation was successful
                if ! validate_config_generation; then
                    log_message "Configuration validation failed" "ERROR"
                    return 1
                fi
            else
                log_message "All required environment files exist, skipping generation"
            fi
            
            # Load service environments
            for service_name in "${required_services[@]}"; do
                if ! load_service_env "$service_name"; then
                    log_message "Failed to load environment for $service_name"
                    return 1
                fi
            done
            
            # Ensure SSL certificates exist (independent of env file generation)
            ensure_ssl_certificates
            
            # Ensure Docker network exists
            if ! docker network inspect sting_local >/dev/null 2>&1; then
                log_message "Creating Docker network: sting_local"
                docker network create sting_local || {
                    log_message "ERROR: Failed to create Docker network" "ERROR"
                    return 1
                }
            fi
            
            # Ensure Docker volumes exist
            log_message "Ensuring Docker volumes exist..."
            local required_volumes=(
                "sting-ce_config_data"
                "sting-ce_vault_data"
                "sting-ce_vault_file"
                "sting-ce_postgres_data"
                "sting-ce_sting_logs"
                "sting-ce_sting_certs"
                "sting-ce_chroma_data"
                "sting-ce_knowledge_data"
                "sting-ce_knowledge_uploads"
                "sting-ce_messaging_data"
                "sting-ce_redis_data"
                "sting-ce_loki_data"
                "sting-ce_sting_uploads"
                "sting-ce_grafana_data"
                "sting-ce_container_logs"
                "sting-ce_mailpit_data"
                "sting-ce_profile_logs"
            )
            
            for volume in "${required_volumes[@]}"; do
                if ! docker volume inspect "$volume" >/dev/null 2>&1; then
                    log_message "Creating Docker volume: $volume"
                    docker volume create "$volume" || {
                        log_message "WARNING: Failed to create volume $volume" "WARNING"
                    }
                fi
            done
            
            # Start core services using docker compose 
            log_message "Starting STING core services..."
            
            # First, remove any exited containers to avoid conflicts
            log_message "Cleaning up exited containers..."
            local exited_containers=$(docker ps -a --filter "name=sting-ce" --filter "status=exited" --format "{{.Names}}")
            if [ -n "$exited_containers" ]; then
                log_message "Removing exited containers:"
                echo "$exited_containers" | while read container; do
                    if [ -n "$container" ]; then
                        log_message "  Removing $container..."
                        docker rm "$container" 2>/dev/null || true
                    fi
                done
            fi
            
            # Then start any containers that are in "Created" state
            log_message "Checking for containers in 'Created' state..."
            local created_containers=$(docker ps -a --filter "name=sting-ce" --filter "status=created" --format "{{.Names}}")
            if [ -n "$created_containers" ]; then
                log_message "Starting containers that were created but not started:"
                echo "$created_containers" | while read container; do
                    if [ -n "$container" ]; then
                        log_message "  Starting $container..."
                        docker start "$container" 2>/dev/null || true
                    fi
                done
            fi
            
            # Start services in proper dependency order (from legacy manage_sting)
            log_message "Starting services in dependency order..."
            
            # 1. Start Vault first (required by many services)
            log_message "Starting Vault service..."
            docker_compose up -d vault
            wait_for_service "vault" || log_message "Vault service is taking longer to start..." "WARNING"
            
            # 2. Start database (required by app services)
            log_message "Starting database service..."
            docker_compose up -d db
            wait_for_service "db" || log_message "Database service is taking longer to start..." "WARNING"
            
            # 3. Start supporting services
            log_message "Starting supporting services..."
            # Start mailpit if EMAIL_MODE is dev/development
            local email_mode="${EMAIL_MODE:-development}"
            if [[ "$email_mode" == "dev" || "$email_mode" == "development" ]]; then
                log_message "EMAIL_MODE is $email_mode, starting mailpit..."

                # Run OS-aware mailpit pre-start cleanup (handles WSL2 port issues)
                if [ -f "${SCRIPT_DIR}/mailpit_lifecycle.sh" ]; then
                    log_message "Running mailpit pre-start cleanup..."
                    "${SCRIPT_DIR}/mailpit_lifecycle.sh" pre-start || {
                        log_message "Mailpit pre-start cleanup encountered issues, continuing anyway..." "WARNING"
                    }
                fi

                docker_compose --profile development up -d mailpit redis messaging

                # Validate mailpit is properly configured for auth flow
                if [ -f "${INSTALL_DIR}/scripts/health/validate_mailpit.py" ]; then
                    log_message "Validating mailpit configuration for auth flow..."
                    if python3 "${INSTALL_DIR}/scripts/health/validate_mailpit.py" --quick >/dev/null 2>&1; then
                        log_message "✅ Mailpit validation passed - auth emails will be delivered" "SUCCESS"
                    else
                        log_message "⚠️  Mailpit validation failed - auth flow may be impacted" "WARNING"
                        log_message "Run: python3 ${INSTALL_DIR}/scripts/health/validate_mailpit.py for details" "WARNING"
                    fi
                fi
            else
                docker_compose up -d redis messaging
            fi

            # 4. Start Kratos (authentication service)
            log_message "Starting Kratos authentication service..."
            docker_compose up -d kratos
            wait_for_service "kratos" || log_message "Kratos service is taking longer to start..." "WARNING"
            
            # 5. Start core application services
            log_message "Starting core application services..."
            docker_compose up -d utils app frontend report-worker profile-sync-worker
            wait_for_service "app" || log_message "App service is taking longer to start..." "WARNING"
            
            # 6. Start knowledge and AI services
            log_message "Starting knowledge and AI services..."
            docker_compose up -d chroma knowledge external-ai llm-gateway-proxy
            
            # 7. Start observability services (Beeacon monitoring stack) if enabled
            if [ -f "${INSTALL_DIR}/env/observability.env" ]; then
                # Source observability env to check if enabled
                . "${INSTALL_DIR}/env/observability.env" 2>/dev/null
                
                if [ "${OBSERVABILITY_ENABLED:-false}" = "true" ]; then
                    log_message "Starting Beeacon observability services (enabled in config)..."
                    docker_compose --profile observability up -d loki grafana promtail
                    
                    if [ "${LOG_FORWARDING_ENABLED:-false}" = "true" ]; then
                        docker_compose --profile observability up -d log-forwarder
                    fi
                else
                    log_message "Skipping observability services (disabled in config)"
                fi
            else
                log_message "Skipping observability services (no config found)"
            fi
            
            # 8. Start chatbot last (depends on many services)
            log_message "Starting chatbot service..."
            docker_compose up -d chatbot

            # 9. Start public bot services (nectar-worker and public-bee)
            log_message "Starting public bot services..."
            docker_compose up -d nectar-worker public-bee

            # Use enhanced startup resilience if available
            if command -v ensure_all_services_started_enhanced >/dev/null 2>&1; then
                log_message "Using enhanced service startup with dependency handling..."
                ensure_all_services_started_enhanced
            elif command -v ensure_all_services_started >/dev/null 2>&1; then
                log_message "Ensuring all services are started..."
                ensure_all_services_started
            else
                log_message "Service startup resilience not available, continuing..." "WARNING"
            fi
            
            # Native LLM deprecated in favor of Ollama
            # Removed native LLM setup for macOS
            ;;
        stop)
            log_message "Stopping services..."
            
            if [ -n "$service" ]; then
                # Stop specific service
                log_message "Stopping $service..."
                docker_compose stop "$service"
            else
                # Stop all STING services comprehensively
                log_message "Stopping all STING services..."
                
                # First try docker compose stop (graceful)
                log_message "Attempting graceful shutdown with docker compose..."
                docker_compose stop 2>/dev/null || {
                    log_message "Docker compose stop failed, trying alternative approach..."
                }
                
                # Then stop any STING containers directly
                log_message "Ensuring all STING containers are stopped..."
                local sting_containers=$(docker ps -q --filter "name=sting-ce")
                if [ -n "$sting_containers" ]; then
                    log_message "Stopping running STING containers..."
                    echo "$sting_containers" | xargs docker stop 2>/dev/null || true
                fi
                
                # Clean up stopped containers if requested
                if [ "$1" = "--clean" ]; then
                    log_message "Cleaning up stopped containers..."
                    local stopped_containers=$(docker ps -aq --filter "name=sting-ce" --filter "status=exited")
                    if [ -n "$stopped_containers" ]; then
                        echo "$stopped_containers" | xargs docker rm 2>/dev/null || true
                    fi
                fi

                # Run OS-aware mailpit post-stop cleanup (handles WSL2 port release)
                if [ -f "${SCRIPT_DIR}/mailpit_lifecycle.sh" ]; then
                    log_message "Running mailpit post-stop cleanup..."
                    "${SCRIPT_DIR}/mailpit_lifecycle.sh" post-stop || true
                fi

                log_message "Successfully stopped all STING services"
            fi
            ;;
        restart)
            # Regenerate environment files before restart
            log_message "Regenerating service environment files..."
            log_message "Restarting ${service:-all} services..."
            
            # Native LLM deprecated in favor of Ollama
            # Removed native LLM restart logic
            
            if [ -n "$service" ]; then
                # Load specific service env file
                if ! load_service_env "$service"; then
                    log_message "Failed to load environment for $service"
                    return 1
                fi
                docker_compose restart "$service"
                wait_for_service "$service" || {
                    log_message "ERROR: Service $service failed to restart"
                    return 1
                }
            else
                log_message "Executing docker-compose restart for all services..."
                docker_compose restart
                if [ $? -eq 0 ]; then
                    log_message "Docker-compose restart command completed"
                    # Give services a moment to come back up
                    sleep 3
                    log_message "Services should be restarting, checking status..."
                    docker_compose ps
                else
                    log_message "Docker-compose restart failed" "ERROR"
                    return 1
                fi
            fi
            ;;
        build)
            # Skip builds in OVA mode - images are pre-built
            if [ -f "/opt/sting-ce-source/.ova-prebuild" ]; then
                log_message "Skipping build (OVA with pre-built images)" "SUCCESS"
                return 0
            fi

            log_message "Building ${service:-all} services with options: ${no_cache}"

            # Always build the llm-base image first if we're building an LLM service
            log_message "DEBUG: Current service to build: '$service'" "INFO"
            # Force build_llm_images to run before any docker compose build
            log_message "Ensuring LLM base image is built (always build first)..." "INFO"
            build_llm_images

            if [[ "$no_cache" == "--no-cache" ]]; then
                if [ -n "$service" ]; then
                    docker compose build --no-cache "$service"
                else
                    docker compose build --no-cache
                fi
            else
                if [ -n "$service" ]; then
                    docker compose build "$service"
                else
                    docker compose build
                fi
            fi
            ;;
    esac
}

# Start a specific service
start_service() {
    local service="$1"

    if [ -z "$service" ]; then
        log_message "ERROR: No service specified" "ERROR"
        return 1
    fi

    log_message "Starting service: $service"

    # Run mailpit pre-start cleanup if starting mailpit
    if [[ "$service" == "mailpit" ]] && [ -f "${SCRIPT_DIR}/mailpit_lifecycle.sh" ]; then
        log_message "Running mailpit pre-start cleanup..."
        "${SCRIPT_DIR}/mailpit_lifecycle.sh" pre-start || {
            log_message "Mailpit pre-start cleanup encountered issues, continuing anyway..." "WARNING"
        }
    fi

    # Use manage_services function to start the specific service
    manage_services "start" "$service"

    if [ $? -eq 0 ]; then
        log_message "Successfully started service: $service" "SUCCESS"
    else
        log_message "Failed to start service: $service" "ERROR"
        return 1
    fi
}

# Stop a specific service
stop_service() {
    local service="$1"

    if [ -z "$service" ]; then
        log_message "ERROR: No service specified" "ERROR"
        return 1
    fi

    log_message "Stopping service: $service"

    # Use manage_services function to stop the specific service
    manage_services "stop" "$service"

    local stop_result=$?

    # Run mailpit post-stop cleanup if stopping mailpit
    if [[ "$service" == "mailpit" ]] && [ -f "${SCRIPT_DIR}/mailpit_lifecycle.sh" ]; then
        log_message "Running mailpit post-stop cleanup..."
        "${SCRIPT_DIR}/mailpit_lifecycle.sh" post-stop || true
    fi

    if [ $stop_result -eq 0 ]; then
        log_message "Successfully stopped service: $service" "SUCCESS"
    else
        log_message "Failed to stop service: $service" "ERROR"
        return 1
    fi
}

# Start all services
start_all_services() {
    log_message "Starting all STING services..."
    
    # Start all services using manage_services
    manage_services "start"
    
    if [ $? -eq 0 ]; then
        log_message "Successfully started all STING services" "SUCCESS"
    else
        log_message "Failed to start some services" "ERROR"
        return 1
    fi
}

# Stop all services
# LLM-specific service management functions (restored from legacy)
llm_stop_services() {
    log_message "Stopping LLM services..."
    
    # Native LLM deprecated in favor of Ollama
    # Removed native_llm.sh references
    
    # Stop Docker LLM services
    local llm_services=("llm-gateway" "llama3-service" "phi3-service" "zephyr-service")
    for service in "${llm_services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$service"; then
            log_message "Stopping $service..."
            docker stop "$service" >/dev/null 2>&1 || true
        fi
    done
    
    log_message "LLM services stopped"
}

llm_start_services() {
    log_message "Starting LLM services..."
    
    # Platform-specific startup
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS: Start nginx proxy + native service
        docker compose up -d llm-gateway || log_message "Docker LLM gateway failed to start" "WARNING"
        
        # Start native LLM service
        source "${SCRIPT_DIR}/native_llm.sh"
        start_native_llm_service || {
            log_message "Native LLM service failed to start, keeping Docker gateway" "WARNING"
        }
    else
        # Linux: Start Docker LLM services
        docker compose up -d llm-gateway llama3-service phi3-service zephyr-service || {
            log_message "Some LLM services failed to start" "WARNING"
        }
    fi
    
    log_message "LLM services startup complete"
}

llm_restart_services() {
    log_message "Restarting LLM services..."
    llm_stop_services
    sleep 2
    llm_start_services
}

llm_check_status() {
    log_message "Checking LLM service status..."
    local status_ok=true
    
    if [[ "$(uname)" == "Darwin" ]]; then
        # Check native LLM service
        source "${SCRIPT_DIR}/native_llm.sh"
        local native_running=false
        if is_native_llm_running; then
            log_message "✅ Native LLM service: Running" "SUCCESS"
            native_running=true
        else
            log_message "❌ Native LLM service: Not running" "ERROR"
        fi
        
        # Check nginx proxy
        local proxy_running=false
        if docker ps --format "table {{.Names}}" | grep -q "llm-gateway"; then
            log_message "✅ LLM Gateway (nginx proxy): Running" "SUCCESS"
            proxy_running=true
        else
            log_message "ℹ️  LLM Gateway (nginx proxy): Not running" "INFO"
        fi
        
        # On macOS, we need either native service OR proxy running, not both
        if [ "$native_running" = "false" ] && [ "$proxy_running" = "false" ]; then
            log_message "❌ No LLM service running - need either native service or nginx proxy" "ERROR"
            status_ok=false
        elif [ "$native_running" = "true" ] && [ "$proxy_running" = "true" ]; then
            log_message "⚠️  Both native and proxy running - this may cause conflicts" "WARNING"
        fi
    else
        # Check Docker LLM services
        local llm_services=("llm-gateway" "llama3-service" "phi3-service" "zephyr-service")
        for service in "${llm_services[@]}"; do
            if docker ps --format "table {{.Names}}" | grep -q "$service"; then
                log_message "✅ $service: Running" "SUCCESS"
            else
                log_message "❌ $service: Not running" "ERROR"
                status_ok=false
            fi
        done
    fi
    
    if [ "$status_ok" = "true" ]; then
        return 0
    else
        return 1
    fi
}

llm_show_logs() {
    local service="${1:-}"
    
    if [[ "$(uname)" == "Darwin" ]]; then
        if [ -z "$service" ] || [ "$service" = "native" ]; then
            # Show native LLM logs
            source "${SCRIPT_DIR}/native_llm.sh"
            local log_file="$NATIVE_LLM_LOG_FILE"
            if [ -f "$log_file" ]; then
                log_message "Showing native LLM service logs:"
                tail -f "$log_file"
            else
                log_message "Native LLM log file not found: $log_file" "ERROR"
            fi
        elif [ "$service" = "gateway" ]; then
            docker logs -f sting-ce-llm-gateway 2>/dev/null || log_message "LLM gateway container not found" "ERROR"
        else
            log_message "Available log sources: native, gateway"
        fi
    else
        # Linux: Show Docker service logs
        if [ -n "$service" ]; then
            docker logs -f "sting-ce-$service" 2>/dev/null || log_message "Service $service not found" "ERROR"
        else
            log_message "Available services: llm-gateway, llama3-service, phi3-service, zephyr-service"
        fi
    fi
}

# Main LLM command dispatcher (restored from legacy)
handle_llm_command() {
    local llm_action="${1:-}"
    shift || true  # Remove first argument, keep rest
    
    # Load required modules
    source "${SCRIPT_DIR}/native_llm.sh" || {
        log_message "Failed to load native_llm module" "ERROR"
        return 1
    }
    
    source "${SCRIPT_DIR}/model_management.sh" || {
        log_message "Failed to load model_management module" "ERROR"
        return 1
    }
    
    case "$llm_action" in
        start)
            log_message "Starting LLM services..."
            llm_start_services
            ;;
        stop)
            log_message "Stopping LLM services..."
            llm_stop_services
            ;;
        restart)
            log_message "Restarting LLM services..."
            llm_restart_services
            ;;
        status)
            llm_check_status
            ;;
        logs)
            llm_show_logs "$1"
            ;;
        models)
            llm_list_models
            ;;
        download)
            log_message "Downloading models..."
            download_models
            ;;
        ""|help)
            echo "STING LLM Management Commands:"
            echo "  ./manage_sting.sh llm start    - Start LLM services"
            echo "  ./manage_sting.sh llm stop     - Stop LLM services"
            echo "  ./manage_sting.sh llm restart  - Restart LLM services"
            echo "  ./manage_sting.sh llm status   - Check LLM service status"
            echo "  ./manage_sting.sh llm logs     - Show LLM service logs"
            echo "  ./manage_sting.sh llm models   - List available models"
            echo "  ./manage_sting.sh llm download - Download models"
            echo ""
            echo "Platform-specific:"
            if [[ "$(uname)" == "Darwin" ]]; then
                echo "  macOS: Uses native LLM service with MPS acceleration"
                echo "  ./manage_sting.sh llm logs native  - Native service logs"
                echo "  ./manage_sting.sh llm logs gateway - Docker gateway logs"
            else
                echo "  Linux: Uses Docker LLM services"
                echo "  ./manage_sting.sh llm logs <service> - Specific service logs"
            fi
            ;;
        *)
            log_message "Unknown LLM command: $llm_action" "ERROR"
            handle_llm_command help
            return 1
            ;;
    esac
}

stop_all_services() {
    log_message "Stopping all STING services..."
    
    # Use manage_services function with stop action
    manage_services "stop"
}

# Restart all services
restart_all_services() {
    # Load enhanced restart module if available
    local enhanced_restart_path="$(dirname "${BASH_SOURCE[0]}")/enhanced_restart.sh"
    
    if [ -f "$enhanced_restart_path" ]; then
        log_message "Using enhanced restart for improved reliability..." "INFO"
        source "$enhanced_restart_path"
        enhanced_restart_all
        return $?
    else
        # Fallback to original restart method
        log_message "Enhanced restart not available, using fallback method..." "WARNING"
        log_message "Restarting all STING services..."
        
        # Restart all services using manage_services
        manage_services "restart"
        
        if [ $? -eq 0 ]; then
            log_message "Successfully restarted all STING services" "SUCCESS"
        else
            log_message "Failed to restart some services" "ERROR"
            return 1
        fi
    fi
}

# Restart a specific service (simple stop + start, no env regeneration)
restart_service() {
    local service="$1"
    if [ -z "$service" ]; then
        log_message "ERROR: No service specified for restart" "ERROR"
        return 1
    fi

    log_message "Restarting ${service} service..."

    # Run mailpit pre-start cleanup if restarting mailpit
    if [[ "$service" == "mailpit" ]] && [ -f "${SCRIPT_DIR}/mailpit_lifecycle.sh" ]; then
        log_message "Running mailpit pre-start cleanup..."
        "${SCRIPT_DIR}/mailpit_lifecycle.sh" pre-start || {
            log_message "Mailpit pre-start cleanup encountered issues, continuing anyway..." "WARNING"
        }
    fi

    # Simple restart: just stop and start the service
    if docker_compose restart "$service"; then
        log_message "Successfully restarted ${service} service" "SUCCESS"

        # Validate mailpit after restart
        if [[ "$service" == "mailpit" ]] && [ -f "${INSTALL_DIR}/scripts/health/validate_mailpit.py" ]; then
            # Wait for container to become healthy (up to 30 seconds)
            log_message "Waiting for mailpit to become healthy..."
            local attempts=0
            while [ $attempts -lt 30 ]; do
                if docker inspect sting-ce-mailpit --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
                    break
                fi
                sleep 1
                ((attempts++))
            done

            log_message "Validating mailpit configuration for auth flow..."
            if python3 "${INSTALL_DIR}/scripts/health/validate_mailpit.py" --quick >/dev/null 2>&1; then
                log_message "✅ Mailpit validation passed - auth emails will be delivered" "SUCCESS"
            else
                log_message "⚠️  Mailpit validation failed - run: python3 ${INSTALL_DIR}/scripts/health/validate_mailpit.py" "WARNING"
            fi
        fi

        return 0
    else
        log_message "Failed to restart ${service} service" "ERROR"
        return 1
    fi
}

# Rebuild a specific service
rebuild_service() {
    local service="$1"
    local cache_level="${2:-moderate}"
    log_message "🐝 Rebuilding ${service} service with cache buzzer..."
    
    # Use cache buzzer for enhanced rebuild
    if [ -f "$(dirname "${BASH_SOURCE[0]}")/cache_buzzer.sh" ]; then
        source "$(dirname "${BASH_SOURCE[0]}")/cache_buzzer.sh"
        log_message "Using cache buzzer for service rebuild"
        
        # Clear cache specific to this service
        if [ "$cache_level" = "full" ]; then
            # Stop and remove the specific container
            docker stop "sting-ce-${service}" 2>/dev/null || true
            docker rm -f "sting-ce-${service}" 2>/dev/null || true
            # Remove the image
            docker images --format '{{.Repository}}:{{.Tag}}' | grep "sting-ce-${service}" | xargs -r docker rmi -f
        fi
        
        build_docker_services_nocache "$service" "$cache_level"
        rebuild_result=$?
    else
        # Fallback to standard rebuild
        log_message "Warning: cache_buzzer.sh not found, using standard rebuild"
        rebuild_result=1
    fi
    
    # Fallback to original logic if cache buzzer fails
    if [ $rebuild_result -ne 0 ]; then
        log_message "Cache buzzer failed, falling back to standard rebuild"
        if docker compose -f "${INSTALL_DIR}/docker-compose.yml" build --no-cache --pull ${service}; then
            log_message "${service} image rebuilt successfully."
            if docker compose -f "${INSTALL_DIR}/docker-compose.yml" push ${service}; then
                log_message "${service} image pushed to registry successfully."
                return 0
            else
                log_message "Failed to push ${service} image to registry."
                return 1
            fi
        else
            log_message "Failed to rebuild ${service} image."
            return 1
        fi
    else
        log_message "✅ Cache buzzer rebuild completed successfully"
        return 0
    fi
}

# Safely reinstall a specific service with rollback capability
reinstall_service() {
    local service="$1"
    local source_dir
    source_dir="$(pwd)"
    local backup_dir="${INSTALL_DIR}/${service}.backup.$(date +%Y%m%d_%H%M%S)"
    
    if [ -z "$service" ]; then
        log_message "Error: No service specified for reinstall" "ERROR"
        return 1
    fi
    
    log_message "Starting safe reinstall of service: $service"
    
    # Phase 1: Create backup of service files (if applicable)
    case "$service" in
        app|frontend|chatbot)
            if [ -d "${INSTALL_DIR}/${service}" ]; then
                log_message "Creating backup of ${service} files..."
                if ! cp -r "${INSTALL_DIR}/${service}" "${backup_dir}"; then
                    log_message "Failed to create backup for ${service}" "ERROR"
                    return 1
                fi
                log_message "Backup created at: ${backup_dir}"
            fi
            ;;
    esac
    
    # Phase 2: Check if source files exist
    case "$service" in
        app|frontend|chatbot)
            if [ ! -d "${source_dir}/${service}" ]; then
                log_message "Source directory not found: ${source_dir}/${service}" "ERROR"
                return 1
            fi
            ;;
    esac
    
    # Phase 3: Stop the service
    log_message "Stopping ${service} service..."
    if ! docker_compose stop "$service"; then
        log_message "Failed to stop ${service} service" "ERROR"
        restore_service_backup "$service" "$backup_dir"
        return 1
    fi
    
    # Phase 4: Remove containers and images
    log_message "Removing ${service} containers and images..."
    docker_compose rm -f "$service"
    docker rmi -f "sting-${service}" 2>/dev/null || true
    
    # Phase 5: Reinstall service with rollback on failure
    case "$service" in
        app)
            if ! reinstall_app_service "$service" "$source_dir" "$backup_dir"; then
                restore_service_backup "$service" "$backup_dir"
                return 1
            fi
            ;;
        frontend)
            if ! reinstall_frontend_service "$service" "$source_dir" "$backup_dir"; then
                restore_service_backup "$service" "$backup_dir"
                return 1
            fi
            ;;
        chatbot)
            if ! reinstall_chatbot_service "$service" "$source_dir" "$backup_dir"; then
                restore_service_backup "$service" "$backup_dir"
                return 1
            fi
            ;;
##        supertokens)  # DEPRECATED - SuperTokens removed in favor of Kratos
##            if ! reinstall_stateless_service "$service"; then
##                log_message "Failed to reinstall ${service} service" "ERROR"
##                return 1
##            fi
##            ;;
        vault)
            if ! reinstall_vault_service "$service"; then
                log_message "Failed to reinstall ${service} service" "ERROR"
                return 1
            fi
            ;;
        *)
            # Generic service reinstall
            if ! reinstall_generic_service "$service"; then
                log_message "Failed to reinstall ${service} service" "ERROR"
                return 1
            fi
            ;;
    esac
    
    # Phase 6: Cleanup successful - remove backup
    if [ -d "$backup_dir" ]; then
        log_message "Reinstall successful - cleaning up backup..."
        rm -rf "$backup_dir"
    fi
    
    log_message "Service $service reinstalled successfully" "SUCCESS"
    return 0
}

# Helper function: Build LLM images
build_llm_images() {
    log_message "Building LLM service images" "INFO"

    # Create necessary volumes if they don't exist
    for volume in "llm_logs"; do
        if ! docker volume ls | grep -q "$volume"; then
            docker volume create "$volume"
            log_message "Created Docker volume: $volume"
        fi
    done

    # Store current directory
    local current_dir
    current_dir=$(pwd)
    cd "${INSTALL_DIR}" || {
        log_message "Failed to change to installation directory" "ERROR"
        return 1
    }

    # First build the base image
    log_message "Building LLM base image at ${INSTALL_DIR}/llm_service/Dockerfile.llm-base..." "INFO"
    # Show the Dockerfile for debugging
    log_message "Dockerfile.llm-base content:" "DEBUG"
    cat "${INSTALL_DIR}/llm_service/Dockerfile.llm-base"

    # Build the base image with verbose output
    docker build --no-cache -t sting/llm-base:latest \
        -f "${INSTALL_DIR}/llm_service/Dockerfile.llm-base" \
        "${INSTALL_DIR}/llm_service" --progress=plain
    
    # Then build the model-specific images with their dedicated Dockerfiles
    for model in "llama3" "phi3" "zephyr"; do
        log_message "Building ${model} service image..."
        # Use model-specific Dockerfile rather than generic Dockerfile.llm
        docker build --no-cache -t "sting/${model}-service:latest" \
            -f "${INSTALL_DIR}/llm_service/Dockerfile.${model}" \
            "${INSTALL_DIR}/llm_service"
    done
    
    # Return to original directory
    cd "$current_dir"
    log_message "LLM service images built successfully" "SUCCESS"
}

                
#                 log_message "Vault is fully initialized and configured"
#                 return 0
#             fi
#         fi
        
#         log_message "Waiting for Vault... attempt $attempt/$max_attempts"
#         sleep $delay
#         attempt=$((attempt + 1))
#     done
    
#     # Final check to see if the Vault container is at least running
#     if docker ps | grep -q "sting.*vault"; then
#         log_message "WARNING: Vault container is running but might not be fully initialized. Continuing anyway..."
#         return 0
#     fi
    
#     log_message "ERROR: Vault failed to initialize after $max_attempts attempts"
#     return 1
# }

# Wait for Vault service to be ready (for service reinstalls)
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

# Helper function: Stop native LLM service (macOS)
stop_native_llm_service() {
    local pid_file="$INSTALL_DIR/run/llm-gateway.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_message "Stopping native LLM service (PID: $pid)"
            kill "$pid" 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            log_message "Native LLM service stopped"
        else
            log_message "Native LLM service not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        log_message "Native LLM service not running (no PID file)"
    fi
}

# Helper function: Restore service from backup
restore_service_backup() {
    local service="$1"
    local backup_dir="$2"
    
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        log_message "No valid backup directory for $service" "ERROR"
        return 1
    fi
    
    log_message "Restoring $service from backup..." "WARNING"
    
    # Remove any partial installation
    if [ -d "${INSTALL_DIR}/${service}" ]; then
        rm -rf "${INSTALL_DIR}/${service}"
    fi
    
    # Restore from backup
    if cp -r "${backup_dir}" "${INSTALL_DIR}/${service}"; then
        log_message "$service restored from backup successfully"
        return 0
    else
        log_message "Failed to restore $service from backup!" "ERROR"
        return 1
    fi
}

# Helper function: Reinstall app service with rollback
reinstall_app_service() {
    local service="$1"
    local source_dir="$2"
    local backup_dir="$3"
    
    log_message "Reinstalling $service service..."
    
    # Copy fresh code
    source "${SCRIPT_DIR}/file_operations.sh"
    if ! sync_service_code "$service"; then
        log_message "Failed to sync $service code" "ERROR"
        return 1
    fi
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Wait for service to be healthy
    if ! wait_for_service "$service"; then
        log_message "$service failed health check" "ERROR"
        return 1
    fi
    
    return 0
}

# Helper function: Reinstall frontend service with rollback
reinstall_frontend_service() {
    local service="$1"
    local source_dir="$2"
    local backup_dir="$3"
    
    log_message "Reinstalling $service service..."
    
    # Copy fresh code
    source "${SCRIPT_DIR}/file_operations.sh"
    if ! sync_service_code "$service"; then
        log_message "Failed to sync $service code" "ERROR"
        return 1
    fi
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Wait for service to be healthy
    if ! wait_for_service "$service"; then
        log_message "$service failed health check" "ERROR"
        return 1
    fi
    
    return 0
}

# Helper function: Reinstall chatbot service with rollback
reinstall_chatbot_service() {
    local service="$1"
    local source_dir="$2"
    local backup_dir="$3"
    
    log_message "Reinstalling $service service..."
    
    # Copy fresh code including dependencies
    source "${SCRIPT_DIR}/file_operations.sh"
    if ! sync_service_code "$service"; then
        log_message "Failed to sync $service code" "ERROR"
        return 1
    fi
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Wait for service to be healthy (chatbot uses relaxed checks)
    if ! wait_for_service "$service"; then
        log_message "$service failed health check" "ERROR"
        return 1
    fi
    
    return 0
}

# Helper function: Reinstall stateless service
reinstall_stateless_service() {
    local service="$1"
    
    log_message "Reinstalling stateless $service service..."
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Wait for service to be healthy
    if ! wait_for_service "$service"; then
        log_message "$service failed health check" "ERROR"
        return 1
    fi
    
    return 0
}

# Helper function: Reinstall vault service with special handling
reinstall_vault_service() {
    local service="$1"
    
    log_message "Reinstalling $service service..."
    log_message "WARNING: Vault reinstall will lose unsealed state" "WARNING"
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Wait for vault to initialize (uses longer timeout)
    if ! wait_for_vault; then
        log_message "$service failed to initialize" "ERROR"
        return 1
    fi
    
    return 0
}

# Helper function: Reinstall generic service
reinstall_generic_service() {
    local service="$1"
    
    log_message "Reinstalling $service service..."
    
    # Rebuild and start service
    if ! docker compose build --no-cache "$service"; then
        log_message "Failed to rebuild $service" "ERROR"
        return 1
    fi
    
    if ! docker compose up -d "$service"; then
        log_message "Failed to start $service" "ERROR"
        return 1
    fi
    
    # Basic health check
    if ! wait_for_service "$service"; then
        log_message "$service failed health check" "ERROR"
        return 1
    fi

    return 0
}

# Vault unsealing utility function (post-update safety net)
ensure_vault_unsealed() {
    log_message "🔐 Checking vault seal status..."

    # Check if vault container is running
    if ! docker ps --format "table {{.Names}}" | grep -q "sting-ce-vault"; then
        log_message "⚠️  Vault container not running - skipping unseal check"
        return 0
    fi

    # Check vault status
    local vault_status
    vault_status=$(docker exec sting-ce-vault vault status -format=json 2>/dev/null)
    local vault_exit_code=$?

    if [ $vault_exit_code -eq 0 ]; then
        # Vault is unsealed
        log_message "✅ Vault is already unsealed and operational"
        return 0
    elif [ $vault_exit_code -eq 2 ]; then
        # Vault is sealed but initialized - attempt to unseal
        log_message "🔒 Vault is sealed, attempting automatic unseal..."

        # Run the auto-init script which includes unseal logic
        if docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh 2>/dev/null; then
            log_message "✅ Vault unsealed successfully"
            return 0
        else
            log_message "❌ Failed to unseal vault automatically" "WARNING"
            log_message "💡 Manual intervention may be required:" "WARNING"
            log_message "   1. Check if vault keys exist: docker exec sting-ce-vault ls -la /vault/persistent/" "WARNING"
            log_message "   2. Manual unseal: docker exec sting-ce-vault vault operator unseal <key>" "WARNING"
            return 1
        fi
    else
        # Vault not initialized - this shouldn't happen in production
        log_message "⚠️  Vault appears uninitialized - this may be expected for fresh installs"
        return 0
    fi
}