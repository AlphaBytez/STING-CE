-- Migration 007: Support Ticket System Tables
-- Creates tables for the Bee-powered support system
-- Author: Bee AI Support System
-- Date: 2025-01-12

-- Create enum types for support ticket system
CREATE TYPE support_ticket_status AS ENUM (
    'open',
    'in_progress',
    'waiting_for_response', 
    'resolved',
    'closed',
    'cancelled'
);

CREATE TYPE support_ticket_priority AS ENUM (
    'low',
    'normal',
    'high',
    'urgent',
    'critical'
);

CREATE TYPE support_tier AS ENUM (
    'community',
    'professional',
    'enterprise'
);

CREATE TYPE issue_type AS ENUM (
    'authentication',
    'frontend',
    'api',
    'ai_chat',
    'database',
    'performance',
    'general'
);

CREATE TYPE support_session_type AS ENUM (
    'manual',
    'tailscale',
    'wireguard'
);

CREATE TYPE support_session_status AS ENUM (
    'active',
    'expired',
    'closed',
    'failed'
);

-- Support tickets table
CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_by_email VARCHAR(255) NOT NULL,
    
    -- Ticket details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    issue_type issue_type DEFAULT 'general' NOT NULL,
    
    -- Status and priority
    status support_ticket_status DEFAULT 'open' NOT NULL,
    priority support_ticket_priority DEFAULT 'normal' NOT NULL,
    support_tier support_tier DEFAULT 'community' NOT NULL,
    
    -- AI Analysis data (stored as JSONB for flexibility)
    bee_analysis JSONB,
    suggested_services JSONB,
    diagnostic_flags JSONB,
    
    -- Honey jar references
    honey_jar_refs JSONB,
    honey_jar_created BOOLEAN DEFAULT FALSE,
    
    -- Chat integration
    chat_transcript JSONB,
    bee_session_id VARCHAR(255),
    
    -- Secure access
    tailscale_session_id VARCHAR(255),
    secure_access_granted BOOLEAN DEFAULT FALSE,
    access_expires_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    
    CONSTRAINT valid_ticket_id CHECK (ticket_id ~ '^ST-[0-9]{14}-[A-Z0-9]{8}$')
);

-- Support sessions table
CREATE TABLE support_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    
    -- Session details
    session_type support_session_type NOT NULL,
    status support_session_status DEFAULT 'active' NOT NULL,
    connection_details JSONB,
    
    -- Access control
    access_granted_by INTEGER NOT NULL REFERENCES users(id),
    support_engineer_info JSONB,
    
    -- Session timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    
    -- Audit trail
    audit_log JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT valid_session_id CHECK (session_id ~ '^SS-[0-9]{12}-[A-Z0-9]{8}$'),
    CONSTRAINT valid_session_timing CHECK (expires_at > started_at)
);

-- Bee analysis results table
CREATE TABLE bee_analysis_results (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    
    -- Analysis metadata
    analysis_version VARCHAR(20) DEFAULT '1.0',
    confidence_score FLOAT CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Pattern detection
    issue_patterns JSONB,
    
    -- Service correlation
    primary_services JSONB,
    secondary_services JSONB,
    
    -- Diagnostic recommendations
    recommended_flags JSONB,
    log_sources JSONB,
    
    -- Troubleshooting suggestions
    suggested_actions JSONB,
    similar_tickets JSONB,
    
    -- Performance metrics
    analysis_duration_ms INTEGER,
    knowledge_base_version VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX idx_support_tickets_ticket_id ON support_tickets(ticket_id);
CREATE INDEX idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status);
CREATE INDEX idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX idx_support_tickets_issue_type ON support_tickets(issue_type);
CREATE INDEX idx_support_tickets_support_tier ON support_tickets(support_tier);
CREATE INDEX idx_support_tickets_created_at ON support_tickets(created_at);
CREATE INDEX idx_support_tickets_bee_session_id ON support_tickets(bee_session_id);

CREATE INDEX idx_support_sessions_session_id ON support_sessions(session_id);
CREATE INDEX idx_support_sessions_ticket_id ON support_sessions(ticket_id);
CREATE INDEX idx_support_sessions_status ON support_sessions(status);
CREATE INDEX idx_support_sessions_expires_at ON support_sessions(expires_at);
CREATE INDEX idx_support_sessions_granted_by ON support_sessions(access_granted_by);

CREATE INDEX idx_bee_analysis_ticket_id ON bee_analysis_results(ticket_id);
CREATE INDEX idx_bee_analysis_confidence ON bee_analysis_results(confidence_score);
CREATE INDEX idx_bee_analysis_created_at ON bee_analysis_results(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_support_ticket_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE FUNCTION update_support_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER trigger_support_tickets_updated_at
    BEFORE UPDATE ON support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_support_ticket_updated_at();

CREATE TRIGGER trigger_support_sessions_updated_at
    BEFORE UPDATE ON support_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_support_session_updated_at();

-- Grant permissions to application user
GRANT SELECT, INSERT, UPDATE, DELETE ON support_tickets TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON support_sessions TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON bee_analysis_results TO app_user;

-- Grant sequence permissions
GRANT USAGE, SELECT ON SEQUENCE support_tickets_id_seq TO app_user;
GRANT USAGE, SELECT ON SEQUENCE support_sessions_id_seq TO app_user;
GRANT USAGE, SELECT ON SEQUENCE bee_analysis_results_id_seq TO app_user;

-- Insert migration record
INSERT INTO schema_migrations (version, description, applied_at) 
VALUES ('007', 'Support Ticket System Tables', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;

-- Migration completed
SELECT 'Support ticket system tables created successfully' AS result;