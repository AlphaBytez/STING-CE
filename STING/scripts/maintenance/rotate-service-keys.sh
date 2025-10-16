#!/bin/bash

# STING Service API Key Rotation Script
# Generates new service authentication keys and updates affected services

set -e

VAULT_TOKEN="${VAULT_TOKEN:-hvs.TqEboPUVWPzt9HHXHgaVvMjV}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔄 STING Service API Key Rotation"
echo "=================================="

# Function to generate secure API key
generate_api_key() {
    python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode('utf-8'))"
}

# Function to update knowledge service security config
update_knowledge_security() {
    local new_key="$1"
    local old_key="$2"

    echo "📝 Updating knowledge service security configuration..."

    # Create backup
    cp "$PROJECT_DIR/knowledge_service/config/security.py" \
       "$PROJECT_DIR/knowledge_service/config/security.py.backup.$(date +%Y%m%d_%H%M%S)"

    # Add new key to security.py
    python3 << EOF
import re

# Read current security.py
with open('$PROJECT_DIR/knowledge_service/config/security.py', 'r') as f:
    content = f.read()

# Add new key entry
new_key_entry = '''    '$new_key': {
        'name': 'Bee Chat Service Key',
        'description': 'API key for Bee Chat service to access honey jars and context (rotated $(date +%Y-%m-%d))',
        'permissions': ['honey_jar_management', 'read_only'],
        'rate_limit': 200,
        'created_at': '$(date +%Y-%m-%d)',
        'environment': 'production'
    }'''

# Insert before the closing brace of SYSTEM_API_KEYS
if '$old_key' in content:
    # Replace old key with new key
    pattern = r"'$old_key':\\s*{[^}]+}"
    content = re.sub(pattern, new_key_entry.strip(), content)
else:
    # Add new key before closing brace
    content = content.replace('}\\n}', ',\\n' + new_key_entry + '\\n}')

# Write updated content
with open('$PROJECT_DIR/knowledge_service/config/security.py', 'w') as f:
    f.write(content)

print("✅ Knowledge service security.py updated")
EOF
}

# Main rotation process
main() {
    echo "🔍 Checking current configuration..."

    # Get current key from chatbot.env
    CURRENT_KEY=$(grep "STING_SERVICE_API_KEY" ~/.sting-ce/env/chatbot.env 2>/dev/null | cut -d'"' -f2 || echo "")

    if [ -z "$CURRENT_KEY" ]; then
        echo "❌ No current service key found. Run initial setup first."
        exit 1
    fi

    echo "🔑 Current key: ...${CURRENT_KEY: -8}"

    # Generate new key
    echo "🎲 Generating new service API key..."
    NEW_KEY=$(generate_api_key)
    echo "🔑 New key: ...${NEW_KEY: -8}"

    # Store new key in Vault
    echo "💾 Storing new key in Vault..."
    docker exec sting-ce-vault sh -c "VAULT_TOKEN=$VAULT_TOKEN vault kv put sting/service_auth api_key=$NEW_KEY" > /dev/null

    if [ $? -eq 0 ]; then
        echo "✅ New key stored in Vault"
    else
        echo "❌ Failed to store key in Vault"
        exit 1
    fi

    # Update knowledge service security config
    update_knowledge_security "$NEW_KEY" "$CURRENT_KEY"

    # Update chatbot environment
    echo "📝 Updating chatbot environment..."
    sed -i.backup "s/STING_SERVICE_API_KEY=\"$CURRENT_KEY\"/STING_SERVICE_API_KEY=\"$NEW_KEY\"/" \
        ~/.sting-ce/env/chatbot.env

    # Update services
    echo "🔄 Updating affected services..."
    cd "$PROJECT_DIR"
    ./manage_sting.sh update knowledge chatbot

    echo ""
    echo "✅ Service API key rotation completed successfully!"
    echo "🔑 New key: ...${NEW_KEY: -8}"
    echo "📝 Old key backup: knowledge_service/config/security.py.backup.*"
    echo "🧪 Test with: node scripts/test-bee-chat-auth.js"
}

# Run rotation
main "$@"