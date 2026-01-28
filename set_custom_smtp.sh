#!/bin/bash
# Helper script to configure custom SMTP settings for STING
# This replaces the default mailpit configuration with your production SMTP server

echo "🔧 STING Custom SMTP Configuration Helper"
echo "========================================"
echo ""
echo "This script will help you configure STING to use your custom SMTP server"
echo "instead of the default mailpit service."
echo ""

# Ensure mailpit is disabled
export EMAIL_MODE="production"
export DISABLE_MAILPIT="true"

echo "📧 Please enter your SMTP server details:"
echo ""

read -p "SMTP Host (e.g., smtp.gmail.com): " smtp_host
read -p "SMTP Port (e.g., 587): " smtp_port
read -p "SMTP Username: " smtp_username
read -s -p "SMTP Password: " smtp_password
echo ""
read -p "From Email Address: " smtp_from
read -p "From Name (e.g., STING Platform): " smtp_from_name
read -p "Enable TLS? (true/false) [true]: " smtp_tls
smtp_tls=${smtp_tls:-true}

# Add to bashrc
cat >> ~/.bashrc << EOF

# STING Custom SMTP Configuration
export EMAIL_MODE="production"
export DISABLE_MAILPIT="true"
export EMAIL_PROVIDER="smtp"
export SMTP_HOST="${smtp_host}"
export SMTP_PORT="${smtp_port}"
export SMTP_USERNAME="${smtp_username}"
export SMTP_PASSWORD="${smtp_password}"
export SMTP_FROM="${smtp_from}"
export SMTP_FROM_NAME="${smtp_from_name}"
export SMTP_TLS_ENABLED="${smtp_tls}"
export SMTP_STARTTLS_ENABLED="${smtp_tls}"
EOF

echo ""
echo "✅ SMTP configuration saved to ~/.bashrc"
echo "🔄 Please run: source ~/.bashrc"
echo "🚀 Then restart STING: ./manage_sting.sh restart"
echo ""
echo "⚠️  IMPORTANT: Mailpit is now permanently disabled."
echo "   All emails will be sent via your custom SMTP server."