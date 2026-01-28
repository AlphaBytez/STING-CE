#!/bin/bash
# Observability service management for STING
# Handles Grafana, Loki, and Promtail services without touching core dependencies

# Check if observability is enabled in config
is_observability_enabled() {
    local config_file="${CONFIG_FILE:-${INSTALL_DIR}/conf/config.yml}"
    
    if [ ! -f "$config_file" ]; then
        echo "false"
        return 1
    fi
    
    # Check if observability is enabled in config
    local enabled=$(grep -A 1 "^observability:" "$config_file" | grep "enabled:" | awk '{print $2}')
    
    if [ "$enabled" = "true" ]; then
        echo "true"
        return 0
    else
        echo "false"
        return 1
    fi
}

# Start observability services safely
start_observability_services() {
    log_message "Starting observability services..."
    
    # First check if observability is enabled
    if ! is_observability_enabled; then
        log_message "Observability is disabled in configuration"
        return 0
    fi
    
    # Check if core services are running (indicating vault is up)
    if ! docker ps --format "{{.Names}}" | grep -q "sting-ce-app"; then
        log_message "Core services not running - cannot start observability" "WARNING"
        return 1
    fi
    
    # Vault should already be running - verify but don't start it
    if ! docker ps --format "{{.Names}}" | grep -q "sting-ce-vault"; then
        log_message "Vault is not running - cannot start observability safely" "ERROR"
        return 1
    fi
    
    log_message "Core dependencies verified, starting observability stack..."
    
    # Start only the observability services, not vault
    local compose_file="${INSTALL_DIR}/docker-compose.yml"
    if [ ! -f "$compose_file" ]; then
        log_message "Docker compose file not found at $compose_file" "ERROR"
        return 1
    fi
    
    # Use the install directory for proper context
    local original_dir=$(pwd)
    cd "${INSTALL_DIR}" || {
        log_message "Failed to change to install directory" "ERROR"
        return 1
    }
    
    # Start observability services explicitly (without vault)
    log_message "Starting Loki (log aggregation)..."
    docker compose up -d loki 2>&1 | grep -v "is up-to-date" || true
    
    # Wait for Loki to be healthy
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker ps --format "{{.Names}} {{.Status}}" | grep "sting-ce-loki" | grep -q "healthy"; then
            log_message "Loki is healthy"
            break
        fi
        sleep 2
        ((attempt++))
    done
    
    log_message "Starting Grafana (dashboards)..."
    docker compose up -d grafana 2>&1 | grep -v "is up-to-date" || true
    
    log_message "Starting Promtail (log collector)..."
    docker compose up -d promtail 2>&1 | grep -v "is up-to-date" || true
    
    cd "$original_dir" || true
    
    # Verify services started
    sleep 3
    local running_count=$(docker ps --format "{{.Names}}" | grep -E "loki|grafana|promtail" | wc -l)
    
    if [ "$running_count" -eq 3 ]; then
        log_message "[+] All observability services started successfully" "SUCCESS"
        log_message "  Grafana: http://localhost:3000"
        log_message "  Loki: http://localhost:3100"
        return 0
    else
        log_message "[!] Only $running_count/3 observability services running" "WARNING"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "loki|grafana|promtail"
        return 1
    fi
}

# Stop observability services
stop_observability_services() {
    log_message "Stopping observability services..."
    
    local compose_file="${INSTALL_DIR}/docker-compose.yml"
    if [ ! -f "$compose_file" ]; then
        log_message "Docker compose file not found" "ERROR"
        return 1
    fi
    
    # Stop only observability services
    docker compose -f "$compose_file" stop grafana promtail loki 2>&1 | grep -v "Warning" || true
    
    log_message "Observability services stopped"
    return 0
}

# Restart observability services
restart_observability_services() {
    log_message "Restarting observability services..."
    
    # Don't stop/start, just restart to avoid dependency issues
    local compose_file="${INSTALL_DIR}/docker-compose.yml"
    if [ ! -f "$compose_file" ]; then
        log_message "Docker compose file not found" "ERROR"
        return 1
    fi
    
    docker compose -f "$compose_file" restart grafana promtail loki 2>&1 | grep -v "Warning" || true
    
    log_message "Observability services restarted"
    return 0
}

# Check observability service status
check_observability_status() {
    local all_healthy=true
    
    echo " Observability Service Status:"
    echo "================================"
    
    # Check if enabled
    if ! is_observability_enabled; then
        echo "  [!]  Observability is disabled in configuration"
        return 0
    fi
    
    # Check each service
    for service in loki grafana promtail; do
        local container_name="sting-ce-$service"
        local status=$(docker ps --format "{{.Names}} {{.Status}}" | grep "$container_name" | awk '{$1=""; print $0}' | xargs)
        
        if [ -n "$status" ]; then
            if echo "$status" | grep -q "healthy"; then
                echo "  [+] $service: $status"
            elif echo "$status" | grep -q "starting"; then
                echo "   $service: $status"
                all_healthy=false
            else
                echo "  [!]  $service: $status"
                all_healthy=false
            fi
        else
            echo "  [-] $service: not running"
            all_healthy=false
        fi
    done
    
    echo ""
    if [ "$all_healthy" = true ]; then
        echo "[+] All observability services are healthy"
        echo "  📊 Grafana: http://localhost:3000"
        echo "  📝 Loki API: http://localhost:3100"
    else
        echo "[!]  Some observability services need attention"
    fi
}

# Clean up orphaned observability containers
cleanup_observability_containers() {
    log_message "Cleaning up orphaned observability containers..."
    
    # Remove any stopped observability containers
    docker ps -a --format "{{.Names}}" | grep -E "loki|grafana|promtail" | while read container; do
        if ! docker ps --format "{{.Names}}" | grep -q "$container"; then
            log_message "Removing stopped container: $container"
            docker rm "$container" 2>/dev/null || true
        fi
    done
    
    log_message "Cleanup complete"
}

# Main function for standalone execution
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Source required functions if not already loaded
    if ! command -v log_message &>/dev/null; then
        log_message() {
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
        }
    fi
    
    case "${1:-}" in
        start)
            start_observability_services
            ;;
        stop)
            stop_observability_services
            ;;
        restart)
            restart_observability_services
            ;;
        status)
            check_observability_status
            ;;
        cleanup)
            cleanup_observability_containers
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|cleanup}"
            exit 1
            ;;
    esac
fi