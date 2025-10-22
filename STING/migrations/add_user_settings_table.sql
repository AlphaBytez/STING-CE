-- Migration: Add user_settings table for storing user preferences and flags
-- This table is used to store settings that don't belong in Kratos identity traits
-- to avoid schema validation issues

CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,  -- Kratos identity ID
    email VARCHAR(255) NOT NULL,
    
    -- Password management
    force_password_change BOOLEAN DEFAULT FALSE,
    password_changed_at TIMESTAMP,
    
    -- Role management
    role VARCHAR(50) DEFAULT 'user',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on user_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- Create index on email for lookups
CREATE INDEX IF NOT EXISTS idx_user_settings_email ON user_settings(email);

-- Add trigger to update updated_at timestamp (PostgreSQL)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;
CREATE TRIGGER update_user_settings_updated_at 
    BEFORE UPDATE ON user_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();