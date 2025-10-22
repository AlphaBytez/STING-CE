-- Migration to clean up custom authentication fields
-- Moving to Kratos as single source of truth

-- Remove force_password_change from user_settings
-- We'll use Kratos flows instead
ALTER TABLE user_settings 
DROP COLUMN IF EXISTS force_password_change;

-- Remove password_changed_at as Kratos tracks this
ALTER TABLE user_settings 
DROP COLUMN IF EXISTS password_changed_at;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_kratos_id ON users(kratos_id);
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- Update any admin users to ensure they have proper role
UPDATE users 
SET role = 'ADMIN' 
WHERE email = 'admin@sting.local' 
AND role != 'ADMIN';

-- Add comment explaining the new approach
COMMENT ON TABLE user_settings IS 'User preferences and settings. Authentication state is managed by Kratos.';
COMMENT ON TABLE users IS 'User records synced from Kratos. Kratos is the source of truth for authentication.';