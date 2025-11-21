#!/bin/bash
# Migration: Add Bee Conversation Schema to sting_messaging database
# This runs on existing installs to add the conversation persistence tables
# For fresh installs, this is handled by 05-bee-conversations.sql

set -e

MIGRATION_NAME="add_bee_conversations"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo "🐝 Running migration: ${MIGRATION_NAME}"

# Check if database container is running
if ! docker ps --format '{{.Names}}' | grep -q "sting-ce-db"; then
    echo "❌ Database container not running. Start STING first."
    exit 1
fi

# Check if schema already exists
SCHEMA_EXISTS=$(docker exec sting-ce-db psql -U postgres -d sting_messaging -tAc \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations');" 2>/dev/null || echo "false")

if [ "$SCHEMA_EXISTS" = "t" ]; then
    echo "✅ Conversation schema already exists, skipping migration"
    exit 0
fi

echo "📦 Creating Bee conversation schema in sting_messaging..."

# Run the schema creation
docker exec -i sting-ce-db psql -U postgres -d sting_messaging << 'EOSQL'

-- Create extensions if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    bot_id UUID DEFAULT NULL,
    title VARCHAR(255) DEFAULT NULL,
    conversation_type VARCHAR(50) DEFAULT 'bee_chat',
    status VARCHAR(20) DEFAULT 'active',
    is_pinned BOOLEAN DEFAULT FALSE,
    settings JSONB DEFAULT '{}',
    summary JSONB DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Conversation summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    topics TEXT[] DEFAULT '{}',
    key_points TEXT[] DEFAULT '{}',
    entities TEXT[] DEFAULT '{}',
    action_items TEXT[] DEFAULT '{}',
    message_count INTEGER NOT NULL,
    start_message_id UUID DEFAULT NULL,
    end_message_id UUID DEFAULT NULL,
    start_timestamp TIMESTAMPTZ,
    end_timestamp TIMESTAMPTZ,
    generated_by VARCHAR(50) DEFAULT 'fallback',
    model_used VARCHAR(100) DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_status ON conversations(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON conversations(user_id, last_message_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_bot_id ON conversations(bot_id) WHERE bot_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_time ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_role ON messages(conversation_id, role);
CREATE INDEX IF NOT EXISTS idx_summaries_conversation_id ON conversation_summaries(conversation_id);

-- Triggers
CREATE OR REPLACE FUNCTION update_conversation_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET last_message_at = NEW.created_at, updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation_on_message ON messages;
CREATE TRIGGER trigger_update_conversation_on_message
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamps();

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_conversations_updated_at ON conversations;
CREATE TRIGGER trigger_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial Bee conversation schema')
ON CONFLICT (version) DO NOTHING;

-- Permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO messaging_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO messaging_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO messaging_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;

EOSQL

if [ $? -eq 0 ]; then
    echo "✅ Migration ${MIGRATION_NAME} completed successfully"
    echo "   Tables created: conversations, messages, conversation_summaries"
else
    echo "❌ Migration failed"
    exit 1
fi
