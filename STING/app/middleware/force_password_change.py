"""
Force Password Change Middleware
Ensures users with force_password_change flag must change their password
"""

from flask import request, jsonify, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Endpoints that are allowed without password change
ALLOWED_ENDPOINTS = [
    'auth.change_password',
    'auth.logout',
    'auth.session',
    'auth.verify_password',
    'auth.verify_status',
    'auth.login',
    'auth.password_change_login',
    'auth.me',
    'auth.admin_notice',
    'users.me',
    'session.whoami',
    'session.session_proxy',
    'webauthn.begin_add_passkey',
    'webauthn.complete_add_passkey',
    'webauthn.list_passkeys',
    'webauthn.passkey_stats',
    'static',
    'health',
]

def check_password_change_required():
    """Middleware to enforce password change for users with the flag set"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip for allowed endpoints
            if request.endpoint in ALLOWED_ENDPOINTS:
                return f(*args, **kwargs)
            
            # Get current user from g
            from flask import g
            user = getattr(g, 'user', None)
            if not user:
                return f(*args, **kwargs)
            
            # Check if user has force_password_change flag
            try:
                # Get identity from Kratos to check traits
                from app.utils.kratos_admin import get_identity_by_email
                identity = get_identity_by_email(user.email)
                
                if identity and identity.get('traits', {}).get('force_password_change', False):
                    # User must change password
                    return jsonify({
                        'error': 'Password change required',
                        'code': 'PASSWORD_CHANGE_REQUIRED',
                        'message': 'You must change your password before continuing',
                        'redirect': '/change-password'
                    }), 403
                    
            except Exception as e:
                logger.error(f"Error checking password change requirement: {e}")
                # Allow request to continue on error
                
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator

def apply_force_password_change_middleware(app):
    """Apply the middleware to all routes"""
    @app.before_request
    def before_request():
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return
            
        # Skip for static files and health checks
        if request.endpoint and request.endpoint in ALLOWED_ENDPOINTS:
            return
            
        # Check if user needs to change password
        from flask import g
        user = getattr(g, 'user', None)
        if user:
            try:
                from app.utils.kratos_admin import get_identity_by_email
                identity = get_identity_by_email(user.email)
                
                if identity and identity.get('traits', {}).get('force_password_change', False):
                    # Allow password change and passkey setup related endpoints
                    allowed_force_change_endpoints = [
                        'auth.change_password', 
                        'auth.password_change_login',
                        'auth.logout',
                        'auth.verify_password',
                        'auth.verify_status',
                        'auth.test_change_password',
                        'webauthn.begin_add_passkey',
                        'webauthn.complete_add_passkey',
                        'webauthn.list_passkeys',
                        'webauthn.passkey_stats',
                        # Allow essential endpoints for app initialization
                        'auth.me',
                        'auth.admin_notice',
                        'users.me',
                        'session.whoami',
                        'session.session_proxy',
                        # Allow static resources
                        'static'
                    ]
                    if request.endpoint not in allowed_force_change_endpoints:
                        # For API calls, return JSON error
                        if request.path.startswith('/api/'):
                            return jsonify({
                                'error': 'Password change required',
                                'code': 'PASSWORD_CHANGE_REQUIRED',
                                'message': 'You must change your password before continuing',
                                'redirect': '/password-change-login'
                            }), 403
                        # For web pages, redirect to password change login
                        else:
                            from flask import redirect
                            return redirect('/password-change-login')
                        
            except Exception as e:
                logger.error(f"Error in password change middleware: {e}")
                # Allow request to continue on error