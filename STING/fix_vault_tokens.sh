#!/bin/bash
# Quick fix for Vault token synchronization issues
# Use this if services have mismatched Vault tokens

set -e

echo "🔧 Fixing Vault token synchronization..."

INSTALL_DIR="${INSTALL_DIR:-$HOME/.sting-ce}"
cd "$INSTALL_DIR"

# 1. Ensure Vault is unsealed
if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Sealed.*true"; then
    echo "📦 Unsealing Vault..."
    docker exec sting-ce-vault sh /vault/scripts/auto-init-vault.sh >/dev/null 2>&1
fi

# 2. Regenerate env files with current Vault token
echo "📝 Regenerating environment files..."
docker exec sting-ce-utils sh -c "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode runtime" >/dev/null 2>&1

# 3. Force recreate services that need Vault token
echo "🔄 Recreating services with new tokens..."
for service in utils app; do
    docker compose stop $service >/dev/null 2>&1
    docker compose rm -f $service >/dev/null 2>&1
done

docker compose up -d utils app >/dev/null 2>&1

echo "⏳ Waiting for services to start..."
sleep 5

# 4. Verify tokens match
echo ""
echo "🔍 Verifying token synchronization:"
VAULT_TOKEN=$(docker exec sting-ce-vault printenv VAULT_TOKEN 2>/dev/null | head -c 30)
UTILS_TOKEN=$(docker exec sting-ce-utils printenv VAULT_TOKEN 2>/dev/null | head -c 30)
APP_TOKEN=$(docker exec sting-ce-app printenv VAULT_TOKEN 2>/dev/null | head -c 30)

if [ "$VAULT_TOKEN" = "$UTILS_TOKEN" ] && [ "$UTILS_TOKEN" = "$APP_TOKEN" ]; then
    echo "✅ Success! All services have matching Vault tokens."
    echo "   Token: ${VAULT_TOKEN}..."
else
    echo "❌ Warning: Tokens may still be mismatched."
    echo "   Vault: ${VAULT_TOKEN}..."
    echo "   Utils: ${UTILS_TOKEN}..."
    echo "   App:   ${APP_TOKEN}..."
fi

echo ""
echo "💡 Tip: Run './manage_sting.sh status' to check service health"