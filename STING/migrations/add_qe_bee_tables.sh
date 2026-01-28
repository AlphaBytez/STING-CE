#!/bin/bash
# Migration: Add QE Bee (Quality Engineering Bee) tables
# Creates review_queue, review_history, and webhook_configs tables

set -e

MIGRATION_NAME="add_qe_bee_tables"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo "🐝 Running migration: ${MIGRATION_NAME}"

# Check if database container is running
if ! docker ps --format '{{.Names}}' | grep -q "sting-ce-db"; then
    echo "❌ Database container not running. Start STING first."
    exit 1
fi

# Check if tables already exist
TABLE_EXISTS=$(docker exec sting-ce-db psql -U postgres -d sting_app -tAc \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'review_queue');" 2>/dev/null || echo "false")

if [ "$TABLE_EXISTS" = "t" ]; then
    echo "✅ QE Bee tables already exist, skipping migration"
    exit 0
fi

echo "📦 Creating QE Bee tables..."

# Run the schema migration
docker exec -i sting-ce-db psql -U postgres -d sting_app << 'EOSQL'

-- Create enum types for review system
DO $$ BEGIN
    CREATE TYPE review_target_type AS ENUM ('report', 'message', 'document', 'pii_detection');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE review_type AS ENUM ('output_validation', 'pii_check', 'quality_check', 'format_validation', 'compliance_check');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE review_status AS ENUM ('pending', 'reviewing', 'passed', 'failed', 'escalated', 'skipped');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE review_result_code AS ENUM (
        'PASS', 'PASS_WITH_WARNINGS',
        'PII_TOKENS_REMAINING', 'PII_DESERIALIZATION_INCOMPLETE',
        'OUTPUT_TRUNCATED', 'OUTPUT_EMPTY', 'OUTPUT_MALFORMED', 'GENERATION_ERROR',
        'QUALITY_LOW', 'CONTENT_INCOHERENT', 'OFF_TOPIC',
        'FORMAT_INVALID', 'MISSING_SECTIONS',
        'REVIEW_TIMEOUT', 'REVIEW_ERROR', 'SKIPPED_BY_CONFIG'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Review Queue table
CREATE TABLE IF NOT EXISTS review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Target identification
    target_type review_target_type NOT NULL,
    target_id VARCHAR(100) NOT NULL,

    -- Review configuration
    review_type review_type NOT NULL DEFAULT 'output_validation',
    priority INTEGER DEFAULT 5,

    -- Status tracking
    status review_status NOT NULL DEFAULT 'pending',

    -- Results
    result_code review_result_code,
    result_message TEXT,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    review_details JSONB,

    -- Webhook tracking
    webhook_url VARCHAR(500),
    webhook_sent BOOLEAN DEFAULT FALSE,
    webhook_sent_at TIMESTAMPTZ,
    webhook_response_code INTEGER,

    -- Processing metadata
    worker_id VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- User context
    user_id VARCHAR(100)
);

-- Review History table (for analytics and audit)
CREATE TABLE IF NOT EXISTS review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to original queue item
    queue_id UUID,

    -- Target identification
    target_type review_target_type NOT NULL,
    target_id VARCHAR(100) NOT NULL,

    -- Review details
    review_type review_type NOT NULL,
    result_code review_result_code NOT NULL,
    result_message TEXT,
    confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    review_details JSONB,

    -- Processing metadata
    worker_id VARCHAR(100),
    model_used VARCHAR(100),
    processing_time_ms INTEGER,

    -- Context
    user_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Webhook Configs table
CREATE TABLE IF NOT EXISTS webhook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Owner
    user_id VARCHAR(100) NOT NULL,

    -- Configuration
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(255),

    -- Event filters
    event_types JSONB,
    target_types JSONB,
    result_codes JSONB,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,

    -- Statistics
    total_sent INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    last_sent_at TIMESTAMPTZ,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_review_queue_status_priority ON review_queue(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_review_queue_target ON review_queue(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_user ON review_queue(user_id, status);

-- Create indexes for history analytics
CREATE INDEX IF NOT EXISTS idx_review_history_result ON review_history(result_code, created_at);
CREATE INDEX IF NOT EXISTS idx_review_history_target ON review_history(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_review_history_user ON review_history(user_id, created_at);

-- Create indexes for webhook configs
CREATE INDEX IF NOT EXISTS idx_webhook_user_active ON webhook_configs(user_id, is_active);

-- Add comments for documentation
COMMENT ON TABLE review_queue IS 'QE Bee review queue - items awaiting quality review';
COMMENT ON TABLE review_history IS 'QE Bee review history - audit trail of all reviews performed';
COMMENT ON TABLE webhook_configs IS 'User webhook configurations for QE Bee notifications';

COMMENT ON COLUMN review_queue.confidence_score IS 'Review confidence 0-100, higher = more certain';
COMMENT ON COLUMN review_queue.priority IS 'Queue priority 1=highest, 10=lowest';
COMMENT ON COLUMN review_history.processing_time_ms IS 'Time taken to complete review in milliseconds';

EOSQL

if [ $? -eq 0 ]; then
    echo "✅ Migration ${MIGRATION_NAME} completed successfully"
    echo "   Created tables: review_queue, review_history, webhook_configs"
    echo "   Created enums: review_target_type, review_type, review_status, review_result_code"
else
    echo "❌ Migration failed"
    exit 1
fi
