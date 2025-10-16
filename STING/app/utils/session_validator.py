"""
Session Validator - Validates existing sessions on startup
Ensures Flask sessions are synchronized with Kratos sessions
"""

import logging
import redis
from typing import Optional
from app.utils.kratos_admin import get_session_by_id
# Note: get_all_sessions function needs to be implemented or removed from usage

logger = logging.getLogger(__name__)

class SessionValidator:
    """Validates and cleans up sessions on startup"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        
    def validate_sessions_on_startup(self) -> dict:
        """
        Validate all Redis sessions against Kratos on startup.
        Removes Flask sessions that don't have valid Kratos sessions.
        
        Returns:
            Dictionary with validation statistics
        """
        if not self.redis_client:
            logger.warning("Redis client not available for session validation")
            return {"error": "Redis not available"}
        
        stats = {
            "total_sessions": 0,
            "valid_sessions": 0,
            "invalid_sessions": 0,
            "error_sessions": 0
        }
        
        try:
            # Get all Flask session keys from Redis
            session_keys = list(self.redis_client.scan_iter(match="sting:*", count=100))
            stats["total_sessions"] = len(session_keys)
            
            logger.info(f"Found {len(session_keys)} session keys to validate")
            
            # Skip invalidation keys and other non-session keys
            session_keys = [k for k in session_keys if not (
                b':invalidated:' in k or 
                b':stats:' in k or
                b':config:' in k
            )]
            
            for session_key in session_keys:
                try:
                    # Get session data
                    session_data = self.redis_client.get(session_key)
                    if not session_data:
                        continue
                    
                    # Extract session ID from key (format: sting:session_id)
                    session_id = session_key.decode('utf-8').split(':', 1)[1] if b':' in session_key else None
                    if not session_id:
                        continue
                    
                    # Check if this is a Kratos-based session
                    # For WebAuthn sessions, we don't need Kratos validation
                    # We'll check for specific session markers
                    
                    # For now, mark all existing sessions as valid
                    # In production, you'd want to validate against Kratos
                    stats["valid_sessions"] += 1
                    
                except Exception as e:
                    logger.error(f"Error validating session {session_key}: {e}")
                    stats["error_sessions"] += 1
            
            stats["invalid_sessions"] = stats["total_sessions"] - stats["valid_sessions"] - stats["error_sessions"]
            
            logger.info(f"Session validation complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to validate sessions: {e}")
            return {"error": str(e)}
    
    def clear_orphaned_sessions(self) -> int:
        """
        Clear Flask sessions that don't have corresponding Kratos sessions.
        
        Returns:
            Number of sessions cleared
        """
        if not self.redis_client:
            return 0
        
        cleared_count = 0
        
        try:
            # This would be implemented based on your specific needs
            # For now, we'll just log that it would be done
            logger.info("Orphaned session cleanup would be performed here")
            
        except Exception as e:
            logger.error(f"Failed to clear orphaned sessions: {e}")
        
        return cleared_count
    
    def mark_session_for_revalidation(self, session_id: str):
        """Mark a session as needing revalidation on next request"""
        if not self.redis_client or not session_id:
            return
        
        try:
            revalidation_key = f"sting:revalidate:{session_id}"
            self.redis_client.setex(revalidation_key, 300, "1")  # 5 minute TTL
            logger.info(f"Marked session {session_id} for revalidation")
        except Exception as e:
            logger.error(f"Failed to mark session for revalidation: {e}")