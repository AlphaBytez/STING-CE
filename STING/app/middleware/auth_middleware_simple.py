"""
Simplified auth middleware that trusts Kratos completely
Following best practices - no duplicate state management
"""
from flask import request, g, jsonify
from functools import wraps
import logging
from app.utils.kratos_client import whoami
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

# Endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    'static',
    'health',
    'auth.login',
    'auth.logout',
    'kratos_webhooks.webhook_health',
    'kratos_webhooks.user_registered',
    'kratos_webhooks.password_changed',
    'kratos_webhooks.session_created',
]

def load_user_from_kratos():
    """
    Load user from Kratos session
    This is the ONLY source of truth for authentication
    """
    # Clear any existing user
    g.user = None
    g.identity = None
    
    # Skip auth for public endpoints
    if request.endpoint and request.endpoint in PUBLIC_ENDPOINTS:
        return
    
    # Check for Kratos session
    session_cookie = request.cookies.get('ory_kratos_session')
    auth_header = request.headers.get('Authorization', '')
    
    # Try cookie first, then bearer token
    if session_cookie:
        identity_data = whoami(session_cookie, is_token=False)
    elif auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        identity_data = whoami(token, is_token=True)
    else:
        # No credentials provided
        logger.debug(f"No auth credentials for {request.path}")
        return
    
    if identity_data and 'identity' in identity_data:
        identity = identity_data['identity']
        g.identity = identity
        
        # Get or create user from Kratos identity
        # This syncs our database with Kratos
        try:
            user = UserService.get_or_create_user_from_kratos(identity)
            g.user = user
            logger.debug(f"Loaded user {user.email} from Kratos session")
        except Exception as e:
            logger.error(f"Error loading user from Kratos: {e}")
            # Continue without user - let endpoints handle authorization
    else:
        logger.debug(f"No valid Kratos session for {request.path}")

def require_auth(f):
    """
    Decorator to require authentication
    Use this on endpoints that need auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('user'):
            return jsonify({
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(role):
    """
    Decorator to require specific role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.get('user'):
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            
            if g.user.role != role and g.user.role != 'SUPER_ADMIN':
                return jsonify({
                    'error': 'Insufficient permissions',
                    'code': 'FORBIDDEN'
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator