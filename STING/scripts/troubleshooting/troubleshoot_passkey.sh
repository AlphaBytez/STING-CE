#!/bin/bash

# Troubleshoot Passkey Registration Issues
# This script helps diagnose and fix common passkey registration problems

echo "🔍 STING Passkey Registration Troubleshooting"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}📋 $1${NC}"
    echo "----------------------------------------"
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

# Function to check if services are running
check_services() {
    print_header "Checking Docker Services"
    
    # Check if docker-compose services are running
    RUNNING_SERVICES=$(docker-compose ps --filter "status=running" --format "table {{.Service}}" | tail -n +2)
    
    if [ -z "$RUNNING_SERVICES" ]; then
        print_error "No Docker services are running!"
        echo "   Run: docker-compose up -d"
        return 1
    fi
    
    echo "Running services:"
    echo "$RUNNING_SERVICES" | while read service; do
        if [ ! -z "$service" ]; then
            print_success "$service"
        fi
    done
    
    # Check specific services needed for passkeys
    REQUIRED_SERVICES=("kratos" "app" "frontend" "db")
    for service in "${REQUIRED_SERVICES[@]}"; do
        if ! echo "$RUNNING_SERVICES" | grep -q "$service"; then
            print_warning "$service is not running"
        fi
    done
}

# Function to check WebAuthn configuration
check_webauthn_config() {
    print_header "Checking WebAuthn Configuration"
    
    # Check Kratos configuration
    if [ -f "./kratos/main.kratos.yml" ]; then
        print_success "Kratos configuration file found"
        
        # Check if passkey is enabled
        if grep -q "passkey:" "./kratos/main.kratos.yml"; then
            print_success "Passkey configuration found in Kratos"
        else
            print_error "Passkey configuration missing in Kratos"
        fi
        
        # Check RP ID
        RP_ID=$(grep -A 2 "rp:" "./kratos/main.kratos.yml" | grep "id:" | head -1 | awk '{print $2}')
        if [ "$RP_ID" = "localhost" ]; then
            print_success "RP ID is set to localhost"
        else
            print_warning "RP ID is: $RP_ID (expected: localhost)"
        fi
        
        # Check origins
        if grep -A 10 "origins:" "./kratos/main.kratos.yml" | grep -q "https://localhost:3000"; then
            print_success "Frontend origin configured"
        else
            print_warning "Frontend origin (https://localhost:3000) not found"
        fi
        
    else
        print_error "Kratos configuration file not found"
    fi
}

# Function to check certificates
check_certificates() {
    print_header "Checking SSL Certificates"
    
    if [ -f "./certs/server.crt" ] && [ -f "./certs/server.key" ]; then
        print_success "SSL certificates found"
        
        # Check certificate validity
        if openssl x509 -in ./certs/server.crt -noout -checkend 86400 2>/dev/null; then
            print_success "Certificate is valid"
        else
            print_warning "Certificate may be expired or invalid"
        fi
        
        # Check if certificate includes localhost
        if openssl x509 -in ./certs/server.crt -noout -text | grep -q "localhost"; then
            print_success "Certificate includes localhost"
        else
            print_warning "Certificate may not include localhost"
        fi
    else
        print_error "SSL certificates not found"
        echo "   Generate with: ./generate_certificates.sh"
    fi
}

# Function to check network connectivity
check_connectivity() {
    print_header "Checking Service Connectivity"
    
    # Check if Kratos is accessible
    if curl -k -s "https://localhost:4433/health/ready" > /dev/null 2>&1; then
        print_success "Kratos is accessible"
    else
        print_error "Kratos is not accessible at https://localhost:4433"
    fi
    
    # Check if app is accessible
    if curl -k -s "https://localhost:5050/health" > /dev/null 2>&1; then
        print_success "App is accessible"
    else
        print_error "App is not accessible at https://localhost:5050"
    fi
    
    # Check if frontend is accessible
    if curl -k -s "https://localhost:3000" > /dev/null 2>&1; then
        print_success "Frontend is accessible"
    else
        print_error "Frontend is not accessible at https://localhost:3000"
    fi
}

# Function to check browser requirements
check_browser_requirements() {
    print_header "Browser Requirements for Passkeys"
    
    echo "✅ Required Browser Features:"
    echo "   • WebAuthn API support"
    echo "   • HTTPS (or localhost)"
    echo "   • Platform authenticator (TouchID, FaceID, Windows Hello)"
    echo ""
    echo "🌐 Supported Browsers:"
    echo "   • Chrome 67+ (recommended)"
    echo "   • Safari 14+"
    echo "   • Firefox 90+"
    echo "   • Edge 88+"
    echo ""
    echo "⚠️  Common Issues:"
    echo "   • Mixed content (HTTP/HTTPS)"
    echo "   • Invalid certificates"
    echo "   • Browser extensions blocking WebAuthn"
}

# Function to fix common issues
fix_common_issues() {
    print_header "Fixing Common Issues"
    
    echo "🔧 Applying fixes..."
    
    # Restart services
    echo "   Restarting services..."
    docker-compose restart kratos app frontend
    
    # Wait for services to be ready
    echo "   Waiting for services to be ready..."
    sleep 10
    
    print_success "Services restarted"
}

# Function to test WebAuthn endpoint
test_webauthn_endpoint() {
    print_header "Testing WebAuthn Endpoint"
    
    # Test WebAuthn registration endpoint
    echo "Testing /api/auth/webauthn/registration/begin..."
    
    RESPONSE=$(curl -k -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"test@example.com","user_id":"test-user"}' \
        "https://localhost:5050/api/auth/webauthn/registration/begin" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
        if echo "$RESPONSE" | grep -q "challenge"; then
            print_success "WebAuthn endpoint is working"
        else
            print_error "WebAuthn endpoint returned error: $RESPONSE"
        fi
    else
        print_error "Cannot reach WebAuthn endpoint"
    fi
}

# Function to show logs
show_logs() {
    print_header "Recent Service Logs"
    
    echo "📄 Kratos logs (last 20 lines):"
    docker-compose logs --tail=20 kratos 2>/dev/null || echo "   Kratos logs not available"
    
    echo ""
    echo "📄 App logs (last 20 lines):"
    docker-compose logs --tail=20 app 2>/dev/null || echo "   App logs not available"
}

# Main execution
main() {
    echo "Starting troubleshooting..."
    echo ""
    
    check_services
    echo ""
    
    check_webauthn_config
    echo ""
    
    check_certificates
    echo ""
    
    check_connectivity
    echo ""
    
    test_webauthn_endpoint
    echo ""
    
    check_browser_requirements
    echo ""
    
    # Ask if user wants to see logs
    read -p "Do you want to see recent service logs? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
        echo ""
    fi
    
    # Ask if user wants to try fixes
    read -p "Do you want to try automatic fixes? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        fix_common_issues
        echo ""
        echo "🔄 Please try registering a passkey again"
    fi
    
    echo ""
    print_header "Manual Troubleshooting Steps"
    echo "1. Ensure you're using a supported browser"
    echo "2. Try in an incognito/private window"
    echo "3. Clear browser cache and cookies"
    echo "4. Disable browser extensions temporarily"
    echo "5. Check browser console for JavaScript errors"
    echo "6. Verify you have a platform authenticator available"
    echo ""
    print_success "Troubleshooting complete!"
}

# Run main function
main
