-- Final Permissions Setup
-- This script runs AFTER all other initialization scripts to ensure
-- all permissions are properly set on all created objects

-- Connect to sting_app database to finalize permissions
\c sting_app;

-- Grant all privileges on ALL existing tables, sequences, and functions to app_user
-- This ensures any tables created by previous scripts have proper permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO app_user;

-- Ensure app_user can create new objects
GRANT CREATE ON SCHEMA public TO app_user;

-- Make sure app_user owns all tables created by postgres in this database
-- This fixes the ownership issue that can cause permission problems
DO $$
DECLARE 
    table_name TEXT;
BEGIN
    FOR table_name IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(table_name) || ' OWNER TO app_user';
    END LOOP;
END $$;

-- Do the same for sequences
DO $$
DECLARE 
    seq_name TEXT;
BEGIN
    FOR seq_name IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' LOOP
        EXECUTE 'ALTER SEQUENCE ' || quote_ident(seq_name) || ' OWNER TO app_user';
    END LOOP;
END $$;

-- Connect to sting_messaging database to finalize permissions
\c sting_messaging;

-- Grant all privileges on ALL existing tables, sequences, and functions
GRANT ALL ON ALL TABLES IN SCHEMA public TO messaging_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO messaging_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO messaging_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Ensure proper ownership
DO $$
DECLARE 
    table_name TEXT;
BEGIN
    FOR table_name IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE 'ALTER TABLE ' || quote_ident(table_name) || ' OWNER TO messaging_user';
    END LOOP;
END $$;

DO $$
DECLARE 
    seq_name TEXT;
BEGIN
    FOR seq_name IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' LOOP
        EXECUTE 'ALTER SEQUENCE ' || quote_ident(seq_name) || ' OWNER TO messaging_user';
    END LOOP;
END $$;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'FINAL PERMISSIONS SETUP COMPLETED SUCCESSFULLY';
    RAISE NOTICE 'All database objects have been granted proper';
    RAISE NOTICE 'ownership and permissions to application users';
    RAISE NOTICE '=================================================';
END $$;
