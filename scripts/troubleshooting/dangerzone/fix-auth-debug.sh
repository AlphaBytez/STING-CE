#!/bin/bash
# Script to fix authentication debug issues

echo "🔧 Fixing STING authentication debug issues..."

# Step 1: Fix AppRoutes.js missing import
echo "📝 Fixing AppRoutes.js missing import..."
sed -i '' '5i\
import DebugPage from '\''./components/auth/DebugPage'\'';
' frontend/src/AppRoutes.js

# Step 2: Check and fix SSL certificates for local development
echo "🔒 Ensuring SSL certificates are trusted..."
if [ ! -f "certs/server.crt" ] || [ ! -f "certs/server.key" ]; then
  echo "⚠️ SSL certificates missing. Generating self-signed certificates..."
  mkdir -p certs
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key -out certs/server.crt \
    -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  echo "✅ Self-signed certificates generated."
fi

# Step 3: Verify Kratos configuration
echo "🔍 Verifying Kratos configuration..."
KRATOS_CONFIG="kratos/main.kratos.yml"

# Ensure webauthn is enabled
if grep -q "webauthn:" "$KRATOS_CONFIG"; then
  echo "✅ WebAuthn is configured in Kratos."
else
  echo "⚠️ WebAuthn configuration missing. Please add proper WebAuthn configuration."
fi

# Step 4: Verify and fix CORS configuration
echo "🌐 Verifying CORS configuration..."
if grep -q "cors:" "$KRATOS_CONFIG"; then
  echo "✅ CORS is configured in Kratos."
  
  # Ensure all necessary origins are allowed
  if ! grep -q "http://localhost:3000" "$KRATOS_CONFIG"; then
    echo "⚠️ Missing origin: http://localhost:3000. Please add it to allowed_origins."
  fi
  if ! grep -q "https://localhost:3000" "$KRATOS_CONFIG"; then
    echo "⚠️ Missing origin: https://localhost:3000. Please add it to allowed_origins."
  fi
else
  echo "⚠️ CORS configuration missing. Please configure CORS in Kratos."
fi

# Step 5: Update MailSlurper connection
echo "📧 Updating MailSlurper connection configuration..."
MAILVIEWER_PATH="frontend/src/components/auth/MailViewer.jsx"
sed -i '' 's|const mailSlurperUrl = '\''https://localhost:4436'\'';|const mailSlurperUrl = window.env?.REACT_APP_MAILSLURPER_URL || '\''https://localhost:4436'\'';|' "$MAILVIEWER_PATH"

# Step 6: Update frontend environment
echo "🌍 Updating frontend environment variables..."
if [ -f "frontend/update-env.sh" ]; then
  (cd frontend && ./update-env.sh)
  echo "✅ Frontend environment updated."
else
  echo "⚠️ frontend/update-env.sh not found. Creating a basic environment update..."
  cat > frontend/public/env.js << EOL
window.env = {
  REACT_APP_API_URL: "https://localhost:5050",
  REACT_APP_KRATOS_PUBLIC_URL: "https://localhost:4433",
  REACT_APP_MAILSLURPER_URL: "https://localhost:4436",
  PUBLIC_URL: "https://localhost:3000"
};
EOL
  echo "✅ Basic environment file created."
fi

# Step 7: Restart necessary services
echo "🔄 Do you want to restart the services? (y/n)"
read -r answer
if [ "$answer" = "y" ]; then
  echo "🔄 Restarting services..."
  ./manage_sting.sh restart kratos
  ./manage_sting.sh restart frontend
  ./manage_sting.sh restart mailslurper
  echo "✅ Services restarted."
else
  echo "⚠️ Services not restarted. Please restart them manually with:"
  echo "./manage_sting.sh restart kratos"
  echo "./manage_sting.sh restart frontend"
  echo "./manage_sting.sh restart mailslurper"
fi

echo "✅ Fix script completed. Please try accessing the debug page again."
echo "📋 Check the following URLs:"
echo "- Debug page: https://localhost:3000/debug"
echo "- MailSlurper: https://localhost:4436"
echo "- Kratos health: https://localhost:4433/health/ready"