from functools import wraps
from flask import request, jsonify, g
import logging
import requests
import os
from app.utils.decorators import require_auth
from app.middleware.api_key_middleware import api_key_optional

logger = logging.getLogger(__name__)

def check_kratos_session():
    """
    Check if there's a valid Kratos session by looking for ory_kratos_session cookie
    and verifying it with Kratos admin API.
    Returns user info dict or None if not authenticated.
    """
    try:
        # Look for Kratos session cookie
        kratos_cookie = request.cookies.get('ory_kratos_session')
        if not kratos_cookie:
            return None
        
        # Verify session with Kratos public API (whoami endpoint)
        kratos_public_url = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
        headers = {
            'Cookie': f'ory_kratos_session={kratos_cookie}',
            'Accept': 'application/json'
        }
        
        response = requests.get(
            f'{kratos_public_url}/sessions/whoami',
            headers=headers,
            timeout=5,
            verify=False  # For local development with self-signed certs
        )
        
        if response.status_code == 200:
            session_data = response.json()
            identity = session_data.get('identity', {})
            traits = identity.get('traits', {})
            
            return {
                'id': identity.get('id'),
                'email': traits.get('email'),
                'auth_method': 'kratos_session',
                'role': traits.get('role', 'user'),
                'session_id': session_data.get('id'),
                'kratos_identity': identity
            }
        
        logger.debug(f"Kratos session check failed: {response.status_code}")
        return None
        
    except Exception as e:
        logger.debug(f"Error checking Kratos session: {e}")
        return None

def require_auth_flexible():
    """
    Enhanced decorator that accepts multiple authentication methods:
    1. Middleware authentication (Flask session + Kratos)
    2. API key authentication
    3. Flask session authentication  
    4. Kratos session authentication
    
    Falls back gracefully and allows endpoints to return demo data.
    """
    def decorator(f):
        @wraps(f)
        @api_key_optional()  # Check for API key first
        def decorated_function(*args, **kwargs):
            logger.info(f"[FLEXIBLE_AUTH] Processing request to {request.path}")
            logger.info(f"[FLEXIBLE_AUTH] Request headers: Authorization={request.headers.get('Authorization', 'None')}")
            logger.info(f"[FLEXIBLE_AUTH] Has g.api_key: {hasattr(g, 'api_key')}")
            logger.info(f"[FLEXIBLE_AUTH] Has g.user: {hasattr(g, 'user')}")
            if hasattr(g, 'api_key'):
                logger.info(f"[FLEXIBLE_AUTH] g.api_key value: {g.api_key}")
            if hasattr(g, 'user'):
                logger.info(f"[FLEXIBLE_AUTH] g.user type: {type(g.user)}")
                logger.info(f"[FLEXIBLE_AUTH] g.user value: {g.user}")
                logger.info(f"[FLEXIBLE_AUTH] g.user email: {getattr(g.user, 'email', 'No email')}")
                logger.info(f"[FLEXIBLE_AUTH] g.user has email attr: {hasattr(g.user, 'email') if g.user else False}")
            
            # Method 1: Check if middleware has already authenticated the user
            if hasattr(g, 'user') and g.user and hasattr(g.user, 'email'):
                logger.info("Authentication successful via middleware")
                # Ensure g.identity is set for compatibility
                if not hasattr(g, 'identity') or not g.identity:
                    g.identity = {
                        'id': str(getattr(g.user, 'id', '')),
                        'traits': {
                            'email': g.user.email,
                            'role': getattr(g.user, 'role', 'user')
                        }
                    }
                return f(*args, **kwargs)
            
            # Method 2: Check if API key authentication was successful
            if hasattr(g, 'api_key') and g.api_key:
                logger.info("Authentication successful via API key")
                # Set compatible globals for endpoints that expect g.user and g.identity
                from app.models.user_models import User
                try:
                    user = User.query.filter_by(email=g.api_key.user_email).first()
                    if user:
                        g.user = user
                    # Create mock identity for API key auth
                    g.identity = {
                        'id': str(g.api_key.user_id),
                        'traits': {
                            'email': g.api_key.user_email,
                            'role': 'admin' if 'admin' in g.api_key.scopes else 'user'
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to load user for API key: {e}")
                return f(*args, **kwargs)
            
            # Method 3: Check Kratos session
            kratos_user = check_kratos_session()
            if kratos_user:
                logger.info("Authentication successful via Kratos session")
                # Set compatible globals for endpoints that expect g.user and g.identity
                from app.models.user_models import User
                try:
                    user = User.query.filter_by(email=kratos_user['email']).first()
                    if user:
                        g.user = user
                    else:
                        # Create a minimal user object for Kratos-only users
                        class KratosUser:
                            def __init__(self, email, user_id, role='user'):
                                self.email = email
                                self.id = user_id
                                self.role = role
                        g.user = KratosUser(kratos_user['email'], kratos_user['id'], kratos_user.get('role', 'user'))
                    
                    # Set identity for Kratos compatibility
                    g.identity = kratos_user.get('kratos_identity', {
                        'id': kratos_user['id'],
                        'traits': {
                            'email': kratos_user['email'],
                            'role': kratos_user.get('role', 'user')
                        }
                    })
                except Exception as e:
                    logger.warning(f"Failed to load user for Kratos session: {e}")
                
                # Also store in g.current_user for backward compatibility
                g.current_user = kratos_user
                return f(*args, **kwargs)
            
            # Method 4: Check Flask session (original behavior)
            try:
                @require_auth
                @wraps(f)
                def session_auth_wrapper(*args, **kwargs):
                    logger.debug("Authentication successful via Flask session")
                    return f(*args, **kwargs)
                
                return session_auth_wrapper(*args, **kwargs)
            except Exception as e:
                logger.debug(f"Flask session auth failed: {e}")
                # All authentication methods failed - let endpoint handle gracefully
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def get_current_auth_user():
    """
    Get the current authenticated user from any authentication method.
    Returns a dict with user info or None if not authenticated.
    
    Checks in order: Middleware -> API key -> Kratos session -> Flask session
    """
    # Method 1: API key authentication
    if hasattr(g, 'api_key') and g.api_key:
        return {
            'id': g.api_key.user_id,
            'email': g.api_key.user_email,
            'auth_method': 'api_key',
            'api_key_id': g.api_key.key_id,
            'scopes': g.api_key.scopes,
            'permissions': g.api_key.permissions
        }
    
    # Method 2: Check if Kratos user was set by flexible auth
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user
    
    # Method 3: Check Kratos session directly
    kratos_user = check_kratos_session()
    if kratos_user:
        return kratos_user
    
    # Method 4: Flask session authentication
    if hasattr(g, 'user') and g.user:
        return {
            'id': g.user.id,
            'email': g.user.email,
            'auth_method': 'flask_session',
            'role': getattr(g.user, 'role', 'user')
        }
    
    return None