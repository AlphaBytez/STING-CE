#!/bin/bash

# Enhanced Status Module for STING
# Provides comprehensive service status with verbose mode and error diagnostics

# Platform detection
detect_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if grep -q Microsoft /proc/version 2>/dev/null; then
            echo "wsl"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Check for dependencies and provide installation hints
check_dependencies() {
    local platform=$(detect_platform)
    local missing_deps=()
    
    if ! command -v jq >/dev/null 2>&1; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Missing dependencies detected on $platform:${NC}" >&2
        case $platform in
            "wsl"|"linux")
                echo -e "${YELLOW}   Install with: sudo apt update && sudo apt install ${missing_deps[*]}${NC}" >&2
                ;;
            "macos")
                echo -e "${YELLOW}   Install with: brew install ${missing_deps[*]}${NC}" >&2
                ;;
        esac
        echo -e "${YELLOW}   Status checks will use fallback methods${NC}" >&2
        echo "" >&2
    fi
}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to get container health status
get_container_health() {
    local container_name="$1"
    
    # Check if jq is available, fallback to basic parsing if not
    if command -v jq >/dev/null 2>&1; then
        local health_status=$(docker inspect "$container_name" 2>/dev/null | jq -r '.[0].State.Health.Status // "none"')
    else
        # Fallback: use grep/sed to extract health status without jq
        local health_status=$(docker inspect "$container_name" 2>/dev/null | grep -A 10 '"Health"' | grep '"Status"' | sed 's/.*"Status": *"\([^"]*\)".*/\1/' | head -1)
        if [ -z "$health_status" ]; then
            health_status="none"
        fi
    fi
    echo "$health_status"
}

# Function to get last few error logs from container
get_container_errors() {
    local container_name="$1"
    local lines="${2:-5}"
    
    # Get last N lines of logs and filter for errors
    docker logs "$container_name" 2>&1 --tail "$lines" | grep -i -E "(error|exception|failed|fatal|critical)" 2>/dev/null || echo ""
}

# Function to check service endpoint
check_service_endpoint() {
    local service="$1"
    local endpoint="$2"
    local timeout="${3:-2}"
    
    if curl -sf --max-time "$timeout" "$endpoint" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Main enhanced status function
show_enhanced_status() {
    local verbose="${1:-false}"
    local service_filter="${2:-}"
    
    log_message "🔍 STING Services Enhanced Status Report" "INFO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_message "❌ Docker is not running or not accessible" "ERROR"
        echo "Please ensure Docker Desktop is running and try again."
        return 1
    fi
    
    # Define services and their properties using simple functions for compatibility
    get_service_endpoint() {
        case "$1" in
            "app") echo "https://localhost:5050/health" ;;
            "frontend") echo "https://localhost:8443" ;;
            "knowledge") echo "http://localhost:8090/health" ;;
            "messaging") echo "http://localhost:8082/health" ;;
            "external-ai") echo "http://localhost:8091/health" ;;
            "chatbot") echo "http://localhost:8081/health" ;;
            "kratos") echo "https://localhost:4433/health/alive" ;;
            "vault") echo "https://localhost:8200/v1/sys/health" ;;
            "db") echo "postgresql://postgres:password@localhost:5432/sting_app" ;;
            "report-worker") echo "" ;;
            "loki") echo "http://localhost:3100/ready" ;;
            "grafana") echo "http://localhost:3000/api/health" ;;
            "promtail") echo "http://localhost:9080/ready" ;;
            "log-forwarder") echo "" ;;
            *) echo "" ;;
        esac
    }
    
    get_container_name() {
        case "$1" in
            "db") echo "sting-ce-db" ;;
            "vault") echo "sting-ce-vault" ;;
            "kratos") echo "sting-ce-kratos" ;;
            "app") echo "sting-ce-app" ;;
            "frontend") echo "sting-ce-frontend" ;;
            "knowledge") echo "sting-ce-knowledge" ;;
            "messaging") echo "sting-ce-messaging" ;;
            "external-ai") echo "sting-ce-external-ai" ;;
            "chatbot") echo "sting-ce-chatbot" ;;
            "report-worker") echo "sting-ce-report-worker" ;;
            "loki") echo "sting-ce-loki" ;;
            "grafana") echo "sting-ce-grafana" ;;
            "promtail") echo "sting-ce-promtail" ;;
            "log-forwarder") echo "sting-ce-log-forwarder" ;;
            *) echo "" ;;
        esac
    }
    
    get_service_description() {
        case "$1" in
            "db") echo "PostgreSQL Database" ;;
            "vault") echo "HashiCorp Vault (Secrets)" ;;
            "kratos") echo "Ory Kratos (Authentication)" ;;
            "app") echo "Flask Backend API" ;;
            "frontend") echo "React Frontend" ;;
            "knowledge") echo "Knowledge Management" ;;
            "messaging") echo "Messaging Service" ;;
            "external-ai") echo "External AI Bridge" ;;
            "chatbot") echo "Bee AI Assistant" ;;
            "report-worker") echo "Report Generation Worker" ;;
            "loki") echo "Beeacon Log Store (Loki)" ;;
            "grafana") echo "Beeacon Dashboard (Grafana)" ;;
            "promtail") echo "Beeacon Log Agent (Promtail)" ;;
            "log-forwarder") echo "Beeacon Log Forwarder" ;;
            *) echo "Unknown Service" ;;
        esac
    }
    
    # Core services (must be running)
    local core_services=("db" "vault" "kratos" "app" "frontend" "report-worker")
    
    # Auxiliary services (nice to have)
    local aux_services=("knowledge" "messaging" "external-ai" "chatbot")
    
    # Observability services (Beeacon monitoring stack)
    local observability_services=("loki" "grafana" "promtail" "log-forwarder")
    
    # Combined list
    local all_services=("${core_services[@]}" "${aux_services[@]}" "${observability_services[@]}")
    
    # Filter services if requested
    if [ -n "$service_filter" ]; then
        all_services=("$service_filter")
    fi
    
    # Track overall health
    local unhealthy_count=0
    local core_unhealthy=0
    
    echo ""
    echo "🔷 Core Services:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    # Check each service
    for service in "${all_services[@]}"; do
        local container_name=$(get_container_name "$service")
        local description=$(get_service_description "$service")
        local endpoint=$(get_service_endpoint "$service")
        local is_core=false
        
        # Check if it's a core service
        for core in "${core_services[@]}"; do
            if [ "$service" = "$core" ]; then
                is_core=true
                break
            fi
        done
        
        # Print section header for auxiliary services
        if [ "$is_core" = "false" ] && [ "$service" = "${aux_services[0]}" ]; then
            echo ""
            echo "🔶 Auxiliary Services:"
            echo "─────────────────────────────────────────────────────────────────────────────"
        fi
        
        # Print section header for observability services
        if [ "$service" = "${observability_services[0]}" ]; then
            echo ""
            echo "🔍 Beeacon Observability (Monitoring Stack):"
            echo "─────────────────────────────────────────────────────────────────────────────"
        fi
        
        printf "%-20s %-25s " "$service:" "$description"
        
        # Check if container exists
        local container_exists=$(docker ps -a --format "{{.Names}}" | grep -w "$container_name" 2>/dev/null)
        
        if [ -z "$container_exists" ]; then
            printf "${RED}❌ Not Found${NC}\n"
            unhealthy_count=$((unhealthy_count + 1))
            [ "$is_core" = "true" ] && core_unhealthy=$((core_unhealthy + 1))
            
            if [ "$verbose" = "true" ]; then
                echo "  └─ Container $container_name does not exist"
            fi
            continue
        fi
        
        # Check if container is running
        local is_running=$(docker ps --format "{{.Names}}" | grep -w "$container_name" 2>/dev/null)
        
        if [ -z "$is_running" ]; then
            printf "${RED}❌ Stopped${NC}\n"
            unhealthy_count=$((unhealthy_count + 1))
            [ "$is_core" = "true" ] && core_unhealthy=$((core_unhealthy + 1))
            
            if [ "$verbose" = "true" ]; then
                # Get exit code and reason
                local exit_code=$(docker inspect "$container_name" 2>/dev/null | jq -r '.[0].State.ExitCode // "unknown"')
                local finished_at=$(docker inspect "$container_name" 2>/dev/null | jq -r '.[0].State.FinishedAt // "unknown"')
                echo "  ├─ Exit Code: $exit_code"
                echo "  ├─ Stopped at: $finished_at"
                
                # Get last error logs
                local errors=$(get_container_errors "$container_name" 10)
                if [ -n "$errors" ]; then
                    echo "  └─ Recent errors:"
                    echo "$errors" | sed 's/^/     /'
                fi
            fi
            continue
        fi
        
        # Container is running, check health
        local health_status=$(get_container_health "$container_name")
        local endpoint_status="unchecked"
        
        # Check endpoint if available (skip for DB)
        if [ "$service" != "db" ] && [ -n "$endpoint" ]; then
            if check_service_endpoint "$service" "$endpoint"; then
                endpoint_status="reachable"
            else
                endpoint_status="unreachable"
            fi
        elif [ "$service" = "db" ]; then
            # Special check for database
            if docker exec "$container_name" pg_isready -U postgres >/dev/null 2>&1; then
                endpoint_status="reachable"
            else
                endpoint_status="unreachable"
            fi
        fi
        
        # Determine overall status
        if [ "$health_status" = "healthy" ] || ([ "$health_status" = "none" ] && [ "$endpoint_status" = "reachable" ]); then
            printf "${GREEN}✅ Healthy${NC}\n"
        elif [ "$health_status" = "unhealthy" ] || [ "$endpoint_status" = "unreachable" ]; then
            printf "${RED}⚠️  Unhealthy${NC}\n"
            unhealthy_count=$((unhealthy_count + 1))
            [ "$is_core" = "true" ] && core_unhealthy=$((core_unhealthy + 1))
            
            if [ "$verbose" = "true" ]; then
                echo "  ├─ Container Status: Running"
                echo "  ├─ Health Check: $health_status"
                echo "  ├─ Endpoint ($endpoint): $endpoint_status"
                
                # Get recent errors
                local errors=$(get_container_errors "$container_name" 10)
                if [ -n "$errors" ]; then
                    echo "  └─ Recent errors:"
                    echo "$errors" | sed 's/^/     /'
                else
                    echo "  └─ No recent errors in logs"
                fi
            fi
        else
            printf "${YELLOW}⏳ Starting${NC}\n"
            if [ "$verbose" = "true" ]; then
                echo "  └─ Health: $health_status, Endpoint: $endpoint_status"
            fi
        fi
    done
    
    # Resource usage section
    echo ""
    echo "📊 Resource Usage:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    # Get resource stats for running containers
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | grep -E "(NAME|sting-ce-)" || echo "Unable to fetch resource stats"
    
    # Network status
    if [ "$verbose" = "true" ]; then
        echo ""
        echo "🌐 Network Status:"
        echo "─────────────────────────────────────────────────────────────────────────────"
        
        # Check if sting_local network exists
        if docker network inspect sting_local >/dev/null 2>&1; then
            echo "✅ Docker network 'sting_local' exists"
            
            # Count connected containers
            local connected_count=$(docker network inspect sting_local 2>/dev/null | jq -r '.[0].Containers | length // 0')
            echo "   Connected containers: $connected_count"
        else
            echo "❌ Docker network 'sting_local' not found"
        fi
    fi
    
    # Overall health summary
    echo ""
    echo "📋 Summary:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    
    if [ $unhealthy_count -eq 0 ]; then
        log_message "✅ All services are healthy!" "SUCCESS"
    else
        if [ $core_unhealthy -gt 0 ]; then
            log_message "❌ $core_unhealthy core service(s) need attention" "ERROR"
        fi
        if [ $((unhealthy_count - core_unhealthy)) -gt 0 ]; then
            log_message "⚠️  $((unhealthy_count - core_unhealthy)) auxiliary service(s) need attention" "WARNING"
        fi
        
        echo ""
        echo "🔧 Quick fixes:"
        echo "  • Restart all services: msting restart"
        echo "  • Restart specific service: msting restart <service>"
        echo "  • View service logs: docker logs sting-ce-<service>"
        echo "  • Run diagnostics: msting debug"
    fi
    
    # Check for Ollama (check configured endpoint from config.yml)
    echo ""
    echo "🤖 AI Services:"
    echo "─────────────────────────────────────────────────────────────────────────────"

    # Try to read Ollama endpoint from config.yml
    local ollama_endpoint="http://localhost:11434"
    if [ -f "${INSTALL_DIR}/conf/config.yml" ]; then
        local config_endpoint=$(grep -A5 "^llm_service:" "${INSTALL_DIR}/conf/config.yml" | grep "endpoint:" | head -1 | sed 's/.*endpoint: *"\([^"]*\)".*/\1/' | sed "s/.*endpoint: *'\([^']*\)'.*/\1/" | sed 's/.*endpoint: *\([^ ]*\).*/\1/')
        if [ -n "$config_endpoint" ]; then
            ollama_endpoint="$config_endpoint"
        fi
    fi

    # Check the configured Ollama endpoint
    if curl -sf "${ollama_endpoint}/v1/models" >/dev/null 2>&1; then
        echo "✅ Ollama is accessible at ${ollama_endpoint}"
        if [ "$verbose" = "true" ] && command -v ollama >/dev/null 2>&1; then
            local models=$(ollama list 2>/dev/null | tail -n +2 | wc -l)
            echo "   Available models: $models"
        fi
    else
        echo "⚠️  Ollama endpoint not accessible: ${ollama_endpoint}"
        if [ "$ollama_endpoint" != "http://localhost:11434" ]; then
            echo "   (External Ollama configured - verify network connectivity)"
        else
            echo "   Start local Ollama with: ollama serve"
        fi
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return $unhealthy_count
}

# Export the function
export -f show_enhanced_status
export -f get_container_health
export -f get_container_errors
export -f check_service_endpoint