#!/bin/bash
# STING Service Recovery Tool
# Interactive tool to diagnose and recover failed services

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Source the enhanced service startup functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/service_startup_resilience.sh"

# Function to display service status
display_service_status() {
    echo -e "${BLUE}=== STING Service Status ===${NC}"
    echo
    
    local all_services=$(docker compose ps --services 2>/dev/null || docker-compose ps --services)
    
    for service in $all_services; do
        local container_name="sting-ce-$service"
        local state=$(docker inspect "$container_name" --format='{{.State.Status}}' 2>/dev/null || echo "missing")
        local health=$(docker inspect "$container_name" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
        
        case "$state" in
            "running")
                if [[ "$health" == "healthy" ]] || check_service_health "$service" 1 >/dev/null 2>&1; then
                    echo -e "  ${GREEN}[+]${NC} $service: ${GREEN}running (healthy)${NC}"
                else
                    echo -e "  ${YELLOW}[!]${NC} $service: ${YELLOW}running (unhealthy)${NC}"
                fi
                ;;
            "created")
                echo -e "  ${YELLOW}○${NC} $service: ${YELLOW}created (not started)${NC}"
                ;;
            "exited")
                local exit_code=$(docker inspect "$container_name" --format='{{.State.ExitCode}}' 2>/dev/null || echo "?")
                echo -e "  ${RED}[-]${NC} $service: ${RED}exited (code: $exit_code)${NC}"
                ;;
            "missing")
                echo -e "  ${RED}[-]${NC} $service: ${RED}missing${NC}"
                ;;
            *)
                echo -e "  ${YELLOW}?${NC} $service: ${YELLOW}$state${NC}"
                ;;
        esac
    done
    echo
}

# Function to show recent logs for a service
show_service_logs() {
    local service=$1
    local lines=${2:-20}
    
    echo -e "${BLUE}=== Recent logs for $service ===${NC}"
    docker logs "sting-ce-$service" --tail "$lines" 2>&1 || echo "Unable to fetch logs"
    echo
}

# Function to check disk space
check_disk_space() {
    echo -e "${BLUE}=== Disk Space Check ===${NC}"
    df -h | grep -E '^/|Filesystem' | while read line; do
        if [[ "$line" == "Filesystem"* ]]; then
            echo -e "${CYAN}$line${NC}"
        else
            usage=$(echo "$line" | awk '{print $5}' | sed 's/%//')
            if [[ "$usage" -gt 90 ]]; then
                echo -e "${RED}$line${NC}"
            elif [[ "$usage" -gt 75 ]]; then
                echo -e "${YELLOW}$line${NC}"
            else
                echo "$line"
            fi
        fi
    done
    echo
}

# Function to check Docker daemon
check_docker_daemon() {
    echo -e "${BLUE}=== Docker Daemon Check ===${NC}"
    
    if docker info >/dev/null 2>&1; then
        echo -e "  ${GREEN}[+] Docker daemon is running${NC}"
        
        # Check Docker disk usage
        local docker_usage=$(docker system df --format "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}")
        echo
        echo "  Docker disk usage:"
        echo "$docker_usage" | sed 's/^/    /'
    else
        echo -e "  ${RED}[-] Docker daemon is not responding${NC}"
        return 1
    fi
    echo
}

# Function to attempt automatic recovery
automatic_recovery() {
    echo -e "${BLUE}=== Attempting Automatic Recovery ===${NC}"
    echo
    
    # First, try to start any services in "created" state
    local created_services=$(docker ps -a --filter "name=sting-ce-" --filter "status=created" --format "{{.Names}}" | sed 's/sting-ce-//')
    
    if [[ -n "$created_services" ]]; then
        echo -e "${YELLOW}Found services in 'created' state:${NC}"
        for service in $created_services; do
            echo "  - $service"
        done
        echo
        
        # Use the enhanced startup function
        ensure_all_services_started_enhanced
    else
        echo "No services found in 'created' state."
        
        # Check for exited services
        local exited_services=$(docker ps -a --filter "name=sting-ce-" --filter "status=exited" --format "{{.Names}}" | sed 's/sting-ce-//')
        
        if [[ -n "$exited_services" ]]; then
            echo -e "${YELLOW}Found services in 'exited' state:${NC}"
            for service in $exited_services; do
                echo "  - $service"
                start_service_with_retry "$service"
            done
        else
            echo -e "${GREEN}All services appear to be running.${NC}"
        fi
    fi
}

# Function to recreate a specific service
recreate_service() {
    local service=$1
    
    echo -e "${BLUE}Recreating $service...${NC}"
    
    # Stop and remove the container
    docker stop "sting-ce-$service" 2>/dev/null || true
    docker rm "sting-ce-$service" 2>/dev/null || true
    
    # Recreate the service
    docker compose up -d "$service" --force-recreate
    
    # Wait for it to start
    sleep 3
    
    # Check health
    if check_service_health "$service"; then
        echo -e "${GREEN}[+] $service recreated successfully${NC}"
        return 0
    else
        echo -e "${RED}[-] $service recreated but not healthy${NC}"
        return 1
    fi
}

# Interactive menu
show_menu() {
    echo -e "${CYAN}=== STING Service Recovery Tool ===${NC}"
    echo
    echo "1) Show service status"
    echo "2) Check system resources"
    echo "3) Automatic recovery attempt"
    echo "4) Show service logs"
    echo "5) Recreate specific service"
    echo "6) Check port conflicts"
    echo "7) Full system restart"
    echo "8) Exit"
    echo
}

# Main interactive loop
main() {
    clear
    
    # Initial status display
    display_service_status
    
    while true; do
        show_menu
        read -p "Select option (1-8): " choice
        
        case $choice in
            1)
                clear
                display_service_status
                ;;
            2)
                clear
                check_disk_space
                check_docker_daemon
                check_port_conflicts
                ;;
            3)
                clear
                automatic_recovery
                echo
                display_service_status
                ;;
            4)
                read -p "Enter service name (e.g., app, frontend, chatbot): " service
                read -p "Number of lines to show (default 20): " lines
                lines=${lines:-20}
                clear
                show_service_logs "$service" "$lines"
                ;;
            5)
                read -p "Enter service name to recreate: " service
                clear
                recreate_service "$service"
                ;;
            6)
                clear
                check_port_conflicts
                ;;
            7)
                echo -e "${YELLOW}This will restart all STING services.${NC}"
                read -p "Are you sure? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    clear
                    echo -e "${BLUE}Restarting all services...${NC}"
                    docker compose down
                    docker compose up -d
                    sleep 5
                    ensure_all_services_started_enhanced
                fi
                ;;
            8)
                echo -e "${GREEN}Exiting recovery tool.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Please try again.${NC}"
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
        clear
    done
}

# Check if running with required permissions
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to Docker daemon.${NC}"
    echo "Please ensure Docker is running and you have the necessary permissions."
    exit 1
fi

# Change to STING directory
cd "$SCRIPT_DIR/.."

# Run main function
main