#!/usr/bin/env python3
"""
Nectar Bot Database Migration
Creates tables for Nectar Bot management and handoff system

Migration: 001_create_nectar_bot_tables
Created: 2025-08-31
Description: Initial Nectar Bot tables for AI-as-a-Service platform
"""

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_connection():
    """Get database connection from environment variables"""
    try:
        # Database connection parameters
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'sting_app'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password')
        }
        
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def create_nectar_bot_tables(cursor):
    """Create all Nectar Bot related tables"""
    
    # 1. Create nectar_bots table
    logger.info("Creating nectar_bots table...")
    cursor.execute("""
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
        );
    """)
    
    # 2. Create nectar_bot_handoffs table
    logger.info("Creating nectar_bot_handoffs table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nectar_bot_handoffs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bot_id UUID NOT NULL REFERENCES nectar_bots(id) ON DELETE CASCADE,
            
            -- Conversation context
            conversation_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            user_info JSONB,
            
            -- Handoff details
            reason VARCHAR(100) NOT NULL,
            urgency VARCHAR(20) DEFAULT 'medium',
            status VARCHAR(20) DEFAULT 'pending',
            
            -- Context data
            conversation_history JSONB,
            honey_jars_used JSONB DEFAULT '[]',
            trigger_message TEXT,
            bot_response TEXT,
            confidence_score REAL,
            
            -- Resolution tracking
            assigned_to VARCHAR(255),
            resolved_at TIMESTAMP WITH TIME ZONE,
            resolution_notes TEXT,
            resolution_time_minutes INTEGER,
            
            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)
    
    # 3. Create nectar_bot_usage table
    logger.info("Creating nectar_bot_usage table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nectar_bot_usage (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bot_id UUID NOT NULL REFERENCES nectar_bots(id) ON DELETE CASCADE,
            
            -- Request details
            conversation_id VARCHAR(255) NOT NULL,
            message_id VARCHAR(255),
            user_id VARCHAR(255),
            user_ip VARCHAR(45),
            user_agent TEXT,
            
            -- Message content (optional, for analytics)
            user_message TEXT,
            bot_response TEXT,
            confidence_score REAL,
            response_time_ms INTEGER,
            
            -- Honey Jar usage
            honey_jars_queried JSONB DEFAULT '[]',
            knowledge_matches INTEGER DEFAULT 0,
            
            -- Rate limiting
            rate_limit_hit BOOLEAN DEFAULT FALSE,
            
            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    logger.info("Creating indexes for better performance...")
    
    # Create indexes for nectar_bots table
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bots_owner_id ON nectar_bots(owner_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bots_api_key ON nectar_bots(api_key);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bots_status ON nectar_bots(status);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bots_created_at ON nectar_bots(created_at);
    """)
    
    # Create indexes for nectar_bot_handoffs table
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_bot_id ON nectar_bot_handoffs(bot_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_status ON nectar_bot_handoffs(status);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_urgency ON nectar_bot_handoffs(urgency);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_conversation_id ON nectar_bot_handoffs(conversation_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_created_at ON nectar_bot_handoffs(created_at);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_assigned_to ON nectar_bot_handoffs(assigned_to);
    """)
    
    # Create indexes for nectar_bot_usage table
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_bot_id ON nectar_bot_usage(bot_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_conversation_id ON nectar_bot_usage(conversation_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_user_id ON nectar_bot_usage(user_id);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_created_at ON nectar_bot_usage(created_at);
    """)
    
    # Create composite indexes for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_handoffs_status_urgency 
        ON nectar_bot_handoffs(status, urgency, created_at);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_nectar_bot_usage_bot_created 
        ON nectar_bot_usage(bot_id, created_at);
    """)


def create_migration_tracking_table(cursor):
    """Create table to track applied migrations"""
    logger.info("Creating migration tracking table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            description TEXT
        );
    """)


def record_migration(cursor, migration_name, description):
    """Record this migration as applied"""
    cursor.execute("""
        INSERT INTO schema_migrations (migration_name, description)
        VALUES (%s, %s)
        ON CONFLICT (migration_name) DO NOTHING;
    """, (migration_name, description))


def migration_already_applied(cursor, migration_name):
    """Check if migration has already been applied"""
    cursor.execute("""
        SELECT COUNT(*) FROM schema_migrations WHERE migration_name = %s;
    """, (migration_name,))
    return cursor.fetchone()[0] > 0


def main():
    """Run the migration"""
    migration_name = "001_create_nectar_bot_tables"
    description = "Initial Nectar Bot tables for AI-as-a-Service platform"
    
    logger.info(f"Starting migration: {migration_name}")
    logger.info(f"Description: {description}")
    
    try:
        # Connect to database
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Create migration tracking table
        create_migration_tracking_table(cursor)
        
        # Check if migration already applied
        if migration_already_applied(cursor, migration_name):
            logger.info(f"Migration {migration_name} already applied, skipping...")
            return
        
        # Run the migration
        logger.info("Creating Nectar Bot tables...")
        create_nectar_bot_tables(cursor)
        
        # Record the migration
        record_migration(cursor, migration_name, description)
        
        logger.info(f"Migration {migration_name} completed successfully!")
        logger.info("Tables created:")
        logger.info("- nectar_bots")
        logger.info("- nectar_bot_handoffs")
        logger.info("- nectar_bot_usage")
        logger.info("- schema_migrations")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def rollback():
    """Rollback the migration (drop tables)"""
    logger.warning("Rolling back migration: 001_create_nectar_bot_tables")
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Drop tables in reverse order (handle foreign key constraints)
        tables = [
            'nectar_bot_usage',
            'nectar_bot_handoffs', 
            'nectar_bots'
        ]
        
        for table in tables:
            logger.info(f"Dropping table: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        
        # Remove migration record
        cursor.execute("""
            DELETE FROM schema_migrations WHERE migration_name = %s;
        """, ("001_create_nectar_bot_tables",))
        
        logger.info("Rollback completed successfully!")
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Nectar Bot Database Migration')
    parser.add_argument('--rollback', action='store_true', 
                       help='Rollback the migration (drop tables)')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback()
    else:
        main()