#!/bin/bash
# test_auth_suite.sh - Comprehensive authentication testing script for STING
# This script tests the complete authentication flow including registration, login, and session management

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KRATOS_PUBLIC_URL="https://localhost:4433"
KRATOS_ADMIN_URL="https://localhost:4434"
MAILPIT_URL="http://localhost:8025"
APP_URL="https://localhost:5050"
FRONTEND_URL="https://localhost:3000"

# Test data
TEST_EMAIL="test-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123!"
TEST_FIRST_NAME="Test"
TEST_LAST_NAME="User"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if services are running
check_services() {
    log_info "Checking services..."
    
    local services=("kratos" "mailpit" "app" "frontend")
    local all_running=true
    
    for service in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "sting-ce-$service"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        log_error "Not all required services are running. Please start them first."
        exit 1
    fi
}

# Test 1: Registration Flow
test_registration() {
    log_info "Testing registration flow..."
    
    # Get registration flow
    local flow_response
    flow_response=$(curl -s -k "$KRATOS_PUBLIC_URL/self-service/registration/api")
    local flow_id=$(echo "$flow_response" | jq -r '.id')
    
    if [ -z "$flow_id" ] || [ "$flow_id" = "null" ]; then
        log_error "Failed to create registration flow"
        return 1
    fi
    
    log_info "Created registration flow: $flow_id"
    
    # Submit profile data
    local profile_response
    profile_response=$(curl -s -k -X POST \
        "$KRATOS_PUBLIC_URL/self-service/registration?flow=$flow_id" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "Accept: application/json" \
        -d "method=profile&traits.email=$TEST_EMAIL&traits.name.first=$TEST_FIRST_NAME&traits.name.last=$TEST_LAST_NAME")
    
    # Check if we need to submit password
    if echo "$profile_response" | jq -e '.ui.nodes[] | select(.attributes.name == "password")' >/dev/null; then
        log_info "Submitting password..."
        
        # Submit password
        local register_response
        register_response=$(curl -s -k -X POST \
            "$KRATOS_PUBLIC_URL/self-service/registration?flow=$flow_id" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -H "Accept: application/json" \
            -d "method=password&password=$TEST_PASSWORD&traits.email=$TEST_EMAIL&traits.name.first=$TEST_FIRST_NAME&traits.name.last=$TEST_LAST_NAME")
        
        # Check for session
        if echo "$register_response" | jq -e '.session' >/dev/null; then
            SESSION_TOKEN=$(echo "$register_response" | jq -r '.session_token')
            IDENTITY_ID=$(echo "$register_response" | jq -r '.identity.id')
            log_success "Registration successful! Identity ID: $IDENTITY_ID"
            return 0
        else
            log_error "Registration failed:"
            echo "$register_response" | jq '.ui.messages'
            return 1
        fi
    else
        log_error "Unexpected registration flow state"
        echo "$profile_response" | jq '.'
        return 1
    fi
}

# Test 2: Login Flow
test_login() {
    log_info "Testing login flow..."
    
    # Get login flow
    local flow_response
    flow_response=$(curl -s -k "$KRATOS_PUBLIC_URL/self-service/login/api")
    local flow_id=$(echo "$flow_response" | jq -r '.id')
    
    if [ -z "$flow_id" ] || [ "$flow_id" = "null" ]; then
        log_error "Failed to create login flow"
        return 1
    fi
    
    log_info "Created login flow: $flow_id"
    
    # Submit credentials
    local login_response
    login_response=$(curl -s -k -X POST \
        "$KRATOS_PUBLIC_URL/self-service/login?flow=$flow_id" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -H "Accept: application/json" \
        -d "method=password&identifier=$TEST_EMAIL&password=$TEST_PASSWORD")
    
    # Check for session
    if echo "$login_response" | jq -e '.session' >/dev/null; then
        SESSION_TOKEN=$(echo "$login_response" | jq -r '.session_token')
        log_success "Login successful! Session token: ${SESSION_TOKEN:0:20}..."
        return 0
    else
        log_error "Login failed:"
        echo "$login_response" | jq '.ui.messages'
        return 1
    fi
}

# Test 3: Session Validation
test_session() {
    log_info "Testing session validation..."
    
    if [ -z "$SESSION_TOKEN" ]; then
        log_error "No session token available"
        return 1
    fi
    
    # Validate session
    local session_response
    session_response=$(curl -s -k \
        -H "Authorization: Bearer $SESSION_TOKEN" \
        "$KRATOS_PUBLIC_URL/sessions/whoami")
    
    if echo "$session_response" | jq -e '.active' >/dev/null; then
        local email=$(echo "$session_response" | jq -r '.identity.traits.email')
        log_success "Session is valid for user: $email"
        return 0
    else
        log_error "Session validation failed"
        return 1
    fi
}

# Test 4: Check Mailpit for emails
test_emails() {
    log_info "Checking for emails in Mailpit..."
    
    local messages
    messages=$(curl -s "$MAILPIT_URL/api/v1/messages")
    local count=$(echo "$messages" | jq -r '.total')
    
    if [ "$count" -gt 0 ]; then
        log_success "Found $count email(s) in Mailpit"
        echo "$messages" | jq '.messages[] | {from: .From[0].Address, to: .To[0].Address, subject: .Subject}'
    else
        log_warning "No emails found in Mailpit"
    fi
}

# Test 5: Cleanup (optional)
cleanup_test_user() {
    log_info "Cleaning up test user..."
    
    if [ -z "$IDENTITY_ID" ]; then
        log_warning "No identity ID to clean up"
        return 0
    fi
    
    # Delete identity via admin API
    local delete_response
    delete_response=$(curl -s -k -X DELETE \
        "$KRATOS_ADMIN_URL/admin/identities/$IDENTITY_ID")
    
    if [ -z "$delete_response" ]; then
        log_success "Test user deleted successfully"
    else
        log_warning "Could not delete test user: $delete_response"
    fi
}

# Main execution
main() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║          STING Authentication Test Suite                       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo
    
    # Check services first
    check_services
    echo
    
    # Run tests
    local all_passed=true
    
    if test_registration; then
        echo
    else
        all_passed=false
    fi
    
    if test_login; then
        echo
    else
        all_passed=false
    fi
    
    if test_session; then
        echo
    else
        all_passed=false
    fi
    
    test_emails
    echo
    
    # Summary
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                      Test Summary                              ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    
    if [ "$all_passed" = true ]; then
        log_success "All authentication tests passed!"
    else
        log_error "Some tests failed. Check the output above."
    fi
    
    # Optional cleanup
    if [ "${1:-}" = "--cleanup" ]; then
        cleanup_test_user
    else
        log_info "Run with --cleanup to delete the test user"
    fi
}

# Run main function
main "$@"