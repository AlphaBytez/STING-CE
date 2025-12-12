#!/bin/bash
# Enhanced Service Startup Resilience for STING
# This script provides intelligent service startup with retry logic,
# dependency checking, and automatic recovery mechanisms

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service dependencies map (using if statements for macOS compatibility)
get_service_deps() {
    local service=$1
    case "$service" in
        app) echo "db redis" ;;
        frontend) echo "app" ;;
        chatbot) echo "db app" ;;
        knowledge) echo "db redis app" ;;
        nginx) echo "app frontend" ;;
        *) echo "" ;;
    esac
}

# Service health check endpoints
get_health_check() {
    local service=$1
    case "$service" in
        app) echo "https://localhost:5050/health" ;;
        frontend) echo "https://localhost:8443" ;;
        chatbot) echo "http://localhost:8888/health" ;;
        knowledge) echo "http://localhost:8090/health" ;;
        kratos) echo "http://localhost:4433/health/ready" ;;
        loki) echo "http://localhost:3100/ready" ;;
        grafana) echo "http://localhost:3000/api/health" ;;
        promtail) echo "http://localhost:9080/ready" ;;
        *) echo "" ;;
    esac
}

# Maximum retry attempts
MAX_RETRIES=3
RETRY_DELAY=5

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local max_wait=${2:-30}
    local count=0
    
    # First check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "sting-ce-$service"; then
        return 1
    fi
    
    # If no health check URL defined, just check container status
    local health_url=$(get_health_check "$service")
    if [[ -z "$health_url" ]]; then
        docker inspect "sting-ce-$service" --format='{{.State.Status}}' | grep -q "running"
        return $?
    fi
    
    # Perform health check
    echo -n "  Checking health of $service..."
    while [ $count -lt $max_wait ]; do
        if curl -sk "$health_url" >/dev/null 2>&1; then
            echo -e " ${GREEN}healthy${NC}"
            return 0
        fi
        sleep 1
        ((count++))
        echo -n "."
    done
    
    echo -e " ${RED}unhealthy${NC}"
    return 1
}

# Function to check if all dependencies are running
check_dependencies() {
    local service=$1
    local deps=$(get_service_deps "$service")
    
    if [[ -z "$deps" ]]; then
        return 0
    fi
    
    for dep in $deps; do
        if ! docker ps --format "{{.Names}}" | grep -q "sting-ce-$dep"; then
            echo -e "  ${YELLOW}Dependency $dep is not running${NC}"
            return 1
        fi
    done
    
    return 0
}

# Function to start a service with retry logic
start_service_with_retry() {
    local service=$1
    local attempt=0
    
    echo -e "${BLUE}Starting $service...${NC}"
    
    while [ $attempt -lt $MAX_RETRIES ]; do
        ((attempt++))
        echo "  Attempt $attempt/$MAX_RETRIES"
        
        # Check dependencies first
        if ! check_dependencies "$service"; then
            echo "  Waiting for dependencies..."
            sleep $RETRY_DELAY
            continue
        fi
        
        # Check if container exists but is not running
        local container_state=$(docker inspect "sting-ce-$service" --format='{{.State.Status}}' 2>/dev/null || echo "missing")
        
        case "$container_state" in
            "created"|"exited")
                echo "  Container exists in $container_state state, starting..."
                if docker start "sting-ce-$service"; then
                    sleep 2
                    if check_service_health "$service"; then
                        echo -e "  ${GREEN}[+] $service started successfully${NC}"
                        return 0
                    fi
                fi
                ;;
            "running")
                if check_service_health "$service"; then
                    echo -e "  ${GREEN}[+] $service already running and healthy${NC}"
                    return 0
                else
                    echo "  Service running but not healthy, restarting..."
                    docker restart "sting-ce-$service"
                    sleep 3
                fi
                ;;
            *)
                echo "  Container missing or in unknown state, recreating..."
                docker compose up -d "$service" --no-deps
                sleep 3
                ;;
        esac
        
        # Wait before next attempt
        if [ $attempt -lt $MAX_RETRIES ]; then
            echo "  Waiting $RETRY_DELAY seconds before retry..."
            sleep $RETRY_DELAY
        fi
    done
    
    echo -e "  ${RED}[-] Failed to start $service after $MAX_RETRIES attempts${NC}"
    return 1
}

# Function to detect and fix port conflicts
check_port_conflicts() {
    local ports=("8443:frontend" "5050:app" "5005:chatbot" "5030:knowledge" "4433:kratos" "3100:loki" "3000:grafana" "9080:promtail" "80:nginx" "443:nginx")
    local conflicts=0
    
    echo -e "${BLUE}Checking for port conflicts...${NC}"
    
    for port_info in "${ports[@]}"; do
        IFS=':' read -r port service <<< "$port_info"
        
        # Check if port is in use by non-Docker process
        if lsof -i ":$port" | grep -v "docker" >/dev/null 2>&1; then
            echo -e "  ${YELLOW}[!] Port $port is in use by non-Docker process (needed by $service)${NC}"
            ((conflicts++))
        fi
    done
    
    if [ $conflicts -eq 0 ]; then
        echo -e "  ${GREEN}[+] No port conflicts detected${NC}"
    fi
    
    return $conflicts
}

# Main function to ensure all services are started
ensure_all_services_started_enhanced() {
    echo -e "${BLUE}=== Enhanced Service Startup Check ===${NC}"
    
    # First check for port conflicts
    check_port_conflicts || true
    
    # Get list of all services from docker-compose
    local all_services=$(docker compose ps --services 2>/dev/null || docker-compose ps --services)
    local failed_services=()
    
    # Define startup order based on dependencies
    local startup_order=(
        "db"
        "redis"
        "kratos"
        "kratos-migrate"
        "mailpit"
        "app"
        "frontend"
        "chatbot"
        "knowledge"
        "nectar-worker"
        "public-bee"
        "log-forwarder"
        "loki"
        "grafana"
        "promtail"
        "nginx"
    )
    
    # Start services in dependency order
    for service in "${startup_order[@]}"; do
        # Skip if service doesn't exist in compose
        if ! echo "$all_services" | grep -q "^$service$"; then
            continue
        fi
        
        # Check if service needs to be started
        local container_state=$(docker inspect "sting-ce-$service" --format='{{.State.Status}}' 2>/dev/null || echo "missing")
        
        if [[ "$container_state" != "running" ]] || ! check_service_health "$service" 10; then
            if ! start_service_with_retry "$service"; then
                failed_services+=("$service")
            fi
        else
            echo -e "${GREEN}[+] $service already running${NC}"
        fi
    done
    
    # Report results
    echo
    echo -e "${BLUE}=== Service Startup Summary ===${NC}"
    
    if [ ${#failed_services[@]} -eq 0 ]; then
        echo -e "${GREEN}[+] All services started successfully!${NC}"
        return 0
    else
        echo -e "${RED}[-] Failed to start the following services:${NC}"
        for service in "${failed_services[@]}"; do
            echo "  - $service"
            echo "    Last logs:"
            docker logs "sting-ce-$service" --tail 5 2>&1 | sed 's/^/    /'
        done
        echo
        echo -e "${YELLOW}Manual intervention may be required. Try:${NC}"
        echo "  1. Check logs: docker logs sting-ce-<service>"
        echo "  2. Restart individual service: docker restart sting-ce-<service>"
        echo "  3. Recreate service: docker compose up -d <service> --force-recreate"
        return 1
    fi
}

# Export functions for use in other scripts
export -f check_service_health
export -f check_dependencies
export -f start_service_with_retry
export -f check_port_conflicts
export -f ensure_all_services_started_enhanced

# If script is run directly, execute the main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ensure_all_services_started_enhanced
fi