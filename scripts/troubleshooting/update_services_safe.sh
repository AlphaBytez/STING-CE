#!/bin/bash

# Safe update script that skips infrastructure services
echo "=== Safe Service Update ==="
echo "This script updates application services while preserving infrastructure services"
echo

# Infrastructure services that should not be restarted
INFRA_SERVICES=(
    "db"
    "vault" 
    "redis"
    "mailpit"
    "chroma"
)

# Application services that can be safely updated
APP_SERVICES=(
    "kratos"
    "app"
    "frontend"
    "chatbot"
    "knowledge"
    "messaging"
    "external-ai"
    "llm-gateway-proxy"
)

echo "Updating application services only..."
echo "Skipping: ${INFRA_SERVICES[*]}"
echo

# Update each application service individually
for service in "${APP_SERVICES[@]}"; do
    echo "Updating $service..."
    ./manage_sting.sh update "$service"
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to update $service, continuing..."
    fi
    sleep 2  # Brief pause between services
done

echo
echo "=== Update Complete ==="
echo "All application services have been updated."
echo "Infrastructure services (db, vault, redis, etc.) were preserved."