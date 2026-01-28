-- Update Passkey model with new columns and constraints
-- Migration 005: Update passkey models for industry best practices

-- Add missing columns to passkeys table
ALTER TABLE passkeys 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500),
ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);

-- Rename backup columns to match model
ALTER TABLE passkeys 
RENAME COLUMN backup_eligible TO is_backup_eligible;

ALTER TABLE passkeys 
RENAME COLUMN backup_state TO is_backup_state;

-- Add trigger to update updated_at automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_passkeys_updated_at ON passkeys;
CREATE TRIGGER update_passkeys_updated_at 
    BEFORE UPDATE ON passkeys 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Update existing records to have updated_at = created_at
UPDATE passkeys SET updated_at = created_at WHERE updated_at IS NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_passkeys_user_id_status ON passkeys(user_id, status);
CREATE INDEX IF NOT EXISTS idx_passkeys_credential_id ON passkeys(credential_id);
CREATE INDEX IF NOT EXISTS idx_passkey_registration_challenges_challenge_id ON passkey_registration_challenges(challenge_id);
CREATE INDEX IF NOT EXISTS idx_passkey_registration_challenges_expires_at ON passkey_registration_challenges(expires_at);
CREATE INDEX IF NOT EXISTS idx_passkey_authentication_challenges_challenge_id ON passkey_authentication_challenges(challenge_id);
CREATE INDEX IF NOT EXISTS idx_passkey_authentication_challenges_expires_at ON passkey_authentication_challenges(expires_at);

-- Add cleanup function for expired challenges
CREATE OR REPLACE FUNCTION cleanup_expired_challenges()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired registration challenges
    DELETE FROM passkey_registration_challenges 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete expired authentication challenges
    DELETE FROM passkey_authentication_challenges 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comment on tables and important columns
COMMENT ON TABLE passkeys IS 'WebAuthn/FIDO2 passkey credentials for user authentication';
COMMENT ON COLUMN passkeys.credential_id IS 'Base64-encoded WebAuthn credential ID';
COMMENT ON COLUMN passkeys.public_key IS 'CBOR-encoded public key for credential verification';
COMMENT ON COLUMN passkeys.counter IS 'Signature counter for replay attack prevention';

COMMENT ON TABLE passkey_registration_challenges IS 'Temporary storage for WebAuthn registration challenges';
COMMENT ON TABLE passkey_authentication_challenges IS 'Temporary storage for WebAuthn authentication challenges';