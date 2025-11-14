#!/bin/bash
# Migration to fix postgres password to match db.env
# This handles the case where database was initialized before env files were generated

echo "Checking if postgres password needs to be updated..."

# Read password from db.env
DB_ENV_FILE="${INSTALL_DIR:-/opt/sting-ce}/env/db.env"
if [ ! -f "$DB_ENV_FILE" ]; then
    echo "Warning: db.env not found at $DB_ENV_FILE"
    exit 0
fi

POSTGRES_PASSWORD=$(grep '^POSTGRES_PASSWORD=' "$DB_ENV_FILE" | cut -d'=' -f2-)

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Warning: POSTGRES_PASSWORD not found in db.env"
    exit 0
fi

# Try to connect with the password from db.env
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h db -U postgres -c "SELECT 1" >/dev/null 2>&1; then
    echo "✅ Postgres password already matches db.env"
    exit 0
fi

# Password doesn't match, try with default 'postgres' password and update it
if PGPASSWORD='postgres' psql -h db -U postgres -c "ALTER USER postgres WITH PASSWORD '$POSTGRES_PASSWORD';" >/dev/null 2>&1; then
    echo "✅ Updated postgres password to match db.env"
    exit 0
else
    echo "Warning: Could not update postgres password (database may not be accessible)"
    exit 0
fi
