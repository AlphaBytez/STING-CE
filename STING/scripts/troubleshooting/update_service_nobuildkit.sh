#!/bin/bash
# Quick fix for BuildKit caching issue - update service without BuildKit

set -e

# Get service name from command line
SERVICE="$1"

if [ -z "$SERVICE" ]; then
    echo "Usage: $0 <service_name>"
    echo "Example: $0 app"
    exit 1
fi

# Set directories
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.sting-ce"

echo "🔧 Updating $SERVICE service (BuildKit disabled)..."

# Step 1: Copy files from project to install directory
echo "📋 Copying files..."
case "$SERVICE" in
    app)
        rsync -av --delete "$PROJECT_DIR/app/" "$INSTALL_DIR/app/"
        ;;
    frontend)
        rsync -av --delete "$PROJECT_DIR/frontend/" "$INSTALL_DIR/frontend/"
        ;;
    chatbot)
        rsync -av --delete "$PROJECT_DIR/chatbot/" "$INSTALL_DIR/chatbot/"
        ;;
    *)
        echo "⚠️  Unknown service: $SERVICE"
        echo "📋 Copying entire service directory..."
        if [ -d "$PROJECT_DIR/$SERVICE" ]; then
            rsync -av --delete "$PROJECT_DIR/$SERVICE/" "$INSTALL_DIR/$SERVICE/"
        fi
        ;;
esac

# Step 2: Stop and remove the container
echo "🛑 Stopping $SERVICE..."
docker compose -f "$INSTALL_DIR/docker-compose.yml" stop "$SERVICE"
docker compose -f "$INSTALL_DIR/docker-compose.yml" rm -f "$SERVICE"

# Step 3: Remove the old image
echo "🗑️  Removing old image..."
docker rmi "sting-ce-$SERVICE:latest" 2>/dev/null || true

# Step 4: Build without BuildKit
echo "🔨 Building $SERVICE (BuildKit disabled)..."
cd "$INSTALL_DIR"
DOCKER_BUILDKIT=0 docker compose build --no-cache "$SERVICE"

# Step 5: Start the service
echo "🚀 Starting $SERVICE..."
docker compose up -d "$SERVICE"

# Step 6: Verify the update
echo "✅ Verifying update..."
sleep 5

# Check if container is running
if docker ps | grep -q "sting-ce-$SERVICE"; then
    echo "✅ $SERVICE is running"
    
    # For app service, check if the new code is present
    if [ "$SERVICE" = "app" ]; then
        if docker exec "sting-ce-$SERVICE" grep -q "logout_flow_url" /opt/sting-ce/app/routes/auth_routes.py 2>/dev/null; then
            echo "✅ New code is present in container"
        else
            echo "⚠️  Warning: New code may not be present in container"
            echo "   You may need to manually copy files:"
            echo "   docker cp $INSTALL_DIR/app/routes/auth_routes.py sting-ce-app:/opt/sting-ce/app/routes/"
        fi
    fi
else
    echo "❌ $SERVICE is not running"
    exit 1
fi

echo "✅ Update complete!"