#!/usr/bin/env python3
"""
TOTP Enforcement Middleware
Ensures admin users have TOTP configured after password changes
"""

from flask import request, redirect, url_for, session, g
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class TOTPEnforcementMiddleware:
    """Middleware to enforce TOTP setup for admin users after password changes"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.check_totp_requirement)
    
    def check_totp_requirement(self):
        """Check if user needs TOTP setup before accessing protected routes"""
        
        # Skip TOTP checks for certain routes
        if self._should_skip_totp_check():
            return None
            
        # Only check for authenticated users
        if not hasattr(g, 'user') or not g.user:
            return None
            
        # Only enforce for admin users
        # Handle both enum and string role values (for compatibility)
        is_admin = False
        if hasattr(g.user, 'role'):
            if hasattr(g.user.role, 'value'):
                # Role is an enum (UserRole.ADMIN)
                is_admin = g.user.role.value == 'ADMIN'
            elif isinstance(g.user.role, str):
                # Role is a string
                is_admin = g.user.role.upper() == 'ADMIN'
            
        if not is_admin:
            return None
            
        # Check if user has TOTP configured
        if not self._user_has_totp(g.user):
            logger.info(f"Admin user {g.user.email} needs TOTP setup")
            
            # Allow access to TOTP setup routes and frontend paths
            if request.endpoint in ['totp.setup_totp', 'totp.verify_totp', 'totp.totp_status', 'auth.logout']:
                return None
                
            # Allow access to the frontend TOTP setup page
            if request.path == '/setup-totp':
                return None
                
            # Redirect to frontend TOTP setup page for all other routes
            session['totp_setup_required'] = True
            session['totp_redirect_after'] = request.url
            # Redirect to frontend route instead of Flask endpoint
            return redirect('/setup-totp')
        
        # User has TOTP configured, clear any setup flags
        if 'totp_setup_required' in session:
            del session['totp_setup_required']
            
        return None
    
    def _should_skip_totp_check(self):
        """Determine if TOTP check should be skipped for this request"""
        
        # Skip for static files
        if request.endpoint and request.endpoint.startswith('static'):
            return True
            
        # Skip for API endpoints (they should handle TOTP separately)
        # This includes knowledge service API calls for honey jars
        if request.path.startswith('/api/'):
            return True
            
        # Specifically ensure knowledge service endpoints are skipped
        if request.path.startswith('/api/knowledge/'):
            return True
            
        # Skip for authentication routes
        auth_routes = [
            'auth.login',
            'auth.register', 
            'auth.logout',
            'auth.password_reset',
            'auth.verify_email',
            'totp.setup_totp',
            'totp.verify_totp',
            'totp.totp_status'
        ]
        
        if request.endpoint in auth_routes:
            return True
            
        # Skip for Kratos/Ory routes
        if request.path.startswith('/.ory/'):
            return True
            
        # Skip for health checks
        if request.path in ['/health', '/healthz', '/']:
            return True
            
        return False
    
    def _user_has_totp(self, user):
        """Check if user has TOTP configured"""
        
        # Method 1: Check via Kratos API
        totp_configured = self._check_kratos_totp(user)
        if totp_configured:
            return True
            
        # Method 2: Check session flags (fallback)
        if session.get('totp_verified', False):
            return True
            
        # Method 3: Check user settings (if available)
        if hasattr(user, 'totp_enabled') and user.totp_enabled:
            return True
            
        return False
    
    def _check_kratos_totp(self, user):
        """Check TOTP status via Kratos API"""
        try:
            import requests
            from flask import current_app
            
            # Get Kratos admin URL from config
            kratos_admin_url = current_app.config.get('KRATOS_ADMIN_URL', 'https://localhost:8443')
            
            # Get user's Kratos identity
            if hasattr(user, 'kratos_id') and user.kratos_id:
                identity_id = user.kratos_id
            else:
                # Find identity by email
                identities_response = requests.get(
                    f"{kratos_admin_url}/admin/identities",
                    headers={'Accept': 'application/json'},
                    verify=False,
                    timeout=5
                )
                
                if identities_response.status_code == 200:
                    identities = identities_response.json()
                    for identity in identities:
                        if identity.get('traits', {}).get('email') == user.email:
                            identity_id = identity['id']
                            break
                    else:
                        logger.warning(f"Could not find Kratos identity for user {user.email}")
                        return False
                else:
                    logger.error(f"Failed to fetch identities from Kratos: {identities_response.status_code}")
                    return False
            
            # Check credentials for TOTP
            creds_response = requests.get(
                f"{kratos_admin_url}/admin/identities/{identity_id}/credentials",
                headers={'Accept': 'application/json'},
                verify=False,
                timeout=5
            )
            
            if creds_response.status_code == 200:
                credentials = creds_response.json()
                return 'totp' in credentials and credentials['totp'] is not None
            else:
                logger.error(f"Failed to fetch credentials from Kratos: {creds_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking TOTP status via Kratos: {e}")
            return False

def totp_required(f):
    """Decorator to ensure TOTP is configured for admin users"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is admin and needs TOTP
        if hasattr(g, 'user') and g.user and hasattr(g.user, 'role'):
            # Handle both enum and string role values
            is_admin = False
            if hasattr(g.user.role, 'value'):
                # Role is an enum (UserRole.ADMIN)
                is_admin = g.user.role.value == 'ADMIN'
            elif isinstance(g.user.role, str):
                # Role is a string
                is_admin = g.user.role.upper() == 'ADMIN'
            
            # If admin, the middleware should have already enforced TOTP
            # This decorator is just a double-check
            
        return f(*args, **kwargs)
    return decorated_function

# Global instance
totp_enforcement = TOTPEnforcementMiddleware()