-- Migration: Add missing columns to file_assets table for report generation
-- Date: 2025-11-07
-- Description: Adds file_type, storage_backend, access_level, and deleted_at columns
--              required for proper report file storage and management

-- Add file_type column to categorize files (e.g., 'report', 'document', 'image')
ALTER TABLE file_assets
ADD COLUMN IF NOT EXISTS file_type VARCHAR(100);

-- Add storage_backend column to track where file is stored (e.g., 'vault', 'local', 's3')
ALTER TABLE file_assets
ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(100);

-- Add access_level column for permission control (e.g., 'private', 'public', 'shared')
ALTER TABLE file_assets
ADD COLUMN IF NOT EXISTS access_level VARCHAR(50) DEFAULT 'private';

-- Add deleted_at column for soft deletes
ALTER TABLE file_assets
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Add index on file_type for efficient querying by type
CREATE INDEX IF NOT EXISTS idx_file_assets_file_type ON file_assets(file_type);

-- Add index on storage_backend for efficient querying by storage location
CREATE INDEX IF NOT EXISTS idx_file_assets_storage_backend ON file_assets(storage_backend);

-- Add index on access_level for permission filtering
CREATE INDEX IF NOT EXISTS idx_file_assets_access_level ON file_assets(access_level);

-- Add index on deleted_at for soft delete queries
CREATE INDEX IF NOT EXISTS idx_file_assets_deleted_at ON file_assets(deleted_at);

-- Add comment to document the migration
COMMENT ON COLUMN file_assets.file_type IS 'Type of file: report, document, image, etc.';
COMMENT ON COLUMN file_assets.storage_backend IS 'Storage backend: vault, local, s3, etc.';
COMMENT ON COLUMN file_assets.access_level IS 'Access level: private, public, shared';
COMMENT ON COLUMN file_assets.deleted_at IS 'Soft delete timestamp';
