#!/usr/bin/env python3
"""
Migration script to add new fields to report_templates table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db, init_app
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add missing columns to report_templates table"""
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/sting_app?sslmode=disable'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.init_app(app)
        
        try:
            # Check if we need to add the columns
            with db.engine.connect() as conn:
                # Check if generator_class column exists
                result = conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='report_templates' AND column_name='generator_class'
                """)
                
                if result.rowcount == 0:
                    logger.info("Adding generator_class column...")
                    conn.execute("""
                        ALTER TABLE report_templates 
                        ADD COLUMN generator_class VARCHAR(255)
                    """)
                    conn.commit()
                
                # Check if parameters column exists
                result = conn.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='report_templates' AND column_name='parameters'
                """)
                
                if result.rowcount == 0:
                    logger.info("Adding parameters column...")
                    conn.execute("""
                        ALTER TABLE report_templates 
                        ADD COLUMN parameters JSON NOT NULL DEFAULT '{}'
                    """)
                    conn.commit()
                
                # Update existing templates with default generator classes
                logger.info("Updating existing templates with default generator classes...")
                conn.execute("""
                    UPDATE report_templates 
                    SET generator_class = CASE 
                        WHEN name = 'honey_jar_summary' THEN 'HoneyJarSummaryGenerator'
                        WHEN name = 'user_activity_audit' THEN 'UserActivityAuditGenerator'
                        WHEN name = 'document_processing_report' THEN 'DocumentProcessingReportGenerator'
                        WHEN name = 'bee_chat_analytics' THEN 'BeeChatAnalyticsGenerator'
                        WHEN name = 'encryption_status_report' THEN 'EncryptionStatusReportGenerator'
                        WHEN name = 'storage_utilization_report' THEN 'StorageUtilizationReportGenerator'
                        ELSE 'BaseReportGenerator'
                    END
                    WHERE generator_class IS NULL
                """)
                conn.commit()
                
                # Update parameters for existing templates
                conn.execute("""
                    UPDATE report_templates 
                    SET parameters = CASE 
                        WHEN name = 'honey_jar_summary' THEN '[]'
                        ELSE '[]'
                    END
                    WHERE parameters IS NULL OR parameters = '{}'
                """)
                conn.commit()
                
                logger.info("Migration completed successfully!")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == '__main__':
    run_migration()