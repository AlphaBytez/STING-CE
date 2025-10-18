#!/bin/bash
# Quick fix for admin creation after installation
# Run this if admin creation failed during installation

echo "🔧 STING Admin Creation Fix"
echo "============================"
echo ""

# Change to STING directory
INSTALL_DIR="/opt/sting-ce"
if [ -d "$HOME/.sting-ce" ]; then
    INSTALL_DIR="$HOME/.sting-ce"
fi

cd "$INSTALL_DIR" || exit 1
echo "STING directory: $INSTALL_DIR"
echo ""

# Check if services are running
echo "Checking if STING services are running..."
if ! docker ps | grep -q "sting-ce-kratos.*healthy"; then
    echo "❌ Kratos service is not healthy yet"
    echo "   Please wait for all services to be healthy"
    echo "   Run: docker ps"
    exit 1
fi
echo "✅ Kratos is healthy"
echo ""

# Fix the admin creation script permissions
echo "Step 1: Ensuring admin creation script is accessible..."
if [ -f "$INSTALL_DIR/scripts/admin/create-new-admin.py" ]; then
    chmod +x "$INSTALL_DIR/scripts/admin/create-new-admin.py" 2>/dev/null || sudo chmod +x "$INSTALL_DIR/scripts/admin/create-new-admin.py"
    echo "✅ Script permissions set"
else
    echo "❌ Admin creation script not found"
    exit 1
fi
echo ""

# Run the admin creation
echo "Step 2: Creating admin account..."
echo "Email: admin@sting.local"
echo ""

# Run with proper environment
export KRATOS_ADMIN_URL="http://localhost:4434"
export STING_API_URL="http://localhost:5050"

if python3 "$INSTALL_DIR/scripts/admin/create-new-admin.py" --email admin@sting.local; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Admin Account Created Successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Next steps:"
    echo "1. Open: https://localhost:8443/login"
    echo "2. Enter: admin@sting.local"
    echo "3. Check Mailpit for verification code:"
    echo "   http://localhost:8025"
    echo ""
else
    echo ""
    echo "❌ Admin creation failed"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if Kratos is accessible:"
    echo "   curl -k http://localhost:4434/health/ready"
    echo ""
    echo "2. Check if app service is accessible:"
    echo "   curl http://localhost:5050/health"
    echo ""
    echo "3. Check Docker logs:"
    echo "   docker logs sting-ce-kratos"
    echo "   docker logs sting-ce-app"
fi
