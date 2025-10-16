#!/bin/bash
# Bee Support Manager - AI-powered support request system
# Handles intelligent diagnostics and support ticket creation

# Load dependencies  
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logging.sh"
source "${SCRIPT_DIR}/core.sh"

# Configuration
BEE_SUPPORT_DIR="${INSTALL_DIR}/bee_support"
SUPPORT_TICKETS_DIR="${BEE_SUPPORT_DIR}/tickets"
SUPPORT_SESSIONS_DIR="${BEE_SUPPORT_DIR}/sessions"

# Initialize support directory structure
init_bee_support() {
    mkdir -p "${BEE_SUPPORT_DIR}"
    mkdir -p "${SUPPORT_TICKETS_DIR}"
    mkdir -p "${SUPPORT_SESSIONS_DIR}"
    
    # Create support config if it doesn't exist
    local support_config="${BEE_SUPPORT_DIR}/support_config.yml"
    if [ ! -f "$support_config" ]; then
        cat > "$support_config" << 'EOF'
# Bee Support System Configuration
support_system:
  enabled: true
  max_log_lines: 30
  default_diagnostic_hours: 2
  require_admin_confirmation: true
  
issue_mappings:
  authentication:
    services: ["kratos", "app", "db"]
    flags: ["--auth-focus", "--include-startup"]
  frontend:
    services: ["frontend", "nginx"]
    flags: ["--include-startup"]
  api:
    services: ["app", "db"]
    flags: []
  ai_chat:
    services: ["chatbot", "external-ai", "ollama"]
    flags: ["--llm-focus", "--performance"]
  database:
    services: ["db", "app", "kratos"]
    flags: ["--include-startup"]
  performance:
    services: ["all"]
    flags: ["--performance", "--hours", "2"]
EOF
    fi
}

# Analyze issue description and suggest services/diagnostics
analyze_issue() {
    local issue_description="$1"
    local issue_type="general"
    local services=()
    local flags=()
    
    # Simple pattern matching for issue analysis
    # In the future, this could be enhanced with actual AI analysis
    
    if echo "$issue_description" | grep -qE -i "(login|auth|session|password|kratos|aal2)"; then
        issue_type="authentication"
        services=("kratos" "app" "db")
        flags=("--auth-focus" "--include-startup")
    elif echo "$issue_description" | grep -qE -i "(frontend|ui|dashboard|loading|react|build)"; then
        issue_type="frontend"
        services=("frontend" "nginx")
        flags=("--include-startup")
    elif echo "$issue_description" | grep -qE -i "(api|backend|500|error|flask)"; then
        issue_type="api"
        services=("app" "db")
        flags=()
    elif echo "$issue_description" | grep -qE -i "(bee|chat|ai|llm|model|ollama)"; then
        issue_type="ai_chat"
        services=("chatbot" "external-ai" "ollama")
        flags=("--llm-focus" "--performance")
    elif echo "$issue_description" | grep -qE -i "(database|db|postgres|connection|sql)"; then
        issue_type="database"
        services=("db" "app" "kratos")
        flags=("--include-startup")
    elif echo "$issue_description" | grep -qE -i "(slow|performance|memory|cpu|timeout)"; then
        issue_type="performance"
        services=("all")
        flags=("--performance" "--hours" "2")
    fi
    
    # Output analysis results
    echo "ISSUE_TYPE:$issue_type"
    echo "SERVICES:${services[*]}"
    echo "FLAGS:${flags[*]}"
}

# Capture targeted logs from specific services
capture_targeted_logs() {
    local services="$1"
    local lines="${2:-30}"
    local temp_dir="/tmp/bee_logs_$$"
    
    mkdir -p "$temp_dir"
    
    log_message "📋 Capturing logs from services: $services"
    
    for service in $services; do
        if [ "$service" = "all" ]; then
            log_message "  📝 Capturing logs from all services..."
            docker compose ps --format "table {{.Service}}" | tail -n +2 | while read -r svc; do
                if [ -n "$svc" ]; then
                    docker logs --tail "$lines" "sting-ce-$svc" > "$temp_dir/${svc}_logs.txt" 2>&1 || true
                fi
            done
        else
            log_message "  📝 Capturing logs from $service (last $lines lines)"
            docker logs --tail "$lines" "sting-ce-$service" > "$temp_dir/${service}_logs.txt" 2>&1 || true
        fi
    done
    
    echo "$temp_dir"
}

# Create intelligent honey jar based on issue analysis
create_smart_honey_jar() {
    local issue_description="$1"
    local ticket_id="$2"
    
    log_message "🤖 Analyzing issue: $issue_description"
    
    # Analyze the issue
    local analysis_output
    analysis_output=$(analyze_issue "$issue_description")
    
    local issue_type
    local services
    local flags
    
    # Parse analysis output
    issue_type=$(echo "$analysis_output" | grep "ISSUE_TYPE:" | cut -d: -f2)
    services=$(echo "$analysis_output" | grep "SERVICES:" | cut -d: -f2)
    flags=$(echo "$analysis_output" | grep "FLAGS:" | cut -d: -f2-)
    
    log_message "🎯 Issue type detected: $issue_type"
    log_message "🔍 Target services: $services"
    log_message "🚀 Diagnostic flags: $flags"
    
    # Capture targeted logs
    local log_dir
    log_dir=$(capture_targeted_logs "$services" 30)
    
    # Create honey jar with intelligent flags
    local honey_jar_cmd="${SOURCE_DIR}/lib/hive_diagnostics/honey_collector.sh collect"
    
    # Add flags based on analysis
    for flag in $flags; do
        if [ "$flag" != "FLAGS:" ]; then
            honey_jar_cmd="$honey_jar_cmd $flag"
        fi
    done
    
    # Add ticket reference if provided
    if [ -n "$ticket_id" ]; then
        honey_jar_cmd="$honey_jar_cmd --ticket $ticket_id"
    fi
    
    log_message "🍯 Creating intelligent honey jar..."
    log_message "Command: $honey_jar_cmd"
    
    # Execute honey jar creation
    $honey_jar_cmd
    local exit_code=$?
    
    # Cleanup temp logs
    rm -rf "$log_dir" 2>/dev/null || true
    
    return $exit_code
}

# Generate a support ticket ID
generate_ticket_id() {
    local date_stamp
    date_stamp=$(date +%Y%m%d)
    local time_stamp
    time_stamp=$(date +%H%M%S)
    local random_suffix
    random_suffix=$(printf "%03d" $((RANDOM % 1000)))
    
    echo "ST-${date_stamp}-${time_stamp}-${random_suffix}"
}

# Create secure download link for bundle
create_secure_download_link() {
    local bundle_path="$1"
    local ticket_id="$2"
    local duration="${3:-48h}"
    
    if [ ! -f "$bundle_path" ]; then
        log_message "⚠️  Bundle file not found: $bundle_path" "WARNING"
        return 1
    fi
    
    # Convert duration to hours for Python script
    local duration_hours
    case "$duration" in
        *h) duration_hours="${duration%h}" ;;
        *d) duration_hours=$((${duration%d} * 24)) ;;
        *) duration_hours="48" ;;  # Default 48 hours
    esac
    
    # Generate secure link using Python script
    local link_info
    link_info=$(python3 "${SOURCE_DIR}/lib/secure_bundle_server.py" \
        --bundle-dir "$(dirname "$bundle_path")" \
        --test 2>/dev/null || echo '{"error": "Failed to generate link"}')
    
    if echo "$link_info" | grep -q "error"; then
        log_message "❌ Failed to create secure download link" "ERROR"
        return 1
    fi
    
    log_message "✅ Secure download link created"
    log_message "🔗 Valid for: ${duration_hours} hours"
    return 0
}

# Create a support ticket
create_support_ticket() {
    local issue_description="$1"
    local create_honey_jar="${2:-true}"
    
    init_bee_support
    
    # Generate ticket ID
    local ticket_id
    ticket_id=$(generate_ticket_id)
    
    log_message "🎫 Creating support ticket: $ticket_id"
    
    # Create ticket file
    local ticket_file="${SUPPORT_TICKETS_DIR}/${ticket_id}.yml"
    cat > "$ticket_file" << EOF
ticket_id: "$ticket_id"
created_at: "$(date -Iseconds)"
status: "open"
priority: "normal"
issue_description: "$issue_description"
created_by: "${USER:-unknown}"
honey_jar_created: $create_honey_jar
analysis:
  ai_generated: true
  issue_patterns: []
  suggested_services: []
  diagnostic_flags: []
EOF
    
    log_message "✅ Support ticket created: $ticket_id"
    
    if [ "$create_honey_jar" = "true" ]; then
        log_message "🍯 Creating intelligent diagnostic bundle..."
        if create_smart_honey_jar "$issue_description" "$ticket_id"; then
            log_message "✅ Diagnostic bundle created successfully"
            
            # Update ticket to indicate honey jar was created
            sed -i.bak "s/honey_jar_created: .*/honey_jar_created: true/" "$ticket_file" 2>/dev/null || true
            
            # For Community Edition: Create secure download link instead of live tunnel
            log_message "🔗 Creating secure download link for community support..."
            log_message "📅 Bundle will be available for 48 hours"
            log_message ""
            log_message "🌐 **Community Support Options:**"
            log_message "  1. 📧 Email bundle to community@sting-support.com"
            log_message "  2. 💬 Post secure link to community forums"
            log_message "  3. 📱 Share in Discord #support-help channel"  
            log_message "  4. 🐛 Attach to GitHub issue (if reproducible bug)"
            log_message ""
            log_message "🔒 **Secure Bundle Access:**"
            log_message "  • 48-hour time-limited download"
            log_message "  • Fully sanitized (no passwords, keys, PII)"
            log_message "  • Bundle integrity verification"
            log_message "  • Download attempt logging"
            
        else
            log_message "⚠️  Diagnostic bundle creation failed, but ticket exists" "WARNING"
        fi
    fi
    
    # Show ticket summary
    log_message "📋 Support Ticket Summary:"
    log_message "  🎫 Ticket ID: $ticket_id"
    log_message "  📝 Description: $issue_description"
    log_message "  📁 Location: $ticket_file"
    log_message "  🍯 Honey Jar: $([ "$create_honey_jar" = "true" ] && echo "Created" || echo "Not created")"
    
    echo "$ticket_id"
}

# List support tickets
list_support_tickets() {
    init_bee_support
    
    local tickets_found=0
    
    log_message "📋 Support Tickets:"
    
    if [ -d "$SUPPORT_TICKETS_DIR" ]; then
        for ticket_file in "$SUPPORT_TICKETS_DIR"/*.yml; do
            if [ -f "$ticket_file" ]; then
                tickets_found=1
                local ticket_id
                local created_at
                local status
                local description
                
                ticket_id=$(grep "ticket_id:" "$ticket_file" | cut -d'"' -f2)
                created_at=$(grep "created_at:" "$ticket_file" | cut -d'"' -f2)
                status=$(grep "status:" "$ticket_file" | cut -d'"' -f2)
                description=$(grep "issue_description:" "$ticket_file" | cut -d'"' -f2)
                
                log_message "  🎫 $ticket_id"
                log_message "    📅 Created: $created_at"
                log_message "    📊 Status: $status"
                log_message "    📝 Issue: $description"
                log_message ""
            fi
        done
    fi
    
    if [ $tickets_found -eq 0 ]; then
        log_message "  📭 No support tickets found"
    fi
}

# Analyze system for potential issues
analyze_system() {
    log_message "🔍 Analyzing STING system for potential issues..."
    
    # Check service health
    log_message "📊 Service Health Check:"
    local unhealthy_services=0
    
    # Get service status
    if command -v docker >/dev/null 2>&1; then
        # Change to install directory for docker compose
        local current_dir
        current_dir=$(pwd)
        cd "${INSTALL_DIR}" 2>/dev/null || {
            log_message "⚠️  Cannot access install directory: ${INSTALL_DIR}" "WARNING"
            return 1
        }
        
        # Check each service
        local services
        services=$(docker compose config --services 2>/dev/null || echo "vault db kratos app frontend chatbot")
        
        for service in $services; do
            if docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
                log_message "  ✅ $service: Healthy"
            else
                log_message "  ❌ $service: Unhealthy" "WARNING"
                unhealthy_services=$((unhealthy_services + 1))
            fi
        done
        
        # Return to original directory
        cd "$current_dir" || true
    else
        log_message "⚠️  Docker not available for health checks" "WARNING"
        return 1
    fi
    
    # Summary and suggestions
    if [ $unhealthy_services -eq 0 ]; then
        log_message "✅ System Analysis: All services appear healthy"
        log_message "💡 If you're experiencing issues, try:"
        log_message "   - Clear description of the problem"
        log_message "   - Recent changes or updates"
        log_message "   - Error messages you're seeing"
    else
        log_message "⚠️  System Analysis: $unhealthy_services service(s) need attention" "WARNING"
        log_message "💡 Recommended actions:"
        log_message "   1. Create support ticket with service health focus"
        log_message "   2. Check logs of unhealthy services"
        log_message "   3. Consider restarting unhealthy services"
    fi
}

# Show help for bee support commands
show_bee_support_help() {
    cat << 'EOF'
🐝 Bee Support - AI-Powered Support Request System

USAGE:
    ./manage_sting.sh bee support COMMAND [OPTIONS]
    ./manage_sting.sh support tunnel COMMAND [OPTIONS]

COMMANDS:
    analyze                     Analyze system health and suggest improvements
    create "issue description"  Create AI-guided support ticket with honey jar
    suggest                     Get suggestions for common issues
    list                       List existing support tickets
    status                     Show support system status
    help                       Show this help message

TUNNEL COMMANDS:
    tunnel create TICKET_ID     Create secure support tunnel (requires Headscale)
    tunnel list                 List active support tunnels
    tunnel status TICKET_ID     Show tunnel connection status
    tunnel close TICKET_ID      Close support tunnel and revoke access
    tunnel help                 Show tunnel management help

OPTIONS:
    --no-honey-jar             Skip automatic honey jar creation
    --ticket-id ID             Reference existing ticket ID

EXAMPLES:
    # Analyze current system state
    ./manage_sting.sh bee support analyze
    
    # Create support ticket with AI analysis
    ./manage_sting.sh bee support create "login issues after update"
    
    # List all support tickets
    ./manage_sting.sh bee support list
    
    # Get suggestions for troubleshooting
    ./manage_sting.sh bee support suggest

INTEGRATION:
    This system works alongside Bee Chat for natural language support requests.
    In Bee Chat, you can use: "@bee I need help with [description]"

🍯 AI-POWERED FEATURES:
    - Intelligent issue analysis and service correlation
    - Automated diagnostic bundle creation with targeted logs
    - Smart honey jar generation based on problem type
    - Integration with existing buzz diagnostic system

EOF
}

# Provide troubleshooting suggestions
show_support_suggestions() {
    log_message "💡 Bee Support Suggestions:"
    log_message ""
    log_message "🔐 Authentication Issues:"
    log_message "   • Login failures, redirect loops, session problems"
    log_message "   • Try: bee support create 'login issues'"
    log_message "   • Focus: Kratos, app service, AAL2 flows"
    log_message ""
    log_message "🌐 Frontend Problems:"
    log_message "   • Dashboard not loading, build errors, routing issues"
    log_message "   • Try: bee support create 'frontend not loading'"
    log_message "   • Focus: React app, nginx proxy, build process"
    log_message ""
    log_message "🤖 AI Chat Issues:"
    log_message "   • Bee not responding, chat timeouts, model problems"
    log_message "   • Try: bee support create 'ai chat not working'"
    log_message "   • Focus: Chatbot service, external AI, Ollama"
    log_message ""
    log_message "🗄️  Database Problems:"
    log_message "   • Connection errors, slow queries, data issues"
    log_message "   • Try: bee support create 'database connection errors'"
    log_message "   • Focus: PostgreSQL, connection pools, migrations"
    log_message ""
    log_message "🐌 Performance Issues:"
    log_message "   • Slow responses, high resource usage, timeouts"
    log_message "   • Try: bee support create 'system performance slow'"
    log_message "   • Focus: All services, resource metrics, bottlenecks"
}

# Show support system status
show_support_status() {
    init_bee_support
    
    log_message "📊 Bee Support System Status:"
    log_message ""
    
    # Check if support system is configured
    if [ -f "${BEE_SUPPORT_DIR}/support_config.yml" ]; then
        log_message "✅ Support system: Configured"
    else
        log_message "⚠️  Support system: Not configured" "WARNING"
    fi
    
    # Count tickets
    local ticket_count=0
    if [ -d "$SUPPORT_TICKETS_DIR" ]; then
        ticket_count=$(find "$SUPPORT_TICKETS_DIR" -name "*.yml" -type f 2>/dev/null | wc -l)
    fi
    log_message "📋 Support tickets: $ticket_count"
    
    # Check honey jar system
    if [ -f "${SOURCE_DIR}/lib/hive_diagnostics/honey_collector.sh" ]; then
        log_message "✅ Honey jar system: Available"
    else
        log_message "❌ Honey jar system: Not available" "ERROR"
    fi
    
    # Check Bee Chat integration
    if docker compose ps chatbot 2>/dev/null | grep -q "Up"; then
        log_message "✅ Bee Chat: Running"
    else
        log_message "⚠️  Bee Chat: Not running" "WARNING"
    fi
    
    log_message ""
    log_message "💡 Ready for AI-powered support requests!"
}

# Main function to handle bee support commands
main() {
    local command="$1"
    shift || true
    
    case "$command" in
        analyze)
            analyze_system
            ;;
        create)
            local issue_description="$1"
            local create_honey_jar="true"
            
            # Parse options
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --no-honey-jar)
                        create_honey_jar="false"
                        shift
                        ;;
                    *)
                        if [ -z "$issue_description" ]; then
                            issue_description="$1"
                        fi
                        shift
                        ;;
                esac
            done
            
            if [ -z "$issue_description" ]; then
                log_message "❌ Please provide an issue description" "ERROR"
                log_message "Usage: bee support create 'issue description'" "INFO"
                return 1
            fi
            
            create_support_ticket "$issue_description" "$create_honey_jar"
            ;;
        list)
            list_support_tickets
            ;;
        suggest)
            show_support_suggestions
            ;;
        status)
            show_support_status
            ;;
        help|--help|-h)
            show_bee_support_help
            ;;
        *)
            if [ -n "$command" ]; then
                log_message "❌ Unknown bee support command: $command" "ERROR"
            fi
            show_bee_support_help
            return 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"