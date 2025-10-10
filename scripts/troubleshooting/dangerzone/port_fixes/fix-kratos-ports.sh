#!/bin/bash
# Script to fix Kratos port conflicts and configuration issues

set -e

echo "=== STING Kratos Port Fix ==="
echo "This script will update Kratos ports in all configuration files."

# Step 1: Update the docker-compose.yml file to ensure ports are correctly mapped
echo "Updating port mappings in docker-compose.yml..."
sed -i'.bak.kratos' \
    -e 's/4433:4433/4443:4433/g' \
    -e 's/4434:4434/4444:4434/g' \
    docker-compose.yml

# Step 2: Update the config.yml file for Kratos configuration
echo "Updating Kratos port references in config.yml..."
sed -i'.bak.kratos' \
    -e 's|public_url: "https://localhost:4433"|public_url: "https://localhost:4443"|g' \
    -e 's|admin_url: "https://localhost:4434"|admin_url: "https://localhost:4444"|g' \
    conf/config.yml

# Step 3: Ensure the healthcheck is using the correct internal port
echo "Ensuring healthcheck uses internal port (4434)..."
grep -q "localhost:4434/admin/health/ready" docker-compose.yml || sed -i'.bak.healthcheck' 's|test: \["CMD-SHELL", "wget --no-check-certificate --no-verbose --spider https://localhost:443[0-9]/admin/health/ready|test: \["CMD-SHELL", "wget --no-check-certificate --no-verbose --spider https://localhost:4434/admin/health/ready|g' docker-compose.yml

# Step 4: Check frontend environment settings
echo "Checking frontend configuration..."
grep -q "REACT_APP_KRATOS_PUBLIC_URL.*4443" docker-compose.yml || sed -i'.bak.frontend' 's|REACT_APP_KRATOS_PUBLIC_URL: "https://localhost:4433"|REACT_APP_KRATOS_PUBLIC_URL: "https://localhost:4443"|g' docker-compose.yml

# Step 5: Update any env files
if [ -f "env/kratos.env" ]; then
    echo "Updating Kratos environment variables..."
    grep -q "KRATOS_PUBLIC_PORT=4443" env/kratos.env || sed -i'.bak.kratos' 's/KRATOS_PUBLIC_PORT=4433/KRATOS_PUBLIC_PORT=4443/g' env/kratos.env
    grep -q "KRATOS_ADMIN_PORT=4444" env/kratos.env || sed -i'.bak.kratos' 's/KRATOS_ADMIN_PORT=4434/KRATOS_ADMIN_PORT=4444/g' env/kratos.env
fi

echo "Port fixes applied successfully!"
echo "You should restart Kratos using: docker-compose restart kratos"
echo "To verify Kratos is working, run: curl -k https://localhost:4444/admin/health/ready"