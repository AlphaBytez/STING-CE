#!/bin/bash
# Setup custom domain for STING

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try to read domain from config.yml
if [ -f "$SCRIPT_DIR/conf/config.yml" ] && command -v python3 &> /dev/null; then
    CONFIG_DOMAIN=$(python3 -c "
import yaml
try:
    with open('$SCRIPT_DIR/conf/config.yml', 'r') as f:
        config = yaml.safe_load(f)
        system = config.get('system', {})
        domain = system.get('domain')
        if domain:
            print(domain)
except:
    pass
" 2>/dev/null)
fi

# Use domain from config, environment, or default to queen.hive
if [ -n "$CONFIG_DOMAIN" ]; then
    CUSTOM_DOMAIN="$CONFIG_DOMAIN"
    echo "📖 Using domain from config.yml: $CUSTOM_DOMAIN"
else
    CUSTOM_DOMAIN="${CUSTOM_DOMAIN:-queen.hive}"
fi
CUSTOM_IP="${CUSTOM_IP:-127.0.0.1}"

echo "🌐 Setting up custom domain: $CUSTOM_DOMAIN"

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Backup hosts file
cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d_%H%M%S)

# Check if entry already exists
if grep -q "$CUSTOM_DOMAIN" /etc/hosts; then
    echo "[+] $CUSTOM_DOMAIN already configured in /etc/hosts"
else
    echo "Adding $CUSTOM_DOMAIN to /etc/hosts..."
    echo "" >> /etc/hosts
    echo "# STING Local Development - Queen's Hive " >> /etc/hosts
    echo "$CUSTOM_IP    $CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    api.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    auth.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    hive.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    bee.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    honey.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    vault.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "$CUSTOM_IP    mail.$CUSTOM_DOMAIN" >> /etc/hosts
    echo "[+] Added $CUSTOM_DOMAIN entries to /etc/hosts"
fi

echo ""
echo "📝 Custom domain setup complete!"
echo ""
echo "Welcome to the Queen's Hive! 👑"
echo ""
echo "You can now access STING services at:"
echo "  🌐 Main App:        https://$CUSTOM_DOMAIN:8443"
echo "  🔐 Authentication:  https://auth.$CUSTOM_DOMAIN:4433"
echo "   API Gateway:     https://api.$CUSTOM_DOMAIN:5050"
echo "   Hive Manager:    https://hive.$CUSTOM_DOMAIN:8443/dashboard/hive"
echo "   Bee Chat:        https://bee.$CUSTOM_DOMAIN:8443/dashboard/bee-chat"
echo "  🏺 Honey Jars:      https://honey.$CUSTOM_DOMAIN:8443/dashboard/honey-pot"
echo "   Vault UI:        http://vault.$CUSTOM_DOMAIN:8200"
echo "  📧 Mail Testing:    http://mail.$CUSTOM_DOMAIN:8025"
echo ""
echo "[!]  Note: You'll still get SSL certificate warnings since we're using self-signed certs"
echo ""

# For network access
echo "🏠 For access from other devices on your network:"
echo "  1. Find your local IP: ifconfig | grep 'inet ' | grep -v 127.0.0.1"
echo "  2. Share this URL: https://YOUR_LOCAL_IP:8443"
echo "  3. Other users need to accept the self-signed certificate"