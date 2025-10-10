#!/bin/bash
# Script to roll back port changes while keeping the model path and database healthcheck fixes

set -e

echo "=== Rolling back port changes ==="
echo "This script will restore original port mappings while keeping the important fixes."

# Create a backup of the current docker-compose.yml file
cp docker-compose.yml docker-compose.yml.rollback.bak

# Roll back port changes in docker-compose.yml
echo "Rolling back port changes in docker-compose.yml..."
sed -i'.bak.rollback' \
    -e 's/8201:8200/8200:8200/g' \
    -e 's/8086:8080/8085:8080/g' \
    -e 's/5434:5432/5433:5432/g' \
    -e 's/1027:1025/1026:1025/g' \
    -e 's/4438:4436/4436:4436/g' \
    -e 's/4439:4437/4437:4437/g' \
    -e 's/4443:4433/4433:4433/g' \
    -e 's/4444:4434/4434:4434/g' \
    -e 's/\${FLASK_PORT:-5051}:5050/\${FLASK_PORT:-5050}:5050/g' \
    -e 's/3002:3000/3000:3000/g' \
    docker-compose.yml

# Roll back port changes in config.yml
echo "Rolling back port changes in config.yml..."
sed -i'.bak.rollback' \
    -e 's|public_url: "https://localhost:4443"|public_url: "https://localhost:4433"|g' \
    -e 's|admin_url: "https://localhost:4444"|admin_url: "https://localhost:4434"|g' \
    conf/config.yml

# Roll back port changes in frontend environment settings
echo "Rolling back frontend configuration..."
sed -i'.bak.rollback' 's|REACT_APP_KRATOS_PUBLIC_URL: "https://localhost:4443"|REACT_APP_KRATOS_PUBLIC_URL: "https://localhost:4433"|g' docker-compose.yml
sed -i'.bak.rollback' 's|REACT_APP_API_URL: "https://localhost:5051"|REACT_APP_API_URL: "https://localhost:5050"|g' docker-compose.yml

# Ensure the app healthcheck URL is updated to match
sed -i'.bak.rollback.health' 's|test: \["CMD", "curl", "-f", "-k", "https://localhost:5051/api/auth/health"\]|test: \["CMD", "curl", "-f", "-k", "https://localhost:5050/api/auth/health"\]|g' docker-compose.yml

# IMPORTANT: Keep the database healthcheck fix
echo "Ensuring database healthcheck remains fixed..."
grep -q "pg_isready.*postgres" docker-compose.yml || \
    sed -i'.bak.dbfix' 's/test: \["CMD", "pg_isready"\]/test: \["CMD", "pg_isready", "-U", "postgres"\]/g' docker-compose.yml

echo ""
echo "Port changes rolled back successfully!"
echo "The model path fix and database healthcheck fix have been preserved."
echo ""
echo "You should restart all services with: ./manage_sting.sh restart"
echo "Or restart individual services with: docker-compose restart [service-name]"