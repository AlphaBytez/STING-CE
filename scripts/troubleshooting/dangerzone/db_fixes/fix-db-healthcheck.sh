#!/bin/bash
# This script fixes the Postgres database healthcheck that was incorrectly using "root" user

set -e

echo "Fixing database healthcheck in docker-compose.yml..."
sed -i'.bak.dbfix' 's/test: \["CMD", "pg_isready"\]/test: \["CMD", "pg_isready", "-U", "postgres"\]/g' docker-compose.yml

echo "Stopping the database container..."
docker-compose stop db

echo "Removing the database container (data will be preserved)..."
docker-compose rm -f db

echo "Bringing up the database container with fixed healthcheck..."
docker-compose up -d db

echo "Waiting for database to become healthy..."
for i in {1..30}; do
  health_status=$(docker inspect --format='{{.State.Health.Status}}' sting-db-1 2>/dev/null || echo "container not found")
  if [ "$health_status" = "healthy" ]; then
    echo "Database container is now healthy!"
    break
  fi
  echo "Waiting for database to become healthy... (attempt $i/30)"
  sleep 5
done

if [ "$health_status" != "healthy" ]; then
  echo "Database container failed to become healthy after multiple attempts."
  echo "Checking logs for errors:"
  docker logs sting-db-1 2>&1 | tail -n 50
  exit 1
fi

echo "Database health check fixed successfully!"
echo "You can now bring up the rest of the services with: docker-compose up -d"