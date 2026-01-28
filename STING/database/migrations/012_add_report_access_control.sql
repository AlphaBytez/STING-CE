-- Migration: Add access control fields to reports table
-- Date: 2025-11-09
-- Description: Adds access_grants and access_type columns for Bee-generated reports

-- Create access_type enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE report_access_type AS ENUM ('user-owned', 'service-generated');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add access_grants column
ALTER TABLE reports ADD COLUMN IF NOT EXISTS access_grants JSON DEFAULT '[]';

-- Add access_type column  
ALTER TABLE reports ADD COLUMN IF NOT EXISTS access_type report_access_type DEFAULT 'user-owned';

-- Update existing records
UPDATE reports SET access_type = 'user-owned' WHERE access_type IS NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reports_access_type ON reports(access_type);
CREATE INDEX IF NOT EXISTS idx_reports_generated_by ON reports(generated_by);

-- Grant permissions
GRANT ALL ON reports TO app_user;
