#!/bin/bash
# Enhanced Restart Module for STING Management
# Fixes reliability issues with full system restart (`msting restart`)

# Load dependencies
source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"
source "$(dirname "${BASH_SOURCE[0]}")/services.sh"

# Cross-platform timeout function for macOS and Linux compatibility
safe_timeout() {
    local timeout_duration="$1"
    shift
    
    if command -v timeout >/dev/null 2>&1; then
        # Linux/GNU timeout available
        timeout "$timeout_duration" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        # macOS with GNU coreutils installed
        gtimeout "$timeout_duration" "$@"
    else
        # Fallback using background process and kill (macOS default)
        local pid
        "$@" &
        pid=$!
        
        # Wait for timeout_duration or process completion
        local count=0
        local max_count=$timeout_duration
        while [ $count -lt $max_count ] && kill -0 $pid 2>/dev/null; do
            sleep 1
            count=$((count + 1))
        done
        
        # If process still running, kill it
        if kill -0 $pid 2>/dev/null; then
            kill -TERM $pid 2>/dev/null
            sleep 2
            if kill -0 $pid 2>/dev/null; then
                kill -KILL $pid 2>/dev/null
            fi
            return 124  # timeout exit code
        else
            wait $pid
            return $?
        fi
    fi
}

# Enhanced restart all services with proper dependency ordering
restart_all_services_enhanced() {
    log_message "🔄 Starting enhanced full system restart..." "INFO"
    
    # Pre-restart validation
    if ! validate_restart_conditions; then
        log_message "❌ Pre-restart validation failed" "ERROR"
        return 1
    fi
    
    # Store current directory and change to install directory
    local original_dir="$(pwd)"
    cd "${INSTALL_DIR}" || {
        log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
        return 1
    }
    
    # Load environment variables
    source_service_envs || {
        log_message "Failed to load service environments" "ERROR"
        cd "$original_dir"
        return 1
    }
    
    # Execute restart with dependency awareness
    if restart_with_dependency_order; then
        log_message "✅ Full system restart completed successfully" "SUCCESS"
        cd "$original_dir"
        return 0
    else
        log_message "❌ Full system restart failed" "ERROR"
        cd "$original_dir"
        return 1
    fi
}

# Validate conditions for restart
validate_restart_conditions() {
    log_message "🔍 Validating restart conditions..."
    
    # Store current directory and change to install directory for compose operations
    local original_dir="$(pwd)"
    cd "${INSTALL_DIR}" || {
        log_message "Failed to change to installation directory: ${INSTALL_DIR}" "ERROR"
        return 1
    }
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_message "Docker daemon not accessible" "ERROR"
        cd "$original_dir"
        return 1
    fi
    
    # Check disk space
    if ! check_disk_space >/dev/null 2>&1; then
        log_message "Insufficient disk space for restart" "ERROR"
        cd "$original_dir"
        return 1
    fi
    
    # Check if any critical services are missing (now running from correct directory)
    local critical_services=("vault" "db" "kratos" "app")
    for service in "${critical_services[@]}"; do
        if ! docker compose ps --format "{{.Service}}" | grep -q "^${service}$"; then
            log_message "Critical service $service not found in compose configuration" "ERROR"
            cd "$original_dir"
            return 1
        fi
    done
    
    log_message "✅ Pre-restart validation passed"
    cd "$original_dir"
    return 0
}

# Restart with proper dependency ordering
restart_with_dependency_order() {
    log_message "🔄 Restarting services in dependency order..."
    
    # Phase 1: Stop all services gracefully
    log_message "📥 Phase 1: Graceful shutdown of all services..."
    if ! graceful_stop_all_services; then
        log_message "Warning: Graceful stop had issues, proceeding with restart" "WARNING"
    fi
    
    # Phase 2: Start services in dependency order
    log_message "🚀 Phase 2: Starting services in dependency order..."
    
    # Tier 1: Core infrastructure (no dependencies)
    if ! start_service_tier "Infrastructure" vault db redis; then
        log_message "Failed to start infrastructure services" "ERROR"
        return 1
    fi

    # Tier 2: Authentication and messaging (depends on Tier 1)
    if ! start_service_tier "Authentication" kratos mailpit messaging; then
        log_message "Failed to start authentication services" "ERROR"
        return 1
    fi

    # Tier 3: Core application services (depends on Tier 1 & 2)
    if ! start_service_tier "Application" utils app knowledge external-ai chroma; then
        log_message "Failed to start application services" "ERROR"
        return 1
    fi

    # Tier 4: Frontend and workers (depends on Tier 3)
    if ! start_service_tier "Frontend" frontend report-worker profile-sync-worker; then
        log_message "Failed to start frontend services" "ERROR"
        return 1
    fi

    # Tier 5: AI and auxiliary services (depends on previous tiers)
    if ! start_service_tier "AI/Auxiliary" chatbot llm-gateway-proxy; then
        log_message "Failed to start AI services" "ERROR"
        return 1
    fi
    
    # Tier 6: Observability (if enabled)
    start_observability_services_if_enabled
    
    log_message "✅ All service tiers restarted successfully"
    return 0
}

# Graceful stop with timeout
graceful_stop_all_services() {
    log_message "Stopping all services gracefully..."
    
    # First attempt: graceful docker compose stop
    if safe_timeout 60 docker compose stop; then
        log_message "✅ All services stopped gracefully"
        return 0
    else
        log_message "⚠️  Graceful stop timed out, forcing stop..." "WARNING"
        # Force stop any remaining containers
        local running_containers=$(docker ps -q --filter "name=sting-ce")
        if [ -n "$running_containers" ]; then
            echo "$running_containers" | xargs docker stop -t 10 || true
        fi
        return 1
    fi
}

# Start a tier of services with health checks
start_service_tier() {
    local tier_name="$1"
    shift
    local services=("$@")
    
    log_message "🚀 Starting $tier_name tier: ${services[*]}"
    
    # Start all services in this tier simultaneously
    for service in "${services[@]}"; do
        if docker compose ps --format "{{.Service}}" | grep -q "^${service}$"; then
            log_message "Starting $service..."
            docker compose up -d "$service" || {
                log_message "Failed to start $service" "ERROR"
                return 1
            }
        else
            log_message "⚠️  Service $service not found in compose, skipping..." "WARNING"
        fi
    done
    
    # Wait for all services in this tier to be healthy
    log_message "⏳ Waiting for $tier_name tier to be healthy..."
    local tier_healthy=true
    
    for service in "${services[@]}"; do
        if docker compose ps --format "{{.Service}}" | grep -q "^${service}$"; then
            if ! wait_for_service_enhanced "$service"; then
                log_message "❌ $service failed health check" "ERROR"
                tier_healthy=false
            else
                log_message "✅ $service is healthy"
            fi
        fi
    done
    
    if [ "$tier_healthy" = true ]; then
        log_message "✅ $tier_name tier is fully healthy"
        return 0
    else
        log_message "❌ $tier_name tier has unhealthy services" "ERROR"
        return 1
    fi
}

# Enhanced wait for service with better timeout handling
wait_for_service_enhanced() {
    local service="$1"
    local max_attempts=30
    local attempt=1
    
    # Service-specific timeout adjustments
    case "$service" in
        "vault")
            max_attempts=60  # Vault needs more time to initialize
            ;;
        "kratos")
            max_attempts=45  # Kratos may need time for migrations
            ;;
        "db")
            max_attempts=40  # Database startup can be slow
            ;;
        "knowledge"|"chatbot")
            max_attempts=50  # AI services need more startup time
            ;;
        *)
            max_attempts=30  # Default timeout
            ;;
    esac
    
    log_message "⏳ Waiting for $service to be healthy (max ${max_attempts} attempts)..."
    
    while [ $attempt -le $max_attempts ]; do
        case "$service" in
            "vault")
                if docker exec sting-ce-vault vault status >/dev/null 2>&1; then
                    return 0
                fi
                ;;
            "db")
                if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
                    return 0
                fi
                ;;
            "kratos")
                if curl -s -f -k https://localhost:4434/admin/health/ready >/dev/null 2>&1; then
                    return 0
                fi
                ;;
            "app")
                if curl -k -s "https://localhost:5050/health" >/dev/null 2>&1; then
                    return 0
                fi
                ;;
            "frontend")
                if docker ps --format "{{.Names}}" | grep -q "sting-ce-frontend"; then
                    return 0
                fi
                ;;
            *)
                # Generic health check - just verify container is running
                if docker ps --format "{{.Names}}" | grep -q "sting-ce-$service"; then
                    return 0
                fi
                ;;
        esac
        
        # Show progress every 10 attempts
        if [ $((attempt % 10)) -eq 0 ]; then
            log_message "⏳ Still waiting for $service... (attempt $attempt/$max_attempts)"
        fi
        
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_message "❌ $service failed to become healthy after ${max_attempts} attempts" "ERROR"
    return 1
}

# Start observability services if enabled
start_observability_services_if_enabled() {
    if [ -f "${INSTALL_DIR}/env/observability.env" ]; then
        # Source observability env to check if enabled
        . "${INSTALL_DIR}/env/observability.env" 2>/dev/null
        
        if [ "${OBSERVABILITY_ENABLED:-false}" = "true" ]; then
            log_message "🔍 Starting observability services (enabled in config)..."
            
            # Start observability services
            docker compose --profile observability up -d loki grafana promtail 2>/dev/null || {
                log_message "⚠️  Some observability services failed to start" "WARNING"
            }
            
            # Optional log forwarding
            if [ "${LOG_FORWARDING_ENABLED:-false}" = "true" ]; then
                log_message "🔄 Starting log forwarding service..."
                docker compose --profile log-forwarding up -d log-forwarder 2>/dev/null || {
                    log_message "⚠️  Log forwarder failed to start (this is non-critical)" "WARNING"
                }
            fi
            
            log_message "✅ Observability services started"
        else
            log_message "ℹ️  Observability services disabled in configuration"
        fi
    else
        log_message "ℹ️  No observability configuration found"
    fi
}

# Function to replace the default restart_all_services
enhanced_restart_all() {
    log_message "🔄 Enhanced full system restart initiated..."
    
    # Use the enhanced restart function
    if restart_all_services_enhanced; then
        log_message "✅ Enhanced full system restart completed successfully" "SUCCESS"
        
        # Show final status
        log_message "📊 Final system status:"
        sleep 3  # Give services a moment to stabilize
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
        
        return 0
    else
        log_message "❌ Enhanced full system restart failed" "ERROR"
        
        # Show what went wrong
        log_message "🔍 Current service status after failed restart:"
        docker compose ps 2>/dev/null || true
        
        return 1
    fi
}

# Export the main function for use by manage_sting.sh
export -f enhanced_restart_all