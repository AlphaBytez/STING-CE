"""
Fix for Flask-Session Redis backend returning bytes instead of strings.
This is a workaround for a known issue in Flask-Session with Redis.
"""

import logging
from flask_session import RedisSessionInterface

logger = logging.getLogger(__name__)


class FixedRedisSessionInterface(RedisSessionInterface):
    """Redis session interface that properly handles bytes/string conversion."""
    
    def save_session(self, app, session, response):
        """Override save_session to ensure session_id is always a string."""
        from flask import request
        
        # Get the session ID
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        
        # CRITICAL FIX: Don't save empty/meaningless sessions for health checks
        # Check if session is effectively empty (only _permanent flag)
        session_data = dict(session)
        meaningful_keys = [k for k in session_data.keys() if k not in ['_permanent', 'csrf_token']]
        
        # Debug logging to see what's happening
        logger.info(f"Session save check: path={request.path}, remote_addr={request.remote_addr}, meaningful_keys={meaningful_keys}, modified={session.modified}")
        
        # Skip saving if:
        # 1. Session is empty or only has permanent flag
        # 2. Request is from health checks (no meaningful user data)
        # 3. Session was not explicitly modified with user data
        if (not meaningful_keys and 
            (not session.modified or 
             request.path in ['/health', '/api/health', '/system/health'] or
             request.remote_addr == '127.0.0.1')):
            logger.info(f"🚫 Skipping empty session save for {request.path} from {request.remote_addr}")
            return
        
        # Check if session should be deleted (empty and not modified)
        if not session and not session.modified:
            response.delete_cookie(
                app.config["SESSION_COOKIE_NAME"],
                domain=domain,
                path=path
            )
            return
        
        # Get or generate session ID
        if session.new or not hasattr(session, 'sid') or session.sid is None:
            session_id = self.generate_sid()
            session.sid = session_id
        else:
            session_id = session.sid
        
        # Ensure session_id is a string, not bytes
        if isinstance(session_id, bytes):
            session_id = session_id.decode('utf-8')
            session.sid = session_id
        elif session_id is None:
            session_id = self.generate_sid()
            session.sid = session_id
        
        # Save to Redis
        try:
            # Filter out None values from session data
            session_data = {}
            for key, value in dict(session).items():
                if value is not None:
                    session_data[key] = value
            
            logger.info(f"Session data to save: {session_data}")
            logger.info(f"Session ID to save: {session_id}")
            
            val = self.serializer.dumps(session_data)
            
            # Get expiration time
            expiration_time = self.get_expiration_time(app, session)
            logger.info(f"Session expiration time: {expiration_time}")
            
            # Convert expiration time to seconds
            if expiration_time is None:
                expiration_time = 86400  # Default to 24 hours
            elif hasattr(expiration_time, 'total_seconds'):
                # If it's a timedelta, convert to seconds
                expiration_time = int(expiration_time.total_seconds())
            elif isinstance(expiration_time, (int, float)):
                # If it's already a number, convert to int
                expiration_time = int(expiration_time)
            else:
                # Default fallback
                expiration_time = 86400
            
            # Save to Redis with proper key
            redis_key = self.key_prefix + session_id
            self.redis.setex(
                name=redis_key,
                time=expiration_time,
                value=val
            )
            logger.info(f"Session saved to Redis with key: {redis_key}")
            
            # Set the cookie with the string session ID
            # Get cookie configuration
            cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
            cookie_httponly = app.config.get("SESSION_COOKIE_HTTPONLY", True)
            cookie_secure = app.config.get("SESSION_COOKIE_SECURE", False)
            cookie_samesite = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
            
            # Calculate expiration
            if session.permanent:
                from datetime import datetime, timezone
                cookie_expires = datetime.now(timezone.utc) + app.permanent_session_lifetime
            else:
                cookie_expires = None
            
            response.set_cookie(
                cookie_name,
                session_id,
                expires=cookie_expires,
                httponly=cookie_httponly,
                domain=domain,
                path=path,
                secure=cookie_secure,
                samesite=cookie_samesite
            )
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            # If there's an error, still try to set a cookie
            # to avoid breaking the response
            pass


def patch_flask_session(app):
    """Patch Flask-Session to fix bytes/string issue."""
    from flask_session import FileSystemSessionInterface
    
    # Get the original save_session method
    original_interface = app.session_interface
    original_save_session = original_interface.save_session
    
    def fixed_save_session(app, session, response):
        """Wrapper that ensures session_id is always a string."""
        # Call the original method
        try:
            # Temporarily patch the session to ensure sid is a string
            if hasattr(session, 'sid') and isinstance(session.sid, bytes):
                session.sid = session.sid.decode('utf-8')
            original_save_session(app, session, response)
        except TypeError as e:
            if "cannot use a string pattern on a bytes-like object" in str(e):
                logger.warning("Caught bytes/string error in session save, attempting fix...")
                # If it's the bytes error, decode and retry
                if hasattr(session, 'sid') and isinstance(session.sid, bytes):
                    session.sid = session.sid.decode('utf-8')
                original_save_session(app, session, response)
            else:
                raise
    
    # Replace the save_session method
    original_interface.save_session = fixed_save_session
    logger.info(f"Patched Flask-Session {type(original_interface).__name__} to fix bytes/string issue")