#!/bin/bash

# Build Logging Module for STING
# Captures Docker build logs for Bee Intelligence & Enterprise Security features

# Initialize build logging directory
initialize_build_logging() {
    local install_dir="${INSTALL_DIR:-/opt/sting-ce}"
    
    # Create build logs directory if it doesn't exist in Docker volume
    docker volume inspect build_logs >/dev/null 2>&1 || docker volume create build_logs
    docker volume inspect build_analytics >/dev/null 2>&1 || docker volume create build_analytics
    
    # Create temporary container to initialize directory structure
    docker run --rm \
        -v build_logs:/var/log/builds \
        -v build_analytics:/var/log/builds/analytics \
        alpine:latest sh -c "
            mkdir -p /var/log/builds/analytics
            chmod 755 /var/log/builds /var/log/builds/analytics
            touch /var/log/builds/.initialized
            touch /var/log/builds/analytics/.initialized
        " >/dev/null 2>&1
}

# Enhanced docker build with logging
build_with_logging() {
    local service="$1"
    local build_command="$2"
    local build_type="${3:-update}"  # install, update, rebuild
    
    local timestamp=$(date -Iseconds)
    local log_file="docker-build-${service}-${timestamp}.log"
    local analytics_file="build-analytics-${service}-${timestamp}.json"
    local start_time=$(date +%s)
    
    log_message "🐝 Starting monitored build for service: $service" "INFO"
    
    # Create temporary file for build output
    local temp_log="/tmp/build_${service}_$$.log"
    local temp_analytics="/tmp/analytics_${service}_$$.json"
    
    # Initialize analytics
    cat > "$temp_analytics" <<EOF
{
    "timestamp": "$timestamp",
    "service": "$service",
    "operation": "$build_type",
    "start_time": $start_time,
    "duration_seconds": 0,
    "cache_hit_ratio": 0,
    "build_size_mb": 0,
    "success": false,
    "error_count": 0,
    "warning_count": 0,
    "docker_version": "$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',' || echo 'unknown')",
    "compose_version": "$(docker-compose --version 2>/dev/null | cut -d' ' -f4 | tr -d ',' || echo 'unknown')",
    "build_args": "$build_command"
}
EOF

    # Execute build command with logging
    {
        echo "$(date -Iseconds) [STING-BUILD] Starting build for $service"
        echo "$(date -Iseconds) [STING-BUILD] Command: $build_command"
        echo "$(date -Iseconds) [STING-BUILD] Type: $build_type"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Run build command and capture output
        if eval "$build_command" 2>&1; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            local success=true
            
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "$(date -Iseconds) [STING-BUILD] Build completed successfully in ${duration}s"
            
            # Update analytics
            local error_count=$(grep -c -i "error\|failed\|exception" "$temp_log" 2>/dev/null || echo 0)
            local warning_count=$(grep -c -i "warning\|warn" "$temp_log" 2>/dev/null || echo 0)
            local cache_hits=$(grep -c "CACHED" "$temp_log" 2>/dev/null || echo 0)
            local total_steps
            total_steps=$(grep -c "Step [0-9]*/[0-9]*" "$temp_log" 2>/dev/null | head -1 || echo 1)
            local cache_ratio=0
            if [ "$total_steps" -gt 0 ] 2>/dev/null; then
                cache_ratio=$(( (cache_hits * 100) / total_steps ))
            fi
            
            # Try to get image size (if available)
            local image_size=0
            if command -v docker >/dev/null 2>&1; then
                image_size=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "$service" | head -1 | awk '{print $2}' | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo 0)
            fi
            
            # Update analytics JSON
            jq --arg duration "$duration" \
               --arg success "true" \
               --arg errors "$error_count" \
               --arg warnings "$warning_count" \
               --arg cache_ratio "$cache_ratio" \
               --arg size "$image_size" \
               '.duration_seconds = ($duration | tonumber) | 
                .success = ($success | test("true")) |
                .error_count = ($errors | tonumber) |
                .warning_count = ($warnings | tonumber) |
                .cache_hit_ratio = ($cache_ratio | tonumber) |
                .build_size_mb = ($size | tonumber)' \
               "$temp_analytics" > "${temp_analytics}.tmp" && mv "${temp_analytics}.tmp" "$temp_analytics"
            
            return 0
        else
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "$(date -Iseconds) [STING-BUILD] Build failed after ${duration}s"
            
            # Update analytics for failure
            local error_count=$(grep -c -i "error\|failed\|exception" "$temp_log" 2>/dev/null || echo 1)
            local warning_count=$(grep -c -i "warning\|warn" "$temp_log" 2>/dev/null || echo 0)
            
            jq --arg duration "$duration" \
               --arg success "false" \
               --arg errors "$error_count" \
               --arg warnings "$warning_count" \
               '.duration_seconds = ($duration | tonumber) | 
                .success = false |
                .error_count = ($errors | tonumber) |
                .warning_count = ($warnings | tonumber)' \
               "$temp_analytics" > "${temp_analytics}.tmp" && mv "${temp_analytics}.tmp" "$temp_analytics"
            
            return 1
        fi
    } | tee "$temp_log"
    
    # Copy logs to Docker volumes
    copy_build_logs_to_volume "$temp_log" "$log_file" "$temp_analytics" "$analytics_file"
    
    # Clean up temp files
    rm -f "$temp_log" "$temp_analytics"
    
    return $?
}

# Copy build logs to Docker volumes
copy_build_logs_to_volume() {
    local temp_log="$1"
    local log_file="$2"
    local temp_analytics="$3" 
    local analytics_file="$4"
    
    # Copy logs to Docker volumes using a temporary container
    docker run --rm \
        -v build_logs:/var/log/builds \
        -v build_analytics:/var/log/builds/analytics \
        -v "$(dirname "$temp_log"):/tmp/host:ro" \
        alpine:latest sh -c "
            cp /tmp/host/$(basename "$temp_log") /var/log/builds/$log_file
            cp /tmp/host/$(basename "$temp_analytics") /var/log/builds/analytics/$analytics_file
            chmod 644 /var/log/builds/$log_file /var/log/builds/analytics/$analytics_file
        " 2>/dev/null || {
            log_message "Warning: Could not copy build logs to volumes" "WARNING"
        }
}

# Cleanup old build logs (keep last 24 hours)
cleanup_build_logs() {
    local retention_hours="${1:-24}"
    
    log_message "🧹 Cleaning up build logs older than ${retention_hours} hours" "INFO"
    
    docker run --rm \
        -v build_logs:/var/log/builds \
        -v build_analytics:/var/log/builds/analytics \
        alpine:latest sh -c "
            find /var/log/builds -name '*.log' -mtime +${retention_hours}h -delete 2>/dev/null || true
            find /var/log/builds/analytics -name '*.json' -mtime +${retention_hours}h -delete 2>/dev/null || true
        " 2>/dev/null || {
            log_message "Warning: Could not clean up old build logs" "WARNING"
        }
}

# Get build analytics summary
get_build_analytics() {
    local service="${1:-all}"
    local hours="${2:-24}"
    
    # Use a temporary container to analyze logs
    docker run --rm \
        -v build_analytics:/var/log/builds/analytics:ro \
        alpine:latest sh -c "
            if [ '$service' = 'all' ]; then
                find /var/log/builds/analytics -name '*.json' -newermt '${hours} hours ago' | head -20
            else
                find /var/log/builds/analytics -name '*${service}*.json' -newermt '${hours} hours ago' | head -10
            fi | while read file; do
                echo '--- Build Analytics ---'
                cat \"\$file\" 2>/dev/null | jq -r '\"Service: \" + .service + \", Duration: \" + (.duration_seconds | tostring) + \"s, Success: \" + (.success | tostring) + \", Errors: \" + (.error_count | tostring)'
                echo
            done
        " 2>/dev/null || echo "No analytics available"
}

# Export functions for use in other modules
export -f initialize_build_logging
export -f build_with_logging
export -f copy_build_logs_to_volume
export -f cleanup_build_logs
export -f get_build_analytics