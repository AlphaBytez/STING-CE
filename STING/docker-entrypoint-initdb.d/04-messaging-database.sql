-- Create messaging database for STING CE
-- This database handles messaging queue and notifications

-- Connect to postgres database to create the messaging database
\c postgres;

-- Create the messaging database if it doesn't exist
CREATE DATABASE sting_messaging;

-- Connect to the messaging database
\c sting_messaging;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant privileges to messaging_user (primary user for messaging service)
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO messaging_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO messaging_user;

-- Grant privileges to app_user (for cross-service operations)
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO messaging_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO app_user;

-- Also ensure postgres user retains superuser access for maintenance
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO postgres;

-- Log successful database creation
DO $$
BEGIN
    RAISE NOTICE 'Messaging database created successfully';
    RAISE NOTICE '  - Database: sting_messaging';
    RAISE NOTICE '  - Primary user: messaging_user';
    RAISE NOTICE '  - Cross-service access: app_user';
END $$;