-- Migration 006: User Preferences
-- Adds user preference columns to support database-backed UI settings
-- including navigation configuration, theme preferences, and general UI settings

-- Add preference columns to user_settings table
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS navigation_config JSONB DEFAULT NULL;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS navigation_version INTEGER DEFAULT 4;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS theme_preferences JSONB DEFAULT NULL;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS ui_preferences JSONB DEFAULT NULL;

-- Add index for efficient preference queries
CREATE INDEX IF NOT EXISTS idx_user_settings_navigation_version ON user_settings(navigation_version);
CREATE INDEX IF NOT EXISTS idx_user_settings_navigation_config ON user_settings USING gin(navigation_config);

-- Create organization_preferences table for admin-controlled defaults
CREATE TABLE IF NOT EXISTS organization_preferences (
    id SERIAL PRIMARY KEY,
    preference_type VARCHAR(50) NOT NULL, -- 'navigation', 'theme', 'ui'
    config JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 4,
    created_by VARCHAR(255) NOT NULL, -- user_id who created
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(preference_type)
);

-- Create index for organization preferences
CREATE INDEX IF NOT EXISTS idx_org_preferences_type ON organization_preferences(preference_type);
CREATE INDEX IF NOT EXISTS idx_org_preferences_active ON organization_preferences(is_active);

-- Create user_preference_history table for audit trail
CREATE TABLE IF NOT EXISTS user_preference_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    preference_type VARCHAR(50) NOT NULL, -- 'navigation', 'theme', 'ui'
    old_config JSONB,
    new_config JSONB,
    old_version INTEGER,
    new_version INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(255), -- for admin-initiated changes
    change_reason VARCHAR(255) -- 'user_update', 'admin_push', 'migration', etc.
);

-- Create indexes for preference history
CREATE INDEX IF NOT EXISTS idx_user_pref_history_user_id ON user_preference_history(user_id);
CREATE INDEX IF NOT EXISTS idx_user_pref_history_type ON user_preference_history(preference_type);
CREATE INDEX IF NOT EXISTS idx_user_pref_history_date ON user_preference_history(changed_at);

-- Insert default organization preferences
INSERT INTO organization_preferences (preference_type, config, version, created_by) 
VALUES (
    'navigation',
    '{
        "version": 4,
        "persistent": [
            {"id": "dashboard", "name": "Dashboard", "icon": "DashboardOutlined", "path": "/dashboard", "enabled": true},
            {"id": "chat", "name": "Bee Chat", "icon": "MessageOutlined", "path": "/dashboard/chat", "enabled": true},
            {"id": "basket", "name": "Basket", "icon": "BasketOutlined", "path": "/dashboard/basket", "enabled": true}
        ],
        "scrollable": [
            {"id": "search", "name": "Search", "icon": "SearchOutlined", "path": "/dashboard/search", "enabled": true},
            {"id": "reports", "name": "Bee Reports", "icon": "FileTextOutlined", "path": "/dashboard/reports", "enabled": true},
            {"id": "report-templates", "name": "Templates", "icon": "FileTextOutlined", "path": "/dashboard/report-templates", "enabled": true},
            {"id": "honey-jars", "name": "Honey Jars", "icon": "AppstoreOutlined", "path": "/dashboard/honey-jars", "enabled": true},
            {"id": "hive-manager", "name": "Manager", "icon": "SettingOutlined", "path": "/dashboard/hive-manager", "enabled": true},
            {"id": "swarm", "name": "Swarm", "icon": "GlobalOutlined", "path": "/dashboard/swarm", "enabled": true, "badge": "Enterprise"},
            {"id": "marketplace", "name": "Marketplace", "icon": "ShoppingOutlined", "path": "/dashboard/marketplace", "enabled": true},
            {"id": "admin", "name": "Admin", "icon": "TeamOutlined", "path": "/dashboard/admin", "enabled": true, "adminOnly": true},
            {"id": "beeacon", "name": "Beeacon", "icon": "BarChartOutlined", "path": "/dashboard/beeacon", "enabled": true},
            {"id": "settings", "name": "Settings", "icon": "SettingOutlined", "path": "/dashboard/settings", "enabled": true}
        ]
    }'::jsonb,
    4,
    'system'
) ON CONFLICT (preference_type) DO NOTHING;

-- Insert default theme preferences
INSERT INTO organization_preferences (preference_type, config, version, created_by)
VALUES (
    'theme',
    '{
        "theme": "modern-glass",
        "darkMode": true,
        "compactMode": false,
        "animations": true
    }'::jsonb,
    1,
    'system'
) ON CONFLICT (preference_type) DO NOTHING;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_organization_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER organization_preferences_updated_at
    BEFORE UPDATE ON organization_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_organization_preferences_updated_at();

-- Comments for documentation
COMMENT ON TABLE organization_preferences IS 'Organization-wide default preferences that can be pushed to users';
COMMENT ON TABLE user_preference_history IS 'Audit trail for user preference changes';
COMMENT ON COLUMN user_settings.navigation_config IS 'User-specific navigation configuration (JSONB)';
COMMENT ON COLUMN user_settings.navigation_version IS 'Navigation configuration version for automatic updates';
COMMENT ON COLUMN user_settings.theme_preferences IS 'User-specific theme settings (JSONB)';
COMMENT ON COLUMN user_settings.ui_preferences IS 'General UI preferences like compact mode, animations etc. (JSONB)';

-- Grant permissions (adjust based on your user setup)
-- GRANT SELECT, INSERT, UPDATE ON organization_preferences TO app_user;
-- GRANT SELECT, INSERT ON user_preference_history TO app_user;
-- GRANT SELECT, UPDATE ON user_settings TO app_user;