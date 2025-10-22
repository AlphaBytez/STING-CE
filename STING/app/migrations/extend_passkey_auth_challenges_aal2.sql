-- Migration: Extend PasskeyAuthenticationChallenge table for AAL2 support
-- Date: 2025-08-18
-- Purpose: Add AAL level and authentication options to existing table

-- Add AAL level column
ALTER TABLE passkey_authentication_challenges 
ADD COLUMN IF NOT EXISTS aal_level VARCHAR(10) DEFAULT 'aal1' NOT NULL;

-- Add authentication options column for storing challenge details
ALTER TABLE passkey_authentication_challenges 
ADD COLUMN IF NOT EXISTS authentication_options JSON;

-- Add constraint to ensure valid AAL levels
ALTER TABLE passkey_authentication_challenges 
ADD CONSTRAINT IF NOT EXISTS chk_aal_level_valid 
CHECK (aal_level IN ('aal1', 'aal2'));

-- Create index on aal_level for better query performance
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_aal_level 
    ON passkey_authentication_challenges(aal_level);

-- Insert migration record
INSERT INTO migration_history (migration_name, applied_at, description)
VALUES (
    'extend_passkey_auth_challenges_aal2',
    NOW(),
    'Extend PasskeyAuthenticationChallenge table with AAL2 support fields'
) ON CONFLICT (migration_name) DO NOTHING;