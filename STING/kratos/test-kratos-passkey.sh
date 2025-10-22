#!/bin/bash

# Test Kratos with passwordless WebAuthn configuration

echo "🔐 Testing Kratos with passwordless WebAuthn configuration..."

# Create a test directory
TEST_DIR="/tmp/kratos-passkey-test"
mkdir -p "$TEST_DIR"

# Copy configuration files
cp /Users/captain-wolf/Documents/GitHub/STING-CE/STING/kratos/kratos.yml "$TEST_DIR/"
cp /Users/captain-wolf/Documents/GitHub/STING-CE/STING/kratos/identity.schema.json "$TEST_DIR/"

# Start PostgreSQL for Kratos
echo "📦 Starting PostgreSQL..."
docker run -d \
  --name kratos-test-db \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=kratos \
  -p 5432:5432 \
  postgres:16

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
sleep 10

# Update DSN in kratos.yml for test
sed -i.bak 's|postgresql://.*@db:5432/.*|postgresql://postgres:secret@host.docker.internal:5432/kratos?sslmode=disable|' "$TEST_DIR/kratos.yml"

# Start Kratos
echo "🚀 Starting Kratos with passwordless WebAuthn..."
docker run -d \
  --name kratos-test \
  -p 4433:4433 \
  -p 4434:4434 \
  -v "$TEST_DIR/kratos.yml:/etc/config/kratos/kratos.yml" \
  -v "$TEST_DIR/identity.schema.json:/etc/config/kratos/identity.schema.json" \
  --add-host=host.docker.internal:host-gateway \
  oryd/kratos:latest \
  serve -c /etc/config/kratos/kratos.yml --dev --watch-courier

echo "⏳ Waiting for Kratos to start..."
sleep 10

# Check Kratos health
echo "🏥 Checking Kratos health..."
curl -s http://localhost:4434/admin/health/ready | jq .

# Check configuration
echo "📋 Checking WebAuthn configuration..."
docker exec kratos-test cat /etc/config/kratos/kratos.yml | grep -A 10 "webauthn:"

echo ""
echo "✅ Kratos test instance is running!"
echo "   Public URL: http://localhost:4433"
echo "   Admin URL: http://localhost:4434"
echo ""
echo "🧹 To clean up test containers:"
echo "   docker stop kratos-test kratos-test-db"
echo "   docker rm kratos-test kratos-test-db"