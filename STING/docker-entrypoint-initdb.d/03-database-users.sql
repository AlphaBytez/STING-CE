-- Database User Setup for STING CE
-- This script creates separate database users for better security and separation of concerns

-- Connect to postgres database to create users
\c postgres;

-- Create separate database users with secure passwords
-- In production, these should be loaded from environment variables or secrets
CREATE USER kratos_user WITH PASSWORD 'kratos_secure_password_change_me';
CREATE USER app_user WITH PASSWORD 'app_secure_password_change_me';
CREATE USER messaging_user WITH PASSWORD 'messaging_secure_password_change_me';

-- Grant connection privileges
GRANT CONNECT ON DATABASE kratos TO kratos_user;
GRANT CONNECT ON DATABASE sting_app TO app_user;
GRANT CONNECT ON DATABASE sting_messaging TO messaging_user;

-- Connect to kratos database to set up permissions
\c kratos;

-- Grant all privileges on kratos database to kratos_user
GRANT ALL PRIVILEGES ON DATABASE kratos TO kratos_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO kratos_user;
GRANT CREATE ON SCHEMA public TO kratos_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO kratos_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO kratos_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO kratos_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO kratos_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO kratos_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO kratos_user;

-- Connect to sting_app database to set up permissions
\c sting_app;

-- Grant all privileges on sting_app database to app_user
GRANT ALL PRIVILEGES ON DATABASE sting_app TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;

-- Grant permissions on existing tables, sequences, and functions
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- Set default privileges for future objects created by postgres
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public 
    GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO app_user;

-- Set default privileges for future objects created by app_user
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public 
    GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO app_user;

-- Connect to sting_messaging database to set up permissions
\c sting_messaging;

-- Grant all privileges on sting_messaging database to messaging_user
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO messaging_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO messaging_user;
GRANT CREATE ON SCHEMA public TO messaging_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO messaging_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO messaging_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO messaging_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON TABLES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON SEQUENCES TO messaging_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL ON FUNCTIONS TO messaging_user;

-- Also grant app_user access to messaging database for cross-service operations
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO app_user;

-- Also ensure postgres user retains superuser access for maintenance
GRANT ALL PRIVILEGES ON DATABASE kratos TO postgres;
GRANT ALL PRIVILEGES ON DATABASE sting_app TO postgres;
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO postgres;

-- Log successful user creation
DO $$
BEGIN
    RAISE NOTICE 'Database users created successfully:';
    RAISE NOTICE '  - kratos_user: For Kratos authentication service';
    RAISE NOTICE '  - app_user: For STING application services';
    RAISE NOTICE '  - messaging_user: For messaging queue service';
    RAISE NOTICE 'Remember to change default passwords in production!';
END $$;