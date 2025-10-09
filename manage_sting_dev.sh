#!/bin/bash

# STING CE Developer Preview Management Script
set -e

echo "STING CE Developer Preview Management"
echo "======================================"

# Default configuration
INSTALL_DIR="${INSTALL_DIR:-$(pwd)}"
COMPOSE_FILE="docker-compose.dev.yml"

# Function to print usage
print_usage() {
    echo "Usage: $0 [start|stop|restart|status|logs|update|build]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart specific service or all services"
    echo "  status    - Check service status"
    echo "  logs      - View logs for a specific service"
    echo "  update    - Update specific service (rebuilds and restarts)"
    echo "  build     - Build all services without starting"
    echo ""
}

# Function to start services
start_services() {
    echo "Starting STING CE Developer Preview services..."

    # Start all services in the correct order
    docker compose -f "$COMPOSE_FILE" up -d

    echo ""
    echo "✅ Services started successfully!"
    echo ""
    echo "Access the services at:"
    echo "  - Backend API: http://localhost:5050"
    echo "  - Knowledge Service: http://localhost:8090"
    echo "  - Chatbot: http://localhost:8888"
    echo "  - External AI: http://localhost:8091"
    echo "  - Kratos Admin: http://localhost:4434"
    echo "  - Kratos Public: http://localhost:4433"
    echo "  - PostgreSQL: localhost:5433"
    echo "  - Redis: localhost:6379"
    echo "  - Chroma: http://localhost:8000"
    echo ""
    echo "Check status with './manage_sting_dev.sh status'"
}

# Function to stop services
stop_services() {
    echo "Stopping STING CE Developer Preview services..."

    docker compose -f "$COMPOSE_FILE" down

    echo "✅ Services stopped."
}

# Function to restart services
restart_service() {
    local service="$1"

    if [ -z "$service" ]; then
        echo "Restarting all services..."
        docker compose -f "$COMPOSE_FILE" restart
    else
        echo "Restarting $service service..."
        docker compose -f "$COMPOSE_FILE" restart "$service"
    fi
}

# Function to check status
check_status() {
    echo "Checking STING CE Developer Preview service status..."
    echo ""

    docker compose -f "$COMPOSE_FILE" ps
}

# Function to view logs
view_logs() {
    local service="$1"

    if [ -z "$service" ]; then
        echo "Viewing logs for all services..."
        docker compose -f "$COMPOSE_FILE" logs --follow
    else
        echo "Viewing logs for $service service..."
        docker compose -f "$COMPOSE_FILE" logs --follow "$service"
    fi
}

# Function to update service (rebuild and restart)
update_service() {
    local service="$1"

    if [ -z "$service" ]; then
        echo "Rebuilding and restarting all services..."
        docker compose -f "$COMPOSE_FILE" build --no-cache
        docker compose -f "$COMPOSE_FILE" up -d
    else
        echo "Rebuilding and restarting $service service..."
        docker compose -f "$COMPOSE_FILE" build --no-cache "$service"
        docker compose -f "$COMPOSE_FILE" up -d "$service"
    fi
}

# Function to build services
build_services() {
    echo "Building STING CE Developer Preview services..."

    docker compose -f "$COMPOSE_FILE" build

    echo "✅ Build complete."
}

# Main command handling
case "${1:-help}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_service "$2"
        ;;
    "status")
        check_status
        ;;
    "logs")
        view_logs "$2"
        ;;
    "update")
        update_service "$2"
        ;;
    "build")
        build_services
        ;;
    "help"|*)
        print_usage
        exit 1
        ;;
esac

echo ""
echo "Done."
