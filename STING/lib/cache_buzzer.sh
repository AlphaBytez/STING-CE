#!/bin/bash
# Cache Busting Functions for STING Docker Operations
# Ensures true cache-free rebuilds by clearing all Docker artifacts

# Source build logging for Bee Intelligence
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/build_logging.sh" ]; then
    source "${SCRIPT_DIR}/build_logging.sh"
fi

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Aggressive cache clearing function
clear_docker_cache() {
    local clear_level="${1:-full}"  # full, moderate, minimal, service-specific
    local service_name="${2:-}"     # Optional service name for targeted clearing
    
    echo -e "${BLUE}🧹 Clearing Docker cache (level: $clear_level)...${NC}"
    
    case "$clear_level" in
        "service")
            if [ -z "$service_name" ]; then
                echo -e "${RED}❌ Service name required for service-specific cache clearing${NC}"
                return 1
            fi
            echo -e "${YELLOW}Service-specific cache clear for: $service_name${NC}"
            
            # Stop and remove the specific service container
            docker ps --format '{{.Names}}' | grep "^sting-ce-${service_name}$" | xargs -r docker stop
            docker ps -a --format '{{.Names}}' | grep "^sting-ce-${service_name}$" | xargs -r docker rm -f
            
            # Remove the specific service image
            docker images --format '{{.Repository}}:{{.Tag}}' | grep "^sting-ce-${service_name}:latest$" | xargs -r docker rmi -f
            
            # Clear build cache
            docker builder prune -af
            docker buildx prune -af
            ;;
            
        "full")
            echo -e "${YELLOW}⚠️  Full cache clear - this will remove ALL unused Docker data${NC}"
            # Stop all STING containers first
            docker ps --format '{{.Names}}' | grep '^sting-ce-' | xargs -r docker stop
            
            # Remove all STING containers
            docker ps -a --format '{{.Names}}' | grep '^sting-ce-' | xargs -r docker rm -f
            
            # Remove all STING images
            docker images --format '{{.Repository}}:{{.Tag}}' | grep '^sting-ce-' | xargs -r docker rmi -f
            
            # Clear build cache
            docker builder prune -af
            
            # Clear all unused data - but protect named volumes
            # List STING volumes that should be preserved
            echo -e "${YELLOW}Preserving critical data volumes...${NC}"
            docker volume ls --format '{{.Name}}' | grep -E '(postgres_data|vault-data|vault-logs|vault-file|redis_data)' || true
            
            # Prune system but preserve the sting_local network
            # Note: docker system prune removes unused networks, so we need to be careful
            docker container prune -f
            docker image prune -af
            docker volume prune -f
            # Don't use 'docker system prune' as it removes custom networks!
            
            # Clear buildx cache
            docker buildx prune -af
            ;;
            
        "moderate")
            echo -e "${YELLOW}Moderate cache clear - removing build cache and unused images${NC}"
            # Clear build cache
            docker builder prune -af
            
            # Remove dangling images
            docker image prune -af
            
            # Clear buildx cache  
            docker buildx prune -af
            ;;
            
        "minimal")
            echo -e "${YELLOW}Minimal cache clear - build cache only${NC}"
            # Clear only build cache
            docker builder prune -af
            docker buildx prune -af
            ;;
    esac
    
    echo -e "${GREEN}✅ Cache clearing complete${NC}"
}

# Enhanced build function with proper cache busting
build_docker_services_nocache() {
    local service="$1"
    local cache_level="${2:-moderate}"  # full, moderate, minimal, skip
    
    echo -e "${BLUE}🔨 Building ${service:-all} services with enhanced cache busting...${NC}"
    
    # Clear cache if requested
    if [ "$cache_level" != "skip" ]; then
        # Handle special frontend-extreme cache level
        if [ "$cache_level" = "frontend-extreme" ]; then
            # Force service-specific clearing with aggressive options for frontend
            clear_docker_cache "service" "$service"
        # If updating a specific service, use service-specific clearing
        elif [ -n "$service" ] && [ "$cache_level" != "full" ]; then
            clear_docker_cache "service" "$service"
        else
            clear_docker_cache "$cache_level"
        fi
    fi
    
    # Ensure we're in the right directory
    local compose_dir="${INSTALL_DIR:-/Users/captain-wolf/.sting-ce}"
    if [ ! -f "$compose_dir/docker-compose.yml" ]; then
        echo -e "${RED}❌ docker-compose.yml not found in $compose_dir${NC}"
        return 1
    fi
    
    # Change to the compose directory
    cd "$compose_dir" || {
        echo -e "${RED}❌ Failed to change to directory: $compose_dir${NC}"
        return 1
    }
    
    # Initialize buildx builder if not exists
    # First, clean up any existing problematic builders
    docker buildx rm sting-builder &>/dev/null || true
    
    # Try to use default builder first to avoid segfaults
    echo -e "${BLUE}Using default Docker builder to avoid segfault issues...${NC}"
    docker buildx use default &>/dev/null || true
    
    # Optionally try to create custom builder (but continue if it fails)
    if false; then  # Disabled for now due to segfault
        if ! docker buildx inspect sting-builder &>/dev/null; then
            echo -e "${BLUE}Creating buildx builder 'sting-builder'...${NC}"
            docker buildx create --name sting-builder --driver docker-container --use || {
                echo -e "${YELLOW}⚠️  Failed to create custom builder, using default${NC}"
                docker buildx use default || true
            }
        else
            docker buildx use sting-builder || docker buildx use default
        fi
    fi
    
    # Add build arguments to force cache busting
    local build_args="--build-arg CACHEBUST=$(date +%s) --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    # Disable BuildKit inline cache to ensure fresh builds
    export BUILDKIT_INLINE_CACHE=0
    
    # Verify files are synced before building
    if [ -n "$service" ]; then
        verify_file_sync "$service"
    fi
    
    # Initialize build logging for Bee Intelligence
    if command -v initialize_build_logging >/dev/null 2>&1; then
        initialize_build_logging
    fi

    if [ -z "$service" ]; then
        # Build all services with enhanced cache busting and logging
        echo -e "${BLUE}Building all services...${NC}"
        local build_cmd="docker compose build --no-cache $build_args"
        
        if command -v build_with_logging >/dev/null 2>&1; then
            build_with_logging "all-services" "$build_cmd" "rebuild"
        else
            $build_cmd
        fi
    else
        # Build specific service with enhanced cache busting and logging  
        echo -e "${BLUE}Building service: $service${NC}"
        local build_cmd="docker compose build --no-cache $build_args \"$service\""
        
        if command -v build_with_logging >/dev/null 2>&1; then
            build_with_logging "$service" "$build_cmd" "update"
        else
            eval "$build_cmd"
        fi
    fi
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Build completed successfully${NC}"
    else
        echo -e "${RED}❌ Build failed with exit code $exit_code${NC}"
    fi
    
    return $exit_code
}

# Verify files are synced before building
verify_file_sync() {
    local service="$1"
    local project_dir="${PROJECT_DIR:-/Users/captain-wolf/Documents/GitHub/STING-CE/STING}"
    local install_dir="${INSTALL_DIR:-/Users/captain-wolf/.sting-ce}"
    
    echo -e "${BLUE}🔍 Verifying file sync for ${service:-all services}...${NC}"
    
    # Map service names to directories
    case "$service" in
        app)
            local src_dir="$project_dir/app"
            local dst_dir="$install_dir/app"
            ;;
        frontend)
            local src_dir="$project_dir/frontend"
            local dst_dir="$install_dir/frontend"
            ;;
        chatbot)
            local src_dir="$project_dir/chatbot"
            local dst_dir="$install_dir/chatbot"
            ;;
        *)
            # For other services or all services, skip verification
            echo -e "${YELLOW}⚠️  File sync verification not implemented for: ${service:-all}${NC}"
            return 0
            ;;
    esac
    
    # Check if source directory exists
    if [ ! -d "$src_dir" ]; then
        echo -e "${RED}❌ Source directory not found: $src_dir${NC}"
        return 1
    fi
    
    # Ensure destination directory exists
    mkdir -p "$dst_dir"
    
    # Compare key files
    local files_differ=false
    for file in $(find "$src_dir" -name "*.py" -o -name "*.js" -o -name "*.jsx" -type f | head -10); do
        local rel_path="${file#$src_dir/}"
        local dst_file="$dst_dir/$rel_path"
        
        if [ -f "$dst_file" ]; then
            if ! cmp -s "$file" "$dst_file"; then
                echo -e "${YELLOW}⚠️  File differs: $rel_path${NC}"
                files_differ=true
            fi
        else
            echo -e "${YELLOW}⚠️  File missing in install dir: $rel_path${NC}"
            files_differ=true
        fi
    done
    
    if [ "$files_differ" = "true" ]; then
        echo -e "${YELLOW}📋 Copying updated files...${NC}"
        rsync -av --delete "$src_dir/" "$dst_dir/"
        echo -e "${GREEN}✅ Files synced successfully${NC}"
    else
        echo -e "${GREEN}✅ Files are already in sync${NC}"
    fi
    
    return 0
}

# Function to validate that containers were actually rebuilt
validate_fresh_build() {
    local container="$1"
    local max_age_minutes="${2:-30}"  # Consider fresh if built within last 30 minutes
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${RED}❌ Container $container not running${NC}"
        return 1
    fi
    
    local created=$(docker inspect "$container" --format='{{.Created}}' 2>/dev/null)
    if [ -z "$created" ]; then
        echo -e "${RED}❌ Could not get creation time for $container${NC}"
        return 1
    fi
    
    # Convert to Unix timestamp (simplified for macOS compatibility)
    local created_unix=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${created%.*}" "+%s" 2>/dev/null || echo "0")
    local current_unix=$(date +%s)
    local age_minutes=$(((current_unix - created_unix) / 60))
    
    if [ $age_minutes -le $max_age_minutes ]; then
        echo -e "${GREEN}✅ Container $container is fresh (${age_minutes}m old)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Container $container might be stale (${age_minutes}m old)${NC}"
        return 1
    fi
}

# Main function for complete fresh rebuild
fresh_rebuild() {
    local service="$1"
    local cache_level="${2:-full}"
    
    echo -e "${BLUE}🚀 Starting fresh rebuild process...${NC}"
    
    # Step 1: Clear cache
    clear_docker_cache "$cache_level"
    
    # Step 2: Build services
    build_docker_services_nocache "$service" "skip"
    local build_result=$?
    
    if [ $build_result -ne 0 ]; then
        echo -e "${RED}❌ Fresh rebuild failed${NC}"
        return $build_result
    fi
    
    # Step 3: Start services
    echo -e "${BLUE}Starting services...${NC}"
    docker compose up -d
    
    # Step 4: Validate freshness
    echo -e "${BLUE}Validating fresh build...${NC}"
    local validation_failed=false
    
    if [ -z "$service" ]; then
        # Check all STING containers
        for container in sting-ce-app sting-ce-frontend sting-ce-kratos sting-ce-chatbot; do
            if ! validate_fresh_build "$container" 10; then
                validation_failed=true
            fi
        done
    else
        if ! validate_fresh_build "sting-ce-$service" 10; then
            validation_failed=true
        fi
    fi
    
    if [ "$validation_failed" = "true" ]; then
        echo -e "${YELLOW}⚠️  Some containers may not be fresh - consider running validation script${NC}"
        return 2
    fi
    
    echo -e "${GREEN}✅ Fresh rebuild completed successfully${NC}"
    return 0
}