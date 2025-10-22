#!/bin/bash
# Script to set WebAuthn domain for passkey portability

echo "🔐 WebAuthn Domain Configuration"
echo "================================"
echo ""
echo "IMPORTANT: For passkeys to work across different machines, all machines"
echo "must use the SAME domain name (RP ID). This can be:"
echo ""
echo "1. A real domain (e.g., sting.local) - Recommended"
echo "2. An IP address (e.g., 192.168.1.100)"
echo "3. localhost (only works on the same machine)"
echo ""

# Get current hostname
CURRENT_HOSTNAME=$(hostname -s | tr '[:upper:]' '[:lower:]')
CURRENT_IP=$(ipconfig getifaddr en0 2>/dev/null || ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1 | head -1)

echo "Current hostname: $CURRENT_HOSTNAME"
echo "Current IP: ${CURRENT_IP:-Not detected}"
echo ""

# Prompt for domain
read -p "Enter the domain/hostname to use for WebAuthn (e.g., sting.local, 192.168.1.100): " WEBAUTHN_DOMAIN

if [ -z "$WEBAUTHN_DOMAIN" ]; then
    echo "❌ No domain provided. Exiting."
    exit 1
fi

echo ""
echo "Setting WebAuthn RP ID to: $WEBAUTHN_DOMAIN"
echo ""

# Export for config loader
export HOSTNAME="$WEBAUTHN_DOMAIN"

# Update config.yml if needed
CONFIG_FILE="conf/config.yml"
if [ -f "$CONFIG_FILE" ]; then
    echo "📝 Updating config.yml..."
    # Backup original
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update rp_id
    sed -i.tmp "s/rp_id: .*/rp_id: \"$WEBAUTHN_DOMAIN\"/" "$CONFIG_FILE"
    rm -f "${CONFIG_FILE}.tmp"
    
    echo "✅ Config updated"
fi

# Regenerate environment files
echo ""
echo "🔄 Regenerating environment files..."
python conf/config_loader.py conf/config.yml

# Check if successful
if grep -q "WEBAUTHN_RP_ID=\"$WEBAUTHN_DOMAIN\"" ~/.sting-ce/env/app.env 2>/dev/null; then
    echo "✅ WebAuthn domain successfully set to: $WEBAUTHN_DOMAIN"
    echo ""
    echo "Next steps:"
    echo "1. Update app service: ./manage_sting.sh update app"
    echo "2. Add '$WEBAUTHN_DOMAIN' to /etc/hosts on all machines (if using custom domain)"
    echo "   Example: echo '192.168.1.100 sting.local' | sudo tee -a /etc/hosts"
    echo "3. Access STING using: https://$WEBAUTHN_DOMAIN:3000"
    echo ""
    echo "⚠️  IMPORTANT: All machines must use the same domain to share passkeys!"
else
    echo "❌ Failed to set WebAuthn domain"
    exit 1
fi