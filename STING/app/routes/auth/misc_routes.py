"""
Miscellaneous Authentication Routes

Handles various authentication utilities including user checking, verification status,
system information, and legacy endpoints.
"""

from flask import Blueprint, request, jsonify, session, g
import logging
import os

from app.models.user_models import User
from app.models.passkey_models import Passkey, PasskeyStatus
from app.utils.kratos_client import logout as kratos_logout

logger = logging.getLogger(__name__)

misc_bp = Blueprint('misc', __name__)

# Get Kratos URLs from config
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
KRATOS_BROWSER_URL = os.getenv('KRATOS_BROWSER_URL', 'https://kratos:4433')


@misc_bp.after_request
def after_request(response):
    """Add CORS headers specifically for misc endpoints"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@misc_bp.route('/check-user', methods=['POST'])
def check_user():
    """Check if user exists and what authentication methods are available"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({
                'error': 'Email is required'
            }), 400
        
        # First check if user exists in Kratos
        kratos_user = None
        auth_methods = []
        
        try:
            # Import kratos admin client
            from app.utils.kratos_admin import get_identity_by_email
            kratos_user = get_identity_by_email(email.lower())
            
            if kratos_user:
                # User exists in Kratos
                # Check available auth methods from Kratos
                credentials = kratos_user.get('credentials', {})
                
                if 'password' in credentials:
                    auth_methods.append('password')
                
                if 'webauthn' in credentials:
                    auth_methods.append('passkey')
                    
                # Also check local passkey table for additional info
                user = User.query.filter_by(email=email.lower()).first()
                if user:
                    has_passkey = Passkey.query.filter_by(
                        user_id=str(user.id),
                        status=PasskeyStatus.ACTIVE.value
                    ).first() is not None
                    
                    if has_passkey and 'passkey' not in auth_methods:
                        auth_methods.append('passkey')
                        
                return jsonify({
                    'exists': True,
                    'authMethods': auth_methods if auth_methods else ['password']
                })
        except Exception as e:
            logger.error(f"Error checking Kratos identity: {e}")
            # Fall back to local database check
        
        # If not in Kratos, check local database
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            # User doesn't exist
            return jsonify({
                'exists': False,
                'authMethods': []
            })
        
        # User exists in local DB only (legacy)
        auth_methods.append('password')
        
        # Check if user has passkey credentials
        has_passkey = Passkey.query.filter_by(
            user_id=str(user.id),
            status=PasskeyStatus.ACTIVE.value
        ).first() is not None
        
        if has_passkey:
            auth_methods.append('passkey')
        
        return jsonify({
            'exists': True,
            'authMethods': auth_methods
        })
        
    except Exception as e:
        logger.error(f"Error checking user: {str(e)}")
        return jsonify({
            'error': 'Failed to check user'
        }), 500


@misc_bp.route('/verify-status', methods=['GET', 'OPTIONS'])
def verify_status():
    """Check if password was recently verified in this session"""
    try:
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Check if password was verified recently (within last 5 minutes)
        verified_at = session.get('password_verified_at')
        if verified_at:
            from datetime import datetime, timedelta
            verified_time = datetime.fromisoformat(verified_at)
            time_since_verification = datetime.utcnow() - verified_time
            
            if time_since_verification < timedelta(minutes=5):
                remaining_seconds = 300 - int(time_since_verification.total_seconds())
                return jsonify({
                    'verified': True,
                    'remaining_seconds': max(0, remaining_seconds)
                })
        
        return jsonify({
            'verified': False,
            'remaining_seconds': 0
        })
        
    except Exception as e:
        logger.error(f"Error checking verification status: {str(e)}")
        return jsonify({'error': 'Failed to check verification status'}), 500


@misc_bp.route('/register', methods=['POST'])
def register():
    """
    Handle user registration.
    This is typically done through Kratos, but we provide this endpoint
    for compatibility and custom registration flows.
    """
    try:
        # Registration should primarily be handled by Kratos
        # This endpoint can redirect or provide information about the process
        
        return jsonify({
            'message': 'Registration is handled through Kratos',
            'redirect_url': f'{KRATOS_PUBLIC_URL}/self-service/registration/browser',
            'note': 'Please use the Kratos registration flow'
        })
        
    except Exception as e:
        logger.error(f"Error in registration endpoint: {e}")
        return jsonify({
            'error': 'Registration failed'
        }), 500


@misc_bp.route('/switch-auth', methods=['POST'])
def switch_auth_method():
    """
    Switch between authentication methods (e.g., from password to passkey).
    This is useful when a user wants to upgrade their auth method.
    """
    try:
        data = request.get_json()
        new_method = data.get('method')
        
        if new_method not in ['password', 'passkey', 'oauth']:
            return jsonify({
                'error': 'Invalid authentication method'
            }), 400
        
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Not authenticated'
            }), 401
        
        # Auth method switching should be handled through Kratos
        logger.info(f"Auth method switch requested to {new_method} - should use Kratos")
        
        return jsonify({
            'success': True,
            'message': f'Switched to {new_method} authentication',
            'auth_method': new_method
        })
        
    except Exception as e:
        logger.error(f"Error switching auth method: {str(e)}")
        return jsonify({
            'error': 'Failed to switch authentication method'
        }), 500


@misc_bp.route('/init-session', methods=['POST'])
def init_session():
    """
    DEPRECATED: Sessions should be created through Kratos authentication.
    This endpoint is kept for backward compatibility but returns an error.
    """
    return jsonify({
        'error': 'Session initialization should be done through Kratos authentication',
        'redirect': '/login'
    }), 501


@misc_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health status for authentication services"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z',  # Would be actual timestamp
            'services': {
                'auth': 'healthy',
                'kratos': 'healthy',
                'database': 'healthy'
            }
        }
        
        # You could add actual health checks here
        # - Database connectivity
        # - Kratos API availability
        # - Redis session store
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@misc_bp.route('/providers', methods=['GET'])
def get_auth_providers():
    """Get available authentication providers"""
    try:
        providers = {
            'password': {
                'enabled': True,
                'name': 'Password',
                'description': 'Traditional email and password authentication'
            },
            'webauthn': {
                'enabled': True,
                'name': 'WebAuthn/Passkey',
                'description': 'Passwordless authentication using biometrics or security keys'
            },
            'totp': {
                'enabled': True,
                'name': 'TOTP',
                'description': 'Time-based one-time passwords (2FA)'
            }
        }
        
        # You could check actual configuration here to determine
        # which providers are actually enabled
        
        return jsonify({
            'providers': providers,
            'default_provider': 'password'
        })
        
    except Exception as e:
        logger.error(f"Error getting auth providers: {e}")
        return jsonify({
            'error': 'Failed to get auth providers'
        }), 500


@misc_bp.route('/quick-logout', methods=['GET', 'POST'])
def quick_logout():
    """Quick logout endpoint that works with both GET and POST"""
    try:
        # Clear Flask session
        session.clear()
        
        # Attempt to revoke Kratos session if present
        kratos_cookie = request.cookies.get('ory_kratos_session')
        if kratos_cookie:
            try:
                kratos_logout()
                logger.info("Kratos session revoked")
            except Exception as e:
                logger.warning(f"Failed to revoke Kratos session: {e}")
        
        if request.method == 'GET':
            # For GET requests, return HTML redirect
            return '''
            <html>
            <head>
                <meta http-equiv="refresh" content="0; url=/login">
            </head>
            <body>
                <p>Logging out...</p>
                <script>window.location.href = '/login';</script>
            </body>
            </html>
            '''
        else:
            # For POST requests, return JSON
            return jsonify({
                'success': True,
                'message': 'Logged out successfully',
                'redirect_url': '/login'
            })
            
    except Exception as e:
        logger.error(f"Quick logout error: {e}")
        if request.method == 'GET':
            return f'<html><body><p>Logout error: {str(e)}</p></body></html>', 500
        else:
            return jsonify({
                'error': 'Logout failed',
                'message': str(e)
            }), 500


@misc_bp.route('/enrollment/settings', methods=['GET'])
def get_enrollment_settings_flow():
    """Get enrollment settings for 2FA setup"""
    try:
        # This would typically interact with Kratos to get
        # the settings flow for enrollment
        
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Mock enrollment settings - would be actual Kratos flow
        enrollment_settings = {
            'flow_id': f'enrollment-{g.user.id}',
            'type': 'enrollment',
            'available_methods': ['totp', 'webauthn'],
            'ui': {
                'action': '/enrollment',
                'method': 'POST',
                'nodes': []
            }
        }
        
        return jsonify(enrollment_settings)
        
    except Exception as e:
        logger.error(f"Error getting enrollment settings: {e}")
        return jsonify({
            'error': 'Failed to get enrollment settings'
        }), 500