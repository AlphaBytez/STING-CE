-- Add conversation summaries table for Bee chatbot
-- This table stores summaries of pruned conversation segments

\c sting_app;

-- Conversation summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    message_count INTEGER NOT NULL,  -- Number of messages summarized
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,  -- Timestamp of first message in summary
    end_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,    -- Timestamp of last message in summary
    metadata JSONB DEFAULT '{}',  -- Additional metadata (topics, entities, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conversation_id ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_created_at ON conversation_summaries(created_at);

-- Add columns to conversations table for better token tracking
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS total_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS active_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS pruning_strategy VARCHAR(50) DEFAULT 'sliding_window';

-- Add token_count column to messages table
ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS token_count INTEGER DEFAULT 0;

-- Function to get total tokens for a conversation
CREATE OR REPLACE FUNCTION get_conversation_tokens(conv_id UUID)
RETURNS TABLE(total_tokens INTEGER, active_tokens INTEGER, summary_tokens INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(m.token_count), 0)::INTEGER as total_tokens,
        COALESCE(SUM(CASE WHEN m.id IN (
            SELECT id FROM messages 
            WHERE conversation_id = conv_id 
            ORDER BY timestamp DESC 
            LIMIT 50  -- Keep last 50 messages as active
        ) THEN m.token_count ELSE 0 END), 0)::INTEGER as active_tokens,
        COALESCE(SUM(s.token_count), 0)::INTEGER as summary_tokens
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    LEFT JOIN conversation_summaries s ON c.id = s.conversation_id
    WHERE c.id = conv_id
    GROUP BY c.id;
END;
$$ LANGUAGE plpgsql;

-- Function to prune old messages and create summary
CREATE OR REPLACE FUNCTION prune_conversation_messages(
    conv_id UUID,
    keep_recent INTEGER DEFAULT 10,
    max_tokens INTEGER DEFAULT 4096
)
RETURNS UUID AS $$
DECLARE
    summary_id UUID;
    pruned_messages RECORD;
    summary_text TEXT;
    pruned_count INTEGER;
    pruned_tokens INTEGER;
BEGIN
    -- Get messages to prune (older messages beyond keep_recent limit)
    WITH messages_to_prune AS (
        SELECT *
        FROM messages
        WHERE conversation_id = conv_id
        AND id NOT IN (
            SELECT id FROM messages 
            WHERE conversation_id = conv_id 
            ORDER BY timestamp DESC 
            LIMIT keep_recent
        )
        ORDER BY timestamp ASC
    )
    SELECT 
        COUNT(*) as count,
        SUM(token_count) as tokens,
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        STRING_AGG(
            CASE 
                WHEN role = 'user' THEN 'User: ' || LEFT(content, 200)
                WHEN role = 'assistant' THEN 'Assistant: ' || LEFT(content, 200)
                ELSE role || ': ' || LEFT(content, 100)
            END, E'\n' ORDER BY timestamp
        ) as summary
    INTO pruned_count, pruned_tokens, pruned_messages
    FROM messages_to_prune;
    
    -- Only create summary if there are messages to prune
    IF pruned_count > 0 THEN
        -- Create summary entry
        INSERT INTO conversation_summaries (
            conversation_id,
            summary_text,
            token_count,
            message_count,
            start_timestamp,
            end_timestamp,
            metadata
        ) VALUES (
            conv_id,
            pruned_messages.summary,
            COALESCE(pruned_tokens, 0),
            pruned_count,
            pruned_messages.start_time,
            pruned_messages.end_time,
            jsonb_build_object(
                'pruning_reason', 'token_limit',
                'max_tokens', max_tokens,
                'kept_messages', keep_recent
            )
        ) RETURNING id INTO summary_id;
        
        -- Delete the pruned messages
        DELETE FROM messages
        WHERE conversation_id = conv_id
        AND id NOT IN (
            SELECT id FROM messages 
            WHERE conversation_id = conv_id 
            ORDER BY timestamp DESC 
            LIMIT keep_recent
        );
        
        -- Update conversation token counts
        UPDATE conversations
        SET active_tokens = (
            SELECT COALESCE(SUM(token_count), 0)
            FROM messages
            WHERE conversation_id = conv_id
        )
        WHERE id = conv_id;
        
        RETURN summary_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON conversation_summaries TO postgres;
GRANT ALL PRIVILEGES ON conversation_summaries TO sting_app;