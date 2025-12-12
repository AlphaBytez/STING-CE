#!/bin/bash

# Setup Grafana dashboards for STING
echo "🎯 Setting up STING Grafana dashboards..."

GRAFANA_URL="http://localhost:3001"
GRAFANA_USER="admin"
GRAFANA_PASS="nL3dfxEy1KgsGQXX"

# Wait for Grafana to be ready
echo "⏳ Waiting for Grafana to be ready..."
for i in {1..30}; do
    if curl -s "${GRAFANA_URL}/api/health" > /dev/null 2>&1; then
        echo "[+] Grafana is ready!"
        break
    fi
    echo -n "."
    sleep 2
done

# First, setup the Loki data source if not exists
echo "📊 Setting up Loki data source..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  -d '{
    "name": "Loki",
    "type": "loki",
    "url": "http://sting-ce-loki:3100",
    "access": "proxy",
    "isDefault": true,
    "jsonData": {}
  }' \
  "${GRAFANA_URL}/api/datasources" 2>/dev/null

echo ""
echo "📈 Importing dashboards..."

# Import each dashboard
for dashboard in grafana-dashboards/*.json; do
    if [ -f "$dashboard" ]; then
        dashboard_name=$(basename "$dashboard" .json)
        echo "  - Importing ${dashboard_name}..."
        
        # Wrap the dashboard JSON in the import format
        jq '{dashboard: ., overwrite: true, inputs: [], folderId: 0}' "$dashboard" | \
        curl -X POST \
          -H "Content-Type: application/json" \
          -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
          -d @- \
          "${GRAFANA_URL}/api/dashboards/import" > /dev/null 2>&1
          
        if [ $? -eq 0 ]; then
            echo "    [+] Imported successfully"
        else
            echo "    [!]  Import failed (dashboard might already exist)"
        fi
    fi
done

echo ""
echo " Dashboard setup complete!"
echo ""
echo "📊 Access your dashboards at: ${GRAFANA_URL}"
echo "   Default login: admin / admin"
echo ""
echo "Available dashboards:"
echo "  1. STING System Overview - Overall system health and logs"
echo "  2. STING Authentication Audit - Login attempts and security events"
echo ""
echo "TIP: Tip: The dashboards will start populating with data as services generate logs."
echo "        Generate some activity by logging in/out or using the application."