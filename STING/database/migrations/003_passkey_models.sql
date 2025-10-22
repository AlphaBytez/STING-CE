-- Migration: Create passkey tables for WebAuthn/FIDO2 support
-- Version: 003
-- Description: Creates tables for passkey authentication

-- Create passkey status enum
CREATE TYPE passkey_status AS ENUM ('active', 'inactive', 'suspended', 'revoked');

-- Create passkeys table
CREATE TABLE IF NOT EXISTS passkeys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credential_id VARCHAR(1024) UNIQUE NOT NULL,
    public_key BYTEA NOT NULL,
    counter INTEGER DEFAULT 0 NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(100),
    aaguid VARCHAR(36),
    status VARCHAR(20) DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    transports JSONB,
    backup_eligible BOOLEAN DEFAULT FALSE NOT NULL,
    backup_state BOOLEAN DEFAULT FALSE NOT NULL,
    metadata JSONB
);

-- Create indexes for passkeys
CREATE INDEX idx_passkeys_user_id ON passkeys(user_id);
CREATE INDEX idx_passkeys_credential_id ON passkeys(credential_id);
CREATE INDEX idx_passkeys_status ON passkeys(status);

-- Create passkey registration challenges table
CREATE TABLE IF NOT EXISTS passkey_registration_challenges (
    id SERIAL PRIMARY KEY,
    challenge_id VARCHAR(128) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge VARCHAR(1024) NOT NULL,
    user_verification VARCHAR(20) NOT NULL,
    attestation VARCHAR(20) NOT NULL,
    timeout INTEGER DEFAULT 300000 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    registration_options JSONB
);

-- Create indexes for registration challenges
CREATE INDEX idx_passkey_reg_challenges_challenge_id ON passkey_registration_challenges(challenge_id);
CREATE INDEX idx_passkey_reg_challenges_user_id ON passkey_registration_challenges(user_id);
CREATE INDEX idx_passkey_reg_challenges_expires_at ON passkey_registration_challenges(expires_at);

-- Create passkey authentication challenges table
CREATE TABLE IF NOT EXISTS passkey_authentication_challenges (
    id SERIAL PRIMARY KEY,
    challenge_id VARCHAR(128) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    challenge VARCHAR(1024) NOT NULL,
    user_verification VARCHAR(20) NOT NULL,
    timeout INTEGER DEFAULT 300000 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE NOT NULL,
    authentication_options JSONB
);

-- Create indexes for authentication challenges
CREATE INDEX idx_passkey_auth_challenges_challenge_id ON passkey_authentication_challenges(challenge_id);
CREATE INDEX idx_passkey_auth_challenges_user_id ON passkey_authentication_challenges(user_id);
CREATE INDEX idx_passkey_auth_challenges_expires_at ON passkey_authentication_challenges(expires_at);

-- Create cleanup job for expired challenges (PostgreSQL-specific)
-- This removes expired challenges older than 1 hour
CREATE OR REPLACE FUNCTION cleanup_expired_passkey_challenges()
RETURNS void AS $$
BEGIN
    DELETE FROM passkey_registration_challenges 
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
    
    DELETE FROM passkey_authentication_challenges 
    WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Note: You may want to set up a cron job or scheduled task to call:
-- SELECT cleanup_expired_passkey_challenges();
