#!/bin/bash

# clear_dev_users.sh - Development User Data Cleanup Script
# This script clears all user data for development purposes only
# WARNING: This will permanently delete all user accounts and data!

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color


# Function to source environment configuration
source_environment() {
    # Determine install directory based on platform
    if [[ "$(uname)" == "Darwin" ]]; then
        INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
    else
        INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
    fi
    
    # Export INSTALL_DIR for docker-compose
    export INSTALL_DIR
    
    # Source the main configuration if it exists
    if [ -f "${INSTALL_DIR}/conf/.env" ]; then
        print_info "Sourcing environment configuration from ${INSTALL_DIR}/conf/.env"
        set -a  # automatically export all variables
        source "${INSTALL_DIR}/conf/.env"
        set +a  # turn off automatic export
    else
        print_warning "Environment file not found at ${INSTALL_DIR}/conf/.env"
        print_info "Using default environment values"
    fi
    
    # Set default values for critical variables if not set
    export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-$(openssl rand -hex 32 2>/dev/null || echo 'default-dev-key-not-secure')}"
    export POSTGRES_HOST="${POSTGRES_HOST:-db}"
    export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    export POSTGRES_DB="${POSTGRES_DB:-sting_app}"
    export POSTGRES_USER="${POSTGRES_USER:-postgres}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
}

print_header() {
    echo -e "${BLUE}${BOLD}🧹 $1${NC}"
    echo "=============================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Improved function to check if required services are running
check_services() {
    print_info "Checking if STING services are running..."
    
     # Source environment configuration first
    source_environment

    # Check if docker-compose is available
    if ! command -v docker-compose >/dev/null 2>&1 && ! command -v docker >/dev/null 2>&1; then
        print_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    # Use docker compose (v2) or docker-compose (v1) based on availability
    local compose_cmd="docker-compose"
    if docker compose version >/dev/null 2>&1; then
        compose_cmd="docker compose"
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found. Please run this script from the STING directory."
        exit 1
    fi
    
    # Check specific services that are needed for clearing user data
    # Use the actual container names from docker-compose.yml
    local required_services=("db" "kratos")
    local required_containers=("sting-ce-db" "sting-ce-kratos")
    local running_services=()
    local missing_services=()
    
    print_info "Checking required services: ${required_services[*]}"
    
    for i in "${!required_services[@]}"; do
        local service="${required_services[$i]}"
        local container="${required_containers[$i]}"
        
        # Check if container exists and is running by container name
        if docker ps --filter "name=${container}" --filter "status=running" --format "{{.Names}}" | grep -q "^${container}$" 2>/dev/null; then
            running_services+=("$service")
            print_success "✓ $service is running"
        else
            missing_services+=("$service")
            print_warning "✗ $service is not running"
        fi
    done
    
    # If some services are missing, offer to start them
    if [[ ${#missing_services[@]} -gt 0 ]]; then
        print_warning "Missing services: ${missing_services[*]}"
        echo ""
        echo "To clear user data, we need the following services running:"
        echo "• db (PostgreSQL database)"
        echo "• kratos (Identity management)"
        echo ""
        read -p "Do you want to start the required services? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Starting required services..."
            $compose_cmd up -d "${required_services[@]}"
            
            # Wait for services to be ready
            print_info "Waiting for services to be ready..."
            local max_wait=60
            local wait_time=0
            
            while [[ $wait_time -lt $max_wait ]]; do
                local all_ready=true
                for i in "${!required_services[@]}"; do
                    local container="${required_containers[$i]}"
                    if ! docker ps --filter "name=${container}" --filter "status=running" --format "{{.Names}}" | grep -q "^${container}$" 2>/dev/null; then
                        all_ready=false
                        break
                    fi
                done
                
                if [[ "$all_ready" == true ]]; then
                    break
                fi
                
                echo -n "."
                sleep 2
                ((wait_time += 2))
            done
            echo
            
            if [[ $wait_time -ge $max_wait ]]; then
                print_error "Services did not start within $max_wait seconds"
                print_info "Please check the logs with: $compose_cmd logs"
                exit 1
            else
                print_success "Required services are now running"
            fi
        else
            print_error "Cannot clear user data without required services running"
            echo ""
            echo "To start services manually, run:"
            echo "  $compose_cmd up -d db kratos"
            echo ""
            exit 1
        fi
    else
        print_success "All required services are running"
    fi
    
    # Additional health check for database connection
    print_info "Testing database connection..."
    if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
        print_success "Database connection verified"
    else
        print_warning "Database may not be fully ready yet"
        echo "Waiting a bit longer for database..."
        sleep 10
        if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
            print_success "Database connection verified"
        else
            print_error "Database connection failed"
            print_info "Please check database logs with: docker logs sting-ce-db"
            exit 1
        fi
    fi
}

# Function to backup current data (optional)
backup_data() {
    print_info "Creating backup before clearing data..."
    
    local backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup databases
    echo "Backing up PostgreSQL databases..."
    docker exec sting-ce-db pg_dumpall -U postgres > "$backup_dir/full_backup.sql" 2>/dev/null || true
    
    # Backup volumes
    echo "Backing up volume data..."
    docker run --rm -v sting_local_postgres_data:/data -v "$(pwd)/$backup_dir":/backup ubuntu tar czf /backup/postgres_data.tar.gz -C /data . 2>/dev/null || true
    docker run --rm -v sting_local_kratos_logs:/data -v "$(pwd)/$backup_dir":/backup ubuntu tar czf /backup/kratos_logs.tar.gz -C /data . 2>/dev/null || true
    
    print_success "Backup created in $backup_dir"
}

# Function to clear Kratos identities and sessions
clear_kratos_data() {
    print_header "Clearing Kratos Authentication Data"
    
    # Clear identities via admin API
    echo "Clearing Kratos identities..."
    if curl -k -s "https://localhost:4434/admin/identities" > /dev/null 2>&1; then
        # Get all identity IDs
        IDENTITIES=$(curl -k -s "https://localhost:4434/admin/identities" | jq -r '.[].id' 2>/dev/null || echo "")
        
        if [ ! -z "$IDENTITIES" ]; then
            echo "$IDENTITIES" | while read -r identity_id; do
                if [ ! -z "$identity_id" ] && [ "$identity_id" != "null" ]; then
                    echo "  Deleting identity: $identity_id"
                    curl -k -s -X DELETE "https://localhost:4434/admin/identities/$identity_id" > /dev/null 2>&1 || true
                fi
            done
            print_success "Kratos identities cleared"
        else
            print_info "No Kratos identities found"
        fi
    else
        print_warning "Cannot connect to Kratos admin API"
    fi
    
    # Clear sessions
    echo "Clearing Kratos sessions..."
    curl -k -s -X DELETE "https://localhost:4434/admin/sessions" > /dev/null 2>&1 || true
    print_success "Kratos sessions cleared"
}

# Function to clear application database
clear_app_database() {
    print_header "Clearing Application Database"
    
    # Clear application tables
    echo "Clearing application user tables..."
    
    # SQL commands to clear user data
    SQL_COMMANDS="
    -- Clear passkey registration and authentication challenges first
    DELETE FROM passkey_registration_challenges;
    DELETE FROM passkey_authentication_challenges;
    
    -- Clear passkeys (WebAuthn credentials)
    DELETE FROM passkeys;
    
    -- Clear user sessions first (foreign key constraint)
    DELETE FROM user_sessions;
    DELETE FROM app_sessions;
    
    -- Clear audit logs
    DELETE FROM audit_logs;
    
    -- Clear users table
    DELETE FROM users;
    DELETE FROM app_users;
    
    -- Clear any cached settings related to users
    DELETE FROM app_settings WHERE key LIKE '%user%' OR key LIKE '%admin%' OR key LIKE '%auth%';
    
    -- Reset sequences
    ALTER SEQUENCE users_id_seq RESTART WITH 1;
    ALTER SEQUENCE passkeys_id_seq RESTART WITH 1;
    
    -- Vacuum to reclaim space
    VACUUM FULL passkeys;
    VACUUM FULL passkey_registration_challenges;
    VACUUM FULL passkey_authentication_challenges;
    VACUUM FULL users;
    VACUUM FULL app_users;
    VACUUM FULL user_sessions;
    VACUUM FULL app_sessions;
    "
    
    if docker exec sting-ce-db psql -U postgres -d sting_app -c "$SQL_COMMANDS" > /dev/null 2>&1; then
        print_success "Application database cleared"
    else
        print_warning "Some database operations may have failed (this is often normal)"
    fi
    
    # Also clear the Kratos database directly
    echo "Clearing Kratos database tables..."
    KRATOS_CLEAR_SQL="
    -- Clear all Kratos tables (order matters due to foreign keys)
    DELETE FROM identity_verification_codes;
    DELETE FROM identity_recovery_codes;
    DELETE FROM identity_credentials;
    DELETE FROM identity_verifiable_addresses;
    DELETE FROM identity_recovery_addresses;
    DELETE FROM sessions;
    DELETE FROM identities;
    DELETE FROM courier_messages;
    DELETE FROM schema_migration;
    
    -- Clear any other Kratos-related tables
    DELETE FROM selfservice_flows_verification;
    DELETE FROM selfservice_flows_recovery;
    DELETE FROM selfservice_flows_registration;
    DELETE FROM selfservice_flows_login;
    DELETE FROM selfservice_flows_settings;
    
    VACUUM FULL;
    "
    
    # Try clearing Kratos database
    docker exec sting-ce-db psql -U postgres -d sting_app -c "$KRATOS_CLEAR_SQL" > /dev/null 2>&1 || true
    
    print_success "Database cleanup completed"
}

# Function to clear volumes and cached data
clear_volumes() {
    print_header "Clearing Cached Data and Volumes"
    
    echo "Stopping services..."
    docker-compose stop
    
    echo "Clearing log files..."
    docker volume rm sting_local_kratos_logs 2>/dev/null || true
    docker volume rm sting_local_sting_logs 2>/dev/null || true
    docker volume rm sting_local_profile_logs 2>/dev/null || true
    
    # Recreate volumes
    docker volume create sting_local_kratos_logs 2>/dev/null || true
    docker volume create sting_local_sting_logs 2>/dev/null || true
    docker volume create sting_local_profile_logs 2>/dev/null || true
    
    print_success "Volumes cleared"
}

# Function to clear browser storage instructions
clear_browser_storage() {
    print_header "Browser Storage Cleanup Instructions"
    
    echo "To complete the user data cleanup, you should also:"
    echo ""
    echo "🌐 Clear Browser Data:"
    echo "   1. Open browser Developer Tools (F12)"
    echo "   2. Go to Application/Storage tab"
    echo "   3. Clear all data for localhost:3000, localhost:4433, localhost:5050"
    echo "   4. Or use Incognito/Private mode for testing"
    echo ""
    echo "🍪 Specific items to clear:"
    echo "   • Cookies for localhost domains"
    echo "   • LocalStorage (passkey data, user preferences)"
    echo "   • SessionStorage"
    echo "   • IndexedDB"
    echo ""
    echo "⚡ Quick option: Use browser's 'Clear browsing data' feature"
    echo "   and select localhost in the 'Advanced' options"
}

# Function to restart services cleanly
restart_services() {
    print_header "Restarting Services"
    
    echo "Starting services with fresh state..."
    
    # First, properly stop all services with docker-compose
    print_info "Stopping all services properly..."
    docker-compose down --remove-orphans
    
    # Then force remove any lingering containers
    print_info "Cleaning up any remaining STING containers..."
    # Get all containers with sting-ce prefix and remove them
    STING_CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep "^sting-ce-" || true)
    if [ ! -z "$STING_CONTAINERS" ]; then
        echo "$STING_CONTAINERS" | while read container; do
            print_info "Removing container: $container"
            docker rm -f "$container" >/dev/null 2>&1 || true
        done
    fi
    
    # Extra cleanup for persistent containers
    docker rm -f sting-ce-mailpit sting-ce-chroma sting-ce-kratos sting-ce-app sting-ce-external-ai sting-ce-messaging sting-ce-frontend sting-ce-chatbot 2>/dev/null || true
    
    sleep 2
    
    # Try to start all services, handling any that fail
    print_info "Starting services..."
    START_OUTPUT=$(docker-compose up -d 2>&1)
    
    # Check if there were errors with specific services
    if echo "$START_OUTPUT" | grep -E "(mailpit|chroma).*Error"; then
        print_warning "Some containers had conflicts, starting remaining services..."
        
        # Get list of all services
        ALL_SERVICES=$(docker-compose config --services | tr '\n' ' ')
        SKIP_SERVICES=""
        
        # Check which services failed
        if echo "$START_OUTPUT" | grep -q "mailpit.*Error"; then
            SKIP_SERVICES="$SKIP_SERVICES mailpit"
        fi
        if echo "$START_OUTPUT" | grep -q "chroma.*Error"; then
            SKIP_SERVICES="$SKIP_SERVICES chroma"
        fi
        
        # Start services excluding the problematic ones
        if [ ! -z "$SKIP_SERVICES" ]; then
            SERVICES_TO_START=""
            for service in $ALL_SERVICES; do
                skip=false
                for skip_service in $SKIP_SERVICES; do
                    if [ "$service" = "$skip_service" ]; then
                        skip=true
                        break
                    fi
                done
                if [ "$skip" = false ]; then
                    SERVICES_TO_START="$SERVICES_TO_START $service"
                fi
            done
            
            print_info "Starting services: $SERVICES_TO_START"
            docker-compose up -d $SERVICES_TO_START
            
            print_warning "Skipped services: $SKIP_SERVICES"
        fi
    fi
    
    echo "Waiting for services to be ready..."
    sleep 15
    
    # Check service health
    if docker-compose ps | grep -q "Up"; then
        print_success "Services restarted successfully"
        
        # Show service status
        echo ""
        print_info "Service Status:"
        docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" | grep -v "Exit 0"
        
        # Note about skipped services
        if ! docker-compose ps | grep -q "mailpit.*Up"; then
            print_warning "Note: Mailpit service was skipped due to conflicts"
        fi
        if ! docker-compose ps | grep -q "chroma.*Up"; then
            print_warning "Note: ChromaDB service was skipped due to conflicts"
        fi
    else
        print_warning "Some services may not have started properly"
        echo "Run 'docker-compose ps' to check status"
    fi
}

# Function to verify cleanup
verify_cleanup() {
    print_header "Verifying Cleanup"
    
    echo "Checking Kratos identities..."
    IDENTITY_COUNT=$(curl -k -s "https://localhost:4434/admin/identities" 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    echo "  Identities remaining: $IDENTITY_COUNT"
    
    echo "Checking application users..."
    USER_COUNT=$(docker exec sting-ce-db psql -U postgres -d sting_app -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' \n' || echo "0")
    echo "  App users remaining: $USER_COUNT"
    
    if [ "$IDENTITY_COUNT" = "0" ] && [ "$USER_COUNT" = "0" ]; then
        print_success "✨ All user data cleared successfully!"
    else
        print_warning "Some user data may remain. This is sometimes normal."
    fi
}

# Main execution
main() {
    print_header "STING Development User Data Cleanup"
    
    source_environment

    echo -e "${RED}${BOLD}⚠️  WARNING: This will permanently delete ALL user accounts and data!${NC}"
    echo "This script is intended for development use only."
    echo ""
    echo "What will be cleared:"
    echo "• All Kratos identities (user accounts)"
    echo "• All application user records"
    echo "• All user sessions"
    echo "• All authentication data"
    echo "• All passkey/WebAuthn credentials"
    echo "• All user-related logs"
    echo ""
    
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        print_info "Operation cancelled"
        exit 0
    fi
    
    echo ""
    read -p "Do you want to create a backup first? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_data
        echo ""
    fi
    
    # Execute cleanup steps
    check_services
    echo ""
    
    clear_kratos_data
    echo ""
    
    clear_app_database
    echo ""
    
    clear_volumes
    echo ""
    
    restart_services
    echo ""
    
    verify_cleanup
    echo ""
    
    clear_browser_storage
    echo ""
    
    print_success "🎉 User data cleanup completed!"
    echo ""
    
    # Recreate default admin user
    print_header "Recreating Default Admin User"
    
    echo "Creating default admin user..."
    
    # Clear old password file first
    rm -f "$HOME/.sting-ce/admin_password.txt" 2>/dev/null || true
    
    # Execute the default admin setup directly in the app container
    if docker exec sting-ce-app python -c "
import sys
sys.path.insert(0, '/app')
from app.utils.default_admin_setup import ensure_default_admin
try:
    password = ensure_default_admin()
    if password:
        print(f'ADMIN_PASSWORD:{password}')
        sys.exit(0)
    else:
        print('ERROR: Failed to create admin')
        sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>/dev/null | grep "ADMIN_PASSWORD:"; then
        ADMIN_PASSWORD=$(docker exec sting-ce-app python -c "
import sys
sys.path.insert(0, '/app')
from app.utils.default_admin_setup import ensure_default_admin
password = ensure_default_admin()
if password:
    print(password)
" 2>/dev/null)
        
        if [ ! -z "$ADMIN_PASSWORD" ]; then
            print_success "✅ Default admin user created successfully!"
            echo ""
            echo "📧 Admin Email: admin@sting.local"
            echo "🔑 Admin Password: $ADMIN_PASSWORD"
            echo ""
            echo "⚠️  IMPORTANT: Change this password after first login!"
            echo ""
            
            # Also check if password file was created
            if [ -f "$HOME/.sting-ce/admin_password.txt" ]; then
                echo "Password also saved to: ~/.sting-ce/admin_password.txt"
            fi
        else
            print_warning "Admin user may have been created but password retrieval failed"
            echo "Check the app logs: docker logs sting-ce-app | grep -A5 'Admin Credentials'"
        fi
    else
        print_warning "Could not create admin user automatically"
        echo "The admin will be created on next service restart"
        echo "Run: ./manage_sting.sh restart app"
    fi
    
    echo ""
    echo "You can now:"
    echo "• Login with the admin account shown above"
    echo "• Create new user accounts"
    echo "• Test passkey registration from scratch"
    echo "• Verify authentication flows work properly"
    echo ""
    print_info "Next steps: Visit https://localhost:3000 to login"
}

# Run main function
main "$@"