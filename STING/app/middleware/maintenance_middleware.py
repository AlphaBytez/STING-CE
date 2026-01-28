"""
Maintenance Window Middleware
Handles system maintenance mode with graceful degradation and admin bypass.
"""

from flask import request, jsonify, g, current_app
from functools import wraps
import logging
import redis
import os
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

# Redis key for maintenance state
MAINTENANCE_KEY = 'sting:maintenance:state'
MAINTENANCE_CACHE_TTL = 5  # Cache for 5 seconds to reduce Redis calls

# In-memory cache to reduce Redis calls
_maintenance_cache = {
    'state': None,
    'expires': 0
}

def get_redis_client():
    """Get Redis client with connection pooling"""
    try:
        return redis.from_url(
            os.getenv('REDIS_URL', 'redis://redis:6379/0'),
            decode_responses=True
        )
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


def get_maintenance_state():
    """
    Get current maintenance state from Redis with caching.
    Returns dict with maintenance configuration or None if not in maintenance.
    """
    import time
    
    # Check cache first
    if _maintenance_cache['state'] is not None and time.time() < _maintenance_cache['expires']:
        return _maintenance_cache['state']
    
    try:
        r = get_redis_client()
        if not r:
            return None
        
        state_json = r.get(MAINTENANCE_KEY)
        if not state_json:
            _maintenance_cache['state'] = None
            _maintenance_cache['expires'] = time.time() + MAINTENANCE_CACHE_TTL
            return None
        
        state = json.loads(state_json)
        
        # Check if maintenance is enabled
        if not state.get('enabled', False):
            _maintenance_cache['state'] = None
            _maintenance_cache['expires'] = time.time() + MAINTENANCE_CACHE_TTL
            return None
        
        # Check scheduled time window
        now = datetime.now(timezone.utc)
        
        # If start_time is set and in the future, not in maintenance yet
        if state.get('start_time'):
            start = datetime.fromisoformat(state['start_time'].replace('Z', '+00:00'))
            if now < start:
                _maintenance_cache['state'] = None
                _maintenance_cache['expires'] = time.time() + MAINTENANCE_CACHE_TTL
                return None
        
        # If end_time is set and in the past, maintenance is over
        if state.get('end_time'):
            end = datetime.fromisoformat(state['end_time'].replace('Z', '+00:00'))
            if now > end:
                # Auto-disable maintenance after end time
                disable_maintenance(auto=True)
                _maintenance_cache['state'] = None
                _maintenance_cache['expires'] = time.time() + MAINTENANCE_CACHE_TTL
                return None
        
        # Cache the active state
        _maintenance_cache['state'] = state
        _maintenance_cache['expires'] = time.time() + MAINTENANCE_CACHE_TTL
        
        return state
        
    except Exception as e:
        logger.error(f"Error getting maintenance state: {e}")
        return None


def set_maintenance_state(state: dict):
    """
    Set maintenance state in Redis and invalidate cache.
    """
    try:
        r = get_redis_client()
        if not r:
            raise Exception("Redis not available")
        
        # Add timestamp
        state['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        r.set(MAINTENANCE_KEY, json.dumps(state))
        
        # Invalidate cache
        _maintenance_cache['state'] = None
        _maintenance_cache['expires'] = 0
        
        # Publish to Redis pub/sub for real-time updates
        r.publish('sting:maintenance:updates', json.dumps({
            'type': 'state_changed',
            'state': state
        }))
        
        logger.info(f"Maintenance state updated: enabled={state.get('enabled')}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting maintenance state: {e}")
        return False


def enable_maintenance(
    message: str = "System maintenance in progress",
    start_time: str = None,
    end_time: str = None,
    allow_admins: bool = True,
    updated_by: str = None
):
    """
    Enable maintenance mode.
    
    Args:
        message: Message to display to users
        start_time: ISO format datetime for scheduled start (optional)
        end_time: ISO format datetime for auto-end (optional)
        allow_admins: Whether admins can bypass maintenance
        updated_by: User ID or email of admin who enabled maintenance
    """
    state = {
        'enabled': True,
        'message': message,
        'start_time': start_time,
        'end_time': end_time,
        'allow_admins': allow_admins,
        'updated_by': updated_by,
        'enabled_at': datetime.now(timezone.utc).isoformat()
    }
    
    return set_maintenance_state(state)


def disable_maintenance(updated_by: str = None, auto: bool = False):
    """
    Disable maintenance mode.
    
    Args:
        updated_by: User ID or email of admin who disabled maintenance
        auto: Whether this was an automatic disable (end_time reached)
    """
    state = {
        'enabled': False,
        'disabled_at': datetime.now(timezone.utc).isoformat(),
        'disabled_by': updated_by if not auto else 'auto',
        'auto_disabled': auto
    }
    
    return set_maintenance_state(state)


def clear_maintenance_cache():
    """Clear the in-memory maintenance cache"""
    _maintenance_cache['state'] = None
    _maintenance_cache['expires'] = 0


# Endpoints that should ALWAYS work, even during maintenance
MAINTENANCE_BYPASS_PATHS = [
    '/health',                          # System health check
    '/api/health',                      # API health check
    '/api/system/health',               # Detailed health check
    '/api/system/maintenance',          # Maintenance status endpoint
    '/api/admin/maintenance',           # Admin maintenance control
    '/.ory/',                           # Kratos auth (admins need to login)
    '/api/auth/me',                     # Session check
    '/api/auth/logout',                 # Allow logout
    '/api/auth/session',                # Session management
    '/static/',                         # Static assets
    '/favicon.ico',                     # Favicon
    '/maintenance',                     # Maintenance page itself
]


def is_admin_user():
    """Check if the current user is an admin"""
    user = getattr(g, 'user', None)
    if not user:
        return False
    
    role = getattr(user, 'role', None)
    if role:
        return role in ('admin', 'super_admin')
    
    return False


def should_bypass_maintenance():
    """
    Determine if the current request should bypass maintenance mode.
    """
    path = request.path
    
    # Always allow certain paths
    for bypass_path in MAINTENANCE_BYPASS_PATHS:
        if path.startswith(bypass_path):
            return True
    
    # Allow OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        return True
    
    return False


def apply_maintenance_middleware(app):
    """
    Apply the maintenance middleware to the Flask app.
    This should be called early in app initialization.
    """
    
    @app.before_request
    def check_maintenance_mode():
        """Check if system is in maintenance mode and block if necessary"""
        
        # Check bypass conditions first (fast path)
        if should_bypass_maintenance():
            return None
        
        # Get maintenance state
        state = get_maintenance_state()
        
        # Not in maintenance mode
        if not state or not state.get('enabled'):
            return None
        
        # Check if admins can bypass
        if state.get('allow_admins', True) and is_admin_user():
            # Add header to indicate admin bypass
            g.maintenance_bypassed = True
            return None
        
        # System is in maintenance mode - block the request
        message = state.get('message', 'System maintenance in progress')
        end_time = state.get('end_time')
        
        # For API requests, return JSON
        if request.path.startswith('/api/'):
            response_data = {
                'error': 'Service Unavailable',
                'code': 'MAINTENANCE_MODE',
                'message': message,
                'retry_after': 300  # Suggest retry in 5 minutes
            }
            
            if end_time:
                response_data['estimated_end'] = end_time
            
            response = jsonify(response_data)
            response.status_code = 503
            response.headers['Retry-After'] = '300'
            return response
        
        # For browser requests, redirect to maintenance page
        # The frontend will handle displaying the maintenance page
        return jsonify({
            'error': 'Service Unavailable',
            'code': 'MAINTENANCE_MODE',
            'message': message,
            'redirect': '/maintenance'
        }), 503
    
    logger.info("✅ Maintenance middleware initialized")


def require_no_maintenance(f):
    """
    Decorator for routes that should fail if maintenance mode is active.
    Unlike the global middleware, this raises an error even for bypass paths.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        state = get_maintenance_state()
        
        if state and state.get('enabled'):
            # Check admin bypass
            if state.get('allow_admins', True) and is_admin_user():
                return f(*args, **kwargs)
            
            return jsonify({
                'error': 'Service Unavailable',
                'code': 'MAINTENANCE_MODE',
                'message': state.get('message', 'System maintenance in progress')
            }), 503
        
        return f(*args, **kwargs)
    
    return decorated_function
