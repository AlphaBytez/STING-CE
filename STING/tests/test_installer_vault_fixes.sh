#!/bin/bash
# Test script to verify Vault token synchronization fixes
# This script checks that all services have the same Vault token after installation

set -e

echo "==================================="
echo "STING Vault Token Verification Test"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get installation directory
if [[ "$(uname)" == "Darwin" ]]; then
    INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
else
    INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
fi

echo "Installation directory: $INSTALL_DIR"
echo ""

# Function to check if container is running
check_container() {
    local container=$1
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "${GREEN}✓${NC} $container is running"
        return 0
    else
        echo -e "${RED}✗${NC} $container is not running"
        return 1
    fi
}

# Function to get token from container
get_container_token() {
    local container=$1
    local token=""

    if docker exec "$container" printenv VAULT_TOKEN 2>/dev/null; then
        return 0
    else
        echo "N/A"
        return 1
    fi
}

# Function to get token from env file
get_env_file_token() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        grep "^VAULT_TOKEN=" "$env_file" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "N/A"
    else
        echo "FILE_NOT_FOUND"
    fi
}

echo "1. Checking Vault Status"
echo "------------------------"

# Check if Vault is running and get its status
if check_container "sting-ce-vault"; then
    vault_status=$(docker exec sting-ce-vault vault status -format=json 2>/dev/null || echo "{}")
    is_initialized=$(echo "$vault_status" | jq -r '.initialized // false')
    is_sealed=$(echo "$vault_status" | jq -r '.sealed // true')

    echo "   Initialized: $is_initialized"
    echo "   Sealed: $is_sealed"

    if [ "$is_initialized" = "false" ]; then
        echo -e "   ${RED}ERROR: Vault is not initialized!${NC}"
        exit 1
    fi

    if [ "$is_sealed" = "true" ]; then
        echo -e "   ${YELLOW}WARNING: Vault is sealed${NC}"
    fi
else
    echo -e "${RED}ERROR: Vault container is not running!${NC}"
    exit 1
fi

echo ""
echo "2. Checking Vault Initialization Files"
echo "---------------------------------------"

# Check for vault init files
vault_init_locations=(
    "$INSTALL_DIR/.vault-init.json"
    "$INSTALL_DIR/vault/vault-init.json"
    "$INSTALL_DIR/conf/.vault-auto-init.json"
)

init_file_found=false
vault_root_token=""

for location in "${vault_init_locations[@]}"; do
    if [ -f "$location" ]; then
        echo -e "${GREEN}✓${NC} Found init file: $location"
        file_token=$(jq -r '.root_token // empty' "$location" 2>/dev/null || echo "")
        if [ -n "$file_token" ]; then
            vault_root_token="$file_token"
            echo "   Token: ${file_token:0:10}..."
        fi
        init_file_found=true
    else
        echo "   Not found: $location"
    fi
done

if [ "$init_file_found" = "false" ]; then
    echo -e "${RED}ERROR: No vault initialization files found!${NC}"
fi

echo ""
echo "3. Checking Environment Files"
echo "------------------------------"

# Get token from vault.env
vault_env_token=$(get_env_file_token "$INSTALL_DIR/env/vault.env")
echo "vault.env token: ${vault_env_token:0:30}..."

echo ""
echo "4. Checking Container Tokens"
echo "-----------------------------"

# Services to check
services=(
    "sting-ce-vault"
    "sting-ce-utils"
    "sting-ce-app"
    "sting-ce-frontend"
    "sting-ce-report-worker"
    "sting-ce-profile-sync-worker"
)

all_tokens_match=true
reference_token=""
mismatched_services=""

for service in "${services[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        token=$(get_container_token "$service")

        if [ -z "$reference_token" ] && [ "$token" != "N/A" ]; then
            reference_token="$token"
        fi

        if [ "$token" = "$reference_token" ] || [ "$token" = "N/A" ]; then
            echo -e "${GREEN}✓${NC} $service: ${token:0:30}..."
        else
            echo -e "${RED}✗${NC} $service: ${token:0:30}... ${RED}(MISMATCH!)${NC}"
            all_tokens_match=false
            mismatched_services="$mismatched_services $service:${token:0:10}"
        fi
    else
        echo -e "${YELLOW}⚠${NC} $service: Not running"
    fi
done

echo ""
echo "5. Token Comparison Summary"
echo "----------------------------"

if [ "$all_tokens_match" = "true" ]; then
    echo -e "${GREEN}✅ SUCCESS: All running services have the same Vault token!${NC}"
else
    echo -e "${RED}❌ FAILURE: Token mismatch detected between services!${NC}"
    if [ -n "$mismatched_services" ]; then
        echo ""
        echo "Mismatched services: $mismatched_services"
    fi
fi

echo ""
echo "6. Checking Utils Service Specifically"
echo "---------------------------------------"

if docker ps --format '{{.Names}}' | grep -q "^sting-ce-utils$"; then
    utils_token=$(get_container_token "sting-ce-utils")

    # Check if utils has vault.env mounted
    utils_mounts=$(docker inspect sting-ce-utils --format='{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}' 2>/dev/null || echo "")

    echo "Utils token: ${utils_token:0:30}..."
    echo "Utils mounts containing 'vault': "
    echo "$utils_mounts" | tr ' ' '\n' | grep -i vault || echo "  None found"

    # Check if utils was restarted recently
    utils_started=$(docker inspect sting-ce-utils --format='{{.State.StartedAt}}' 2>/dev/null || echo "Unknown")
    vault_started=$(docker inspect sting-ce-vault --format='{{.State.StartedAt}}' 2>/dev/null || echo "Unknown")

    echo ""
    echo "Container start times:"
    echo "  Vault started: $vault_started"
    echo "  Utils started: $utils_started"

    # Simple comparison - if utils started before vault, that's a problem
    if [[ "$utils_started" < "$vault_started" ]]; then
        echo -e "  ${YELLOW}WARNING: Utils started before Vault - may have old token${NC}"
    fi
else
    echo -e "${RED}Utils service is not running${NC}"
fi

echo ""
echo "==================================="
echo "Test Complete"
echo "==================================="

if [ "$all_tokens_match" = "true" ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed - review output above${NC}"
    exit 1
fi