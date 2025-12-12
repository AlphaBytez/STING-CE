#!/bin/bash
# Headscale Tunnel Manager for STING Support System
# Manages secure support tunnels using self-hosted Headscale

# Load dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logging.sh"
source "${SCRIPT_DIR}/core.sh"

# Configuration
HEADSCALE_URL="http://localhost:8070"
HEADSCALE_CONTAINER="sting-ce-headscale"
TUNNEL_SESSIONS_DIR="${INSTALL_DIR}/headscale_sessions"
TAILSCALE_CLIENT_CONFIG="/tmp/tailscale"

# Initialize tunnel management
init_tunnel_management() {
    mkdir -p "${TUNNEL_SESSIONS_DIR}"
    
    # Ensure Headscale is running
    if ! docker ps | grep -q "$HEADSCALE_CONTAINER.*Up"; then
        log_message "[!]  Headscale service not running - starting it..." "WARNING"
        
        # Change to install directory for docker-compose
        local current_dir
        current_dir=$(pwd)
        cd "${INSTALL_DIR}" 2>/dev/null || {
            log_message "[-] Cannot access install directory: ${INSTALL_DIR}" "ERROR"
            return 1
        }
        
        # Start Headscale with support-tunnels profile
        if docker compose --profile support-tunnels up -d headscale; then
            log_message "[+] Headscale service started"
            sleep 5  # Give it time to initialize
        else
            log_message "[-] Failed to start Headscale service" "ERROR"
            cd "$current_dir" || true
            return 1
        fi
        
        cd "$current_dir" || true
    fi
}

# Check if Headscale is available
check_headscale_health() {
    local retries=5
    local wait_time=2
    
    for ((i=1; i<=retries; i++)); do
        if curl -s -f "$HEADSCALE_URL/health" >/dev/null 2>&1; then
            return 0
        fi
        
        if [ $i -lt $retries ]; then
            log_message "⏳ Waiting for Headscale (attempt $i/$retries)..."
            sleep $wait_time
        fi
    done
    
    return 1
}

# Create a new support user in Headscale
create_support_user() {
    local username="$1"
    local user_type="${2:-community}"  # community, professional, enterprise
    
    log_message "👤 Creating Headscale user: $username ($user_type)"
    
    # Execute headscale command in container
    if docker exec "$HEADSCALE_CONTAINER" headscale users create "$username" 2>/dev/null; then
        log_message "[+] User $username created successfully"
        return 0
    else
        log_message "[!]  User $username may already exist or creation failed" "WARNING"
        return 1
    fi
}

# Generate pre-auth key for support session
generate_support_auth_key() {
    local username="$1"
    local ticket_id="$2"
    local duration="${3:-30m}"  # Default 30 minutes
    
    log_message "🔑 Generating auth key for $username (duration: $duration)"
    
    # Create ephemeral pre-auth key
    local auth_key
    auth_key=$(docker exec "$HEADSCALE_CONTAINER" headscale preauthkeys create \
        --user "$username" \
        --ephemeral \
        --expiration "$duration" \
        --output json 2>/dev/null | jq -r '.key' 2>/dev/null)
    
    if [ -n "$auth_key" ] && [ "$auth_key" != "null" ]; then
        log_message "[+] Auth key generated successfully"
        
        # Store session info
        local session_file="${TUNNEL_SESSIONS_DIR}/${ticket_id}.json"
        cat > "$session_file" << EOF
{
  "ticket_id": "$ticket_id",
  "username": "$username", 
  "auth_key": "$auth_key",
  "duration": "$duration",
  "created_at": "$(date -Iseconds)",
  "expires_at": "$(date -d "+$duration" -Iseconds 2>/dev/null || date -v "+30M" -Iseconds)",
  "status": "active",
  "headscale_url": "$HEADSCALE_URL"
}
EOF
        
        echo "$auth_key"
        return 0
    else
        log_message "[-] Failed to generate auth key" "ERROR"
        return 1
    fi
}

# Create a support tunnel session
create_support_tunnel() {
    local ticket_id="$1"
    local support_type="${2:-community}"  # community, professional, enterprise
    local duration="${3:-30m}"
    
    log_message "🔗 Creating support tunnel for ticket: $ticket_id"
    
    # Initialize tunnel management
    if ! init_tunnel_management; then
        return 1
    fi
    
    # Check Headscale health
    if ! check_headscale_health; then
        log_message "[-] Headscale service not responding" "ERROR"
        log_message "Try: docker logs $HEADSCALE_CONTAINER" "INFO"
        return 1
    fi
    
    # Create username based on ticket and type
    local username="support-${ticket_id,,}"  # Lowercase
    
    # Create user if doesn't exist
    create_support_user "$username" "$support_type"
    
    # Generate auth key
    local auth_key
    auth_key=$(generate_support_auth_key "$username" "$ticket_id" "$duration")
    
    if [ -z "$auth_key" ]; then
        log_message "[-] Failed to generate support tunnel" "ERROR"
        return 1
    fi
    
    log_message "[+] Support tunnel created successfully!"
    log_message ""
    log_message "📋 **Support Tunnel Details:**"
    log_message "  🎫 Ticket ID: $ticket_id"
    log_message "  👤 Username: $username"
    log_message "  🔑 Auth Key: ${auth_key:0:20}...${auth_key: -10}"
    log_message "  ⏰ Duration: $duration"
    log_message "  🌐 Headscale URL: $HEADSCALE_URL"
    log_message ""
    log_message "📤 **For Support Team:**"
    log_message "  1. Install Tailscale client: https://tailscale.com/download"
    log_message "  2. Join network: tailscale up --login-server=$HEADSCALE_URL --authkey=$auth_key"
    log_message "  3. Access customer system: tailscale ssh $username"
    log_message "  4. Bundle location: ~/.sting-ce/support_bundles/"
    log_message ""
    log_message " **Security:**"
    log_message "  • Ephemeral access (auto-expires)"
    log_message "  • No customer network routing"
    log_message "  • Full audit trail in logs"
    log_message "  • SSH access to STING containers only"
    
    # Return session info for programmatic use
    cat "${TUNNEL_SESSIONS_DIR}/${ticket_id}.json" 2>/dev/null || echo "{\"auth_key\":\"$auth_key\"}"
}

# List active support tunnels
list_support_tunnels() {
    log_message "🔗 Active Support Tunnels:"
    log_message ""
    
    if [ ! -d "$TUNNEL_SESSIONS_DIR" ]; then
        log_message "  📭 No tunnel sessions found"
        return 0
    fi
    
    local sessions_found=0
    
    for session_file in "$TUNNEL_SESSIONS_DIR"/*.json; do
        if [ -f "$session_file" ]; then
            sessions_found=1
            
            local ticket_id
            local username  
            local created_at
            local expires_at
            local status
            
            ticket_id=$(jq -r '.ticket_id // "unknown"' "$session_file" 2>/dev/null)
            username=$(jq -r '.username // "unknown"' "$session_file" 2>/dev/null)
            created_at=$(jq -r '.created_at // "unknown"' "$session_file" 2>/dev/null)
            expires_at=$(jq -r '.expires_at // "unknown"' "$session_file" 2>/dev/null)
            status=$(jq -r '.status // "unknown"' "$session_file" 2>/dev/null)
            
            log_message "  🎫 $ticket_id"
            log_message "    👤 User: $username"
            log_message "    📅 Created: $created_at"
            log_message "    ⏰ Expires: $expires_at"
            log_message "    📊 Status: $status"
            log_message ""
        fi
    done
    
    if [ $sessions_found -eq 0 ]; then
        log_message "  📭 No active tunnel sessions"
    fi
}

# Close a support tunnel
close_support_tunnel() {
    local ticket_id="$1"
    
    log_message " Closing support tunnel for ticket: $ticket_id"
    
    local session_file="${TUNNEL_SESSIONS_DIR}/${ticket_id}.json"
    
    if [ ! -f "$session_file" ]; then
        log_message "[-] Tunnel session not found: $ticket_id" "ERROR"
        return 1
    fi
    
    # Get username from session
    local username
    username=$(jq -r '.username' "$session_file" 2>/dev/null)
    
    if [ -n "$username" ] && [ "$username" != "null" ]; then
        # Delete user from Headscale (this closes all their connections)
        log_message "👤 Removing user: $username"
        docker exec "$HEADSCALE_CONTAINER" headscale users destroy "$username" --force 2>/dev/null || true
        
        # Update session status
        local temp_file
        temp_file=$(mktemp)
        jq '.status = "closed" | .closed_at = now | .closed_at |= strftime("%Y-%m-%dT%H:%M:%S%z")' "$session_file" > "$temp_file" 2>/dev/null
        mv "$temp_file" "$session_file" 2>/dev/null || true
        
        log_message "[+] Support tunnel closed successfully"
    else
        log_message "[!]  Could not determine username, marking session as closed" "WARNING"
    fi
    
    log_message " Tunnel access revoked and session archived"
}

# Check tunnel status
check_tunnel_status() {
    local ticket_id="$1"
    
    local session_file="${TUNNEL_SESSIONS_DIR}/${ticket_id}.json"
    
    if [ ! -f "$session_file" ]; then
        log_message "[-] Tunnel session not found: $ticket_id" "ERROR"
        return 1
    fi
    
    log_message "📊 Tunnel Status for $ticket_id:"
    
    # Parse session file
    local username
    local created_at
    local expires_at
    local status
    
    username=$(jq -r '.username // "unknown"' "$session_file" 2>/dev/null)
    created_at=$(jq -r '.created_at // "unknown"' "$session_file" 2>/dev/null)
    expires_at=$(jq -r '.expires_at // "unknown"' "$session_file" 2>/dev/null)
    status=$(jq -r '.status // "unknown"' "$session_file" 2>/dev/null)
    
    log_message "  👤 Username: $username"
    log_message "  📅 Created: $created_at"
    log_message "  ⏰ Expires: $expires_at"
    log_message "  📊 Status: $status"
    
    # Check if user still exists in Headscale
    if docker exec "$HEADSCALE_CONTAINER" headscale users list 2>/dev/null | grep -q "$username"; then
        log_message "  🔗 Connection: Active"
        
        # List connected devices
        local devices
        devices=$(docker exec "$HEADSCALE_CONTAINER" headscale nodes list --user "$username" --output json 2>/dev/null | jq -r '.[].hostname' 2>/dev/null)
        
        if [ -n "$devices" ]; then
            log_message "  📱 Connected devices:"
            echo "$devices" | while read -r device; do
                if [ -n "$device" ]; then
                    log_message "    • $device"
                fi
            done
        fi
    else
        log_message "  🔗 Connection: Inactive"
    fi
}

# Get Headscale status
get_headscale_status() {
    log_message "🏥 Headscale Support System Status:"
    log_message ""
    
    # Check if container is running
    if docker ps | grep -q "$HEADSCALE_CONTAINER.*Up"; then
        log_message "[+] Headscale container: Running"
        
        # Check health endpoint
        if check_headscale_health; then
            log_message "[+] Headscale service: Healthy"
            
            # Get user count
            local user_count
            user_count=$(docker exec "$HEADSCALE_CONTAINER" headscale users list --output json 2>/dev/null | jq length 2>/dev/null || echo "0")
            log_message "👥 Users registered: $user_count"
            
            # Get node count
            local node_count  
            node_count=$(docker exec "$HEADSCALE_CONTAINER" headscale nodes list --output json 2>/dev/null | jq length 2>/dev/null || echo "0")
            log_message "📱 Devices connected: $node_count"
            
        else
            log_message "[-] Headscale service: Unhealthy" "ERROR"
            log_message "Check logs: docker logs $HEADSCALE_CONTAINER" "INFO"
        fi
    else
        log_message "[-] Headscale container: Not running" "ERROR"
        log_message "Start with: docker compose --profile support-tunnels up -d headscale" "INFO"
    fi
    
    # Count active sessions
    local session_count=0
    if [ -d "$TUNNEL_SESSIONS_DIR" ]; then
        session_count=$(find "$TUNNEL_SESSIONS_DIR" -name "*.json" -type f 2>/dev/null | wc -l)
    fi
    log_message "🔗 Active tunnel sessions: $session_count"
    
    log_message ""
    log_message "🌐 **Access Info:**"
    log_message "  • Headscale URL: $HEADSCALE_URL"
    log_message "  • Web Interface: http://localhost:8070"
    log_message "  • Base Domain: support.sting.local"
    log_message "  • Session Duration: 30 minutes (community)"
}

# Clean up expired sessions
cleanup_expired_sessions() {
    log_message "🧹 Cleaning up expired tunnel sessions..."
    
    if [ ! -d "$TUNNEL_SESSIONS_DIR" ]; then
        log_message "  📭 No sessions to clean up"
        return 0
    fi
    
    local cleaned_count=0
    local current_timestamp
    current_timestamp=$(date +%s)
    
    for session_file in "$TUNNEL_SESSIONS_DIR"/*.json; do
        if [ -f "$session_file" ]; then
            local expires_at
            expires_at=$(jq -r '.expires_at' "$session_file" 2>/dev/null)
            
            if [ -n "$expires_at" ] && [ "$expires_at" != "null" ]; then
                local expiry_timestamp
                expiry_timestamp=$(date -d "$expires_at" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S%z" "$expires_at" +%s 2>/dev/null)
                
                if [ -n "$expiry_timestamp" ] && [ "$current_timestamp" -gt "$expiry_timestamp" ]; then
                    # Session expired
                    local ticket_id
                    ticket_id=$(basename "$session_file" .json)
                    
                    log_message "  ⏰ Expiring session: $ticket_id"
                    close_support_tunnel "$ticket_id"
                    cleaned_count=$((cleaned_count + 1))
                fi
            fi
        fi
    done
    
    log_message "[+] Cleaned up $cleaned_count expired sessions"
}

# Show help for tunnel management
show_tunnel_help() {
    cat << 'EOF'
🔗 Headscale Tunnel Manager - STING Support System

USAGE:
    ./manage_sting.sh support tunnel COMMAND [OPTIONS]

COMMANDS:
    create TICKET_ID [duration]   Create support tunnel for ticket
    list                         List active support tunnels  
    status TICKET_ID             Show tunnel status
    close TICKET_ID              Close support tunnel
    cleanup                      Clean up expired sessions
    headscale-status            Show Headscale service status
    help                        Show this help

OPTIONS:
    duration                    Tunnel duration (30m, 1h, 4h, etc.)

EXAMPLES:
    # Create 30-minute community support tunnel
    ./manage_sting.sh support tunnel create ST-2025-001
    
    # Create 4-hour enterprise support tunnel  
    ./manage_sting.sh support tunnel create ST-2025-002 4h
    
    # List all active tunnels
    ./manage_sting.sh support tunnel list
    
    # Check specific tunnel status
    ./manage_sting.sh support tunnel status ST-2025-001
    
    # Close tunnel when support is complete
    ./manage_sting.sh support tunnel close ST-2025-001

SUPPORT FLOW:
    1. Customer: Create support ticket via Bee Chat or CLI
    2. Admin: Authorize tunnel creation  
    3. System: Generate ephemeral auth key
    4. Support: Join network using auth key
    5. Support: Access customer STING system securely
    6. System: Auto-expire tunnel after duration

SECURITY:
    - Ephemeral access only (auto-cleanup)
    - No customer network routing
    - SSH access to STING containers only
    - Complete audit trail
    - Self-hosted (no external dependencies)

EOF
}

# Main tunnel management function
main() {
    local command="$1"
    shift || true
    
    case "$command" in
        create)
            local ticket_id="$1"
            local duration="${2:-30m}"
            
            if [ -z "$ticket_id" ]; then
                log_message "[-] Ticket ID required" "ERROR"
                log_message "Usage: support tunnel create TICKET_ID [duration]" "INFO"
                return 1
            fi
            
            create_support_tunnel "$ticket_id" "community" "$duration"
            ;;
        list)
            list_support_tunnels
            ;;
        status)
            local ticket_id="$1"
            
            if [ -z "$ticket_id" ]; then
                log_message "[-] Ticket ID required" "ERROR"
                log_message "Usage: support tunnel status TICKET_ID" "INFO"
                return 1
            fi
            
            check_tunnel_status "$ticket_id"
            ;;
        close)
            local ticket_id="$1"
            
            if [ -z "$ticket_id" ]; then
                log_message "[-] Ticket ID required" "ERROR"
                log_message "Usage: support tunnel close TICKET_ID" "INFO"
                return 1
            fi
            
            close_support_tunnel "$ticket_id"
            ;;
        cleanup)
            cleanup_expired_sessions
            ;;
        headscale-status)
            get_headscale_status
            ;;
        help|--help|-h|"")
            show_tunnel_help
            ;;
        *)
            log_message "[-] Unknown tunnel command: $command" "ERROR"
            show_tunnel_help
            return 1
            ;;
    esac
}

# Run main function
main "$@"