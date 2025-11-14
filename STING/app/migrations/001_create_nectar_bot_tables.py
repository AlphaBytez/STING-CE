#!/usr/bin/env python3
"""
Create nectar_bots tables

This migration creates the nectar_bots, nectar_bot_handoffs, and nectar_bot_usage tables.
Uses app_user credentials to ensure proper table ownership.

Run with: python app/migrations/create_nectar_bot_tables.py
"""

import psycopg2
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_migration():
    """Create nectar_bots tables"""

    # Get database URL from environment (uses app_user credentials)
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False

    try:
        # Connect to database as app_user
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()

        logger.info("Connected to database as app_user")

        # Check if tables already exist
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name IN ('nectar_bots', 'nectar_bot_handoffs', 'nectar_bot_usage')
            AND table_schema = 'public'
        """)
        existing_tables = [row[0] for row in cur.fetchall()]

        if len(existing_tables) == 3:
            logger.info("✅ All nectar bot tables already exist - nothing to do")
            conn.close()
            return True

        if existing_tables:
            logger.info(f"Some tables already exist: {existing_tables}")

        # Create nectar_bots table
        logger.info("Creating nectar_bots table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nectar_bots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,

                -- Organization/User ownership
                owner_id UUID NOT NULL,
                owner_email VARCHAR(255) NOT NULL,

                -- Bot configuration
                honey_jar_ids JSONB DEFAULT '[]',
                system_prompt TEXT,
                max_conversation_length INTEGER DEFAULT 20,
                confidence_threshold REAL DEFAULT 0.7,

                -- API configuration
                api_key VARCHAR(255) UNIQUE NOT NULL,
                rate_limit_per_hour INTEGER DEFAULT 100,
                rate_limit_per_day INTEGER DEFAULT 1000,

                -- Status and metadata
                status VARCHAR(20) DEFAULT 'active',
                is_public BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE,
                last_used_at TIMESTAMP WITH TIME ZONE,

                -- Handoff configuration
                handoff_enabled BOOLEAN DEFAULT TRUE,
                handoff_keywords JSONB DEFAULT '["help", "human", "support", "escalate"]',
                handoff_confidence_threshold REAL DEFAULT 0.6,

                -- Statistics (updated periodically)
                total_conversations INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_handoffs INTEGER DEFAULT 0,
                average_confidence REAL DEFAULT 0.0
            )
        """)
        logger.info("✅ nectar_bots table created")

        # Create nectar_bot_handoffs table
        logger.info("Creating nectar_bot_handoffs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nectar_bot_handoffs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bot_id UUID NOT NULL REFERENCES nectar_bots(id) ON DELETE CASCADE,

                -- Conversation context
                conversation_id UUID,
                user_id UUID,
                reason TEXT,
                context JSONB DEFAULT '{}',

                -- Handoff details
                confidence_score REAL,
                status VARCHAR(50) DEFAULT 'pending',
                urgency VARCHAR(20) DEFAULT 'medium',
                assigned_to UUID,
                assigned_at TIMESTAMP WITH TIME ZONE,
                resolved_at TIMESTAMP WITH TIME ZONE,
                resolution_notes TEXT,

                -- Metadata
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """)
        logger.info("✅ nectar_bot_handoffs table created")

        # Create nectar_bot_usage table
        logger.info("Creating nectar_bot_usage table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nectar_bot_usage (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bot_id UUID NOT NULL REFERENCES nectar_bots(id) ON DELETE CASCADE,
                conversation_id UUID,
                user_id UUID,
                message_count INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                confidence_score REAL,
                duration_seconds INTEGER,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        logger.info("✅ nectar_bot_usage table created")

        # Create indexes
        logger.info("Creating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nectar_bots_owner_id ON nectar_bots(owner_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nectar_bots_api_key ON nectar_bots(api_key)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_bot_id ON nectar_bot_handoffs(bot_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_status ON nectar_bot_handoffs(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_bot_id ON nectar_bot_usage(bot_id)")
        logger.info("✅ Indexes created")

        logger.info("🎉 Migration completed successfully!")

        cur.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
