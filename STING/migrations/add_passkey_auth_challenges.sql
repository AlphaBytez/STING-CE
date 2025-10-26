-- Add passkey authentication challenges table
CREATE TABLE IF NOT EXISTS passkey_authentication_challenges (
    id SERIAL PRIMARY KEY,
    challenge VARCHAR(512) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(255),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    used_at TIMESTAMP
);

-- Add index for efficient lookup
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_challenge ON passkey_authentication_challenges(challenge);
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_expires ON passkey_authentication_challenges(expires_at);
CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_used ON passkey_authentication_challenges(used);