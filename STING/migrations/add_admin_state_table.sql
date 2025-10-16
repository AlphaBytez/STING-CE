-- Add admin_state table for persistent admin tracking
-- This prevents admin corruption during container rebuilds

CREATE TABLE IF NOT EXISTS admin_state (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'default_admin',
    kratos_identity_id VARCHAR(100),
    initialized_at TIMESTAMP,
    password_changed_at TIMESTAMP,
    initial_password_changed BOOLEAN DEFAULT FALSE,
    recovery_info TEXT,  -- JSON for recovery data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default record if not exists
INSERT INTO admin_state (id, created_at, updated_at)
SELECT 'default_admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM admin_state WHERE id = 'default_admin');

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_admin_state_kratos_id ON admin_state(kratos_identity_id);