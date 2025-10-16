-- Chatbot and Memory System Tables
-- This file adds tables for conversation management and memory storage

\c sting_app;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pgvector extension for embeddings (if available)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,  -- Can be UUID or external ID
    model_type VARCHAR(50) DEFAULT 'bee',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    metadata JSONB DEFAULT '{}',
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    sentiment JSONB,
    tools_used JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Memory entries for long-term storage
CREATE TABLE IF NOT EXISTS memory_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,  -- 'fact', 'preference', 'interaction', 'learned'
    content TEXT NOT NULL,
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    access_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,  -- Optional expiration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Entities extracted from conversations
CREATE TABLE IF NOT EXISTS extracted_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- 'name', 'location', 'organization', 'date', 'preference'
    entity_value TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Facts learned from conversations
CREATE TABLE IF NOT EXISTS learned_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    fact_type VARCHAR(50) NOT NULL,  -- 'user_identity', 'preference', 'relationship', 'knowledge'
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB DEFAULT '{}',
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User preferences (cross-conversation)
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    preference_type VARCHAR(50) NOT NULL,  -- 'setting', 'style', 'topic', 'feature'
    preference_key VARCHAR(255) NOT NULL,
    preference_value JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_type, preference_key)
);

-- Conversation context cache (for quick access)
CREATE TABLE IF NOT EXISTS conversation_context (
    conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
    context_data JSONB NOT NULL,
    last_summary TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id ON memory_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_entries_importance ON memory_entries(importance DESC);
CREATE INDEX IF NOT EXISTS idx_extracted_entities_conversation ON extracted_entities(conversation_id);
CREATE INDEX IF NOT EXISTS idx_extracted_entities_type_value ON extracted_entities(entity_type, entity_value);
CREATE INDEX IF NOT EXISTS idx_learned_facts_user_id ON learned_facts(user_id);
CREATE INDEX IF NOT EXISTS idx_learned_facts_type ON learned_facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- Create triggers for updated_at
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_entries_updated_at
    BEFORE UPDATE ON memory_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learned_facts_updated_at
    BEFORE UPDATE ON learned_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_context_updated_at
    BEFORE UPDATE ON conversation_context
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up old conversations
CREATE OR REPLACE FUNCTION cleanup_old_conversations(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM conversations 
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_to_keep
    AND status != 'archived';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to summarize conversation
CREATE OR REPLACE FUNCTION summarize_conversation(conv_id UUID)
RETURNS TEXT AS $$
DECLARE
    message_summary TEXT;
BEGIN
    SELECT string_agg(
        CASE 
            WHEN role = 'user' THEN 'User: ' || LEFT(content, 100)
            WHEN role = 'assistant' THEN 'Assistant: ' || LEFT(content, 100)
            ELSE role || ': ' || LEFT(content, 50)
        END, E'\n' ORDER BY timestamp
    ) INTO message_summary
    FROM messages
    WHERE conversation_id = conv_id
    LIMIT 10;
    
    RETURN message_summary;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Also grant to sting_app user if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_user WHERE usename = 'sting_app') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sting_app;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sting_app;
        GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO sting_app;
    END IF;
END $$;