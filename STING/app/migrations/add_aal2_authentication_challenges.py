"""
Migration: Add PasskeyAuthenticationChallenge table for AAL2 hybrid authentication
Date: 2025-08-18
Purpose: Support custom WebAuthn AAL2 authentication alongside Kratos
"""

import logging
from sqlalchemy import text
from app.database import db

logger = logging.getLogger(__name__)

def upgrade():
    """Apply the migration"""
    try:
        logger.info("🔄 Starting AAL2 authentication challenges migration...")
        
        # Create the table
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS passkey_authentication_challenges (
                id SERIAL PRIMARY KEY,
                
                -- Challenge data
                challenge VARCHAR(255) UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id) NOT NULL,
                
                -- AAL level for this authentication
                aal_level VARCHAR(10) DEFAULT 'aal1' NOT NULL,
                
                -- Authentication context
                user_agent VARCHAR(500),
                ip_address VARCHAR(45),
                
                -- Store authentication options for verification (JSON)
                authentication_options JSON,
                
                -- Expiration
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
                
                -- Status
                used BOOLEAN DEFAULT FALSE NOT NULL,
                used_at TIMESTAMP WITHOUT TIME ZONE
            )
        """))
        
        # Create indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_challenge 
                ON passkey_authentication_challenges(challenge)
        """))
        
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_user_id 
                ON passkey_authentication_challenges(user_id)
        """))
        
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_expires_at 
                ON passkey_authentication_challenges(expires_at)
        """))
        
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_passkey_auth_challenges_used 
                ON passkey_authentication_challenges(used)
        """))
        
        # Add constraint for valid AAL levels
        db.session.execute(text("""
            ALTER TABLE passkey_authentication_challenges 
                ADD CONSTRAINT IF NOT EXISTS chk_aal_level 
                CHECK (aal_level IN ('aal1', 'aal2'))
        """))
        
        # Create migration_history table if it doesn't exist
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_history (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
                description TEXT
            )
        """))
        
        # Record migration
        db.session.execute(text("""
            INSERT INTO migration_history (migration_name, applied_at, description)
            VALUES (
                'add_aal2_authentication_challenges',
                NOW(),
                'Add PasskeyAuthenticationChallenge table for hybrid AAL2 WebAuthn authentication'
            ) ON CONFLICT (migration_name) DO NOTHING
        """))
        
        db.session.commit()
        logger.info("✅ AAL2 authentication challenges migration completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.session.rollback()
        raise

def downgrade():
    """Rollback the migration"""
    try:
        logger.info("🔄 Rolling back AAL2 authentication challenges migration...")
        
        # Drop the table (this will also drop indexes and constraints)
        db.session.execute(text("DROP TABLE IF EXISTS passkey_authentication_challenges CASCADE"))
        
        # Remove migration record
        db.session.execute(text("""
            DELETE FROM migration_history 
            WHERE migration_name = 'add_aal2_authentication_challenges'
        """))
        
        db.session.commit()
        logger.info("✅ AAL2 authentication challenges migration rollback completed")
        
    except Exception as e:
        logger.error(f"❌ Migration rollback failed: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    # Allow running migration directly
    from app import create_app
    
    app = create_app()
    with app.app_context():
        upgrade()
        print("Migration completed successfully!")