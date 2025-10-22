-- Migration: Add Biometric Authentication Tracking
-- Purpose: Track when users authenticate with biometric-enabled devices (UV flag)
-- Date: 2025-08-29
-- Context: Separate biometric passkeys (AAL2) from regular passkeys (AAL1)

-- Create table to track biometric authentications
CREATE TABLE IF NOT EXISTS biometric_authentications (
    id SERIAL PRIMARY KEY,
    identity_id VARCHAR(255) NOT NULL,
    credential_id VARCHAR(255),
    user_verified BOOLEAN DEFAULT FALSE,
    auth_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(255),
    user_agent TEXT,
    ip_address INET,
    authenticator_type VARCHAR(50), -- 'platform' or 'cross-platform'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, identity_id) -- One biometric record per session
);

-- Index for fast lookups by identity
CREATE INDEX IF NOT EXISTS idx_biometric_auth_identity_id 
    ON biometric_authentications(identity_id);

-- Index for session-based lookups
CREATE INDEX IF NOT EXISTS idx_biometric_auth_session_id 
    ON biometric_authentications(session_id);

-- Index for time-based cleanup/analytics
CREATE INDEX IF NOT EXISTS idx_biometric_auth_time 
    ON biometric_authentications(auth_time);

-- Create table to track credential details for UI separation
CREATE TABLE IF NOT EXISTS credential_metadata (
    id SERIAL PRIMARY KEY,
    credential_id VARCHAR(255) UNIQUE NOT NULL,
    identity_id VARCHAR(255) NOT NULL,
    credential_name VARCHAR(255),
    is_biometric BOOLEAN DEFAULT FALSE,
    authenticator_type VARCHAR(50), -- 'platform', 'cross-platform'
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for credential lookups
CREATE INDEX IF NOT EXISTS idx_credential_metadata_cred_id 
    ON credential_metadata(credential_id);

-- Index for identity-based credential lists
CREATE INDEX IF NOT EXISTS idx_credential_metadata_identity_id 
    ON credential_metadata(identity_id);

-- Comments for documentation
COMMENT ON TABLE biometric_authentications IS 'Tracks when users authenticate with biometric verification (UV flag = true)';
COMMENT ON COLUMN biometric_authentications.user_verified IS 'True when WebAuthn UV flag was set (biometric verification occurred)';
COMMENT ON COLUMN biometric_authentications.authenticator_type IS 'platform = built-in (TouchID/FaceID), cross-platform = external (YubiKey)';

COMMENT ON TABLE credential_metadata IS 'Metadata about WebAuthn credentials for UI display and security logic';
COMMENT ON COLUMN credential_metadata.is_biometric IS 'True if credential supports and uses biometric verification';