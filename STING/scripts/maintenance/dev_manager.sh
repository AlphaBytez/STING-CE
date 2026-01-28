#!/bin/bash

# STING Development Manager
# Handles development workflow with hot reloading and bidirectional sync

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')]${NC} $*"
}

success() {
    echo -e "${GREEN}[+] $*${NC}"
}

warning() {
    echo -e "${YELLOW}[!]  $*${NC}"
}

error() {
    echo -e "${RED}[-] $*${NC}"
}

info() {
    echo -e "${BLUE}[*]  $*${NC}"
}

# Check if we're in the right directory
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        error "Not in STING project root! Expected docker-compose.yml"
        exit 1
    fi
    
    if [[ ! -d "$INSTALL_DIR" ]]; then
        error "STING not installed at $INSTALL_DIR"
        error "Run: sudo ./manage_sting.sh install first"
        exit 1
    fi
}

# Show help
show_help() {
    cat << EOF
${CYAN}STING Development Manager${NC}

${YELLOW}Commands:${NC}
  ${GREEN}msting dev start${NC}     - Start development environment with hot reload
  ${GREEN}msting dev stop${NC}      - Stop development environment
  ${GREEN}msting dev sync${NC}      - Sync project changes to install dir
  ${GREEN}msting dev sync-back${NC} - Sync install dir changes back to project
  ${GREEN}msting dev status${NC}    - Show development environment status
  ${GREEN}msting dev logs${NC}      - Show development logs
  ${GREEN}msting dev build${NC}     - Build and update specific service
  ${GREEN}msting dev reset${NC}     - Reset to production mode

${YELLOW}Development Features:${NC}
  • Hot reload for frontend (React dev server)
  • Live reload for backend (Flask debug mode)
  • Direct file mounting (no container rebuilds)
  • Bidirectional sync between project and install dirs
  • Service-specific rebuilds

${YELLOW}Examples:${NC}
  msting dev start              # Start dev environment
  msting dev build frontend     # Rebuild only frontend
  msting dev sync-back          # Get changes from install dir
  msting dev logs app           # Show app service logs
EOF
}

# Check if development mode is active
is_dev_mode() {
    [[ -f "$INSTALL_DIR/.dev_mode" ]]
}

# Create development docker-compose override
create_dev_override() {
    log "Creating development docker-compose override..."
    
    cat > "$INSTALL_DIR/docker-compose.override.yml" << 'EOF'
version: '3.8'

services:
  # Backend development with live reload
  app:
    volumes:
      # Mount source code directly for live editing
      - ${PROJECT_ROOT}/app:/app/app
      - ${PROJECT_ROOT}/lib:/app/lib
      - ${PROJECT_ROOT}/conf:/app/conf
      - ${PROJECT_ROOT}/scripts:/app/scripts
      # Keep persistent data volumes
      - ${INSTALL_DIR}/certs:/app/certs:ro
      - sting_logs:/var/log/sting
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
      - PYTHONPATH=/app
      - PROJECT_ROOT=${PROJECT_ROOT}
    ports:
      - "5051:5050"  # Extra port for dev access
    command: >
      sh -c "
        echo '🔥 Starting Flask in development mode...' &&
        python -m flask run --host=0.0.0.0 --port=5050 --debug --reload
      "

  # Frontend development with hot reload
  frontend:
    volumes:
      # Mount source for hot reload
      - ${PROJECT_ROOT}/frontend/src:/app/src
      - ${PROJECT_ROOT}/frontend/public:/app/public
      - ${PROJECT_ROOT}/frontend/package.json:/app/package.json
      - ${PROJECT_ROOT}/frontend/package-lock.json:/app/package-lock.json
      # Keep nginx config for proxying
      - ${INSTALL_DIR}/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    environment:
      - CHOKIDAR_USEPOLLING=true
      - GENERATE_SOURCEMAP=true
      - BROWSER=none
      - PORT=3000
    ports:
      - "3000:3000"  # React dev server
    command: >
      sh -c "
        echo '⚡ Starting React development server...' &&
        npm start
      "
    stdin_open: true
    tty: true

  # Kratos with development settings
  kratos:
    environment:
      - DEV_MODE=true
      - LOG_LEVEL=debug
    volumes:
      # Mount config files for live editing
      - ${PROJECT_ROOT}/kratos:/etc/config/kratos

  # Redis with development persistence
  redis:
    volumes:
      - ${INSTALL_DIR}/redis-data:/data
    command: redis-server --appendonly yes --appendfsync everysec

volumes:
  sting_logs:
    external: true
EOF

    # Set PROJECT_ROOT environment variable for docker-compose
    echo "PROJECT_ROOT=$PROJECT_ROOT" > "$INSTALL_DIR/.env"
    echo "INSTALL_DIR=$INSTALL_DIR" >> "$INSTALL_DIR/.env"
    
    success "Development override created"
}

# Start development environment
start_dev() {
    check_project_root
    
    if is_dev_mode; then
        warning "Development mode already active"
        info "Run 'msting dev stop' first to restart"
        return 0
    fi
    
    log "Starting STING development environment..."
    
    # Create development override
    create_dev_override
    
    # Stop production services
    cd "$INSTALL_DIR"
    docker-compose down
    
    # Start development services
    log "Starting services with development configuration..."
    COMPOSE_FILE="docker-compose.yml:docker-compose.override.yml" \
        docker-compose up -d
    
    # Mark as dev mode
    touch "$INSTALL_DIR/.dev_mode"
    echo "$(date)" > "$INSTALL_DIR/.dev_mode"
    
    success "Development environment started!"
    echo ""
    info "🔥 Services running in development mode:"
    echo "   • Frontend (hot reload):  http://localhost:3000"
    echo "   • Backend (debug):        http://localhost:5051"  
    echo "   • Production proxy:       https://localhost:8443"
    echo "   • Grafana:               http://localhost:3001"
    echo ""
    info "📝 Edit files in project directory for instant updates"
    info " Use 'msting dev sync-back' to commit changes"
}

# Stop development environment
stop_dev() {
    if ! is_dev_mode; then
        warning "Development mode not active"
        return 0
    fi
    
    log "Stopping development environment..."
    
    cd "$INSTALL_DIR"
    docker-compose down
    
    # Remove development files
    rm -f "$INSTALL_DIR/docker-compose.override.yml"
    rm -f "$INSTALL_DIR/.env"
    rm -f "$INSTALL_DIR/.dev_mode"
    
    # Restart in production mode
    docker-compose up -d
    
    success "Switched back to production mode"
}

# Sync project to install directory
sync_to_install() {
    check_project_root
    
    log "Syncing project directory to install directory..."
    
    # Create backup
    backup_dir="$INSTALL_DIR/.backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Sync specific directories (avoid overwriting data)
    rsync -av --progress \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='docker-compose.override.yml' \
        "$PROJECT_ROOT/" "$INSTALL_DIR/"
    
    success "Sync to install directory complete"
}

# Sync install directory back to project
sync_back() {
    check_project_root
    
    warning "This will overwrite files in your project directory!"
    echo -n "Continue? [y/N]: "
    read -r response
    
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Sync cancelled"
        return 0
    fi
    
    log "Syncing install directory back to project..."
    
    # Create backup of project
    backup_dir="$PROJECT_ROOT/.backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r "$PROJECT_ROOT"/{app,frontend,lib,conf,kratos,scripts} "$backup_dir/" 2>/dev/null || true
    
    # Sync back (careful to avoid system files)
    rsync -av --progress \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='docker-compose.override.yml' \
        --exclude='.dev_mode' \
        --exclude='.backups' \
        --exclude='certs' \
        --exclude='redis-data' \
        --exclude='postgres-data' \
        "$INSTALL_DIR/" "$PROJECT_ROOT/"
    
    success "Reverse sync complete"
    info "Backup saved to: $backup_dir"
}

# Show development status
show_status() {
    echo ""
    echo "${CYAN}STING Development Status${NC}"
    echo "========================"
    
    if is_dev_mode; then
        success "Development mode: ACTIVE"
        echo "Started: $(cat "$INSTALL_DIR/.dev_mode")"
    else
        info "Development mode: INACTIVE"
    fi
    
    echo ""
    echo "${YELLOW}Service Status:${NC}"
    cd "$INSTALL_DIR"
    docker-compose ps
    
    echo ""
    echo "${YELLOW}Development Ports:${NC}"
    if is_dev_mode; then
        echo "  • Frontend Dev Server:   http://localhost:3000"
        echo "  • Backend Debug:         http://localhost:5051"
    fi
    echo "  • Production Proxy:      https://localhost:8443"
    echo "  • Grafana:              http://localhost:3001"
}

# Show logs for specific service
show_logs() {
    local service="$1"
    cd "$INSTALL_DIR"
    
    if [[ -n "$service" ]]; then
        docker-compose logs -f --tail=100 "$service"
    else
        docker-compose logs -f --tail=50
    fi
}

# Build specific service
build_service() {
    local service="$1"
    
    if [[ -z "$service" ]]; then
        error "Service name required. Examples: frontend, app"
        return 1
    fi
    
    case "$service" in
        frontend)
            log "Building frontend..."
            cd "$PROJECT_ROOT/frontend"
            npm run build
            
            # Sync built files to install
            log "Syncing built frontend to install directory..."
            rsync -av build/ "$INSTALL_DIR/frontend/build/"
            
            # Restart frontend service
            cd "$INSTALL_DIR"
            docker-compose restart frontend
            ;;
            
        app)
            log "Restarting app service..."
            cd "$INSTALL_DIR"
            docker-compose restart app
            ;;
            
        *)
            log "Restarting service: $service"
            cd "$INSTALL_DIR"
            docker-compose restart "$service"
            ;;
    esac
    
    success "Build complete for: $service"
}

# Reset to production mode
reset_prod() {
    log "Resetting to production mode..."
    
    stop_dev
    sync_to_install
    
    success "Reset to production mode complete"
}

# Main command handler
case "${1:-help}" in
    start)
        start_dev
        ;;
    stop)
        stop_dev
        ;;
    sync)
        sync_to_install
        ;;
    sync-back)
        sync_back
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    build)
        build_service "$2"
        ;;
    reset)
        reset_prod
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac