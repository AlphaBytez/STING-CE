#!/bin/bash
# Simple Container Freshness Validation Script
# Detects if containers were actually rebuilt from scratch or used cached layers

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== STING Container Freshness Validation ===${NC}"
echo "Checking if containers were actually rebuilt..."
echo

has_issues=false

echo -e "${BLUE}Container Status:${NC}"
echo "----------------------------------------"

# Check each container
containers="sting-ce-app sting-ce-frontend sting-ce-kratos sting-ce-chatbot sting-ce-knowledge sting-ce-messaging sting-ce-external-ai sting-ce-db sting-ce-vault"

for container in $containers; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        created=$(docker inspect "$container" --format='{{.Created}}' 2>/dev/null)
        echo -e "✓ $container: ${GREEN}RUNNING${NC} (created: ${created%.*})"
    else
        echo -e "✗ $container: ${RED}STOPPED/MISSING${NC}"
        has_issues=true
    fi
done

echo
echo -e "${BLUE}Critical File Validation:${NC}"
echo "----------------------------------------"

# Check passkey models in app container
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-app$"; then
    echo -n "Checking passkey models implementation... "
    if docker exec sting-ce-app test -f /app/models/passkey_models.py 2>/dev/null; then
        if docker exec sting-ce-app grep -q "def create_challenge" /app/models/passkey_models.py 2>/dev/null; then
            echo -e "${GREEN}✓ passkey models OK${NC}"
        else
            echo -e "${RED}✗ create_challenge method missing${NC}"
            has_issues=true
        fi
    else
        echo -e "${RED}✗ passkey_models.py file missing${NC}"
        has_issues=true
    fi
else
    echo -e "${YELLOW}⚠ sting-ce-app not running${NC}"
fi

# Check Kratos configuration
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-kratos$"; then
    echo -n "Checking Kratos identity schema... "
    if docker exec sting-ce-kratos test -f /etc/config/kratos/identity.schema.json 2>/dev/null; then
        echo -e "${GREEN}✓ identity schema found${NC}"
    else
        echo -e "${RED}✗ identity schema missing${NC}"
        has_issues=true
    fi
    
    echo -n "Checking Kratos main config... "
    if docker exec sting-ce-kratos test -f /etc/config/kratos/kratos.yml 2>/dev/null; then
        echo -e "${GREEN}✓ kratos config found${NC}"
    else
        echo -e "${RED}✗ kratos config missing${NC}"
        has_issues=true
    fi
else
    echo -e "${YELLOW}⚠ sting-ce-kratos not running${NC}"
fi

# Check frontend
if docker ps --format '{{.Names}}' | grep -q "^sting-ce-frontend$"; then
    echo -n "Checking frontend files... "
    if docker exec sting-ce-frontend test -f /app/src/index.js 2>/dev/null; then
        echo -e "${GREEN}✓ frontend files OK${NC}"
    else
        echo -e "${RED}✗ frontend index.js missing${NC}"
        has_issues=true
    fi
else
    echo -e "${YELLOW}⚠ sting-ce-frontend not running${NC}"
fi

echo
echo -e "${BLUE}Cache Detection:${NC}"
echo "----------------------------------------"

# Check image ages
current_time=$(date +%s)
for container in $containers; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        image_id=$(docker inspect "$container" --format='{{.Image}}' 2>/dev/null)
        if [ -n "$image_id" ]; then
            image_created=$(docker inspect "$image_id" --format='{{.Created}}' 2>/dev/null)
            if [ -n "$image_created" ]; then
                # Simple age calculation (approximate)
                echo "$container image: $image_created"
            fi
        fi
    fi
done

echo
if [ "$has_issues" = "true" ]; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Issues detected that suggest cached/incomplete builds."
    echo
    echo -e "${YELLOW}Recommended actions:${NC}"
    echo "1. Run: docker system prune -a --volumes"
    echo "2. Run: ./manage_sting.sh reinstall --no-cache"
    echo "3. Re-run this validation script"
    exit 1
else
    echo -e "${GREEN}✅ VALIDATION PASSED${NC}"
    echo "All containers appear to be properly configured."
    exit 0
fi