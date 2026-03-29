-- Migration 017: Add report progress tracking columns
-- The Report model expects status_message and current_stage columns
-- that were added to the SQLAlchemy model but not migrated to the database.

-- Add status_message column for human-readable progress updates
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'reports' AND column_name = 'status_message'
    ) THEN
        ALTER TABLE reports ADD COLUMN status_message VARCHAR(255);
        RAISE NOTICE 'Added status_message column to reports table';
    ELSE
        RAISE NOTICE 'status_message column already exists';
    END IF;
END $$;

-- Add current_stage column for processing stage tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'reports' AND column_name = 'current_stage'
    ) THEN
        ALTER TABLE reports ADD COLUMN current_stage VARCHAR(50);
        RAISE NOTICE 'Added current_stage column to reports table';
    ELSE
        RAISE NOTICE 'current_stage column already exists';
    END IF;
END $$;
