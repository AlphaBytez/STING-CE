#!/bin/bash

# STING Database Migration Application Script
# This script applies any missing database schema updates to an existing installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running from correct directory
if [ ! -f "./manage_sting.sh" ]; then
    log_error "Please run this script from the STING root directory"
    exit 1
fi

# Get the database container name
DB_CONTAINER="sting-ce-db"

# Check if database container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    log_error "Database container ${DB_CONTAINER} is not running"
    log_info "Please start STING services first: ./manage_sting.sh start"
    exit 1
fi

log_info "Starting database migration process..."

# Function to apply a migration
apply_migration() {
    local migration_file=$1
    local migration_name=$(basename $migration_file)
    
    log_info "Applying migration: ${migration_name}"
    
    # Apply the migration
    if docker exec -i ${DB_CONTAINER} psql -U postgres -d sting_app < "$migration_file" 2>&1 | grep -v "already exists\|duplicate key\|does not exist"; then
        log_success "Applied ${migration_name}"
        return 0
    else
        # Check if there were actual errors (not just notices)
        local result=$?
        if [ $result -ne 0 ]; then
            log_warning "Migration ${migration_name} had warnings or was already applied"
        fi
        return 0
    fi
}

# Function to fix passkey table schema
fix_passkey_schema() {
    log_info "Fixing passkey table schema..."
    
    # Create a temporary SQL file with the fixes
    cat > /tmp/fix_passkey_schema.sql << 'EOF'
-- Fix passkey table columns to match application expectations
\c sting_app;

-- First, check if we need to fix the passkey tables
DO $$
BEGIN
    -- Check if public_key is TEXT instead of BYTEA
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'passkeys' 
        AND column_name = 'public_key' 
        AND data_type = 'text'
    ) THEN
        -- Drop the old table and recreate with correct schema
        DROP TABLE IF EXISTS passkey_authentication_challenges CASCADE;
        DROP TABLE IF EXISTS passkey_registration_challenges CASCADE;
        DROP TABLE IF EXISTS passkeys CASCADE;
        
        -- Recreate with correct schema
        CREATE TABLE passkeys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            credential_id VARCHAR(1024) UNIQUE NOT NULL,
            public_key BYTEA NOT NULL,
            counter INTEGER DEFAULT 0 NOT NULL,
            device_name VARCHAR(255),
            device_type VARCHAR(100),
            aaguid VARCHAR(36),
            status VARCHAR(20) DEFAULT 'active' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_used_at TIMESTAMP WITH TIME ZONE,
            transports JSONB,
            backup_eligible BOOLEAN DEFAULT FALSE NOT NULL,
            backup_state BOOLEAN DEFAULT FALSE NOT NULL,
            metadata JSONB,
            name VARCHAR(255),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            usage_count INTEGER DEFAULT 0 NOT NULL,
            user_agent VARCHAR(500),
            ip_address VARCHAR(45)
        );
        
        CREATE TABLE passkey_registration_challenges (
            id SERIAL PRIMARY KEY,
            challenge_id VARCHAR(128) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            challenge VARCHAR(1024) NOT NULL,
            user_verification VARCHAR(20) NOT NULL,
            attestation VARCHAR(20) NOT NULL,
            timeout INTEGER DEFAULT 300000 NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used BOOLEAN DEFAULT FALSE NOT NULL,
            registration_options JSONB
        );
        
        CREATE TABLE passkey_authentication_challenges (
            id SERIAL PRIMARY KEY,
            challenge_id VARCHAR(128) UNIQUE NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            challenge VARCHAR(1024) NOT NULL,
            user_verification VARCHAR(20) NOT NULL,
            timeout INTEGER DEFAULT 300000 NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used BOOLEAN DEFAULT FALSE NOT NULL,
            authentication_options JSONB
        );
        
        RAISE NOTICE 'Passkey tables recreated with correct schema';
    ELSE
        -- Just ensure the columns exist with correct names
        -- Add missing columns if they don't exist
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS counter INTEGER DEFAULT 0 NOT NULL;
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS aaguid VARCHAR(36);
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS transports JSONB;
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS backup_eligible BOOLEAN DEFAULT FALSE NOT NULL;
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS backup_state BOOLEAN DEFAULT FALSE NOT NULL;
        ALTER TABLE passkeys ADD COLUMN IF NOT EXISTS metadata JSONB;
        
        -- Rename columns if needed
        DO $rename$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'passkeys' AND column_name = 'sign_count') THEN
                ALTER TABLE passkeys RENAME COLUMN sign_count TO counter;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'passkeys' AND column_name = 'is_backup_eligible') THEN
                ALTER TABLE passkeys RENAME COLUMN is_backup_eligible TO backup_eligible;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'passkeys' AND column_name = 'is_backup_state') THEN
                ALTER TABLE passkeys RENAME COLUMN is_backup_state TO backup_state;
            END IF;
        END $rename$;
        
        RAISE NOTICE 'Passkey table columns verified/updated';
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_passkeys_user_id ON passkeys(user_id);
CREATE INDEX IF NOT EXISTS idx_passkeys_credential_id ON passkeys(credential_id);
CREATE INDEX IF NOT EXISTS idx_passkeys_status ON passkeys(status);
CREATE INDEX IF NOT EXISTS idx_passkeys_user_id_status ON passkeys(user_id, status);

CREATE INDEX IF NOT EXISTS idx_passkey_reg_challenges_challenge_id ON passkey_registration_challenges(challenge_id);
CREATE INDEX IF NOT EXISTS idx_passkey_reg_challenges_user_id ON passkey_registration_challenges(user_id);
CREATE INDEX IF NOT EXISTS idx_passkey_reg_challenges_expires_at ON passkey_registration_challenges(expires_at);

CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_challenge_id ON passkey_authentication_challenges(challenge_id);
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_user_id ON passkey_authentication_challenges(user_id);
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_expires_at ON passkey_authentication_challenges(expires_at);

-- Ensure the cleanup function exists
CREATE OR REPLACE FUNCTION cleanup_expired_passkey_challenges()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM passkey_registration_challenges 
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM passkey_authentication_challenges 
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON passkeys TO app_user;
GRANT ALL PRIVILEGES ON passkey_registration_challenges TO app_user;
GRANT ALL PRIVILEGES ON passkey_authentication_challenges TO app_user;
GRANT ALL PRIVILEGES ON passkeys_id_seq TO app_user;
GRANT ALL PRIVILEGES ON passkey_registration_challenges_id_seq TO app_user;
GRANT ALL PRIVILEGES ON passkey_authentication_challenges_id_seq TO app_user;
EOF
    
    # Apply the fix
    if docker exec -i ${DB_CONTAINER} psql -U postgres < /tmp/fix_passkey_schema.sql 2>&1 | grep -v "already exists\|duplicate key"; then
        log_success "Passkey schema fixed"
    else
        log_warning "Passkey schema fix completed with warnings"
    fi
    
    rm -f /tmp/fix_passkey_schema.sql
}

# Main migration process
log_info "Checking and applying database migrations..."

# Fix passkey schema first (critical for enrollment)
fix_passkey_schema

# Apply SQL migration files if they exist
if [ -d "database/migrations" ]; then
    # Get list of migration files in order
    migrations=$(ls database/migrations/*.sql 2>/dev/null | sort)

    if [ -z "$migrations" ]; then
        log_info "No SQL migration files found"
    else
        for migration in $migrations; do
            # Skip certain migrations that are already in complete_schema.sql
            migration_name=$(basename $migration)
            case $migration_name in
                "002_kratos_user_models.sql"|"003_passkey_models.sql"|"005_update_passkey_models.sql")
                    log_info "Skipping $migration_name (already in core schema)"
                    ;;
                *)
                    apply_migration "$migration"
                    ;;
            esac
        done
    fi
else
    log_warning "No migrations directory found"
fi

# Apply Python migration files if they exist
if [ -d "app/migrations" ]; then
    # Get list of Python migration files in order
    python_migrations=$(ls app/migrations/*.py 2>/dev/null | grep -v "__pycache__\|__init__" | sort)

    if [ -z "$python_migrations" ]; then
        log_info "No Python migration files found"
    else
        log_info "Applying Python migrations..."
        for migration in $python_migrations; do
            migration_name=$(basename $migration)
            log_info "Applying Python migration: ${migration_name}"

            # Execute Python migration via app container
            if docker compose exec -T app python "$migration" 2>&1; then
                log_success "Applied ${migration_name}"
            else
                log_warning "Migration ${migration_name} had warnings or was already applied"
            fi
        done
    fi
else
    log_info "No app/migrations directory found"
fi

# Verify critical tables exist
log_info "Verifying critical tables..."

docker exec ${DB_CONTAINER} psql -U postgres -d sting_app -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'passkeys', 'passkey_registration_challenges', 'passkey_authentication_challenges')
ORDER BY table_name;
" | grep -E "users|passkey" && log_success "Critical tables verified" || log_error "Some critical tables missing"

# Check passkey column types
log_info "Verifying passkey table schema..."

docker exec ${DB_CONTAINER} psql -U postgres -d sting_app -c "
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'passkeys' 
AND column_name IN ('credential_id', 'public_key', 'counter', 'aaguid', 'backup_eligible')
ORDER BY column_name;
"

log_success "Database migration check complete!"
log_info ""
log_info "Next steps:"
log_info "1. Restart the app service: ./manage_sting.sh restart app"
log_info "2. Clear browser cache and cookies"
log_info "3. Test passkey registration in enrollment"

# Optional: Run cleanup of expired challenges
log_info ""
log_info "Running cleanup of expired challenges..."
docker exec ${DB_CONTAINER} psql -U postgres -d sting_app -c "SELECT cleanup_expired_passkey_challenges();"

log_success "Migration script complete!"