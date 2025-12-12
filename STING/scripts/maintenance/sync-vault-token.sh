#!/bin/bash
# Vault Token Synchronization Helper
# This script ensures all services have the current Vault token
# Use this after upgrades, reinstalls, or when authentication issues occur

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[*]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC}  $1"
}

log_error() {
    echo -e "${RED}[-]${NC} $1"
}

# Check if we're running from the right directory
if [ ! -f "$INSTALL_DIR/docker-compose.yml" ]; then
    log_error "docker-compose.yml not found in $INSTALL_DIR"
    log_info "Please run this script from STING installation directory or set INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

log_info "Starting Vault token synchronization..."
echo ""

# Step 1: Check if Vault is running and get its token
log_info "Step 1: Checking Vault status..."
if ! docker exec sting-ce-vault vault status >/dev/null 2>&1; then
    if docker exec sting-ce-vault vault status 2>&1 | grep -q "Sealed.*true"; then
        log_warning "Vault is sealed. Attempting to unseal..."
        docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh
        sleep 2
    else
        log_error "Vault is not responding. Please ensure Vault container is running."
        exit 1
    fi
fi

VAULT_TOKEN=$(docker exec sting-ce-vault printenv VAULT_TOKEN 2>/dev/null || echo "")
if [ -z "$VAULT_TOKEN" ]; then
    log_error "Could not retrieve Vault token from Vault container"
    exit 1
fi
log_success "Vault is operational (Token: ${VAULT_TOKEN:0:30}...)"
echo ""

# Step 2: Verify token file exists in shared volume
log_info "Step 2: Verifying shared token file..."
TOKEN_FILE_EXISTS=false
if docker exec sting-ce-vault test -f /app/conf/.vault-auto-init.json; then
    TOKEN_FILE_EXISTS=true
    log_success "Token file exists in shared config volume"
elif docker exec sting-ce-vault test -f /vault/persistent/.vault-init.json; then
    log_info "Copying token file to shared volume..."
    docker exec sting-ce-vault sh -c "cp /vault/persistent/.vault-init.json /app/conf/.vault-auto-init.json && chmod 600 /app/conf/.vault-auto-init.json"
    TOKEN_FILE_EXISTS=true
    log_success "Token file copied to shared volume"
else
    log_warning "Token files not found - this may be a fresh installation"
fi
echo ""

# Step 3: Check which services need token updates
log_info "Step 3: Checking service tokens..."
SERVICES_TO_RESTART=()

check_service_token() {
    local service=$1
    local container=$2

    local service_token=$(docker exec "$container" printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
    local vault_token_short="${VAULT_TOKEN:0:30}"

    if [ "$service_token" = "N/A" ]; then
        log_warning "$service: No token found"
        SERVICES_TO_RESTART+=("$service")
    elif [ "$service_token" = "$vault_token_short" ]; then
        log_success "$service: Token is current"
    elif [ "$service_token" = "dev-only-token" ]; then
        log_error "$service: Has initialization token (outdated)"
        SERVICES_TO_RESTART+=("$service")
    else
        log_warning "$service: Token mismatch"
        SERVICES_TO_RESTART+=("$service")
    fi
}

# Check critical services
check_service_token "utils" "sting-ce-utils"
check_service_token "app" "sting-ce-app"

# Check optional services if they're running
if docker ps --format '{{.Names}}' | grep -q "sting-ce-chatbot"; then
    check_service_token "chatbot" "sting-ce-chatbot"
fi

echo ""

# Step 4: Restart services if needed
if [ ${#SERVICES_TO_RESTART[@]} -eq 0 ]; then
    log_success "All services have current Vault tokens!"
    echo ""
    log_info "No action needed."
    exit 0
fi

log_info "Step 4: Restarting services with outdated tokens..."
echo ""
log_warning "Services to restart: ${SERVICES_TO_RESTART[*]}"
echo ""

# Ask for confirmation
read -p "Restart these services? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Operation cancelled by user"
    exit 0
fi

# Restart services one by one
for service in "${SERVICES_TO_RESTART[@]}"; do
    log_info "Restarting $service..."
    docker compose restart "$service" >/dev/null 2>&1
    log_success "$service restarted"
    sleep 2
done

echo ""
log_info "Waiting for services to initialize..."
sleep 5

# Step 5: Verify all tokens are now synchronized
echo ""
log_info "Step 5: Final verification..."
ALL_SYNCED=true

for service in "${SERVICES_TO_RESTART[@]}"; do
    local container="sting-ce-$service"
    local service_token=$(docker exec "$container" printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
    local vault_token_short="${VAULT_TOKEN:0:30}"

    if [ "$service_token" = "$vault_token_short" ]; then
        log_success "$service: Token synchronized"
    else
        log_error "$service: Token still mismatched (${service_token}...)"
        ALL_SYNCED=false
    fi
done

echo ""
if [ "$ALL_SYNCED" = true ]; then
    log_success "All services successfully synchronized!"
    echo ""
    log_info "You can verify by running: ./manage_sting.sh status"
else
    log_error "Some services failed to synchronize"
    echo ""
    log_warning "Try the following:"
    log_info "1. Check service logs: docker compose logs <service>"
    log_info "2. Manually restart: docker compose restart <service>"
    log_info "3. Or use: ./manage_sting.sh restart <service>"
    exit 1
fi
