-- Migration: Add progress tracking fields to reports table
-- Date: 2025-06-01
-- Description: Adds status_message and current_stage columns for improved progress tracking

-- Add status_message column (human-readable progress message)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS status_message VARCHAR(255);

-- Add current_stage column (processing stage: queued, collecting, generating, reviewing, formatting, saving, completed)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50);

-- Comment on columns
COMMENT ON COLUMN reports.status_message IS 'Human-readable progress message displayed during report generation';
COMMENT ON COLUMN reports.current_stage IS 'Current processing stage: queued, collecting, generating, reviewing, formatting, saving, completed';
