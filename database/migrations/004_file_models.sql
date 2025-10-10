-- Migration: Create file asset tables
-- Version: 004
-- Description: Creates tables for file asset management and permissions

-- Create storage backend enum
CREATE TYPE storage_backend AS ENUM ('local', 'vault', 's3', 'azure', 'gcs');

-- Create access level enum
CREATE TYPE access_level AS ENUM ('private', 'shared', 'public', 'organization');

-- Create permission type enum
CREATE TYPE permission_type AS ENUM ('read', 'write', 'delete', 'share', 'admin');

-- Create file_assets table
CREATE TABLE IF NOT EXISTS file_assets (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    file_hash VARCHAR(128),
    storage_backend VARCHAR(20) DEFAULT 'vault' NOT NULL,
    access_level VARCHAR(20) DEFAULT 'private' NOT NULL,
    encryption_key_id VARCHAR(255),
    is_encrypted BOOLEAN DEFAULT TRUE NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    parent_file_id INTEGER REFERENCES file_assets(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);

-- Create indexes for file_assets
CREATE INDEX idx_file_assets_owner_id ON file_assets(owner_id);
CREATE INDEX idx_file_assets_filename ON file_assets(filename);
CREATE INDEX idx_file_assets_file_hash ON file_assets(file_hash);
CREATE INDEX idx_file_assets_storage_backend ON file_assets(storage_backend);
CREATE INDEX idx_file_assets_access_level ON file_assets(access_level);
CREATE INDEX idx_file_assets_is_deleted ON file_assets(is_deleted);
CREATE INDEX idx_file_assets_parent_file_id ON file_assets(parent_file_id);

-- Create file_permissions table
CREATE TABLE IF NOT EXISTS file_permissions (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES file_assets(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_type VARCHAR(20) NOT NULL,
    granted_by INTEGER NOT NULL REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    metadata JSONB
);

-- Create indexes for file_permissions
CREATE INDEX idx_file_permissions_file_id ON file_permissions(file_id);
CREATE INDEX idx_file_permissions_user_id ON file_permissions(user_id);
CREATE INDEX idx_file_permissions_permission_type ON file_permissions(permission_type);
CREATE INDEX idx_file_permissions_expires_at ON file_permissions(expires_at);
CREATE INDEX idx_file_permissions_is_active ON file_permissions(is_active);

-- Create file_upload_sessions table
CREATE TABLE IF NOT EXISTS file_upload_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    chunk_size INTEGER DEFAULT 1048576 NOT NULL,
    total_chunks INTEGER NOT NULL,
    uploaded_chunks JSONB DEFAULT '[]'::jsonb NOT NULL,
    temporary_path VARCHAR(1024),
    is_complete BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB
);

-- Create indexes for file_upload_sessions
CREATE INDEX idx_file_upload_sessions_session_id ON file_upload_sessions(session_id);
CREATE INDEX idx_file_upload_sessions_user_id ON file_upload_sessions(user_id);
CREATE INDEX idx_file_upload_sessions_expires_at ON file_upload_sessions(expires_at);
CREATE INDEX idx_file_upload_sessions_is_complete ON file_upload_sessions(is_complete);

-- Apply update trigger to file_assets table
CREATE TRIGGER update_file_assets_updated_at BEFORE UPDATE ON file_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create cleanup function for expired upload sessions
CREATE OR REPLACE FUNCTION cleanup_expired_upload_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM file_upload_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Create cleanup function for expired file permissions
CREATE OR REPLACE FUNCTION cleanup_expired_file_permissions()
RETURNS void AS $$
BEGIN
    UPDATE file_permissions 
    SET is_active = FALSE 
    WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE;
END;
$$ LANGUAGE plpgsql;

-- Note: You may want to set up a cron job or scheduled task to call:
-- SELECT cleanup_expired_upload_sessions();
-- SELECT cleanup_expired_file_permissions();
