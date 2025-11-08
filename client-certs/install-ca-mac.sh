#!/bin/bash
# STING-CE CA Certificate Installer for macOS
set -e

CA_FILE="sting-ca.pem"
DOMAIN="sting.local"
VM_IP=""

echo "🔐 STING-CE Certificate Authority Installer for macOS"
echo "=================================================="
echo ""

# Check if CA file exists
if [ ! -f "$CA_FILE" ]; then
    echo "❌ Error: $CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Install CA certificate
echo "📋 Installing CA certificate..."
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CA_FILE"
echo "✅ CA certificate installed successfully"

# Add domain to hosts file if needed
echo ""
echo "🌐 Setting up domain resolution..."
if ! grep -q "$DOMAIN" /etc/hosts; then
    echo "Adding $DOMAIN to /etc/hosts..."
    echo "$VM_IP $DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    echo "✅ Domain added to /etc/hosts"
else
    echo "✅ Domain already in /etc/hosts"
fi

echo ""
echo "🎉 Installation complete!"
echo "You can now access STING securely at: https://$DOMAIN:8443"
echo "⚠️  Please restart your browser to load the new certificate"
