"""
Force Password Change Middleware V2
Uses Flask database instead of Kratos traits for better control
"""

from flask import request, jsonify, current_app, redirect, g
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Endpoints that are allowed without password change
ALLOWED_ENDPOINTS = [
    'auth.change_password',
    'auth.password_change_login', 
    'auth.logout',
    'auth.verify_password',
    'auth.verify_status',
    'auth.test_change_password',
    'auth.login',
    # Remove auth.me from allowed endpoints so it triggers password change check
    # 'auth.me',  
    'auth.admin_notice',
    # Remove users.me as well
    # 'users.me',
    # Keep session endpoints for basic functionality
    'session.whoami',
    'session.session_proxy',
    'webauthn.begin_add_passkey',
    'webauthn.complete_add_passkey',
    'webauthn.list_passkeys',
    'webauthn.passkey_stats',
    # Allow user settings endpoint for enrollment page
    'user.get_user_settings',
    'static',
    'health',
]

def apply_force_password_change_middleware_v2(app):
    """Apply the middleware to all routes using database check"""
    @app.before_request
    def before_request():
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return
            
        # Skip for allowed endpoints
        if request.endpoint and request.endpoint in ALLOWED_ENDPOINTS:
            return
            
        # Special case: Allow auth.me for enrollment paths
        if request.endpoint == 'auth.me' and request.referrer and '/enrollment' in request.referrer:
            return
            
        # Check if user needs to change password
        user = getattr(g, 'user', None)
        if user:
            try:
                # Get user settings from database
                from app.models.user_settings import UserSettings
                from app.database import db
                # Use kratos_id instead of numeric id for user_settings lookup
                user_id = user.kratos_id if hasattr(user, 'kratos_id') else str(user.id)
                
                # Query fresh data from database to ensure we get latest state
                settings = UserSettings.query.filter_by(user_id=user_id).first()
                
                if settings and settings.force_password_change:
                    # Log for debugging
                    logger.info(f"User {user.email} requires password change")
                    
                    # Handle based on request type
                    if request.path.startswith('/api/'):
                        # API request - return JSON
                        return jsonify({
                            'error': 'Password change required',
                            'code': 'PASSWORD_CHANGE_REQUIRED',
                            'message': 'You must change your password before continuing',
                            'redirect': '/password-change-login'
                        }), 403
                    else:
                        # Web request - redirect
                        # But don't redirect if already on password change page
                        if not request.path.startswith('/password-change'):
                            return redirect('/password-change-login')
                        
            except Exception as e:
                logger.error(f"Error in password change middleware: {e}")
                # Allow request to continue on error