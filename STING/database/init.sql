-- First connect to postgres database
\c postgres;

-- Create all required databases (ignore errors if they already exist)
SELECT 'CREATE DATABASE sting_app' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sting_app')\gexec
SELECT 'CREATE DATABASE kratos' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'kratos')\gexec  
SELECT 'CREATE DATABASE sting_messaging' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sting_messaging')\gexec

-- Create dedicated database users with secure passwords
-- These passwords should match docker-compose.yml connection strings
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kratos_user') THEN
        CREATE USER kratos_user WITH PASSWORD 'kratos_secure_password_change_me';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE USER app_user WITH PASSWORD 'app_secure_password_change_me';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'messaging_user') THEN
        CREATE USER messaging_user WITH PASSWORD 'messaging_secure_password_change_me';
    END IF;
END
$$;

-- Set up Kratos database with proper permissions
\c kratos;
GRANT ALL PRIVILEGES ON DATABASE kratos TO kratos_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO kratos_user;
GRANT CREATE ON SCHEMA public TO kratos_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO kratos_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO kratos_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO kratos_user;

-- Set up application database with proper permissions
\c sting_app;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

GRANT ALL PRIVILEGES ON DATABASE sting_app TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO app_user;

-- Set up messaging database with proper permissions
\c sting_messaging;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO messaging_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO messaging_user;
GRANT CREATE ON SCHEMA public TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO messaging_user;

-- Grant app_user access to messaging database as well (for cross-service operations)
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;

-- Ensure postgres superuser has full access to all databases
GRANT ALL PRIVILEGES ON DATABASE kratos TO postgres;
GRANT ALL PRIVILEGES ON DATABASE sting_app TO postgres;
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO postgres;

-- Back to sting_app database for table creation
\c sting_app;

-- Create schema if it doesn't exist (should already exist)
CREATE SCHEMA IF NOT EXISTS public;

-- Set up proper ownership and permissions for all databases
ALTER DATABASE sting_app OWNER TO postgres;
ALTER DATABASE kratos OWNER TO postgres;
ALTER DATABASE sting_messaging OWNER TO postgres;

-- Ensure postgres has all permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;

-- =============================================
-- IMPORTANT: Use complete_schema.sql for new installations
-- This file is kept for backward compatibility but is incomplete
-- For fresh installations, use: database/complete_schema.sql
-- =============================================

-- WARNING: This file contains only basic tables and is INCOMPLETE
-- The complete schema is available in database/complete_schema.sql

-- NOTE: The complete schema includes all current tables with proper:
-- - User management (users, user_settings with preference columns)
-- - Passkey authentication (passkeys, challenges, biometric_authentications) 
-- - API key management (api_keys, api_key_usage)
-- - Honey jars and documents (honey_jars, documents)
-- - Reporting system (report_templates, reports, report_queue)
-- - Nectar bots (nectar_bots, nectar_bot_usage, nectar_bot_handoffs)
-- - Organization preferences (organization_preferences, user_preference_history)
-- - Proper indexes and triggers

-- For development/compatibility - basic tables only
CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit log table for tracking changes
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(255) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id UUID REFERENCES app_users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_app_users_updated_at
    BEFORE UPDATE ON app_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_app_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions on all created objects to all relevant users
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Grant permissions to app_user on sting_app database tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_sessions_user_id ON app_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record ON audit_logs(table_name, record_id);
