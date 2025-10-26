-- Migration: Add missing updated_at field to documents table
-- Issue: Knowledge service failing because trigger expects updated_at field
-- Solution: Add updated_at column and ensure trigger works correctly

-- Description:
-- The update_updated_at_column() trigger function expects an updated_at field
-- but the documents table was missing this field, causing:
-- ERROR: record "new" has no field "updated_at"

BEGIN;

-- Add updated_at column to documents table if it doesn't exist
DO $$
BEGIN
    -- Check if updated_at column exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'documents'
        AND column_name = 'updated_at'
    ) THEN
        -- Add the missing updated_at column
        ALTER TABLE documents ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

        -- Update existing records to have updated_at = upload_date
        UPDATE documents SET updated_at = upload_date WHERE updated_at IS NULL;

        RAISE NOTICE 'Added updated_at column to documents table';
    ELSE
        RAISE NOTICE 'updated_at column already exists on documents table';
    END IF;
END
$$;

-- Ensure the trigger exists and works correctly
-- The trigger should update updated_at when documents are modified
DO $$
BEGIN
    -- Check if the trigger exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.triggers
        WHERE event_object_table = 'documents'
        AND trigger_name = 'update_documents_updated_at'
    ) THEN
        -- Create the trigger
        CREATE TRIGGER update_documents_updated_at
            BEFORE UPDATE ON documents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        RAISE NOTICE 'Created update_documents_updated_at trigger';
    ELSE
        RAISE NOTICE 'update_documents_updated_at trigger already exists';
    END IF;
END
$$;

-- Verify the update_updated_at_column function exists
-- If it doesn't exist, create it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.routines
        WHERE routine_name = 'update_updated_at_column'
    ) THEN
        -- Create the trigger function
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $func$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END
        $func$ LANGUAGE plpgsql;

        RAISE NOTICE 'Created update_updated_at_column function';
    ELSE
        RAISE NOTICE 'update_updated_at_column function already exists';
    END IF;
END
$$;

-- Verify the migration worked
DO $$
BEGIN
    -- Test that we can reference updated_at field
    PERFORM updated_at FROM documents LIMIT 1;
    RAISE NOTICE 'Migration verification passed: updated_at field is accessible';
EXCEPTION
    WHEN undefined_column THEN
        RAISE EXCEPTION 'Migration failed: updated_at field still not accessible';
END
$$;

COMMIT;

-- Post-migration notes:
-- 1. Knowledge service should now start successfully
-- 2. Demo generation should complete all steps
-- 3. Document updates will automatically set updated_at timestamp
-- 4. This fixes the ChromaDB integration that was failing during startup