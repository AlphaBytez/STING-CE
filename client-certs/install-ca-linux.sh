#!/bin/bash
# STING-CE CA Certificate Installer for Linux
set -e

CA_FILE="sting-ca.pem"
DOMAIN="captain-den.local"
VM_IP="192.168.68.101"

echo "🔐 STING-CE Certificate Authority Installer for Linux"
echo "================================================="
echo ""

# Check if CA file exists
if [ ! -f "$CA_FILE" ]; then
    echo "❌ Error: $CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Detect Linux distribution and install CA certificate
echo "📋 Installing CA certificate..."
if [ -d "/etc/ssl/certs" ] && [ -d "/usr/local/share/ca-certificates" ]; then
    # Ubuntu/Debian
    sudo cp "$CA_FILE" /usr/local/share/ca-certificates/sting-ca.crt
    sudo update-ca-certificates
    echo "✅ CA certificate installed (Ubuntu/Debian)"
elif [ -d "/etc/pki/ca-trust/source/anchors" ]; then
    # RHEL/CentOS/Fedora
    sudo cp "$CA_FILE" /etc/pki/ca-trust/source/anchors/sting-ca.crt
    sudo update-ca-trust
    echo "✅ CA certificate installed (RHEL/CentOS/Fedora)"
elif [ -d "/usr/share/ca-certificates" ]; then
    # Generic approach
    sudo cp "$CA_FILE" /usr/share/ca-certificates/sting-ca.crt
    echo "sting-ca.crt" | sudo tee -a /etc/ca-certificates.conf
    sudo update-ca-certificates
    echo "✅ CA certificate installed (Generic Linux)"
else
    echo "⚠️  Unsupported Linux distribution"
    echo "Please manually add $CA_FILE to your system's certificate store"
fi

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
