"""
Cleanup tasks for STING application
"""

import logging
from datetime import datetime, timezone
from app.models.passkey_models import (
    PasskeyRegistrationChallenge, 
    PasskeyAuthenticationChallenge
)
from app.database import db

logger = logging.getLogger(__name__)

def cleanup_expired_passkey_challenges():
    """
    Clean up expired passkey registration and authentication challenges.
    
    Returns:
        int: Number of expired challenges cleaned up
    """
    try:
        # Clean up registration challenges
        reg_count = PasskeyRegistrationChallenge.cleanup_expired()
        
        # Clean up authentication challenges  
        auth_expired = PasskeyAuthenticationChallenge.query.filter(
            PasskeyAuthenticationChallenge.expires_at < datetime.now(timezone.utc)
        ).all()
        
        auth_count = 0
        for challenge in auth_expired:
            db.session.delete(challenge)
            auth_count += 1
        
        if auth_count > 0:
            db.session.commit()
        
        total_cleaned = reg_count + auth_count
        
        if total_cleaned > 0:
            logger.info(f"Cleaned up {total_cleaned} expired passkey challenges "
                       f"({reg_count} registration, {auth_count} authentication)")
        
        return total_cleaned
        
    except Exception as e:
        logger.error(f"Error cleaning up expired passkey challenges: {str(e)}")
        db.session.rollback()
        return 0

def run_periodic_cleanup():
    """
    Run all periodic cleanup tasks.
    
    This can be called by a scheduler (e.g., celery, cron, etc.)
    """
    logger.info("Starting periodic cleanup tasks")
    
    # Clean up expired passkey challenges
    cleanup_expired_passkey_challenges()
    
    logger.info("Completed periodic cleanup tasks")

if __name__ == "__main__":
    # Allow running cleanup directly
    from app import create_app
    
    app = create_app()
    with app.app_context():
        run_periodic_cleanup()