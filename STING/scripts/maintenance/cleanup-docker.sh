#!/bin/bash

# Docker cleanup script to prevent space issues
echo "🧹 Starting Docker cleanup..."

# Show current space usage
echo "📊 Current Docker space usage:"
docker system df

# Clean up build cache (keep last 24 hours)
echo "🗑️  Cleaning build cache..."
docker buildx prune -f --filter until=24h

# Clean up unused images
echo "🖼️  Cleaning unused images..."
docker image prune -f --filter until=24h

# Clean up unused containers
echo "📦 Cleaning unused containers..."
docker container prune -f --filter until=24h

# Clean up unused volumes (be careful with this)
echo "💾 Cleaning unused volumes..."
docker volume prune -f

# Clean up unused networks
echo "🌐 Cleaning unused networks..."
docker network prune -f

# Show space after cleanup
echo "✅ Space usage after cleanup:"
docker system df

echo "🎉 Docker cleanup complete!"