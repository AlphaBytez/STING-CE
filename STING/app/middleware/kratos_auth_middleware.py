"""
Pure Kratos Authentication Middleware for STING
Simplified authentication using only Kratos sessions (no Flask sessions)
"""

import logging
import requests
import os
from datetime import datetime
from flask import g, request, current_app, jsonify
from functools import wraps

logger = logging.getLogger(__name__)

# Kratos configuration
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')

class KratosAuthMiddleware:
    """Simple Kratos-only authentication middleware"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self.load_user_from_kratos)
        logger.info("🔐 Pure Kratos authentication middleware initialized")
    
    def load_user_from_kratos(self):
        """Load user information from Kratos session or API key on each request"""

        # Initialize g.api_key to None
        g.api_key = None

        # Skip authentication for public routes
        public_routes = [
            '/health', '/api/health',
            '/.ory/', '/login', '/registration',
            '/recovery', '/verification', '/error',
            '/api/bootstrap/', '/static/'
        ]

        if any(request.path.startswith(route) for route in public_routes):
            return

        # Check for API key FIRST (before Kratos session)
        auth_header = request.headers.get('Authorization', '')
        x_api_key = request.headers.get('X-API-Key', '')

        api_key_value = None
        if auth_header.startswith('Bearer sk_'):
            api_key_value = auth_header[7:]  # Remove 'Bearer ' prefix
        elif x_api_key and x_api_key.startswith('sk_'):
            api_key_value = x_api_key

        if api_key_value:
            logger.info(f"🔑 Found API key in request for {request.path}")
            try:
                from app.models.api_key_models import ApiKey
                from app.models.user_models import User

                api_key = ApiKey.verify_key(api_key_value)
                if api_key:
                    # Load the user associated with this API key
                    user = User.query.filter_by(kratos_id=api_key.user_id).first()
                    if user:
                        g.user = user
                        g.api_key = api_key
                        g.is_authenticated = True
                        g.auth_method = 'api_key'
                        logger.info(f"🔑 Authenticated via API key: {api_key.name} (scopes: {api_key.scopes})")
                        return
                    else:
                        logger.warning(f"🔑 API key valid but user {api_key.user_id} not found in database")
                else:
                    logger.warning(f"🔑 Invalid API key provided")
            except Exception as e:
                logger.error(f"🔑 Error verifying API key: {e}")

        # Get Kratos session
        session_data = self._get_kratos_session()
        
        if not session_data:
            # No valid session - set g.user to None
            g.user = None
            g.session = None
            g.is_authenticated = False
            return
        
        # Extract user information from Kratos session
        identity = session_data.get('identity', {})
        traits = identity.get('traits', {})
        
        # Create simple user object for Flask compatibility
        class SimpleUser:
            def __init__(self, identity_data, session_data):
                self.id = identity_data.get('id')
                self.email = traits.get('email')
                self.role = traits.get('role', 'user')
                self.name = f"{traits.get('name', {}).get('first', '')} {traits.get('name', {}).get('last', '')}".strip()
                self.aal = session_data.get('authenticator_assurance_level', 'aal1')
                self.kratos_id = identity_data.get('id')
                self.session_id = session_data.get('id')
                self.authenticated_at = session_data.get('authenticated_at')
                self.expires_at = session_data.get('expires_at')

            @property
            def is_admin(self):
                """Check if user has admin role"""
                return self.role in ('admin', 'super_admin')

            @property
            def is_super_admin(self):
                """Check if user has super_admin role"""
                return self.role == 'super_admin'

            def to_dict(self):
                """Return user data as dictionary for API responses"""
                return {
                    'id': self.id,
                    'email': self.email,
                    'role': self.role,
                    'effective_role': self.role,
                    'name': self.name,
                    'firstName': self.name.split()[0] if self.name else '',
                    'lastName': ' '.join(self.name.split()[1:]) if self.name and len(self.name.split()) > 1 else '',
                    'kratos_id': self.kratos_id,
                    'kratos_synced': True,
                    'aal': self.aal,
                    'is_admin': self.is_admin,
                    'is_super_admin': self.is_super_admin
                }
        
        # Set Flask globals for backward compatibility
        g.user = SimpleUser(identity, session_data)
        g.session = session_data
        g.session_data = session_data  # Also set g.session_data for tiered auth compatibility
        g.is_authenticated = True

        logger.debug(f"🔐 Loaded user from Kratos: {g.user.email} (AAL: {g.user.aal})")
    
    def _get_kratos_session(self):
        """Get session data from Kratos"""
        try:
            # Forward browser cookies to Kratos
            cookies = {key: value for key, value in request.cookies.items()}
            
            if not cookies.get('ory_kratos_session'):
                return None
            
            # Call Kratos whoami endpoint
            response = requests.get(
                f"{KRATOS_PUBLIC_URL}/sessions/whoami",
                cookies=cookies,
                headers={'Accept': 'application/json'},
                verify=False,  # For dev environment
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.debug(f"Kratos session check failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Error checking Kratos session: {e}")
            return None

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_aal2(f):
    """Decorator to require AAL2 authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Authentication required'}), 401
            
        user_aal = g.user.aal if g.user else 'aal1'
        if user_aal != 'aal2':
            return jsonify({
                'error': 'AAL2 required',
                'details': 'Enhanced authentication required for this action',
                'current_aal': user_aal,
                'step_up_url': f'/security-upgrade?return_to={request.path}'
            }), 403
            
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Authentication required'}), 401
            
        if not g.user or g.user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
            
        return f(*args, **kwargs)
    return decorated_function