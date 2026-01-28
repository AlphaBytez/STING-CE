-- Migration: Add PasskeyAuthenticationChallenge table for AAL2 hybrid authentication
-- Date: 2025-08-18
-- Purpose: Support custom WebAuthn AAL2 authentication alongside Kratos

-- Create the passkey_authentication_challenges table
CREATE TABLE IF NOT EXISTS passkey_authentication_challenges (
    id SERIAL PRIMARY KEY,
    
    -- Challenge data
    challenge VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    
    -- AAL level for this authentication
    aal_level VARCHAR(10) DEFAULT 'aal1' NOT NULL,
    
    -- Authentication context
    user_agent VARCHAR(500),
    ip_address VARCHAR(45),
    
    -- Store authentication options for verification (JSON)
    authentication_options JSON,
    
    -- Expiration
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Status
    used BOOLEAN DEFAULT FALSE NOT NULL,
    used_at TIMESTAMP WITHOUT TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_challenge 
    ON passkey_authentication_challenges(challenge);

CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_user_id 
    ON passkey_authentication_challenges(user_id);

CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_expires_at 
    ON passkey_authentication_challenges(expires_at);

CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_used 
    ON passkey_authentication_challenges(used);

-- Add constraint to ensure valid AAL levels
ALTER TABLE passkey_authentication_challenges 
    ADD CONSTRAINT chk_aal_level CHECK (aal_level IN ('aal1', 'aal2'));

-- Insert migration record
INSERT INTO migration_history (migration_name, applied_at, description)
VALUES (
    'add_aal2_authentication_challenges',
    NOW(),
    'Add PasskeyAuthenticationChallenge table for hybrid AAL2 WebAuthn authentication'
) ON CONFLICT (migration_name) DO NOTHING;