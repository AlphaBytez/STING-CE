-- File Asset Management Tables Migration
-- Creates tables for file metadata, permissions, and upload sessions

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- File assets table
CREATE TABLE IF NOT EXISTS file_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64),
    storage_backend VARCHAR(20) NOT NULL DEFAULT 'vault',
    storage_path TEXT NOT NULL,
    owner_id UUID NOT NULL,
    access_level VARCHAR(20) NOT NULL DEFAULT 'private',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    
    CONSTRAINT file_storage_backend_check CHECK (storage_backend IN ('vault', 'minio', 'filesystem')),
    CONSTRAINT file_access_level_check CHECK (access_level IN ('public', 'private', 'restricted'))
);

-- File permissions table
CREATE TABLE IF NOT EXISTS file_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID NOT NULL REFERENCES file_assets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    granted_by UUID NOT NULL,
    permission_type VARCHAR(20) NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    
    CONSTRAINT file_permission_type_check CHECK (permission_type IN ('read', 'write', 'delete', 'share'))
);

-- File upload sessions table (for large file uploads)
CREATE TABLE IF NOT EXISTS file_upload_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    total_size BIGINT NOT NULL,
    uploaded_size BIGINT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    chunk_count INTEGER DEFAULT 0,
    temp_storage_path TEXT,
    final_file_id UUID REFERENCES file_assets(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    CONSTRAINT upload_status_check CHECK (status IN ('pending', 'uploading', 'completed', 'failed', 'expired'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_file_assets_owner_type ON file_assets(owner_id, file_type);
CREATE INDEX IF NOT EXISTS idx_file_assets_created ON file_assets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_assets_storage ON file_assets(storage_backend, storage_path);
CREATE INDEX IF NOT EXISTS idx_file_assets_active ON file_assets(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_file_assets_filename ON file_assets(filename);
CREATE INDEX IF NOT EXISTS idx_file_assets_hash ON file_assets(content_hash);

-- File permissions indexes
CREATE INDEX IF NOT EXISTS idx_file_permissions_file_user ON file_permissions(file_id, user_id);
CREATE INDEX IF NOT EXISTS idx_file_permissions_user_type ON file_permissions(user_id, permission_type);
CREATE INDEX IF NOT EXISTS idx_file_permissions_active ON file_permissions(revoked_at) WHERE revoked_at IS NULL;

-- Upload sessions indexes
CREATE INDEX IF NOT EXISTS idx_upload_sessions_user ON file_upload_sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_upload_sessions_expires ON file_upload_sessions(expires_at);

-- GIN indexes for JSONB metadata
CREATE INDEX IF NOT EXISTS idx_file_assets_metadata ON file_assets USING GIN (metadata);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_file_assets_updated_at 
    BEFORE UPDATE ON file_assets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_upload_sessions_updated_at 
    BEFORE UPDATE ON file_upload_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing (optional)
-- INSERT INTO file_assets (filename, original_filename, file_type, file_size, storage_backend, storage_path, owner_id)
-- VALUES ('test.jpg', 'test.jpg', 'profile_picture', 1024, 'vault', 'files/test-user/profile_picture/abc123', uuid_generate_v4());

COMMENT ON TABLE file_assets IS 'Stores metadata for all files in the system';
COMMENT ON TABLE file_permissions IS 'Manages file access permissions between users';
COMMENT ON TABLE file_upload_sessions IS 'Tracks large file upload sessions';

COMMENT ON COLUMN file_assets.storage_backend IS 'Backend storage system: vault, minio, or filesystem';
COMMENT ON COLUMN file_assets.storage_path IS 'Path or identifier in the storage backend';
COMMENT ON COLUMN file_assets.access_level IS 'File access level: public, private, or restricted';
COMMENT ON COLUMN file_assets.content_hash IS 'SHA-256 hash of file content for integrity checking';

COMMENT ON COLUMN file_permissions.permission_type IS 'Type of permission: read, write, delete, or share';
COMMENT ON COLUMN file_permissions.expires_at IS 'Optional expiration time for the permission';
COMMENT ON COLUMN file_permissions.revoked_at IS 'Timestamp when permission was revoked';

COMMENT ON COLUMN file_upload_sessions.status IS 'Upload status: pending, uploading, completed, failed, or expired';
COMMENT ON COLUMN file_upload_sessions.expires_at IS 'When the upload session expires';