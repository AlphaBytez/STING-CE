#!/bin/bash
# Fix for services not starting during update due to dependency timing

# Source the enhanced resilience script if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/service_startup_resilience.sh" ]; then
    source "${SCRIPT_DIR}/service_startup_resilience.sh"
    # Use enhanced version if available
    ensure_all_services_started() {
        ensure_all_services_started_enhanced "$@"
    }
else
    # Fallback to original implementation
    # Function to ensure all services are started
    ensure_all_services_started() {
        local max_attempts=3
        local attempt=1
        
        echo "Ensuring all services are started..."
        
        while [ $attempt -le $max_attempts ]; do
            # Get list of created but not started containers
            local not_started=$(docker ps -a --filter "status=created" --format "{{.Names}}" | grep "sting-ce-")
            
            if [ -z "$not_started" ]; then
                echo "✅ All services are running"
                return 0
            fi
            
            echo "⚠️  Found services not started: $not_started"
            echo "Starting services (attempt $attempt/$max_attempts)..."
            
            # Try to start them
            docker start $not_started 2>/dev/null || true
            
            # Give them a moment to start
            sleep 5
            
            ((attempt++))
        done
        
        # Final check
        not_started=$(docker ps -a --filter "status=created" --format "{{.Names}}" | grep "sting-ce-")
        if [ -n "$not_started" ]; then
            echo "❌ Failed to start services: $not_started"
            echo "You may need to manually start them with: docker start $not_started"
            return 1
        fi
        
        return 0
    }
fi

# If called directly, run the function
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    ensure_all_services_started
fi