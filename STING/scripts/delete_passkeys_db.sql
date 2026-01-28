-- Delete passkeys for admin@sting.local
-- First, find the admin identity and webauthn credential

-- Update the WebAuthn credential config to remove all passkeys
UPDATE identity_credentials 
SET config = '{}'::jsonb
WHERE identity_id = (
    SELECT id FROM identities 
    WHERE traits->>'email' = 'admin@sting.local'
)
AND identity_credential_type_id = (
    SELECT id FROM identity_credential_types 
    WHERE name = 'webauthn'
);

-- Verify the update
SELECT 
    i.traits->>'email' as email,
    ic.config
FROM identity_credentials ic
JOIN identities i ON i.id = ic.identity_id
JOIN identity_credential_types ict ON ict.id = ic.identity_credential_type_id
WHERE ict.name = 'webauthn' 
AND i.traits->>'email' = 'admin@sting.local';