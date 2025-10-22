-- Migration: Add updated_at column to honey_jars table
-- The update_updated_at_column() trigger expects 'updated_at' but table only has 'last_updated'

-- Add the updated_at column if it doesn't exist
ALTER TABLE honey_jars ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Copy existing last_updated values to updated_at for consistency
UPDATE honey_jars SET updated_at = last_updated WHERE updated_at IS NULL;

-- Add trigger to automatically update the updated_at timestamp
DROP TRIGGER IF EXISTS update_honey_jars_updated_at ON honey_jars;
CREATE TRIGGER update_honey_jars_updated_at
    BEFORE UPDATE ON honey_jars
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Note: Keeping last_updated column for backward compatibility
-- Future code should use updated_at for consistency with other tables