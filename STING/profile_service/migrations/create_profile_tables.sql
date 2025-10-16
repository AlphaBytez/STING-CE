-- Profile Service Database Migration
-- Creates tables for user profiles, extensions, and activity tracking

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User profiles table (extends Kratos identity)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE,
    display_name VARCHAR(100),
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    bio TEXT,
    location VARCHAR(100),
    website VARCHAR(255),
    phone VARCHAR(20),
    profile_picture_file_id UUID,
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    preferences JSONB DEFAULT '{}',
    privacy_settings JSONB DEFAULT '{}',
    profile_completion VARCHAR(20) DEFAULT 'incomplete',
    last_activity TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    
    CONSTRAINT profile_completion_check CHECK (profile_completion IN ('incomplete', 'partial', 'complete'))
);

-- Profile extensions table for custom fields
CREATE TABLE IF NOT EXISTS profile_extensions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    extension_type VARCHAR(50) NOT NULL,
    extension_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    sort_order VARCHAR(10) DEFAULT '0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Profile activity tracking table
CREATE TABLE IF NOT EXISTS profile_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_display_name ON user_profiles(display_name);
CREATE INDEX IF NOT EXISTS idx_user_profiles_active ON user_profiles(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_user_profiles_completion ON user_profiles(profile_completion);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created ON user_profiles(created_at DESC);

-- Profile extensions indexes
CREATE INDEX IF NOT EXISTS idx_profile_extensions_profile ON profile_extensions(profile_id, extension_type);
CREATE INDEX IF NOT EXISTS idx_profile_extensions_type ON profile_extensions(extension_type);
CREATE INDEX IF NOT EXISTS idx_profile_extensions_public ON profile_extensions(is_public);

-- Profile activities indexes
CREATE INDEX IF NOT EXISTS idx_profile_activities_profile ON profile_activities(profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_profile_activities_type ON profile_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_profile_activities_created ON profile_activities(created_at DESC);

-- GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_user_profiles_preferences ON user_profiles USING GIN (preferences);
CREATE INDEX IF NOT EXISTS idx_user_profiles_privacy ON user_profiles USING GIN (privacy_settings);
CREATE INDEX IF NOT EXISTS idx_profile_extensions_data ON profile_extensions USING GIN (extension_data);
CREATE INDEX IF NOT EXISTS idx_profile_activities_data ON profile_activities USING GIN (activity_data);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_profile_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_profile_updated_at_column();

CREATE TRIGGER update_profile_extensions_updated_at 
    BEFORE UPDATE ON profile_extensions 
    FOR EACH ROW EXECUTE FUNCTION update_profile_updated_at_column();

-- Function to automatically calculate profile completion
CREATE OR REPLACE FUNCTION calculate_profile_completion()
RETURNS TRIGGER AS $$
DECLARE
    score INTEGER := 0;
    total_fields INTEGER := 8;
    completion_status VARCHAR(20);
BEGIN
    -- Check required/important fields
    IF NEW.display_name IS NOT NULL AND NEW.display_name != '' THEN score := score + 1; END IF;
    IF NEW.first_name IS NOT NULL AND NEW.first_name != '' THEN score := score + 1; END IF;
    IF NEW.last_name IS NOT NULL AND NEW.last_name != '' THEN score := score + 1; END IF;
    IF NEW.bio IS NOT NULL AND NEW.bio != '' THEN score := score + 1; END IF;
    IF NEW.location IS NOT NULL AND NEW.location != '' THEN score := score + 1; END IF;
    IF NEW.profile_picture_file_id IS NOT NULL THEN score := score + 1; END IF;
    IF NEW.timezone IS NOT NULL AND NEW.timezone != 'UTC' THEN score := score + 1; END IF;
    IF NEW.preferences IS NOT NULL AND NEW.preferences != '{}' THEN score := score + 1; END IF;
    
    -- Calculate completion status
    IF score >= 7 THEN
        completion_status := 'complete';
    ELSIF score >= 4 THEN
        completion_status := 'partial';
    ELSE
        completion_status := 'incomplete';
    END IF;
    
    NEW.profile_completion := completion_status;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for automatic profile completion calculation
CREATE TRIGGER calculate_user_profile_completion 
    BEFORE INSERT OR UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION calculate_profile_completion();

-- Sample data for testing (optional)
-- INSERT INTO user_profiles (user_id, display_name, first_name, last_name)
-- VALUES (uuid_generate_v4(), 'Test User', 'Test', 'User');

COMMENT ON TABLE user_profiles IS 'Extended user profile data that complements Kratos identity';
COMMENT ON TABLE profile_extensions IS 'Custom profile fields and extensions';
COMMENT ON TABLE profile_activities IS 'Profile activity and change tracking';

COMMENT ON COLUMN user_profiles.user_id IS 'Links to Kratos identity ID';
COMMENT ON COLUMN user_profiles.profile_picture_file_id IS 'Links to file_assets table for profile picture';
COMMENT ON COLUMN user_profiles.profile_completion IS 'Automatically calculated completion status';
COMMENT ON COLUMN user_profiles.preferences IS 'User preferences as JSON';
COMMENT ON COLUMN user_profiles.privacy_settings IS 'Privacy settings as JSON';

COMMENT ON COLUMN profile_extensions.extension_type IS 'Type of extension: social_links, skills, certifications, etc.';
COMMENT ON COLUMN profile_extensions.extension_data IS 'Extension data as JSON';
COMMENT ON COLUMN profile_extensions.is_public IS 'Whether this extension is publicly visible';

COMMENT ON COLUMN profile_activities.activity_type IS 'Type of activity: profile_updated, picture_changed, etc.';
COMMENT ON COLUMN profile_activities.activity_data IS 'Activity details as JSON';
COMMENT ON COLUMN profile_activities.ip_address IS 'IP address of the user (supports IPv6)';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sting_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sting_app;