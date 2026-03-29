-- Migration 018: Add session jar columns to honey_jars table
-- Supports temporary session-scoped honey jars for chat file uploads.

-- Add jar_type column (standard or session)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'honey_jars' AND column_name = 'jar_type'
    ) THEN
        ALTER TABLE honey_jars ADD COLUMN jar_type VARCHAR(20) DEFAULT 'standard';
        RAISE NOTICE 'Added jar_type column to honey_jars table';
    ELSE
        RAISE NOTICE 'jar_type column already exists';
    END IF;
END $$;

-- Add conversation_id column (links session jar to a conversation)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'honey_jars' AND column_name = 'conversation_id'
    ) THEN
        ALTER TABLE honey_jars ADD COLUMN conversation_id VARCHAR(255);
        CREATE INDEX IF NOT EXISTS idx_honey_jars_conversation_id ON honey_jars(conversation_id);
        RAISE NOTICE 'Added conversation_id column and index to honey_jars table';
    ELSE
        RAISE NOTICE 'conversation_id column already exists';
    END IF;
END $$;

-- Add max_size_bytes column (per-jar size limit)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'honey_jars' AND column_name = 'max_size_bytes'
    ) THEN
        ALTER TABLE honey_jars ADD COLUMN max_size_bytes INTEGER;
        RAISE NOTICE 'Added max_size_bytes column to honey_jars table';
    ELSE
        RAISE NOTICE 'max_size_bytes column already exists';
    END IF;
END $$;

-- Add index for jar_type to speed up filtering
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'honey_jars' AND indexname = 'idx_honey_jars_jar_type'
    ) THEN
        CREATE INDEX idx_honey_jars_jar_type ON honey_jars(jar_type);
        RAISE NOTICE 'Created jar_type index on honey_jars table';
    ELSE
        RAISE NOTICE 'jar_type index already exists';
    END IF;
END $$;
