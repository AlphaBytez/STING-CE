#!/bin/bash

# Database Connectivity Test Script
# Tests database connectivity, user permissions, and diagnoses common issues
# Usage: ./database_connectivity_test.sh [--fix]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_CONTAINER="sting-ce-db"
REQUIRED_DATABASES=("kratos" "sting_app" "sting_messaging")
REQUIRED_USERS=("kratos_user" "app_user" "messaging_user")
FIX_MODE=false

# Parse arguments
if [ "$1" = "--fix" ]; then
    FIX_MODE=true
fi

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${BLUE}[$timestamp] [INFO]${NC} $message"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[$timestamp] [SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[$timestamp] [WARNING]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[$timestamp] [ERROR]${NC} $message"
            ;;
    esac
}

# Check if database container is running
check_container_status() {
    log "INFO" "Checking database container status..."
    
    if ! docker ps --format "table {{.Names}}" | grep -q "$DB_CONTAINER"; then
        log "ERROR" "Database container '$DB_CONTAINER' is not running"
        log "INFO" "Try running: docker start $DB_CONTAINER"
        return 1
    fi
    
    log "SUCCESS" "Database container is running"
    return 0
}

# Test basic PostgreSQL connectivity
test_postgres_connectivity() {
    log "INFO" "Testing PostgreSQL connectivity..."
    
    if docker exec "$DB_CONTAINER" pg_isready -U postgres >/dev/null 2>&1; then
        log "SUCCESS" "PostgreSQL is accepting connections"
        return 0
    else
        log "ERROR" "PostgreSQL is not accepting connections"
        return 1
    fi
}

# Check if required databases exist
check_databases() {
    log "INFO" "Checking required databases..."
    local missing_databases=()
    
    for db in "${REQUIRED_DATABASES[@]}"; do
        if docker exec "$DB_CONTAINER" psql -U postgres -lqt | cut -d \| -f 1 | grep -qw "$db"; then
            log "SUCCESS" "Database '$db' exists"
        else
            log "ERROR" "Database '$db' is missing"
            missing_databases+=("$db")
        fi
    done
    
    if [ ${#missing_databases[@]} -gt 0 ]; then
        log "WARNING" "Missing databases: ${missing_databases[*]}"
        return 1
    fi
    
    return 0
}

# Check if required users exist
check_users() {
    log "INFO" "Checking required database users..."
    local missing_users=()
    
    for user in "${REQUIRED_USERS[@]}"; do
        if docker exec "$DB_CONTAINER" psql -U postgres -c "\du" | grep -qw "$user"; then
            log "SUCCESS" "User '$user' exists"
        else
            log "ERROR" "User '$user' is missing"
            missing_users+=("$user")
        fi
    done
    
    if [ ${#missing_users[@]} -gt 0 ]; then
        log "WARNING" "Missing users: ${missing_users[*]}"
        return 1
    fi
    
    return 0
}

# Test user permissions
test_user_permissions() {
    log "INFO" "Testing user permissions..."
    local permission_issues=()
    
    # Test kratos_user permissions
    if ! docker exec "$DB_CONTAINER" psql -U kratos_user -d kratos -c "SELECT 1;" >/dev/null 2>&1; then
        log "ERROR" "kratos_user cannot connect to kratos database"
        permission_issues+=("kratos_user")
    else
        log "SUCCESS" "kratos_user has access to kratos database"
    fi
    
    # Test app_user permissions
    if ! docker exec "$DB_CONTAINER" psql -U app_user -d sting_app -c "SELECT 1;" >/dev/null 2>&1; then
        log "ERROR" "app_user cannot connect to sting_app database"
        permission_issues+=("app_user")
    else
        log "SUCCESS" "app_user has access to sting_app database"
    fi
    
    # Test messaging_user permissions
    if ! docker exec "$DB_CONTAINER" psql -U messaging_user -d sting_messaging -c "SELECT 1;" >/dev/null 2>&1; then
        log "ERROR" "messaging_user cannot connect to sting_messaging database"
        permission_issues+=("messaging_user")
    else
        log "SUCCESS" "messaging_user has access to sting_messaging database"
    fi
    
    if [ ${#permission_issues[@]} -gt 0 ]; then
        log "WARNING" "Permission issues found for: ${permission_issues[*]}"
        return 1
    fi
    
    return 0
}

# Test schema permissions
test_schema_permissions() {
    log "INFO" "Testing schema creation permissions..."
    local schema_issues=()
    
    # Test kratos_user can create tables
    if ! docker exec "$DB_CONTAINER" psql -U kratos_user -d kratos -c "CREATE TABLE IF NOT EXISTS test_table (id INTEGER); DROP TABLE IF EXISTS test_table;" >/dev/null 2>&1; then
        log "ERROR" "kratos_user cannot create tables in kratos database"
        schema_issues+=("kratos_user")
    else
        log "SUCCESS" "kratos_user can create tables in kratos database"
    fi
    
    # Test app_user can create tables
    if ! docker exec "$DB_CONTAINER" psql -U app_user -d sting_app -c "CREATE TABLE IF NOT EXISTS test_table (id INTEGER); DROP TABLE IF EXISTS test_table;" >/dev/null 2>&1; then
        log "ERROR" "app_user cannot create tables in sting_app database"
        schema_issues+=("app_user")
    else
        log "SUCCESS" "app_user can create tables in sting_app database"
    fi
    
    if [ ${#schema_issues[@]} -gt 0 ]; then
        log "WARNING" "Schema permission issues found for: ${schema_issues[*]}"
        return 1
    fi
    
    return 0
}

# Diagnose connection string compatibility
test_connection_strings() {
    log "INFO" "Testing connection string compatibility with docker-compose.yml..."
    
    # Test Kratos connection string format
    local kratos_conn="postgresql://kratos_user:kratos_secure_password_change_me@db:5432/kratos?sslmode=disable"
    if docker exec "$DB_CONTAINER" psql "$kratos_conn" -c "SELECT 1;" >/dev/null 2>&1; then
        log "SUCCESS" "Kratos connection string format is valid"
    else
        log "ERROR" "Kratos connection string format failed - check password or permissions"
    fi
    
    # Test App connection string format
    local app_conn="postgresql://app_user:app_secure_password_change_me@localhost:5432/sting_app?sslmode=disable"
    # Note: We use localhost instead of db when testing from outside the container
    if docker exec "$DB_CONTAINER" psql "postgresql://app_user:app_secure_password_change_me@localhost:5432/sting_app?sslmode=disable" -c "SELECT 1;" >/dev/null 2>&1; then
        log "SUCCESS" "App connection string format is valid"
    else
        log "ERROR" "App connection string format failed - check password or permissions"
    fi
}

# Fix database issues
fix_database_issues() {
    log "INFO" "Attempting to fix database issues..."
    
    # Create missing databases
    for db in "${REQUIRED_DATABASES[@]}"; do
        log "INFO" "Creating database '$db'..."
        docker exec "$DB_CONTAINER" psql -U postgres -c "CREATE DATABASE $db;" 2>/dev/null || log "INFO" "Database '$db' already exists"
    done
    
    # Create missing users
    docker exec "$DB_CONTAINER" psql -U postgres -c "CREATE USER kratos_user WITH PASSWORD 'kratos_secure_password_change_me';" 2>/dev/null || log "INFO" "User kratos_user already exists"
    docker exec "$DB_CONTAINER" psql -U postgres -c "CREATE USER app_user WITH PASSWORD 'app_secure_password_change_me';" 2>/dev/null || log "INFO" "User app_user already exists"
    docker exec "$DB_CONTAINER" psql -U postgres -c "CREATE USER messaging_user WITH PASSWORD 'messaging_secure_password_change_me';" 2>/dev/null || log "INFO" "User messaging_user already exists"
    
    # Grant permissions for kratos database
    docker exec "$DB_CONTAINER" psql -U postgres -d kratos -c "
        GRANT ALL PRIVILEGES ON DATABASE kratos TO kratos_user;
        GRANT ALL PRIVILEGES ON SCHEMA public TO kratos_user;
        GRANT CREATE ON SCHEMA public TO kratos_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO kratos_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO kratos_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO kratos_user;
    " 2>/dev/null || log "WARNING" "Failed to set some kratos permissions"
    
    # Grant permissions for sting_app database
    docker exec "$DB_CONTAINER" psql -U postgres -d sting_app -c "
        GRANT ALL PRIVILEGES ON DATABASE sting_app TO app_user;
        GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
        GRANT CREATE ON SCHEMA public TO app_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO app_user;
    " 2>/dev/null || log "WARNING" "Failed to set some sting_app permissions"
    
    # Grant permissions for sting_messaging database
    docker exec "$DB_CONTAINER" psql -U postgres -d sting_messaging -c "
        GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO messaging_user;
        GRANT ALL PRIVILEGES ON SCHEMA public TO messaging_user;
        GRANT CREATE ON SCHEMA public TO messaging_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO messaging_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO messaging_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO messaging_user;
        -- Also grant app_user access for cross-service operations
        GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;
        GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
    " 2>/dev/null || log "WARNING" "Failed to set some sting_messaging permissions"
    
    log "SUCCESS" "Database repair completed"
}

# Display summary
display_summary() {
    local overall_status=$1
    
    echo
    echo "======================================"
    echo "DATABASE CONNECTIVITY TEST SUMMARY"
    echo "======================================"
    
    if [ $overall_status -eq 0 ]; then
        log "SUCCESS" "All database connectivity tests passed!"
        echo
        echo "Your database is properly configured for STING services:"
        echo "✓ All required databases exist"
        echo "✓ All required users exist" 
        echo "✓ All permissions are properly set"
        echo "✓ Connection strings are compatible"
    else
        log "WARNING" "Some database issues were found"
        echo
        echo "Common fixes you can try:"
        echo "1. Run this script with --fix flag: ./database_connectivity_test.sh --fix"
        echo "2. Restart database container: docker restart sting-ce-db"
        echo "3. Check service logs: docker logs sting-ce-db"
        echo "4. For fresh install issues, see CLAUDE.md database section"
    fi
    
    echo "======================================"
}

# Main execution
main() {
    log "INFO" "Starting STING Database Connectivity Test"
    log "INFO" "Fix mode: $FIX_MODE"
    echo
    
    local overall_status=0
    
    # Run tests
    check_container_status || overall_status=1
    test_postgres_connectivity || overall_status=1
    check_databases || overall_status=1
    check_users || overall_status=1
    test_user_permissions || overall_status=1
    test_schema_permissions || overall_status=1
    test_connection_strings || overall_status=1
    
    # Fix if requested and issues found
    if [ $FIX_MODE = true ] && [ $overall_status -ne 0 ]; then
        echo
        log "INFO" "Fix mode enabled - attempting repairs..."
        fix_database_issues
        
        # Re-run tests after fix
        echo
        log "INFO" "Re-running tests after repair..."
        overall_status=0
        check_databases || overall_status=1
        check_users || overall_status=1
        test_user_permissions || overall_status=1
        test_schema_permissions || overall_status=1
    fi
    
    # Display summary
    display_summary $overall_status
    
    exit $overall_status
}

# Run main function
main "$@"