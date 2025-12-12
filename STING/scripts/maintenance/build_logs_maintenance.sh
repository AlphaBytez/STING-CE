#!/bin/bash

# Build Logs Maintenance Script for STING
# Manages Docker build logs for Bee Intelligence & Enterprise Security

# Source required modules
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${PROJECT_ROOT}/lib/core.sh"
source "${PROJECT_ROOT}/lib/logging.sh"
source "${PROJECT_ROOT}/lib/build_logging.sh"

# Configuration
RETENTION_HOURS="${BUILD_LOG_RETENTION_HOURS:-24}"
ANALYTICS_RETENTION_DAYS="${BUILD_ANALYTICS_RETENTION_DAYS:-7}"
INSTALL_DIR="${INSTALL_DIR:-/Users/captain-wolf/.sting-ce}"

# Main maintenance function
main() {
    local action="${1:-cleanup}"
    
    case "$action" in
        "cleanup")
            cleanup_old_logs
            ;;
        "analytics")
            show_build_analytics "${2:-all}" "${3:-24}"
            ;;
        "status")
            show_build_status
            ;;
        "init")
            initialize_build_logging
            ;;
        *)
            show_usage
            ;;
    esac
}

# Cleanup old build logs
cleanup_old_logs() {
    log_message "🧹 Starting build logs maintenance" "INFO"
    
    # Cleanup regular build logs
    cleanup_build_logs "$RETENTION_HOURS"
    
    # Cleanup old analytics (longer retention)
    local analytics_hours=$((ANALYTICS_RETENTION_DAYS * 24))
    
    docker run --rm \
        -v build_analytics:/var/log/builds/analytics \
        alpine:latest sh -c "
            echo 'Cleaning analytics older than ${analytics_hours} hours...'
            find /var/log/builds/analytics -name '*.json' -mtime +${analytics_hours}h -print -delete
        " 2>/dev/null || log_message "Warning: Could not clean up old analytics" "WARNING"
    
    log_message "[+] Build logs maintenance completed" "SUCCESS"
}

# Show build analytics
show_build_analytics() {
    local service="${1:-all}"
    local hours="${2:-24}"
    
    log_message "📊 Build Analytics Report (last ${hours} hours)" "INFO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Get analytics using the build_logging function
    get_build_analytics "$service" "$hours"
    
    echo
    echo "📈 Build Performance Summary:"
    docker run --rm \
        -v build_analytics:/var/log/builds/analytics:ro \
        alpine:latest sh -c "
            if [ '$service' = 'all' ]; then
                find /var/log/builds/analytics -name '*.json' -newermt '${hours} hours ago'
            else
                find /var/log/builds/analytics -name '*${service}*.json' -newermt '${hours} hours ago'
            fi | head -20 | while read file; do
                if [ -f \"\$file\" ]; then
                    echo \" \$(basename \"\$file\")\"
                    cat \"\$file\" | grep -E '\"service\"|\"duration_seconds\"|\"success\"|\"error_count\"' | sed 's/^/  /'
                    echo
                fi
            done
        " 2>/dev/null || echo "No analytics data available"
}

# Show build status
show_build_status() {
    log_message " Build Logging Status" "INFO"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if volumes exist
    echo "📁 Docker Volumes:"
    if docker volume ls | grep -q "build_logs"; then
        echo "  [+] build_logs volume exists"
    else
        echo "  [-] build_logs volume missing"
    fi
    
    if docker volume ls | grep -q "build_analytics"; then
        echo "  [+] build_analytics volume exists"
    else
        echo "  [-] build_analytics volume missing"
    fi
    
    # Check recent builds
    echo
    echo "📊 Recent Build Activity:"
    docker run --rm \
        -v build_logs:/var/log/builds:ro \
        alpine:latest sh -c "
            find /var/log/builds -name '*.log' -type f -exec stat -c '%Y %n' {} \\; | sort -nr | head -5 | while read timestamp file; do
                date_str=\$(date -d \"@\$timestamp\" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r \$timestamp '+%Y-%m-%d %H:%M:%S')
                echo \"  \$date_str - \$(basename \"\$file\")\"
            done
        " 2>/dev/null || echo "  No recent build logs found"
    
    # Check Promtail configuration
    echo
    echo " Promtail Configuration:"
    if [ -f "${PROJECT_ROOT}/observability/promtail/config/promtail.yml" ]; then
        if grep -q "sting-build-logs" "${PROJECT_ROOT}/observability/promtail/config/promtail.yml"; then
            echo "  [+] Build logs collection configured"
        else
            echo "  [-] Build logs collection not configured"
        fi
    else
        echo "  [-] Promtail config not found"
    fi
}

# Show usage
show_usage() {
    echo "Build Logs Maintenance Script for STING"
    echo
    echo "Usage: $0 [action] [options]"
    echo
    echo "Actions:"
    echo "  cleanup              - Clean up old build logs (default)"
    echo "  analytics [service]  - Show build analytics for service (or 'all')"
    echo "  status              - Show build logging status"
    echo "  init                - Initialize build logging system"
    echo
    echo "Examples:"
    echo "  $0 cleanup"
    echo "  $0 analytics app 48"
    echo "  $0 status"
    echo
    echo "Environment Variables:"
    echo "  BUILD_LOG_RETENTION_HOURS     - Hours to keep build logs (default: 24)"
    echo "  BUILD_ANALYTICS_RETENTION_DAYS - Days to keep analytics (default: 7)"
}

# Run maintenance if called directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi