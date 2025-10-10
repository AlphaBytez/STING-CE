"""
Hybrid Session Manager - Unified session management for Kratos + Custom WebAuthn AAL2

This manager handles:
1. Kratos sessions (primary) - via cookies and Redis
2. Custom AAL2 markers - for biometric WebAuthn
3. Session synchronization - between Kratos and Flask
4. AAL level tracking - unified AAL1/AAL2 status

Session Architecture:
- Kratos: Handles primary authentication and AAL1 sessions
- Redis: Stores Flask session data and custom AAL2 markers  
- Custom: Tracks biometric AAL2 authentication status
"""

import logging
import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from flask import session, request, current_app, g
from app.utils.kratos_session import whoami, check_recent_aal2_authentication

logger = logging.getLogger(__name__)

class HybridSessionManager:
    """Manages sessions across Kratos and custom WebAuthn with Redis persistence"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or self._get_redis_client()
        self.session_prefix = "sting:hybrid:"
        self.aal2_prefix = "sting:aal2:"
        
    def _get_redis_client(self):
        """Get Redis client from Flask app config"""
        try:
            if hasattr(current_app, 'config') and 'SESSION_REDIS' in current_app.config:
                return current_app.config['SESSION_REDIS']
            else:
                # Fallback to default Redis connection
                return redis.from_url('redis://redis:6379/0')
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            return None
    
    def get_session_status(self) -> Dict[str, Any]:
        """
        Get comprehensive session status including Kratos and custom AAL2
        
        Returns:
            Dict with session details, AAL levels, and authentication methods
        """
        try:
            # 1. Get Kratos session data
            kratos_session = self._get_kratos_session()
            
            if not kratos_session:
                return {
                    'authenticated': False,
                    'kratos_session': None,
                    'effective_aal': 'aal1',
                    'custom_aal2': False,
                    'error': 'No Kratos session found'
                }
            
            # 2. Extract basic session info
            identity = kratos_session.get('identity', {})
            identity_id = identity.get('id')
            user_email = identity.get('traits', {}).get('email')
            base_aal = kratos_session.get('authenticator_assurance_level', 'aal1')
            
            logger.info(f"🔐 Session check for {user_email}: Kratos AAL={base_aal}")
            
            # 3. Check for custom AAL2 status
            custom_aal2_status = self._get_custom_aal2_status(identity_id)
            
            # 4. Check recent AAL2 authentication from Kratos
            recent_aal2_check = check_recent_aal2_authentication(kratos_session)
            
            # 5. Determine effective AAL level
            effective_aal = self._determine_effective_aal(
                base_aal, 
                custom_aal2_status, 
                recent_aal2_check
            )
            
            # 6. Get configured authentication methods
            configured_methods = self._get_configured_methods(kratos_session)
            
            # 7. Build comprehensive status
            status = {
                'authenticated': True,
                'identity_id': identity_id,
                'user_email': user_email,
                'kratos_session': {
                    'id': kratos_session.get('id'),
                    'aal': base_aal,
                    'expires_at': kratos_session.get('expires_at'),
                    'issued_at': kratos_session.get('issued_at')
                },
                'effective_aal': effective_aal,
                'base_aal': base_aal,
                'custom_aal2': custom_aal2_status,
                'recent_aal2_check': recent_aal2_check,
                'configured_methods': configured_methods,
                'session_valid': True
            }
            
            logger.info(f"🔐 Final session status for {user_email}: effective_aal={effective_aal}")
            return status
            
        except Exception as e:
            logger.error(f"🔐 Error getting session status: {e}", exc_info=True)
            return {
                'authenticated': False,
                'error': str(e),
                'effective_aal': 'aal1'
            }
    
    def _get_kratos_session(self) -> Optional[Dict[str, Any]]:
        """Get current Kratos session"""
        try:
            return whoami(request)
        except Exception as e:
            logger.error(f"🔐 Error getting Kratos session: {e}")
            return None
    
    def _get_custom_aal2_status(self, identity_id: str) -> Dict[str, Any]:
        """
        Get custom AAL2 status from Redis and Flask session
        
        Args:
            identity_id: Kratos identity ID
            
        Returns:
            Dict with custom AAL2 status details
        """
        try:
            if not self.redis_client or not identity_id:
                return {'verified': False, 'method': None, 'timestamp': None}
            
            # Check Flask session for custom AAL2 markers
            flask_aal2_verified = session.get('custom_aal2_verified', False)
            flask_aal2_timestamp = session.get('custom_aal2_timestamp')
            flask_aal2_method = session.get('custom_aal2_method')
            
            # Check Redis for persistent AAL2 status
            redis_key = f"{self.aal2_prefix}{identity_id}"
            redis_data = self.redis_client.get(redis_key)
            
            redis_aal2_status = {}
            if redis_data:
                try:
                    redis_aal2_status = json.loads(redis_data)
                except json.JSONDecodeError:
                    logger.warning(f"🔐 Invalid Redis AAL2 data for {identity_id}")
            
            # Prefer Flask session data (more recent) over Redis
            if flask_aal2_verified and flask_aal2_timestamp:
                # Verify timestamp is recent (within 30 minutes)
                try:
                    timestamp = datetime.fromisoformat(flask_aal2_timestamp)
                    age = datetime.utcnow() - timestamp
                    
                    if age <= timedelta(minutes=30):
                        return {
                            'verified': True,
                            'method': flask_aal2_method,
                            'timestamp': flask_aal2_timestamp,
                            'source': 'flask_session',
                            'age_minutes': age.total_seconds() / 60
                        }
                    else:
                        logger.info(f"🔐 Flask AAL2 status expired for {identity_id} ({age.total_seconds()/60:.1f} min)")
                except Exception as e:
                    logger.error(f"🔐 Error parsing Flask AAL2 timestamp: {e}")
            
            # Fall back to Redis data
            if redis_aal2_status.get('verified'):
                redis_timestamp = redis_aal2_status.get('timestamp')
                if redis_timestamp:
                    try:
                        timestamp = datetime.fromisoformat(redis_timestamp)
                        age = datetime.utcnow() - timestamp
                        
                        if age <= timedelta(minutes=30):
                            return {
                                'verified': True,
                                'method': redis_aal2_status.get('method'),
                                'timestamp': redis_timestamp,
                                'source': 'redis',
                                'age_minutes': age.total_seconds() / 60
                            }
                    except Exception as e:
                        logger.error(f"🔐 Error parsing Redis AAL2 timestamp: {e}")
            
            return {'verified': False, 'method': None, 'timestamp': None}
            
        except Exception as e:
            logger.error(f"🔐 Error getting custom AAL2 status: {e}")
            return {'verified': False, 'method': None, 'timestamp': None}
    
    def _determine_effective_aal(
        self, 
        base_aal: str, 
        custom_aal2_status: Dict[str, Any], 
        recent_aal2_check: Dict[str, Any]
    ) -> str:
        """
        Determine the effective AAL level considering all sources
        
        Priority:
        1. Custom AAL2 (biometric WebAuthn) - highest priority
        2. Recent Kratos AAL2 (TOTP within 30 min)
        3. Base Kratos AAL level
        """
        # Custom AAL2 from biometric WebAuthn takes precedence
        if custom_aal2_status.get('verified'):
            logger.info(f"🔐 Effective AAL2 from custom WebAuthn: {custom_aal2_status.get('method')}")
            return 'aal2'
        
        # Recent Kratos AAL2 authentication
        if recent_aal2_check.get('has_recent_aal2'):
            logger.info(f"🔐 Effective AAL2 from recent Kratos: {recent_aal2_check.get('last_aal2_method')}")
            return 'aal2'
        
        # Fall back to base AAL level
        logger.info(f"🔐 Effective AAL from base level: {base_aal}")
        return base_aal
    
    def _get_configured_methods(self, kratos_session: Dict[str, Any]) -> Dict[str, bool]:
        """Get configured authentication methods from session"""
        try:
            identity = kratos_session.get('identity', {})
            credentials = identity.get('credentials', {})
            
            methods = {
                'email_code': True,  # Always available via Kratos
                'webauthn': 'webauthn' in credentials,
                'totp': 'totp' in credentials,
                'lookup_secret': 'lookup_secret' in credentials
            }
            
            # Also check for our custom passkeys
            identity_id = identity.get('id')
            if identity_id:
                from app.models.passkey_models import Passkey
                if hasattr(g, 'user') and g.user:
                    passkey_count = Passkey.count_user_passkeys(g.user.id)
                    methods['custom_passkey'] = passkey_count > 0
            
            return methods
            
        except Exception as e:
            logger.error(f"🔐 Error getting configured methods: {e}")
            return {'email_code': True}
    
    def mark_aal2_verified(
        self, 
        identity_id: str, 
        method: str = 'webauthn_biometric',
        persist_to_redis: bool = True
    ) -> bool:
        """
        Mark user as AAL2 verified in both Flask session and Redis
        
        Args:
            identity_id: Kratos identity ID
            method: Authentication method used
            persist_to_redis: Whether to persist to Redis for cross-session AAL2
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Mark in Flask session (immediate availability)
            session['custom_aal2_verified'] = True
            session['custom_aal2_timestamp'] = timestamp
            session['custom_aal2_method'] = method
            session['custom_aal2_identity_id'] = identity_id
            
            logger.info(f"🔐 Marked AAL2 verified in Flask session: {method} for {identity_id}")
            
            # Persist to Redis (cross-session availability)
            if persist_to_redis and self.redis_client:
                redis_key = f"{self.aal2_prefix}{identity_id}"
                redis_data = {
                    'verified': True,
                    'method': method,
                    'timestamp': timestamp,
                    'identity_id': identity_id
                }
                
                # Set with 30-minute expiration
                self.redis_client.setex(
                    redis_key, 
                    timedelta(minutes=30), 
                    json.dumps(redis_data)
                )
                
                logger.info(f"🔐 Persisted AAL2 status to Redis: {redis_key}")
            
            return True
            
        except Exception as e:
            logger.error(f"🔐 Error marking AAL2 verified: {e}", exc_info=True)
            return False
    
    def clear_aal2_status(self, identity_id: str = None) -> bool:
        """
        Clear AAL2 status from both Flask session and Redis
        
        Args:
            identity_id: Optional identity ID for targeted clearing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear Flask session
            session.pop('custom_aal2_verified', None)
            session.pop('custom_aal2_timestamp', None)
            session.pop('custom_aal2_method', None)
            session.pop('custom_aal2_identity_id', None)
            
            logger.info("🔐 Cleared AAL2 status from Flask session")
            
            # Clear Redis if identity_id provided
            if identity_id and self.redis_client:
                redis_key = f"{self.aal2_prefix}{identity_id}"
                self.redis_client.delete(redis_key)
                logger.info(f"🔐 Cleared AAL2 status from Redis: {redis_key}")
            
            return True
            
        except Exception as e:
            logger.error(f"🔐 Error clearing AAL2 status: {e}")
            return False
    
    def requires_aal2(self, required_level: str = 'aal2') -> Tuple[bool, Dict[str, Any]]:
        """
        Check if current session meets AAL2 requirements
        
        Args:
            required_level: Required AAL level ('aal1' or 'aal2')
            
        Returns:
            Tuple of (requirement_met, session_status)
        """
        session_status = self.get_session_status()
        
        if not session_status.get('authenticated'):
            return False, session_status
        
        if required_level == 'aal1':
            return True, session_status
        
        effective_aal = session_status.get('effective_aal')
        requirement_met = effective_aal == 'aal2'
        
        logger.info(f"🔐 AAL2 requirement check: required={required_level}, effective={effective_aal}, met={requirement_met}")
        
        return requirement_met, session_status
    
    def sync_with_kratos(self) -> bool:
        """
        Synchronize Flask session data with current Kratos session
        
        Returns:
            True if sync successful, False otherwise
        """
        try:
            kratos_session = self._get_kratos_session()
            
            if not kratos_session:
                logger.warning("🔐 No Kratos session to sync with")
                return False
            
            # Update Flask session with Kratos data
            identity = kratos_session.get('identity', {})
            session['kratos_identity_id'] = identity.get('id')
            session['kratos_session_id'] = kratos_session.get('id')
            session['kratos_aal'] = kratos_session.get('authenticator_assurance_level', 'aal1')
            session['user_email'] = identity.get('traits', {}).get('email')
            
            logger.info(f"🔐 Synced Flask session with Kratos for user: {session.get('user_email')}")
            return True
            
        except Exception as e:
            logger.error(f"🔐 Error syncing with Kratos: {e}")
            return False
    
    def cleanup_expired_aal2_sessions(self) -> int:
        """
        Clean up expired AAL2 sessions from Redis
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            if not self.redis_client:
                return 0
            
            # Get all AAL2 keys
            pattern = f"{self.aal2_prefix}*"
            keys = self.redis_client.keys(pattern)
            
            cleaned_count = 0
            current_time = datetime.utcnow()
            
            for key in keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        aal2_status = json.loads(data)
                        timestamp_str = aal2_status.get('timestamp')
                        
                        if timestamp_str:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            age = current_time - timestamp
                            
                            if age > timedelta(minutes=30):
                                self.redis_client.delete(key)
                                cleaned_count += 1
                                logger.debug(f"🔐 Cleaned expired AAL2 session: {key}")
                            
                except Exception as e:
                    logger.error(f"🔐 Error processing AAL2 key {key}: {e}")
                    # Delete corrupted keys
                    self.redis_client.delete(key)
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"🔐 Cleaned up {cleaned_count} expired AAL2 sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"🔐 Error cleaning up AAL2 sessions: {e}")
            return 0

# Global session manager instance
_session_manager = None

def get_session_manager() -> HybridSessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = HybridSessionManager()
    return _session_manager

def require_aal2(f):
    """Decorator to require AAL2 authentication for routes"""
    from functools import wraps
    from flask import redirect, url_for
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_manager = get_session_manager()
        requirement_met, session_status = session_manager.requires_aal2('aal2')
        
        if not requirement_met:
            # Redirect to AAL2 step-up
            return redirect(f"/login?aal=aal2&return_to={request.url}")
        
        # Set session status in g for use in route
        g.session_status = session_status
        return f(*args, **kwargs)
    
    return decorated_function