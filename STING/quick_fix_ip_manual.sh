#!/bin/bash
# quick_fix_ip_manual.sh - Manual fix without config_loader.py dependency
# Run this with: sudo bash quick_fix_ip_manual.sh

set -e

IP_ADDRESS="${1:-10.0.0.158}"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo "Fixing STING for IP: $IP_ADDRESS"

# 1. Update frontend.env
echo "Updating frontend.env..."
cat > "${INSTALL_DIR}/env/frontend.env" <<EOF
REACT_APP_API_URL=https://${IP_ADDRESS}:5050
REACT_APP_KRATOS_PUBLIC_URL=https://${IP_ADDRESS}:4433
REACT_APP_KRATOS_BROWSER_URL=https://${IP_ADDRESS}:4433
NODE_ENV=production
PUBLIC_URL=/
EOF

# 2. Update frontend/public/env.js
echo "Updating frontend/public/env.js..."
mkdir -p "${INSTALL_DIR}/frontend/public"
cat > "${INSTALL_DIR}/frontend/public/env.js" <<EOF
window.env = {
  REACT_APP_API_URL: 'https://${IP_ADDRESS}:5050',
  REACT_APP_KRATOS_PUBLIC_URL: 'https://${IP_ADDRESS}:4433',
  REACT_APP_KRATOS_BROWSER_URL: 'https://${IP_ADDRESS}:4433'
};
EOF

# 3. Update app/static/env.js
echo "Updating app/static/env.js..."
mkdir -p "${INSTALL_DIR}/app/static"
cat > "${INSTALL_DIR}/app/static/env.js" <<EOF
window.env = {
  REACT_APP_API_URL: 'https://${IP_ADDRESS}:5050',
  REACT_APP_KRATOS_PUBLIC_URL: 'https://${IP_ADDRESS}:4433',
  REACT_APP_KRATOS_BROWSER_URL: 'https://${IP_ADDRESS}:4433'
};
EOF

# 4. Update app.env
echo "Updating app.env..."
sed -i "s|DOMAIN_NAME=.*|DOMAIN_NAME=${IP_ADDRESS}|g" "${INSTALL_DIR}/env/app.env" || true
sed -i "s|KRATOS_PUBLIC_URL=.*|KRATOS_PUBLIC_URL=https://${IP_ADDRESS}:4433|g" "${INSTALL_DIR}/env/app.env" || true
sed -i "s|KRATOS_BROWSER_URL=.*|KRATOS_BROWSER_URL=https://${IP_ADDRESS}:4433|g" "${INSTALL_DIR}/env/app.env" || true

# 5. Update .env for docker-compose
echo "Updating .env..."
if [ -f "${INSTALL_DIR}/.env" ]; then
    if grep -q "^HOSTNAME=" "${INSTALL_DIR}/.env"; then
        sed -i "s|^HOSTNAME=.*|HOSTNAME=${IP_ADDRESS}|g" "${INSTALL_DIR}/.env"
    else
        echo "HOSTNAME=${IP_ADDRESS}" >> "${INSTALL_DIR}/.env"
    fi
else
    echo "HOSTNAME=${IP_ADDRESS}" > "${INSTALL_DIR}/.env"
fi

echo "Done! Now run the Kratos fix script and restart services."
echo ""
echo "Next steps:"
echo "  sudo bash /opt/sting-ce/scripts/setup/fix_kratos_allowed_urls.sh"
echo "  cd /opt/sting-ce && docker compose restart kratos frontend app"
