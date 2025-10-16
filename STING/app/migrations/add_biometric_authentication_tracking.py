#!/usr/bin/env python3
"""
Migration: Add Biometric Authentication Tracking
Date: 2025-08-29
Purpose: Create tables to track biometric authentication events and credential metadata
Context: Enable proper AAL2 recognition for biometric passkeys vs regular passkeys
"""

import os
import logging
from sqlalchemy import create_engine, text
from app.utils.environment import get_database_url

logger = logging.getLogger(__name__)

def run_migration():
    """Execute the biometric authentication tracking migration"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        logger.info("🔒 Starting biometric authentication tracking migration...")
        
        # Read SQL migration file
        migration_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file = os.path.join(migration_dir, 'add_biometric_authentication_tracking.sql')
        
        with open(sql_file, 'r') as f:
            sql_statements = f.read()
        
        # Execute migration
        with engine.connect() as conn:
            # Execute as a transaction
            trans = conn.begin()
            try:
                # Split and execute each statement
                statements = [stmt.strip() for stmt in sql_statements.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        logger.info(f"Executing: {statement[:50]}...")
                        conn.execute(text(statement))
                
                trans.commit()
                logger.info("✅ Biometric authentication tracking migration completed successfully")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {e}")
                raise
                
    except Exception as e:
        logger.error(f"❌ Failed to run biometric authentication tracking migration: {e}")
        return False

def check_migration_status():
    """Check if migration has already been applied"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if biometric_authentications table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'biometric_authentications'
                );
            """))
            
            return result.scalar()
            
    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return False

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if already applied
    if check_migration_status():
        print("✅ Biometric authentication tracking migration already applied")
    else:
        # Run migration
        if run_migration():
            print("✅ Migration completed successfully")
        else:
            print("❌ Migration failed")
            exit(1)