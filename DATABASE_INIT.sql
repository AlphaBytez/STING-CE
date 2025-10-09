-- STING CE Developer Preview Database Initialization
-- This script creates the necessary databases and users

-- Create databases
CREATE DATABASE IF NOT EXISTS sting_app;
CREATE DATABASE IF NOT EXISTS sting_messaging;
CREATE DATABASE IF NOT EXISTS kratos;

-- Create users with passwords (change these in production!)
CREATE USER IF NOT EXISTS app_user WITH PASSWORD 'app_secure_password_change_me';
CREATE USER IF NOT EXISTS kratos_user WITH PASSWORD 'kratos_secure_password_change_me';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sting_app TO app_user;
GRANT ALL PRIVILEGES ON DATABASE sting_messaging TO app_user;
GRANT ALL PRIVILEGES ON DATABASE kratos TO kratos_user;

-- Connect to sting_app and create initial schema
\c sting_app;

-- Users table (extends Kratos identity)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kratos_identity_id UUID UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Honey Reserve (encrypted storage)
CREATE TABLE IF NOT EXISTS honey_reserve (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    content_type VARCHAR(100),
    encryption_key_id VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Honey Jar (documents)
CREATE TABLE IF NOT EXISTS honey_jar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    document_type VARCHAR(50),
    file_path TEXT,
    metadata JSONB,
    vector_indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Nectar Bots (API keys)
CREATE TABLE IF NOT EXISTS nectar_bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP
);

-- Nectar Bot Usage
CREATE TABLE IF NOT EXISTS nectar_bot_usage (
    id BIGSERIAL PRIMARY KEY,
    nectar_bot_id UUID NOT NULL REFERENCES nectar_bots(id) ON DELETE CASCADE,
    endpoint VARCHAR(255),
    tokens_used INTEGER,
    response_time_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_kratos_id ON users(kratos_identity_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_honey_reserve_user ON honey_reserve(user_id);
CREATE INDEX IF NOT EXISTS idx_honey_jar_user ON honey_jar(user_id);
CREATE INDEX IF NOT EXISTS idx_nectar_bots_user ON nectar_bots(user_id);
CREATE INDEX IF NOT EXISTS idx_nectar_bots_key ON nectar_bots(api_key);
CREATE INDEX IF NOT EXISTS idx_nectar_usage_bot ON nectar_bot_usage(nectar_bot_id);
CREATE INDEX IF NOT EXISTS idx_nectar_usage_time ON nectar_bot_usage(created_at);

-- Connect to sting_messaging and create schema
\c sting_messaging;

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participants UUID[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL,
    content TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    read_by UUID[] DEFAULT ARRAY[]::UUID[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversations_participants ON conversations USING GIN(participants);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);

-- Set permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
