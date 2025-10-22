#!/bin/bash
# services_status_fix.sh - Additional status functions for services.sh
# This file contains the missing status functionality

# Show comprehensive service status
show_service_status() {
    log_message "STING Services Status" "INFO"
    log_message "=====================" "INFO"
    
    # First check if docker is running
    if ! docker info >/dev/null 2>&1; then
        log_message "Docker is not running or not accessible" "ERROR"
        return 1
    fi
    
    # Check if we're in the right directory
    if [ ! -f "${INSTALL_DIR}/docker-compose.yml" ]; then
        log_message "Docker compose file not found at ${INSTALL_DIR}/docker-compose.yml" "ERROR"
        return 1
    fi
    
    # Change to install directory for docker compose
    cd "$INSTALL_DIR" || {
        log_message "Cannot change to install directory: $INSTALL_DIR" "ERROR"
        return 1
    }
    
    # Load environment variables
    source_service_envs
    
    # Show docker compose status
    log_message "\nDocker Compose Services:" "INFO"
    docker compose ps
    
    # Check individual service health
    log_message "\nService Health Checks:" "INFO"
    log_message "---------------------" "INFO"
    
    # Define services to check
    local core_services=("db" "vault" "kratos" "app" "frontend" "web-server" "report-worker")
    local llm_services=("llm-gateway" "chatbot" "deepseek" "tinyllama" "dialogpt" "llama3" "phi3" "zephyr")
    local support_services=("mailpit" "messaging")
    
    # Check core services
    log_message "\nCore Services:" "INFO"
    for service in "${core_services[@]}"; do
        check_service_status "$service"
    done
    
    # Check LLM services
    log_message "\nLLM Services:" "INFO"
    for service in "${llm_services[@]}"; do
        check_service_status "$service"
    done
    
    # Check support services
    log_message "\nSupport Services:" "INFO"
    for service in "${support_services[@]}"; do
        check_service_status "$service"
    done
    
    # Show port usage
    log_message "\nPort Usage:" "INFO"
    log_message "-----------" "INFO"
    show_port_status
    
    # Show resource usage
    log_message "\nResource Usage:" "INFO"
    log_message "---------------" "INFO"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep "sting" || true
    
    return 0
}

# Check individual service status with health endpoint
check_service_status() {
    local service="$1"
    local status="Down"
    local health="Unknown"
    
    # Check if container is running
    if docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
        status="Running"
        
        # Service-specific health checks
        case "$service" in
            "db")
                if docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            "vault")
                if curl -s http://localhost:8200/v1/sys/health >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            "kratos")
                if curl -k -s https://localhost:4433/health/ready >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            "app")
                if curl -k -s https://localhost:5050/api/auth/health >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            "frontend")
                if curl -k -s https://localhost:8443 >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Starting..."
                fi
                ;;
            "llm-gateway")
                if curl -s http://localhost:8085/health >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            "chatbot")
                if curl -s http://localhost:8081/health >/dev/null 2>&1; then
                    health="Healthy"
                else
                    health="Unhealthy"
                fi
                ;;
            *)
                # For other services, just check if running
                health="No health check"
                ;;
        esac
    fi
    
    # Format output with colors based on status
    if [ "$status" = "Running" ] && [ "$health" = "Healthy" ]; then
        log_message "  ✅ $service: $status ($health)" "SUCCESS"
    elif [ "$status" = "Running" ]; then
        log_message "  ⚠️  $service: $status ($health)" "WARNING"
    else
        log_message "  ❌ $service: $status" "ERROR"
    fi
}

# Show port status
show_port_status() {
    local ports=(
        "8443:Frontend"
        "5050:Backend API"
        "5432:PostgreSQL"
        "8200:Vault"
        "4433:Kratos Public"
        "4434:Kratos Admin"
        "8085:LLM Gateway"
        "8081:Chatbot"
        "4436:MailSlurper SMTP"
        "4437:MailSlurper API"
    )
    
    for port_info in "${ports[@]}"; do
        local port="${port_info%%:*}"
        local service="${port_info#*:}"
        
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            log_message "  ✅ Port $port ($service): In use"
        else
            log_message "  ❌ Port $port ($service): Not in use"
        fi
    done
}

# Quick status summary (one-liner per service)
show_quick_status() {
    log_message "Quick Status Check:" "INFO"
    
    # Just show running/stopped for each service
    docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -v "NAME" | while read -r line; do
        if echo "$line" | grep -q "Up"; then
            echo "  ✅ $line"
        else
            echo "  ❌ $line"
        fi
    done
}