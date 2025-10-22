#!/bin/bash
# debug_auth.sh - Debug authentication issues in STING

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          STING Authentication Debugging Tool                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo

# Check services
echo -e "${BLUE}[1/5] Checking Service Status${NC}"
echo "================================"
services=("kratos" "mailpit" "app" "frontend" "db")
for service in "${services[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "sting-ce-$service"; then
        echo -e "✅ $service: ${GREEN}Running${NC}"
    else
        echo -e "❌ $service: ${RED}Not Running${NC}"
    fi
done
echo

# Check Kratos health
echo -e "${BLUE}[2/5] Checking Kratos Health${NC}"
echo "================================"
if curl -k -s https://localhost:4434/admin/health/ready >/dev/null 2>&1; then
    echo -e "✅ Kratos Admin API: ${GREEN}Healthy${NC}"
else
    echo -e "❌ Kratos Admin API: ${RED}Unhealthy${NC}"
fi

if curl -k -s https://localhost:4433/health/ready >/dev/null 2>&1; then
    echo -e "✅ Kratos Public API: ${GREEN}Healthy${NC}"
else
    echo -e "❌ Kratos Public API: ${RED}Unhealthy${NC}"
fi

# Check version
KRATOS_VERSION=$(curl -k -s https://localhost:4434/admin/version 2>/dev/null | jq -r '.version // "Unknown"')
echo -e "📦 Kratos Version: ${YELLOW}$KRATOS_VERSION${NC}"
echo

# Check configuration
echo -e "${BLUE}[3/5] Checking Kratos Configuration${NC}"
echo "================================"

# Check identity schema
echo "Identity Schema Validation:"
if docker exec sting-ce-kratos kratos validate identity-schema /etc/config/kratos/identity.schema.json >/dev/null 2>&1; then
    echo -e "✅ Identity schema: ${GREEN}Valid${NC}"
else
    echo -e "❌ Identity schema: ${RED}Invalid${NC}"
    docker exec sting-ce-kratos kratos validate identity-schema /etc/config/kratos/identity.schema.json 2>&1 | head -5
fi

# Check methods enabled
echo -e "\nAuthentication Methods:"
METHODS=$(docker exec sting-ce-kratos cat /etc/config/kratos/kratos.yml | grep -A 20 "methods:" | grep "enabled: true" -B 1 | grep -E "password:|webauthn:|code:|oidc:" | sed 's/://g' | tr -d ' ')
if [ -n "$METHODS" ]; then
    for method in $METHODS; do
        echo -e "  ✅ $method: ${GREEN}Enabled${NC}"
    done
else
    echo -e "  ${YELLOW}No methods found or all disabled${NC}"
fi
echo

# Check database
echo -e "${BLUE}[4/5] Checking Database${NC}"
echo "================================"
if docker exec sting-ce-db pg_isready -U postgres >/dev/null 2>&1; then
    echo -e "✅ PostgreSQL: ${GREEN}Ready${NC}"
    
    # Count identities
    IDENTITY_COUNT=$(docker exec sting-ce-db psql -U postgres -d kratos -t -c "SELECT COUNT(*) FROM identities;" 2>/dev/null | tr -d ' ')
    echo -e "👥 Total Identities: ${YELLOW}${IDENTITY_COUNT:-0}${NC}"
    
    # Recent registrations
    echo -e "\nRecent Registrations (last 5):"
    docker exec sting-ce-db psql -U postgres -d kratos -c "SELECT id, created_at, updated_at FROM identities ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "  Could not query identities"
else
    echo -e "❌ PostgreSQL: ${RED}Not Ready${NC}"
fi
echo

# Check recent logs
echo -e "${BLUE}[5/5] Recent Kratos Logs${NC}"
echo "================================"
echo "Last 10 log entries:"
docker logs sting-ce-kratos --tail 10 2>&1 | grep -v "^\s*$"
echo

# Common issues
echo -e "${YELLOW}Common Issues & Solutions:${NC}"
echo "================================"
echo "1. 'Flow expired' - Flows expire after 1 hour. Create new flow."
echo "2. 'CSRF token' - Use /api endpoints for programmatic access."
echo "3. 'Unable to decode JSON' - Use form-encoded data, not JSON."
echo "4. 'Connection refused' - Check if services are running."
echo "5. 'Certificate error' - Use -k flag with curl for self-signed certs."
echo

# Quick commands
echo -e "${BLUE}Useful Commands:${NC}"
echo "================================"
echo "• Test auth flow: ./test_auth_suite.sh"
echo "• View all identities: curl -k -s https://localhost:4434/admin/identities | jq '.'"
echo "• Check Mailpit: http://localhost:8025"
echo "• Kratos logs: docker logs -f sting-ce-kratos"
echo "• Restart Kratos: docker restart sting-ce-kratos"