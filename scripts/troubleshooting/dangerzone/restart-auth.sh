#!/bin/bash
set -e

echo "Stopping services..."
./manage_sting.sh stop kratos frontend

echo "Rebuilding services..."
./manage_sting.sh build kratos frontend

echo "Starting services..."
./manage_sting.sh start kratos frontend

echo "Running Kratos migrations to ensure schema changes are applied..."
docker exec sting-ce-kratos-1 kratos migrate sql -e --yes

echo "Services restarted. Please try the passkey functionality again."
echo "Access the application at: https://localhost:3000"
echo ""
echo "Test WebAuthn support directly at: https://localhost:3000/test-passkey"
echo ""
echo "If you encounter issues:"
echo "1. Check browser console for errors"
echo "2. Verify your browser supports WebAuthn"
echo "3. Try clearing your browser cache and cookies"