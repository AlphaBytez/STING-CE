#!/bin/bash
#
# STING-CE Auto-Update Script
# Pulls latest code from git and syncs to running installation
#
# Usage: ./auto-update.sh [--cron] [--force]
#
# Options:
#   --cron    Run in cron mode (less output, no interactive prompts)
#   --force   Force update even if git pull fails
#
# Set up cron for automatic updates:
#   crontab -e
#   Add: 0 */2 * * * /opt/sting-ce-source/STING/scripts/auto-update.sh --cron  # Every 2 hours
#

set -e

# Configuration
SOURCE_DIR="${SOURCE_DIR:-/opt/sting-ce-source}"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
LOG_FILE="/var/log/sting-auto-update.log"

# Colors for output (disabled in cron mode)
if [ "$1" = "--cron" ]; then
    NC='' BOLD='' GREEN='' YELLOW='' RED=''
else
    NC='\033[0m'
    BOLD='\033[1m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
fi

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Always write to log file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    # Console output with colors
    case "$level" in
        ERROR)
            echo -e "${RED}[$level]${NC} $message" >&2
            ;;
        WARN)
            echo -e "${YELLOW}[$level]${NC} $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[$level]${NC} $message"
            ;;
        *)
            echo "[$level] $message"
            ;;
    esac
}

log_info() {
    log "INFO" "$1"
}

log_success() {
    log "SUCCESS" "$1"
}

log_warn() {
    log "WARN" "$1"
}

log_error() {
    log "ERROR" "$1"
}

# Check prerequisites
check_prerequisites() {
    if [ ! -d "$SOURCE_DIR" ]; then
        log_error "Source directory not found: $SOURCE_DIR"
        log_info "Please set SOURCE_DIR or clone STING-CE to $SOURCE_DIR"
        return 1
    fi

    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "Install directory not found: $INSTALL_DIR"
        log_info "Please set INSTALL_DIR to your STING installation path"
        return 1
    fi

    if ! command -v git &>/dev/null; then
        log_error "git is not installed"
        return 1
    fi

    return 0
}

# Pull latest changes from git
update_git() {
    log_info "Pulling latest changes from git..."

    cd "$SOURCE_DIR"

    # Check if it's a git repo
    if [ ! -d ".git" ]; then
        log_error "$SOURCE_DIR is not a git repository"
        return 1
    fi

    # Fetch latest changes
    if ! git fetch origin 2>&1; then
        log_warn "Git fetch failed, trying anyway..."
    fi

    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

    # Pull changes
    if git pull origin "$current_branch" 2>&1 | tee -a "$LOG_FILE"; then
        local pull_output=$(git pull origin "$current_branch" 2>&1)
        if echo "$pull_output" | grep -q "Already up to date"; then
            log_info "Already up to date"
            return 2  # Special return code for "no updates"
        else
            log_success "Git pull successful"
            return 0
        fi
    else
        log_error "Git pull failed"
        if [ "$1" = "--force" ]; then
            log_warn "Force mode enabled, continuing anyway..."
            return 0
        fi
        return 1
    fi
}

# Sync code to installation
sync_to_installation() {
    local service="${1:-app}"

    log_info "Syncing $service to installation..."

    cd "$SOURCE_DIR/STING"

    # Use msting update with sync-only for fast updates
    if PROJECT_DIR="$SOURCE_DIR/STING" ./manage_sting.sh update "$service" --sync-only 2>&1; then
        log_success "$service synced successfully"
        return 0
    else
        log_error "Failed to sync $service"
        return 1
    fi
}

# Restart services if needed
restart_services() {
    log_info "Restarting services..."

    cd "$INSTALL_DIR"

    if ./manage_sting.sh restart app 2>&1; then
        log_success "Services restarted"
        return 0
    else
        log_error "Failed to restart services"
        return 1
    fi
}

# Check service health
check_health() {
    local service="${1:-app}"

    log_info "Checking $service health..."

    cd "$INSTALL_DIR"

    if ./manage_sting.sh status 2>&1 | grep -q "healthy\|running\|UP"; then
        log_success "$service is healthy"
        return 0
    else
        log_warn "$service may have issues - check logs"
        return 1
    fi
}

# Main update function
main() {
    local force_update=false
    local cron_mode=false
    local services=("app")

    # Parse arguments
    for arg in "$@"; do
        case "$arg" in
            --force)
                force_update=true
                ;;
            --cron)
                cron_mode=true
                ;;
            --help|-h)
                echo "Usage: $0 [--cron] [--force] [service]"
                echo ""
                echo "Options:"
                echo "  --cron     Run in cron mode (minimal output)"
                echo "  --force    Continue even if git pull fails"
                echo "  --help     Show this help message"
                echo ""
                echo "Environment variables:"
                echo "  SOURCE_DIR   Path to STING-CE source (default: /opt/sting-ce-source)"
                echo "  INSTALL_DIR  Path to STING installation (default: /opt/sting-ce)"
                exit 0
                ;;
            *)
                if [ -n "$arg" ] && [ "${arg:0:1}" != "-" ]; then
                    services=("$arg")
                fi
                ;;
        esac
    done

    # Create log directory if needed
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

    log_info "=== STING-CE Auto-Update Started ==="
    log_info "Source: $SOURCE_DIR"
    log_info "Install: $INSTALL_DIR"

    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi

    # Pull from git
    local update_result=0
    if ! update_git "$force_update"; then
        log_error "Git update failed"
        exit 1
    elif [ $? -eq 2 ]; then
        log_info "No updates available"
        exit 0
    fi

    # Sync each service
    local failed=false
    for service in "${services[@]}"; do
        if ! sync_to_installation "$service"; then
            failed=true
        fi
    done

    if [ "$failed" = true ]; then
        log_error "Some services failed to sync"
        exit 1
    fi

    # Check health
    check_health

    log_success "=== Auto-Update Complete ==="
    exit 0
}

# Run main
main "$@"
