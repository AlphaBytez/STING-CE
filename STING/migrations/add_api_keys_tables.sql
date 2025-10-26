-- Migration: Add API Keys tables
-- Description: Create tables for API key authentication system
-- Date: 2025-01-08

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    
    -- Key identification
    name VARCHAR(255) NOT NULL,
    key_id VARCHAR(64) UNIQUE NOT NULL,
    key_hash VARCHAR(128) NOT NULL,
    
    -- User association
    user_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    
    -- Key permissions and scope
    permissions JSON NOT NULL DEFAULT '{}',
    scopes JSON NOT NULL DEFAULT '[]',
    
    -- Key lifecycle
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_used_at TIMESTAMP NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Usage tracking
    usage_count INTEGER NOT NULL DEFAULT 0,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    
    -- Metadata  
    description TEXT NULL,
    key_metadata JSON NOT NULL DEFAULT '{}'
);

-- Create indexes for api_keys table
CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_email ON api_keys(user_email);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);

-- Create api_key_usage table for logging
CREATE TABLE IF NOT EXISTS api_key_usage (
    id VARCHAR(36) PRIMARY KEY,
    
    -- Key reference
    api_key_id VARCHAR(36) NOT NULL,
    key_id VARCHAR(64) NOT NULL,
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NULL,
    
    -- Request metadata
    user_agent VARCHAR(512) NULL,
    ip_address VARCHAR(45) NULL,
    request_size_bytes INTEGER NULL,
    response_size_bytes INTEGER NULL,
    
    -- Timestamps
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Error tracking
    error_message TEXT NULL,
    
    -- Foreign key constraint
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
);

-- Create indexes for api_key_usage table
CREATE INDEX IF NOT EXISTS idx_api_key_usage_api_key_id ON api_key_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_key_id ON api_key_usage(key_id);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_timestamp ON api_key_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_endpoint ON api_key_usage(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_status_code ON api_key_usage(status_code);
CREATE INDEX IF NOT EXISTS idx_api_key_usage_ip_address ON api_key_usage(ip_address);

-- Create composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_api_key_usage_key_timestamp ON api_key_usage(api_key_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_active ON api_keys(user_id, is_active);

-- Insert initial data comment
-- Note: No initial data needed - API keys are created via the API endpoints