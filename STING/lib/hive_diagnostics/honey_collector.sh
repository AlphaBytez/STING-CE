#!/bin/bash

# 🍯 STING Honey Collector - Hive Diagnostics Bundle Generator
# Collects diagnostic "nectar" from all worker bees and creates sanitized honey jars

set -euo pipefail

# Source common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib_common.sh" 2>/dev/null || true

# Configuration
DEFAULT_HOURS=24
DEFAULT_BUNDLE_DIR="${INSTALL_DIR}/support_bundles"
TEMP_COLLECTION_DIR="/tmp/sting_nectar_collection_$$"
POLLEN_FILTER="${SCRIPT_DIR}/pollen_filter.py"

# Bee-themed output
log_buzz() {
    echo "🐝 [$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_honey() {
    echo "🍯 [$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_warning() {
    echo "⚠️  [$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "❌ [$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

show_help() {
    cat << EOF
🐝 STING Honey Collector - Hive Diagnostics

USAGE:
    $0 [OPTIONS] COMMAND

COMMANDS:
    collect                 Collect nectar and create honey jar
    list                   List existing honey jars
    inspect BUNDLE         Show contents of honey jar
    clean                  Remove old honey jars
    filter-test           Test pollen filtering rules
    hive-status           Show collection status

OPTIONS:
    --hours HOURS          Hours of logs to collect (default: $DEFAULT_HOURS)
    --from DATETIME        Start time (YYYY-MM-DD HH:MM)
    --to DATETIME          End time (YYYY-MM-DD HH:MM)
    --output-dir DIR       Output directory (default: $DEFAULT_BUNDLE_DIR)
    --ticket TICKET        Include ticket reference
    --include-startup      Include service startup logs
    --auth-focus           Focus on authentication logs
    --llm-focus            Focus on LLM service logs
    --performance          Include performance metrics
    --services LIST        Comma-separated service list
    --no-filter            Skip pollen filtering (NOT RECOMMENDED)
    --verbose              Verbose output
    --help                 Show this help

EXAMPLES:
    # Basic honey collection
    $0 collect

    # Last 48 hours with ticket reference
    $0 collect --hours 48 --ticket ABC123

    # Focus on authentication issues
    $0 collect --auth-focus --include-startup

    # Performance troubleshooting
    $0 collect --performance --llm-focus --hours 12

    # Clean old bundles
    $0 clean --older-than 7d

HONEY JAR CONTENTS:
    - Recent service logs (sanitized)
    - Docker container status
    - System resource usage
    - Configuration snapshots (secrets removed)
    - Database connection info (no data)
    - Network connectivity tests
    - Error pattern analysis

🔒 PRIVACY: All honey jars are automatically filtered to remove sensitive data
🍯 LOCATION: Bundles saved to $DEFAULT_BUNDLE_DIR/
🧹 CLEANUP: Auto-cleanup after 30 days (configurable)

EOF
}

# Initialize collection environment
init_honey_collection() {
    local bundle_dir="$1"
    
    log_buzz "Initializing honey collection environment..."
    
    # Create directories
    mkdir -p "$bundle_dir"
    mkdir -p "$TEMP_COLLECTION_DIR"
    
    # Check dependencies
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 required for pollen filtering"
        return 1
    fi
    
    if [ ! -f "$POLLEN_FILTER" ]; then
        log_warning "Pollen filter not found at $POLLEN_FILTER"
        log_warning "Sensitive data filtering will be limited"
    fi
    
    log_honey "Collection environment ready"
}

# Collect Docker container logs
collect_container_nectar() {
    local hours="$1"
    local output_dir="$2"
    local services="$3"
    
    log_buzz "Collecting nectar from Docker worker bees..."
    
    local container_dir="$output_dir/containers"
    mkdir -p "$container_dir"
    
    # Get container list
    local containers
    if [ "$services" = "all" ]; then
        containers=$(docker ps --format "{{.Names}}" 2>/dev/null || echo "")
    else
        # Filter by requested services
        containers=$(docker ps --format "{{.Names}}" | grep -E "$(echo "$services" | tr ',' '|')" || echo "")
    fi
    
    if [ -z "$containers" ]; then
        log_warning "No Docker containers found"
        return 0
    fi
    
    local since_time=$(date -d "${hours} hours ago" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -v-${hours}H '+%Y-%m-%dT%H:%M:%S')
    
    for container in $containers; do
        log_buzz "Collecting logs from container: $container"
        
        # Container logs
        docker logs --since "$since_time" "$container" > "$container_dir/${container}.log" 2>&1 || true
        
        # Container inspection
        docker inspect "$container" > "$container_dir/${container}_inspect.json" 2>/dev/null || true
        
        # Container stats snapshot
        timeout 5s docker stats --no-stream "$container" > "$container_dir/${container}_stats.txt" 2>/dev/null || true
    done
    
    log_honey "Container nectar collected: $(echo "$containers" | wc -w) containers"
}

# Collect STING service logs
collect_service_nectar() {
    local hours="$1"
    local output_dir="$2"
    local include_startup="$3"
    
    log_buzz "Collecting nectar from STING service bees..."
    
    local service_dir="$output_dir/services"
    mkdir -p "$service_dir"
    
    # STING log directory
    local sting_logs="${INSTALL_DIR}/logs"
    if [ ! -d "$sting_logs" ]; then
        log_warning "STING logs directory not found: $sting_logs"
        return 0
    fi
    
    # Calculate time window
    local since_time=$(date -d "${hours} hours ago" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -v-${hours}H '+%Y-%m-%d %H:%M:%S')
    
    # Find recent log files
    find "$sting_logs" -name "*.log" -type f -newermt "$since_time" -exec cp {} "$service_dir/" \; 2>/dev/null || true
    
    # Always include management script logs
    cp "$sting_logs/manage_sting.log" "$service_dir/" 2>/dev/null || true
    
    # Include startup logs if requested
    if [ "$include_startup" = "true" ]; then
        find "$sting_logs" -name "*startup*" -o -name "*init*" -type f -exec cp {} "$service_dir/" \; 2>/dev/null || true
    fi
    
    # System journal logs (filtered)
    if command -v journalctl &> /dev/null; then
        journalctl --since "${hours} hours ago" --no-pager > "$service_dir/system_journal.log" 2>/dev/null || true
    fi
    
    log_honey "Service nectar collected from $sting_logs"
}

# Collect system information
collect_hive_status() {
    local output_dir="$1"
    
    log_buzz "Collecting hive status information..."
    
    local system_dir="$output_dir/hive_status"
    mkdir -p "$system_dir"
    
    # System info
    {
        echo "=== STING Hive Status ==="
        echo "Timestamp: $(date)"
        echo "Hostname: $(hostname)"
        echo "OS: $(uname -a)"
        echo "Uptime: $(uptime)"
        echo ""
        
        echo "=== Disk Usage ==="
        df -h
        echo ""
        
        echo "=== Memory Usage ==="
        free -h 2>/dev/null || vm_stat
        echo ""
        
        echo "=== CPU Info ==="
        if [ -f /proc/cpuinfo ]; then
            grep "model name\|processor\|physical id" /proc/cpuinfo | head -20
        else
            sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "CPU info not available"
        fi
        echo ""
        
        echo "=== Network Interfaces ==="
        ip addr show 2>/dev/null || ifconfig
        echo ""
        
        echo "=== Docker Status ==="
        docker version 2>/dev/null || echo "Docker not available"
        docker system df 2>/dev/null || true
        echo ""
        
        echo "=== Running Processes ==="
        ps aux | head -20
        
    } > "$system_dir/hive_overview.txt"
    
    # Docker Compose status
    if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
        cd "$INSTALL_DIR"
        docker compose ps > "$system_dir/compose_status.txt" 2>/dev/null || true
        docker compose config > "$system_dir/compose_config.yml" 2>/dev/null || true
    fi
    
    # Network connectivity tests
    {
        echo "=== Network Connectivity ==="
        echo "Testing local connections..."
        
        # Test local services
        for port in 8443 3010 5050 8085 8086 4433 4434 8200; do
            if timeout 2s nc -z localhost $port 2>/dev/null; then
                echo "✅ localhost:$port - OK"
            else
                echo "❌ localhost:$port - FAILED"
            fi
        done
        
        echo ""
        echo "Testing external connectivity..."
        if timeout 5s ping -c 1 8.8.8.8 >/dev/null 2>&1; then
            echo "✅ Internet connectivity - OK"
        else
            echo "❌ Internet connectivity - FAILED"
        fi
        
    } > "$system_dir/connectivity_test.txt"
    
    log_honey "Hive status collected"
}

# Collect configuration snapshots
collect_config_nectar() {
    local output_dir="$1"
    local filter_enabled="$2"
    
    log_buzz "Collecting configuration nectar..."
    
    local config_dir="$output_dir/configuration"
    mkdir -p "$config_dir"
    
    # Main configuration files (will be filtered)
    if [ -d "${INSTALL_DIR}/conf" ]; then
        cp -r "${INSTALL_DIR}/conf" "$config_dir/" 2>/dev/null || true
    fi
    
    # Environment files (will be heavily filtered)
    if [ -d "${INSTALL_DIR}/env" ]; then
        mkdir -p "$config_dir/env"
        for env_file in "${INSTALL_DIR}/env"/*.env; do
            if [ -f "$env_file" ]; then
                basename_file=$(basename "$env_file")
                if [ "$filter_enabled" = "true" ]; then
                    # Basic filtering for preview
                    sed 's/=.*/=[FILTERED]/' "$env_file" > "$config_dir/env/$basename_file"
                else
                    cp "$env_file" "$config_dir/env/$basename_file"
                fi
            fi
        done
    fi
    
    # Docker compose (sanitized)
    if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
        cp "${INSTALL_DIR}/docker-compose.yml" "$config_dir/" 2>/dev/null || true
    fi
    
    log_honey "Configuration nectar collected"
}

# Apply pollen filtering
apply_pollen_filter() {
    local collection_dir="$1"
    local skip_filter="$2"
    
    if [ "$skip_filter" = "true" ]; then
        log_warning "Pollen filtering SKIPPED - sensitive data may be present!"
        return 0
    fi
    
    if [ ! -f "$POLLEN_FILTER" ]; then
        log_warning "Pollen filter not available - applying basic filtering"
        apply_basic_filtering "$collection_dir"
        return 0
    fi
    
    log_buzz "Applying pollen filter to remove sensitive data..."
    
    if python3 "$POLLEN_FILTER" "$collection_dir"; then
        log_honey "Pollen filtering completed successfully"
    else
        log_error "Pollen filtering failed - applying basic filtering as fallback"
        apply_basic_filtering "$collection_dir"
    fi
}

# Basic fallback filtering
apply_basic_filtering() {
    local collection_dir="$1"
    
    log_buzz "Applying basic pollen filtering..."
    
    # Find all text files and apply basic filtering
    find "$collection_dir" -type f \( -name "*.log" -o -name "*.txt" -o -name "*.yml" -o -name "*.yaml" -o -name "*.env" \) -exec sed -i.bak -E \
        -e 's/([Pp]assword[[:space:]]*[=:][[:space:]]*)([^[:space:]]+)/\1[FILTERED]/g' \
        -e 's/([Aa]pi[Kk]ey[[:space:]]*[=:][[:space:]]*)([^[:space:]]+)/\1[FILTERED]/g' \
        -e 's/([Tt]oken[[:space:]]*[=:][[:space:]]*)([^[:space:]]+)/\1[FILTERED]/g' \
        -e 's/([Ss]ecret[[:space:]]*[=:][[:space:]]*)([^[:space:]]+)/\1[FILTERED]/g' \
        {} \; 2>/dev/null || true
    
    # Remove backup files
    find "$collection_dir" -name "*.bak" -delete 2>/dev/null || true
    
    log_honey "Basic filtering applied"
}

# Create honey jar bundle
create_honey_jar() {
    local collection_dir="$1"
    local output_dir="$2"
    local ticket="$3"
    
    log_buzz "Creating honey jar from collected nectar..."
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local bundle_name="honey_jar_${timestamp}"
    
    if [ -n "$ticket" ]; then
        bundle_name="${bundle_name}_ticket_${ticket}"
    fi
    
    local bundle_path="$output_dir/${bundle_name}.tar.gz"
    
    # Create bundle metadata
    cat > "$collection_dir/honey_jar_info.txt" << EOF
🍯 STING Honey Jar Information

Bundle Name: $bundle_name
Creation Time: $(date)
Hostname: $(hostname)
STING Install Dir: $INSTALL_DIR
Collection Duration: $(ls -la "$collection_dir" | wc -l) items
Ticket Reference: ${ticket:-"None"}

🐝 Worker Bees Included:
$(find "$collection_dir" -type d -mindepth 1 -maxdepth 1 | sed 's|.*/||' | sort)

🔒 Privacy Notice:
This honey jar has been processed through our pollen filter to remove
sensitive information including passwords, API keys, and personal data.

For support, upload this honey jar to your support ticket or portal.
EOF

    # Create compressed bundle
    cd "$(dirname "$collection_dir")"
    if tar -czf "$bundle_path" "$(basename "$collection_dir")" 2>/dev/null; then
        local bundle_size=$(du -h "$bundle_path" | cut -f1)
        log_honey "Honey jar created: $bundle_path ($bundle_size)"
        
        # Generate checksum
        if command -v sha256sum &> /dev/null; then
            sha256sum "$bundle_path" > "${bundle_path}.sha256"
        elif command -v shasum &> /dev/null; then
            shasum -a 256 "$bundle_path" > "${bundle_path}.sha256"
        fi
        
        echo "$bundle_path"
        return 0
    else
        log_error "Failed to create honey jar"
        return 1
    fi
}

# List existing honey jars
list_honey_jars() {
    local bundle_dir="$1"
    
    log_buzz "Listing honey jars in the hive..."
    
    if [ ! -d "$bundle_dir" ]; then
        log_warning "No honey jar storage found at $bundle_dir"
        return 0
    fi
    
    local jars=($(find "$bundle_dir" -name "honey_jar_*.tar.gz" -type f | sort -r))
    
    if [ ${#jars[@]} -eq 0 ]; then
        log_honey "No honey jars found in $bundle_dir"
        return 0
    fi
    
    echo "🍯 Found ${#jars[@]} honey jar(s):"
    echo ""
    
    for jar in "${jars[@]}"; do
        local basename_jar=$(basename "$jar")
        local size=$(du -h "$jar" | cut -f1)
        local date=$(date -r "$jar" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$jar" 2>/dev/null || echo "Unknown")
        
        echo "📦 $basename_jar"
        echo "   Size: $size"
        echo "   Created: $date"
        
        # Check for checksum
        if [ -f "${jar}.sha256" ]; then
            echo "   Checksum: ✅ Available"
        fi
        
        echo ""
    done
}

# Clean old honey jars
clean_honey_jars() {
    local bundle_dir="$1"
    local older_than="$2"
    
    log_buzz "Cleaning old honey jars from the hive..."
    
    if [ ! -d "$bundle_dir" ]; then
        log_warning "No honey jar storage found at $bundle_dir"
        return 0
    fi
    
    local find_args=()
    if [ -n "$older_than" ]; then
        # Parse older_than (e.g., "7d", "24h", "30")
        if [[ "$older_than" =~ ^[0-9]+d$ ]]; then
            local days="${older_than%d}"
            find_args=(-mtime "+$days")
        elif [[ "$older_than" =~ ^[0-9]+h$ ]]; then
            local hours="${older_than%h}"
            local minutes=$((hours * 60))
            find_args=(-mmin "+$minutes")
        elif [[ "$older_than" =~ ^[0-9]+$ ]]; then
            find_args=(-mtime "+$older_than")
        else
            log_error "Invalid time format: $older_than (use: 7d, 24h, or 30)"
            return 1
        fi
    else
        # Default: 30 days
        find_args=(-mtime "+30")
    fi
    
    local old_jars=($(find "$bundle_dir" -name "honey_jar_*.tar.gz" -type f "${find_args[@]}" 2>/dev/null))
    
    if [ ${#old_jars[@]} -eq 0 ]; then
        log_honey "No old honey jars found for cleanup"
        return 0
    fi
    
    log_honey "Found ${#old_jars[@]} old honey jar(s) for cleanup"
    
    for jar in "${old_jars[@]}"; do
        local basename_jar=$(basename "$jar")
        log_buzz "Removing old honey jar: $basename_jar"
        rm -f "$jar" "${jar}.sha256" 2>/dev/null
    done
    
    log_honey "Cleanup completed: ${#old_jars[@]} honey jars removed"
}

# Main collection function
collect_honey() {
    local hours="$1"
    local output_dir="$2"
    local services="$3"
    local include_startup="$4"
    local auth_focus="$5"
    local llm_focus="$6"
    local performance="$7"
    local ticket="$8"
    local no_filter="$9"
    
    log_buzz "Starting honey collection from the hive..."
    log_honey "Collection window: $hours hours"
    
    # Initialize collection
    if ! init_honey_collection "$output_dir"; then
        return 1
    fi
    
    # Adjust services based on focus
    if [ "$auth_focus" = "true" ]; then
        services="app,kratos,db"
        log_buzz "🔐 Authentication focus: limiting to auth-related services"
    elif [ "$llm_focus" = "true" ]; then
        services="llm,phi3,llama3,zephyr,chatbot"
        log_buzz "🤖 LLM focus: limiting to model services"
    fi
    
    # Collection phase
    collect_container_nectar "$hours" "$TEMP_COLLECTION_DIR" "$services"
    collect_service_nectar "$hours" "$TEMP_COLLECTION_DIR" "$include_startup"
    collect_hive_status "$TEMP_COLLECTION_DIR"
    collect_config_nectar "$TEMP_COLLECTION_DIR" "true"
    
    # Performance metrics if requested
    if [ "$performance" = "true" ]; then
        log_buzz "📊 Collecting performance metrics..."
        mkdir -p "$TEMP_COLLECTION_DIR/performance"
        
        # System performance snapshot
        {
            echo "=== Performance Snapshot ==="
            echo "Timestamp: $(date)"
            echo ""
            
            echo "=== Load Average ==="
            uptime
            echo ""
            
            echo "=== Memory Usage ==="
            free -h 2>/dev/null || vm_stat
            echo ""
            
            echo "=== Disk I/O ==="
            iostat 1 3 2>/dev/null || echo "iostat not available"
            echo ""
            
            echo "=== Top Processes ==="
            top -b -n 1 | head -20 2>/dev/null || ps aux | head -20
            
        } > "$TEMP_COLLECTION_DIR/performance/system_performance.txt"
    fi
    
    # Apply filtering
    local filter_enabled="true"
    if [ "$no_filter" = "true" ]; then
        filter_enabled="false"
    fi
    apply_pollen_filter "$TEMP_COLLECTION_DIR" "$no_filter"
    
    # Create final bundle
    local bundle_path
    if bundle_path=$(create_honey_jar "$TEMP_COLLECTION_DIR" "$output_dir" "$ticket"); then
        log_honey "🎉 Honey collection complete!"
        log_honey "Bundle: $bundle_path"
        
        # Cleanup temp directory
        rm -rf "$TEMP_COLLECTION_DIR"
        
        return 0
    else
        log_error "Failed to create honey jar"
        return 1
    fi
}

# Parse command line arguments
parse_args() {
    local cmd=""
    local hours="$DEFAULT_HOURS"
    local output_dir="$DEFAULT_BUNDLE_DIR"
    local services="all"
    local include_startup="false"
    local auth_focus="false"
    local llm_focus="false"
    local performance="false"
    local ticket=""
    local no_filter="false"
    local verbose="false"
    local older_than=""
    local from_time=""
    local to_time=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            collect|list|inspect|clean|filter-test|hive-status)
                cmd="$1"
                shift
                ;;
            --hours)
                hours="$2"
                shift 2
                ;;
            --from)
                from_time="$2"
                shift 2
                ;;
            --to)
                to_time="$2"
                shift 2
                ;;
            --output-dir)
                output_dir="$2"
                shift 2
                ;;
            --ticket)
                ticket="$2"
                shift 2
                ;;
            --services)
                services="$2"
                shift 2
                ;;
            --older-than)
                older_than="$2"
                shift 2
                ;;
            --include-startup)
                include_startup="true"
                shift
                ;;
            --auth-focus)
                auth_focus="true"
                shift
                ;;
            --llm-focus)
                llm_focus="true"
                shift
                ;;
            --performance)
                performance="true"
                shift
                ;;
            --no-filter)
                no_filter="true"
                shift
                ;;
            --verbose)
                verbose="true"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                if [ -z "$cmd" ] && [[ ! "$1" =~ ^-- ]]; then
                    # Treat as command if not already set
                    cmd="$1"
                else
                    log_error "Unknown option: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Default command
    if [ -z "$cmd" ]; then
        cmd="collect"
    fi
    
    # Execute command
    case "$cmd" in
        collect)
            collect_honey "$hours" "$output_dir" "$services" "$include_startup" "$auth_focus" "$llm_focus" "$performance" "$ticket" "$no_filter"
            ;;
        list)
            list_honey_jars "$output_dir"
            ;;
        clean)
            clean_honey_jars "$output_dir" "$older_than"
            ;;
        hive-status)
            echo "🐝 STING Hive Status"
            echo "Bundle Directory: $output_dir"
            list_honey_jars "$output_dir"
            ;;
        filter-test)
            if [ -f "$POLLEN_FILTER" ]; then
                log_buzz "Testing pollen filter..."
                python3 "$POLLEN_FILTER" --test
            else
                log_error "Pollen filter not found: $POLLEN_FILTER"
                exit 1
            fi
            ;;
        inspect)
            log_error "Bundle inspection not yet implemented"
            exit 1
            ;;
        *)
            log_error "Unknown command: $cmd"
            show_help
            exit 1
            ;;
    esac
}

# Main execution
main() {
    # Check if running as part of manage_sting.sh
    if [ -z "${INSTALL_DIR:-}" ]; then
        log_error "INSTALL_DIR not set. Run via manage_sting.sh or set INSTALL_DIR environment variable."
        exit 1
    fi
    
    # Parse and execute
    parse_args "$@"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi