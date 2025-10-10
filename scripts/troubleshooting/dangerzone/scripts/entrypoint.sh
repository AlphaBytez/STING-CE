#!/bin/bash
set -euo pipefail

# Export required environment variables
export KC_DB_URL KC_DB_USERNAME KC_DB_PASSWORD KEYSTORE_PASSWORD

# Print configuration for debugging
echo "Starting Keycloak with configuration:"
echo "Database URL: $KC_DB_URL"
echo "Database Username: $KC_DB_USERNAME"
echo "Hostname: $KC_HOSTNAME"

# Wait for PostgreSQL using nc (netcat) which is included in the base image
echo "Waiting for PostgreSQL..."
timeout 60s bash -c 'until printf "" 2>>/dev/null >>/dev/tcp/db/5432; do sleep 1; echo "Waiting for PostgreSQL..."; done'
echo "PostgreSQL is ready"

echo "Starting Keycloak..."
exec /opt/keycloak/bin/kc.sh \
    start-dev \
    --db=postgres \
    --db-url="$KC_DB_URL" \
    --db-username="$KC_DB_USERNAME" \
    --db-password="$KC_DB_PASSWORD" \
    --http-enabled=true \
    --hostname="$KC_HOSTNAME" \
    --hostname-strict=false \
    --hostname-strict-https=false \
    --proxy=edge \
    --http-relative-path=/auth \
    --http-port=8080 \
    --log-level=INFO