#!/bin/bash
# Migration: Add PII Admin Flagging columns to pii_detection_records table
# This allows admins to flag, review, and take action on PII detections

set -e

MIGRATION_NAME="add_pii_admin_flagging"
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"

echo "🔒 Running migration: ${MIGRATION_NAME}"

# Check if database container is running
if ! docker ps --format '{{.Names}}' | grep -q "sting-ce-db"; then
    echo "❌ Database container not running. Start STING first."
    exit 1
fi

# Check if columns already exist
COLUMN_EXISTS=$(docker exec sting-ce-db psql -U postgres -d sting_app -tAc \
    "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'pii_detection_records' AND column_name = 'flagged_for_review');" 2>/dev/null || echo "false")

if [ "$COLUMN_EXISTS" = "t" ]; then
    echo "✅ PII admin flagging columns already exist, skipping migration"
    exit 0
fi

echo "📦 Adding PII admin flagging columns to pii_detection_records..."

# Run the schema migration
docker exec -i sting-ce-db psql -U postgres -d sting_app << 'EOSQL'

-- Add admin flagging columns to pii_detection_records table
ALTER TABLE pii_detection_records
    ADD COLUMN IF NOT EXISTS flagged_for_review BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS flagged_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS flagged_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS flag_reason TEXT,
    ADD COLUMN IF NOT EXISTS admin_notes TEXT,
    ADD COLUMN IF NOT EXISTS severity_override VARCHAR(20),
    ADD COLUMN IF NOT EXISTS action_required VARCHAR(50),
    ADD COLUMN IF NOT EXISTS review_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100),
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_pii_flagged ON pii_detection_records(flagged_for_review, review_status);
CREATE INDEX IF NOT EXISTS idx_pii_action_required ON pii_detection_records(action_required);

-- Add comments for documentation
COMMENT ON COLUMN pii_detection_records.flagged_for_review IS 'Whether this detection has been flagged by admin or system for review';
COMMENT ON COLUMN pii_detection_records.flagged_by IS 'User ID of admin who flagged this detection';
COMMENT ON COLUMN pii_detection_records.flagged_at IS 'Timestamp when detection was flagged';
COMMENT ON COLUMN pii_detection_records.flag_reason IS 'Reason provided for flagging this detection';
COMMENT ON COLUMN pii_detection_records.admin_notes IS 'Admin notes and comments about this detection';
COMMENT ON COLUMN pii_detection_records.severity_override IS 'Admin can override the auto-detected risk level (high, medium, low)';
COMMENT ON COLUMN pii_detection_records.action_required IS 'Action required: none, investigate, delete, escalate, redact';
COMMENT ON COLUMN pii_detection_records.review_status IS 'Review status: pending, in_review, resolved, dismissed';
COMMENT ON COLUMN pii_detection_records.reviewed_by IS 'User ID of admin who resolved/reviewed this detection';
COMMENT ON COLUMN pii_detection_records.reviewed_at IS 'Timestamp when detection was resolved/reviewed';

EOSQL

if [ $? -eq 0 ]; then
    echo "✅ Migration ${MIGRATION_NAME} completed successfully"
    echo "   Added columns: flagged_for_review, flagged_by, flagged_at, flag_reason,"
    echo "                  admin_notes, severity_override, action_required,"
    echo "                  review_status, reviewed_by, reviewed_at"
else
    echo "❌ Migration failed"
    exit 1
fi
