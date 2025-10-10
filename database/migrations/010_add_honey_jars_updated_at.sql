-- Migration: Add missing updated_at field to honey_jars table
-- Issue: Documents insert triggers honey_jar stats update which fails due to missing updated_at column
-- Solution: Add updated_at column to honey_jars to support automatic trigger updates

-- Description:
-- When documents are inserted, the trigger_update_honey_jar_stats() function runs
-- This function updates the honey_jars table, which has an update_honey_jars_updated_at trigger
-- That trigger calls update_updated_at_column() which expects an updated_at field
-- but the honey_jars table was missing this field, causing:
-- ERROR: record "new" has no field "updated_at"

BEGIN;

-- Add updated_at column to honey_jars table if it doesn't exist
DO $$
BEGIN
    -- Check if updated_at column exists on honey_jars
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'honey_jars'
        AND column_name = 'updated_at'
    ) THEN
        -- Add the missing updated_at column
        ALTER TABLE honey_jars ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

        -- Copy existing last_updated values to updated_at for consistency
        UPDATE honey_jars SET updated_at = last_updated WHERE updated_at IS NULL;

        RAISE NOTICE 'Added updated_at column to honey_jars table';
    ELSE
        RAISE NOTICE 'updated_at column already exists on honey_jars table';
    END IF;
END
$$;

-- Ensure the trigger exists and works correctly
-- The trigger should update updated_at when honey_jars are modified
DO $$
BEGIN
    -- Check if the trigger exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.triggers
        WHERE event_object_table = 'honey_jars'
        AND trigger_name = 'update_honey_jars_updated_at'
    ) THEN
        -- Create the trigger
        CREATE TRIGGER update_honey_jars_updated_at
            BEFORE UPDATE ON honey_jars
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        RAISE NOTICE 'Created update_honey_jars_updated_at trigger';
    ELSE
        RAISE NOTICE 'update_honey_jars_updated_at trigger already exists';
    END IF;
END
$$;

-- Verify the migration worked
DO $$
BEGIN
    -- Test that we can reference updated_at field on honey_jars
    PERFORM updated_at FROM honey_jars LIMIT 1;
    RAISE NOTICE 'Migration verification passed: honey_jars.updated_at field is accessible';
EXCEPTION
    WHEN undefined_column THEN
        RAISE EXCEPTION 'Migration failed: honey_jars.updated_at field still not accessible';
END
$$;

COMMIT;

-- Post-migration notes:
-- 1. Knowledge service should now start successfully during fresh installs
-- 2. Document insertion will complete without trigger errors
-- 3. Honey jar updates will automatically set updated_at timestamp
-- 4. This fixes the installation failure during knowledge service startup