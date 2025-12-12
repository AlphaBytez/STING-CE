#!/bin/bash
# Container Freshness Validation Script
# Detects if containers were actually rebuilt from scratch or used cached layers

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STING_CONTAINERS=(
    "sting-ce-app"
    "sting-ce-frontend" 
    "sting-ce-kratos"
    "sting-ce-chatbot"
    "sting-ce-knowledge"
    "sting-ce-messaging"
    "sting-ce-external-ai"
    "sting-ce-db"
    "sting-ce-vault"
)

# Files to check for build validation
declare -A VALIDATION_FILES=(
    ["sting-ce-app"]="/app/models/passkey_models.py"
    ["sting-ce-frontend"]="/app/src/index.js"
    ["sting-ce-kratos"]="/etc/config/kratos/identity.schema.json"
    ["sting-ce-chatbot"]="/app/bee_server.py"
)

echo -e "${BLUE}=== STING Container Freshness Validation ===${NC}"
echo "Checking if containers were actually rebuilt..."
echo

# Function to get container creation time
get_container_created() {
    local container=$1
    docker inspect "$container" --format='{{.Created}}' 2>/dev/null || echo "NOT_FOUND"
}

# Function to get image creation time  
get_image_created() {
    local container=$1
    local image_id=$(docker inspect "$container" --format='{{.Image}}' 2>/dev/null || echo "")
    if [[ -n "$image_id" ]]; then
        docker inspect "$image_id" --format='{{.Created}}' 2>/dev/null || echo "NOT_FOUND"
    else
        echo "NOT_FOUND"
    fi
}

# Function to check if critical files exist
check_critical_files() {
    local container=$1
    local file_path=${VALIDATION_FILES[$container]:-""}
    
    if [[ -n "$file_path" ]]; then
        if docker exec "$container" test -f "$file_path" 2>/dev/null; then
            echo -e "${GREEN}[+]${NC}"
        else
            echo -e "${RED}[-] Missing: $file_path${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}○${NC}"
    fi
    return 0
}

# Function to get file hash from container
get_file_hash() {
    local container=$1
    local file_path=$2
    docker exec "$container" sha256sum "$file_path" 2>/dev/null | cut -d' ' -f1 || echo "HASH_ERROR"
}

# Function to convert Docker timestamp to Unix timestamp
docker_time_to_unix() {
    local docker_time=$1
    # Convert Docker's RFC3339 format to Unix timestamp
    date -j -f "%Y-%m-%dT%H:%M:%S" "${docker_time%.*}" "+%s" 2>/dev/null || echo "0"
}

# Current time for comparison
current_time=$(date +%s)
rebuild_threshold=$((current_time - 3600)) # Consider fresh if built within last hour

echo -e "${BLUE}Container Status Report:${NC}"
echo "----------------------------------------"
printf "%-20s %-12s %-12s %-8s %-15s\n" "Container" "Status" "Age" "Files" "Freshness"
echo "----------------------------------------"

has_issues=false

for container in "${STING_CONTAINERS[@]}"; do
    # Check if container exists and is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        printf "%-20s %-12s %-12s %-8s %-15s\n" "$container" "${RED}STOPPED${NC}" "N/A" "N/A" "${RED}ISSUE${NC}"
        has_issues=true
        continue
    fi
    
    # Get container and image creation times
    container_created=$(get_container_created "$container")
    image_created=$(get_image_created "$container")
    
    if [[ "$container_created" == "NOT_FOUND" ]]; then
        printf "%-20s %-12s %-12s %-8s %-15s\n" "$container" "${RED}ERROR${NC}" "N/A" "N/A" "${RED}ISSUE${NC}"
        has_issues=true
        continue
    fi
    
    # Calculate age
    container_unix=$(docker_time_to_unix "$container_created")
    age_minutes=$(((current_time - container_unix) / 60))
    
    # Check freshness
    freshness="${GREEN}FRESH${NC}"
    if [[ $container_unix -lt $rebuild_threshold ]]; then
        freshness="${YELLOW}OLD${NC}"
    fi
    
    # Check critical files
    file_status=$(check_critical_files "$container")
    if [[ $? -ne 0 ]]; then
        has_issues=true
        freshness="${RED}ISSUE${NC}"
    fi
    
    printf "%-20s %-12s %-12s %-8s %-15s\n" "$container" "${GREEN}RUNNING${NC}" "${age_minutes}m" "$file_status" "$freshness"
done

echo "----------------------------------------"

# Detailed validation for specific containers
echo
echo -e "${BLUE}Detailed File Validation:${NC}"
echo "----------------------------------------"

# Check passkey models in app container
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-app$"; then
    echo -n "Checking passkey models implementation... "
    if docker exec sting-ce-app grep -q "def create_challenge" /app/models/passkey_models.py 2>/dev/null; then
        echo -e "${GREEN}[+] create_challenge method found${NC}"
    else
        echo -e "${RED}[-] create_challenge method missing${NC}"
        has_issues=true
    fi
    
    if docker exec sting-ce-app grep -q "def get_valid_challenge" /app/models/passkey_models.py 2>/dev/null; then
        echo -e "${GREEN}[+] get_valid_challenge method found${NC}"
    else
        echo -e "${RED}[-] get_valid_challenge method missing${NC}"
        has_issues=true
    fi
fi

# Check Kratos configuration
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-kratos$"; then
    echo -n "Checking Kratos identity schema... "
    if docker exec sting-ce-kratos test -f /etc/config/kratos/identity.schema.json 2>/dev/null; then
        echo -e "${GREEN}[+] Identity schema found${NC}"
    else
        echo -e "${RED}[-] Identity schema missing${NC}"
        has_issues=true
    fi
    
    echo -n "Checking Kratos config file... "
    if docker exec sting-ce-kratos test -f /etc/config/kratos/kratos.yml 2>/dev/null; then
        echo -e "${GREEN}[+] Kratos config found${NC}"
    else
        echo -e "${RED}[-] Kratos config missing${NC}"
        has_issues=true
    fi
fi

# Check frontend build
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-frontend$"; then
    echo -n "Checking frontend update script... "
    if docker exec sting-ce-frontend test -f /app/update-env.sh 2>/dev/null; then
        echo -e "${GREEN}[+] Update script found${NC}"
    else
        echo -e "${RED}[-] Update script missing${NC}"
        has_issues=true
    fi
fi

echo "----------------------------------------"

# Cache detection heuristics
echo
echo -e "${BLUE}Cache Usage Detection:${NC}"
echo "----------------------------------------"

# Check if any containers are using very old base images
echo "Checking for potentially cached base images..."
for container in "${STING_CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        image_created=$(get_image_created "$container")
        if [[ "$image_created" != "NOT_FOUND" ]]; then
            image_unix=$(docker_time_to_unix "$image_created")
            image_age_hours=$(((current_time - image_unix) / 3600))
            
            if [[ $image_age_hours -gt 24 ]]; then
                echo -e "${YELLOW}[!] $container using image older than 24h (${image_age_hours}h old)${NC}"
            fi
        fi
    fi
done

# Final summary
echo
if [[ "$has_issues" == "true" ]]; then
    echo -e "${RED}[-] VALIDATION FAILED${NC}"
    echo "Issues detected that suggest cached/incomplete builds."
    echo
    echo -e "${YELLOW}Recommended actions:${NC}"
    echo "1. Run: docker system prune -a --volumes"
    echo "2. Run: STING/manage_sting.sh reinstall --no-cache"
    echo "3. Re-run this validation script"
    exit 1
else
    echo -e "${GREEN}[+] VALIDATION PASSED${NC}"
    echo "All containers appear to be freshly built and properly configured."
    exit 0
fi