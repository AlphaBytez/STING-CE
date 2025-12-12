#!/bin/bash
# STING Management Script - Debug Module
# Provides comprehensive debugging for STING services

# Source required dependencies
if [[ -z "$SOURCE_DIR" ]]; then
    echo "ERROR: SOURCE_DIR not set. This module must be sourced from manage_sting.sh" >&2
    return 1
fi

# Source logging module
source "$SOURCE_DIR/lib/logging.sh" || {
    echo "ERROR: Failed to load logging module" >&2
    return 1
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Function to display debug header
show_debug_header() {
    echo
    echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                         STING Debug & Diagnostics Tool                        ║"
    echo "║                                                                               ║"
    echo "║  Comprehensive system analysis for troubleshooting STING services            ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
    echo
}

# Function to check service status
check_service_status() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Service Status Check]"
        echo "====================="
    else
        echo -e "${BLUE}${BOLD}[1/8] Service Status Check${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    local services=(
        "db:Database:5432"
        "vault:Vault:8200"
        "kratos:Authentication:4433,4434"
        "app:Backend API:5050"
        "frontend:Web Interface:8443"
        "chatbot:Bee Chatbot:8081"
        "external-ai:External AI:8091"
        "knowledge:Knowledge Service:8090"
        "chroma:Vector Database:8000"
        "messaging:Messaging Service:8889"
        "redis:Cache:6379"
        "mailpit:Email Testing:1025,8025"
        "llm-gateway-proxy:LLM Gateway:8085"
    )
    
    local running=0
    local total=${#services[@]}
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service name ports <<< "$service_info"
        container_name="sting-ce-${service}"
        
        if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            status=$(docker ps --format "table {{.Status}}" --filter "name=${container_name}" | tail -1)
            if [[ "$format" == "plain" ]]; then
                echo "[+] $name ($service): Running - $status"
            else
                echo -e "  [+] ${GREEN}$name${NC} ($service): Running - $status"
            fi
            ((running++))
        else
            if [[ "$format" == "plain" ]]; then
                echo "[-] $name ($service): Not Running"
            else
                echo -e "  [-] ${RED}$name${NC} ($service): Not Running"
            fi
        fi
    done
    
    echo
    if [[ "$format" == "plain" ]]; then
        echo "Summary: $running/$total services running"
    else
        echo -e "  ${BOLD}Summary:${NC} $running/$total services running"
    fi
    echo
}

# Function to check authentication system
check_auth_system() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Authentication System Check]"
        echo "============================"
    else
        echo -e "${BLUE}${BOLD}[2/8] Authentication System (Kratos)${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    # Check Kratos health
    local admin_health=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:4434/admin/health/ready 2>/dev/null)
    local public_health=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost:4433/health/ready 2>/dev/null)
    
    if [[ "$admin_health" == "200" ]]; then
        echo -e "  [+] Kratos Admin API: ${GREEN}Healthy${NC} (https://localhost:4434)"
    else
        echo -e "  [-] Kratos Admin API: ${RED}Unhealthy${NC} (HTTP $admin_health)"
    fi
    
    if [[ "$public_health" == "200" ]]; then
        echo -e "  [+] Kratos Public API: ${GREEN}Healthy${NC} (https://localhost:4433)"
    else
        echo -e "  [-] Kratos Public API: ${RED}Unhealthy${NC} (HTTP $public_health)"
    fi
    
    # Get Kratos version
    local version=$(curl -k -s https://localhost:4434/admin/version 2>/dev/null | jq -r '.version // "Unknown"')
    echo -e "   Version: ${YELLOW}$version${NC}"
    
    # Check authentication methods
    echo -e "\n  ${BOLD}Authentication Methods:${NC}"
    if docker exec sting-ce-kratos cat /etc/config/kratos/kratos.yml 2>/dev/null | grep -q "password:.*enabled: true"; then
        echo -e "    [+] Password authentication: ${GREEN}Enabled${NC}"
    else
        echo -e "    [-] Password authentication: ${RED}Disabled${NC}"
    fi
    
    if docker exec sting-ce-kratos cat /etc/config/kratos/kratos.yml 2>/dev/null | grep -q "webauthn:.*enabled: true"; then
        echo -e "    [+] WebAuthn/Passkeys: ${GREEN}Enabled${NC}"
    else
        echo -e "    [-] WebAuthn/Passkeys: ${RED}Disabled${NC}"
    fi
    
    # Count identities
    local identity_count=$(docker exec sting-ce-db psql -U postgres -d sting_app -t -c "SELECT COUNT(*) FROM identities;" 2>/dev/null | tr -d ' ' || echo "0")
    echo -e "\n  👥 Registered Users: ${YELLOW}${identity_count}${NC}"
    echo
}

# Function to check database
check_database() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Database Check]"
        echo "==============="
    else
        echo -e "${BLUE}${BOLD}[3/8] Database Status${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "  [+] PostgreSQL: ${GREEN}Ready${NC}"
        
        # Get database size
        local db_size=$(docker exec sting-ce-db psql -U postgres -t -c "SELECT pg_size_pretty(pg_database_size('sting_app'));" 2>/dev/null | tr -d ' ')
        echo -e "  💾 Database Size: ${YELLOW}${db_size:-Unknown}${NC}"
        
        # Check tables
        local table_count=$(docker exec sting-ce-db psql -U postgres -d sting_app -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
        echo -e "  📊 Tables: ${YELLOW}${table_count:-0}${NC}"
        
        # Recent activity
        echo -e "\n  ${BOLD}Recent Database Activity:${NC}"
        docker exec sting-ce-db psql -U postgres -d sting_app -c "
            SELECT pid, usename, application_name, state, query_start 
            FROM pg_stat_activity 
            WHERE datname = 'sting_app' 
            ORDER BY query_start DESC 
            LIMIT 5;" 2>/dev/null | head -15 || echo "    Could not query activity"
    else
        echo -e "  [-] PostgreSQL: ${RED}Not Ready${NC}"
    fi
    echo
}

# Function to check network connectivity
check_network() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Network Connectivity Check]"
        echo "==========================="
    else
        echo -e "${BLUE}${BOLD}[4/8] Network Connectivity${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    # Check Docker network
    if docker network ls | grep -q "sting_local"; then
        echo -e "  [+] Docker Network (sting_local): ${GREEN}Exists${NC}"
        
        # Count containers on network
        local container_count=$(docker network inspect sting_local -f '{{len .Containers}}' 2>/dev/null || echo "0")
        echo -e "  🔗 Containers on network: ${YELLOW}$container_count${NC}"
    else
        echo -e "  [-] Docker Network (sting_local): ${RED}Missing${NC}"
    fi
    
    # Check key endpoints
    echo -e "\n  ${BOLD}Service Endpoints:${NC}"
    local endpoints=(
        "https://localhost:8443:Frontend"
        "https://localhost:5050:Backend API"
        "https://localhost:4433:Kratos Public"
        "http://localhost:8025:Mailpit UI"
        "http://localhost:8081:Chatbot"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r proto _ _ port name <<< "$endpoint_info"
        url="${proto}://localhost:${port}"
        
        if curl -k -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "^[23]"; then
            echo -e "    [+] $name: ${GREEN}Accessible${NC} at $url"
        else
            echo -e "    [-] $name: ${RED}Not Accessible${NC} at $url"
        fi
    done
    echo
}

# Function to check SSL certificates
check_ssl_certs() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[SSL Certificate Check]"
        echo "====================="
    else
        echo -e "${BLUE}${BOLD}[5/8] SSL Certificates${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    # Check certificate files
    local cert_dir="${INSTALL_DIR}/certs"
    if [[ -d "$cert_dir" ]]; then
        echo -e "  📁 Certificate Directory: ${GREEN}Found${NC}"
        
        if [[ -f "$cert_dir/server.crt" ]] && [[ -f "$cert_dir/server.key" ]]; then
            echo -e "  [+] SSL Certificate Files: ${GREEN}Present${NC}"
            
            # Check certificate validity
            if openssl x509 -in "$cert_dir/server.crt" -noout -checkend 0 2>/dev/null; then
                echo -e "  [+] Certificate Validity: ${GREEN}Valid${NC}"
                
                # Get expiry date
                local expiry=$(openssl x509 -in "$cert_dir/server.crt" -noout -enddate 2>/dev/null | cut -d= -f2)
                echo -e "  📅 Expires: ${YELLOW}$expiry${NC}"
            else
                echo -e "  [-] Certificate Validity: ${RED}Expired${NC}"
            fi
        else
            echo -e "  [-] SSL Certificate Files: ${RED}Missing${NC}"
        fi
    else
        echo -e "  [-] Certificate Directory: ${RED}Not Found${NC}"
    fi
    echo
}

# Function to check resource usage
check_resources() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Resource Usage]"
        echo "==============="
    else
        echo -e "${BLUE}${BOLD}[6/8] Resource Usage${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    # Disk usage
    local disk_usage=$(df -h "$INSTALL_DIR" 2>/dev/null | awk 'NR==2 {print $5}' | tr -d '%')
    local disk_free=$(df -h "$INSTALL_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    
    if [[ -n "$disk_usage" ]]; then
        if [[ $disk_usage -lt 80 ]]; then
            echo -e "  [+] Disk Usage: ${GREEN}${disk_usage}%${NC} (${disk_free} free)"
        elif [[ $disk_usage -lt 90 ]]; then
            echo -e "  [!]  Disk Usage: ${YELLOW}${disk_usage}%${NC} (${disk_free} free)"
        else
            echo -e "  [-] Disk Usage: ${RED}${disk_usage}%${NC} (${disk_free} free)"
        fi
    fi
    
    # Docker resource usage
    echo -e "\n  ${BOLD}Container Resources:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep "sting-ce" | while read line; do
        echo "    $line"
    done
    echo
}

# Function to check recent logs
check_recent_logs() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Recent Error Logs]"
        echo "=================="
    else
        echo -e "${BLUE}${BOLD}[7/8] Recent Error Logs${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    # Check key service logs for errors
    local services=("kratos" "app" "frontend")
    
    for service in "${services[@]}"; do
        echo -e "  ${BOLD}$service errors (last 24h):${NC}"
        local error_count=$(docker logs "sting-ce-$service" --since 24h 2>&1 | grep -iE "error|fatal|panic" | wc -l)
        
        if [[ $error_count -eq 0 ]]; then
            echo -e "    [+] No errors found"
        else
            echo -e "    [!]  ${YELLOW}$error_count errors found${NC}"
            echo "    Recent errors:"
            docker logs "sting-ce-$service" --since 24h 2>&1 | grep -iE "error|fatal|panic" | tail -3 | sed 's/^/      /'
        fi
        echo
    done
}

# Function to show quick actions
show_quick_actions() {
    local format="${1:-fancy}"
    
    if [[ "$format" == "plain" ]]; then
        echo "[Quick Actions & Commands]"
        echo "========================"
    else
        echo -e "${BLUE}${BOLD}[8/8] Quick Actions & Commands${NC}"
        echo "════════════════════════════════════════════════════════════════════════"
    fi
    
    echo -e "  ${BOLD}Common Fixes:${NC}"
    echo "    • Restart all services:    msting restart"
    echo "    • View real-time logs:     msting logs -f"
    echo "    • Rebuild frontend:        msting update frontend"
    echo "    • Reset authentication:    docker restart sting-ce-kratos"
    echo
    echo -e "  ${BOLD}Diagnostic Commands:${NC}"
    echo "    • Test authentication:     curl -k https://localhost:4433/health/ready"
    echo "    • Check identities:        curl -k https://localhost:4434/admin/identities | jq"
    echo "    • View Kratos config:      docker exec sting-ce-kratos cat /etc/config/kratos/kratos.yml"
    echo "    • Database console:        docker exec -it sting-ce-db psql -U postgres -d sting_app"
    echo
    echo -e "  ${BOLD}Useful URLs:${NC}"
    echo "    • Frontend:               https://localhost:8443"
    echo "    • Debug Page:             https://localhost:8443/debug/auth"
    echo "    • Mailpit (emails):       http://localhost:8025"
    echo "    • API Documentation:      https://localhost:5050/docs"
    echo
}

# Main debug function
run_debug() {
    local format="${1:-fancy}"
    local specific_check="${2:-all}"
    
    # Clear screen for fancy mode
    if [[ "$format" == "fancy" ]]; then
        clear
    fi
    
    show_debug_header
    
    # Get start time
    local start_time=$(date +%s)
    
    # Run checks based on parameter
    case "$specific_check" in
        all)
            check_service_status "$format"
            check_auth_system "$format"
            check_database "$format"
            check_network "$format"
            check_ssl_certs "$format"
            check_resources "$format"
            check_recent_logs "$format"
            show_quick_actions "$format"
            ;;
        services)
            check_service_status "$format"
            ;;
        auth)
            check_auth_system "$format"
            ;;
        db|database)
            check_database "$format"
            ;;
        network)
            check_network "$format"
            ;;
        ssl|certs)
            check_ssl_certs "$format"
            ;;
        resources)
            check_resources "$format"
            ;;
        logs)
            check_recent_logs "$format"
            ;;
        *)
            echo "Unknown check type: $specific_check"
            echo "Available: all, services, auth, database, network, ssl, resources, logs"
            return 1
            ;;
    esac
    
    # Calculate execution time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo "════════════════════════════════════════════════════════════════════════"
    echo -e "Debug scan completed in ${YELLOW}${duration}s${NC}"
    echo
    
    # Save debug output to file
    local debug_log="${INSTALL_DIR}/logs/debug_$(date +%Y%m%d_%H%M%S).log"
    echo "Debug output saved to: $debug_log"
    
    return 0
}

# Export the main function
export -f run_debug