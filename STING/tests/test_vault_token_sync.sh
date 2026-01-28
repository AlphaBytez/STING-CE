#!/bin/bash
# Quick test to verify Vault token synchronization fixes work
# This simulates what happens during installation

set -e

echo "================================"
echo "Vault Token Sync Test"
echo "================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
cd "$INSTALL_DIR"

echo "1. Current token status:"
echo "------------------------"
CURRENT_VAULT_TOKEN=$(docker exec sting-ce-vault printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
CURRENT_UTILS_TOKEN=$(docker exec sting-ce-utils printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
CURRENT_APP_TOKEN=$(docker exec sting-ce-app printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")

echo "Vault: ${CURRENT_VAULT_TOKEN}..."
echo "Utils: ${CURRENT_UTILS_TOKEN}..."
echo "App:   ${CURRENT_APP_TOKEN}..."

if [ "$CURRENT_VAULT_TOKEN" = "$CURRENT_UTILS_TOKEN" ] && [ "$CURRENT_UTILS_TOKEN" = "$CURRENT_APP_TOKEN" ]; then
    echo -e "${GREEN}✓ Tokens currently match${NC}"
else
    echo -e "${YELLOW}⚠ Tokens don't match (expected for test)${NC}"
fi

echo ""
echo "2. Simulating installation scenario:"
echo "------------------------------------"
echo "Restarting Vault (will seal)..."
docker compose restart vault >/dev/null 2>&1
sleep 3

# Check if sealed
if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
    echo -e "${GREEN}✓ Vault is sealed (as expected after restart)${NC}"
else
    echo -e "${RED}✗ Vault should be sealed after restart${NC}"
fi

echo ""
echo "3. Running installer fix sequence:"
echo "-----------------------------------"

# Step 1: Unseal Vault
echo "Unsealing Vault..."
docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh >/dev/null 2>&1
if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*false"; then
    echo -e "${GREEN}✓ Vault unsealed${NC}"
else
    echo -e "${RED}✗ Failed to unseal Vault${NC}"
    exit 1
fi

# Step 2: Regenerate env files with token
echo "Regenerating env files..."
if docker exec sting-ce-utils sh -c "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode runtime" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Env files regenerated${NC}"
else
    echo -e "${YELLOW}⚠ Env regeneration had issues${NC}"
fi

# Step 3: Force recreate utils (as per our fix)
echo "Recreating utils service..."
docker compose stop utils >/dev/null 2>&1
docker compose rm -f utils >/dev/null 2>&1
docker compose up -d utils >/dev/null 2>&1
sleep 3
echo -e "${GREEN}✓ Utils service recreated${NC}"

echo ""
echo "4. Verifying token synchronization:"
echo "------------------------------------"

NEW_VAULT_TOKEN=$(docker exec sting-ce-vault printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
NEW_UTILS_TOKEN=$(docker exec sting-ce-utils printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")
NEW_APP_TOKEN=$(docker exec sting-ce-app printenv VAULT_TOKEN 2>/dev/null | head -c 30 || echo "N/A")

echo "Vault: ${NEW_VAULT_TOKEN}..."
echo "Utils: ${NEW_UTILS_TOKEN}..."
echo "App:   ${NEW_APP_TOKEN}..."

if [ "$NEW_VAULT_TOKEN" = "$NEW_UTILS_TOKEN" ] && [ "$NEW_UTILS_TOKEN" = "$NEW_APP_TOKEN" ]; then
    echo -e "${GREEN}✅ SUCCESS: All tokens match after fix!${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}❌ FAILURE: Tokens still don't match${NC}"
    echo ""
    echo "Mismatches:"
    [ "$NEW_VAULT_TOKEN" != "$NEW_UTILS_TOKEN" ] && echo "  Vault vs Utils mismatch"
    [ "$NEW_UTILS_TOKEN" != "$NEW_APP_TOKEN" ] && echo "  Utils vs App mismatch"
    EXIT_CODE=1
fi

echo ""
echo "5. Service health check:"
echo "------------------------"
APP_HEALTHY=$(docker ps --format '{{.Names}} {{.Status}}' | grep sting-ce-app | grep -q healthy && echo "Yes" || echo "No")
UTILS_HEALTHY=$(docker ps --format '{{.Names}} {{.Status}}' | grep sting-ce-utils | grep -q healthy && echo "Yes" || echo "No")

echo "App healthy: $APP_HEALTHY"
echo "Utils healthy: $UTILS_HEALTHY"

if [ "$APP_HEALTHY" = "Yes" ] && [ "$UTILS_HEALTHY" = "Yes" ]; then
    echo -e "${GREEN}✓ Services are healthy${NC}"
else
    echo -e "${YELLOW}⚠ Some services may need time to become healthy${NC}"
fi

echo ""
echo "================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Test PASSED${NC}"
else
    echo -e "${RED}Test FAILED${NC}"
fi
echo "================================"

exit $EXIT_CODE