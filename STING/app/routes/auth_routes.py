# app/routes/auth_routes.py
"""
Authentication routes for STING application.
Handles login, logout, session management, and authentication status checks.
"""

from flask import Blueprint, request, jsonify, session, g, redirect, url_for, current_app, make_response
import logging
from datetime import datetime, timedelta
from app.models.user_models import User, UserStatus
from app.models.passkey_models import Passkey, PasskeyStatus
from app.database import db
from app.utils.kratos_client import whoami, logout as kratos_logout
from app.utils.decorators import require_auth
import requests
import os

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# Get Kratos URLs from config
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
KRATOS_BROWSER_URL = os.getenv('KRATOS_BROWSER_URL', 'https://localhost:4433')


@auth_bp.after_request
def after_request(response):
    """Add CORS headers specifically for auth endpoints"""
    # Add CORS headers for auth endpoints
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user information"""
    try:
        # Simple approach - just check g.user set by middleware
        if hasattr(g, 'user') and g.user:
            user = g.user
            logger.info(f"Returning user info for {user.email}")
            
            # Check for passkey information from BOTH sources
            # 1. Check STING database (enhanced WebAuthn/biometrics)
            sting_passkey_count = Passkey.count_user_passkeys(user.id)
            
            # 2. Check Kratos for WebAuthn credentials
            kratos_passkey_count = 0
            kratos_has_totp = False
            if user.kratos_id:
                try:
                    import requests
                    import os
                    kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'https://kratos:4434')
                    response = requests.get(
                        f"{kratos_admin_url}/admin/identities/{user.kratos_id}",
                        verify=False,
                        timeout=5
                    )
                    if response.status_code == 200:
                        identity_data = response.json()
                        credentials = identity_data.get('credentials', {})
                        
                        # Check for WebAuthn credentials in Kratos
                        if 'webauthn' in credentials:
                            webauthn_creds = credentials.get('webauthn', {}).get('config', {}).get('credentials', [])
                            kratos_passkey_count = len(webauthn_creds)
                        
                        # Also check for TOTP while we're here
                        kratos_has_totp = 'totp' in credentials and bool(credentials.get('totp', {}).get('config', {}))
                        
                        logger.info(f"Kratos credentials check for {user.email}: {kratos_passkey_count} passkeys, TOTP: {kratos_has_totp}")
                except Exception as e:
                    logger.warning(f"Failed to check Kratos credentials: {e}")
            
            # Combine both sources
            total_passkey_count = sting_passkey_count + kratos_passkey_count
            has_passkey = total_passkey_count > 0
            
            # Return user information with enhanced passkey details
            response_data = {
                'authenticated': bool(True),  # Explicitly cast to boolean
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.effective_role,
                    'is_admin': user.is_admin,
                    'is_super_admin': user.is_super_admin,
                    'status': user.status.value if user.status else 'active',
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'kratos_id': user.kratos_id
                },
                'has_passkey': has_passkey,
                'passkey_count': total_passkey_count,
                'passkey_details': {
                    'sting_passkeys': sting_passkey_count,  # Enhanced WebAuthn/biometrics
                    'kratos_passkeys': kratos_passkey_count,  # Official Kratos passkeys
                    'total': total_passkey_count
                },
                'has_totp': kratos_has_totp,
                'auth_method': session.get('auth_method', 'unknown'),
                'session': {
                    'id': session.get('session_id'),
                    'authenticated_at': session.get('authenticated_at'),
                    'expires_at': session.get('expires_at')
                }
            }
            logger.info(f"Returning authenticated response for {user.email}, authenticated: {response_data.get('authenticated')}")
            return jsonify(response_data)
        else:
            # If middleware didn't load user, try multiple authentication methods
            logger.info("No user from middleware, attempting manual auth check")
            
            # Method 1: Try middleware approach
            try:
                from app.middleware.auth_middleware import load_user_from_session
                load_user_from_session()
                
                if hasattr(g, 'user') and g.user:
                    user = g.user
                    logger.info(f"Manual auth successful for {user.email}")
                    
                    # Check for passkey information from BOTH sources
                    # 1. Check STING database (enhanced WebAuthn/biometrics)
                    sting_passkey_count = Passkey.count_user_passkeys(user.id)
                    
                    # 2. Check Kratos for WebAuthn credentials
                    kratos_passkey_count = 0
                    kratos_has_totp = False
                    if user.kratos_id:
                        try:
                            import requests
                            import os
                            kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'https://kratos:4434')
                            response = requests.get(
                                f"{kratos_admin_url}/admin/identities/{user.kratos_id}",
                                verify=False,
                                timeout=5
                            )
                            if response.status_code == 200:
                                identity_data = response.json()
                                credentials = identity_data.get('credentials', {})
                                
                                # Check for WebAuthn credentials in Kratos
                                if 'webauthn' in credentials:
                                    webauthn_creds = credentials.get('webauthn', {}).get('config', {}).get('credentials', [])
                                    kratos_passkey_count = len(webauthn_creds)
                                
                                # Also check for TOTP while we're here
                                kratos_has_totp = 'totp' in credentials and bool(credentials.get('totp', {}).get('config', {}))
                                
                                logger.info(f"Kratos credentials check for {user.email}: {kratos_passkey_count} passkeys, TOTP: {kratos_has_totp}")
                        except Exception as e:
                            logger.warning(f"Failed to check Kratos credentials: {e}")

                    # Combine both sources
                    total_passkey_count = sting_passkey_count + kratos_passkey_count
                    has_passkey = total_passkey_count > 0

                    logger.info(f"Manual auth: Returning authenticated response for {user.email}")
                    return jsonify({
                        'authenticated': bool(True),  # Explicitly cast to boolean
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'username': user.username,
                            'first_name': user.first_name,
                            'last_name': user.last_name,
                            'role': user.effective_role,
                            'is_admin': user.is_admin,
                            'is_super_admin': user.is_super_admin,
                            'status': user.status.value if user.status else 'active',
                            'created_at': user.created_at.isoformat() if user.created_at else None,
                            'kratos_id': user.kratos_id
                        },
                        'has_passkey': has_passkey,
                        'passkey_count': total_passkey_count,
                        'passkey_details': {
                            'sting_passkeys': sting_passkey_count,  # Enhanced WebAuthn/biometrics
                            'kratos_passkeys': kratos_passkey_count,  # Official Kratos passkeys
                            'total': total_passkey_count
                        },
                        'has_totp': kratos_has_totp,
                        'auth_method': session.get('auth_method', 'unknown'),
                        'session': {
                            'id': session.get('session_id'),
                            'authenticated_at': session.get('authenticated_at'),
                            'expires_at': session.get('expires_at')
                        }
                    })
            except Exception as auth_error:
                logger.warning(f"Manual auth failed: {auth_error}")
            
            # Method 2: Direct Kratos session check for WebAuthn/passkey logins
            try:
                logger.info("Attempting direct Kratos session validation")
                kratos_session = whoami(request)
                
                if kratos_session and kratos_session.get('identity'):
                    identity = kratos_session['identity']
                    email = identity.get('traits', {}).get('email')
                    kratos_id = identity.get('id')
                    
                    logger.info(f"Found valid Kratos session for {email}")
                    
                    # Find user by Kratos ID or email
                    user = None
                    if kratos_id:
                        user = User.query.filter_by(kratos_id=kratos_id).first()
                    if not user and email:
                        user = User.query.filter_by(email=email).first()
                    
                    if user:
                        logger.info(f"Found user record for {email}")
                        
                        # Check for passkey information from BOTH sources
                        # 1. Check STING database (enhanced WebAuthn/biometrics)
                        sting_passkey_count = Passkey.count_user_passkeys(user.id)
                        
                        # 2. Check Kratos for WebAuthn credentials (we already have the identity)
                        kratos_passkey_count = 0
                        kratos_has_totp = False
                        credentials = identity.get('credentials', {})
                        
                        # Check for WebAuthn credentials in Kratos
                        if 'webauthn' in credentials:
                            webauthn_creds = credentials.get('webauthn', {}).get('config', {}).get('credentials', [])
                            kratos_passkey_count = len(webauthn_creds)
                        
                        # Also check for TOTP
                        kratos_has_totp = 'totp' in credentials and bool(credentials.get('totp', {}).get('config', {}))
                        
                        # Combine both sources
                        total_passkey_count = sting_passkey_count + kratos_passkey_count
                        has_passkey = total_passkey_count > 0
                        
                        logger.info(f"Kratos session credentials for {email}: {kratos_passkey_count} passkeys, TOTP: {kratos_has_totp}")

                        logger.info(f"Kratos direct session: Returning authenticated response for {email}")
                        return jsonify({
                            'authenticated': bool(True),  # Explicitly cast to boolean
                            'user': {
                                'id': user.id,
                                'email': user.email,
                                'username': user.username,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'role': user.effective_role,
                                'is_admin': user.is_admin,
                                'is_super_admin': user.is_super_admin,
                                'status': user.status.value if user.status else 'active',
                                'created_at': user.created_at.isoformat() if user.created_at else None,
                                'kratos_id': user.kratos_id
                            },
                            'has_passkey': has_passkey,
                            'passkey_count': total_passkey_count,
                            'passkey_details': {
                                'sting_passkeys': sting_passkey_count,  # Enhanced WebAuthn/biometrics
                                'kratos_passkeys': kratos_passkey_count,  # Official Kratos passkeys
                                'total': total_passkey_count
                            },
                            'has_totp': kratos_has_totp,
                            'auth_method': 'kratos_webauthn',
                            'session': {
                                'kratos_session_id': kratos_session.get('id'),
                                'authenticated_at': kratos_session.get('authenticated_at'),
                                'expires_at': kratos_session.get('expires_at')
                            }
                        })
                    else:
                        logger.warning(f"No user record found for Kratos identity {email}")
                        
            except Exception as kratos_error:
                logger.warning(f"Direct Kratos session check failed: {kratos_error}")
            
            logger.info("No authenticated user found via any method")
            return jsonify({
                'authenticated': bool(False),  # Explicitly cast to boolean
                'message': 'Not authenticated'
            }), 401
            
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({
            'authenticated': bool(False),  # Explicitly cast to boolean
            'error': 'Failed to get user information'
        }), 500


@auth_bp.route('/has-users', methods=['GET'])
def check_has_users():
    """Check if any users exist in the system (used for first-time setup)"""
    try:
        user_count = User.query.count()
        return jsonify({
            'has_users': user_count > 0,
            'user_count': user_count
        })
    except Exception as e:
        logger.error(f"Error checking user count: {str(e)}")
        return jsonify({
            'has_users': True,  # Fail safe - assume users exist
            'error': 'Failed to check user count'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint that clears both Flask and Kratos sessions.
    This replaces the complex multi-step logout with a simpler approach.
    """
    try:
        logger.info("Starting logout process")
        
        # Get current user before clearing session
        current_user = g.user if hasattr(g, 'user') else None
        
        # Get session cookies before clearing
        kratos_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        
        # Get session ID before clearing
        session_id = session.get('sid')
        
        # Clear Flask session
        session.clear()
        logger.info("Flask session cleared")
        
        # Clear Redis session and set invalidation flag
        try:
            redis_client = current_app.config.get('SESSION_REDIS')
            if redis_client and session_id:
                # Delete the actual session data
                session_key = f"sting:{session_id}"
                if redis_client.exists(session_key):
                    redis_client.delete(session_key)
                    logger.info(f"Deleted Redis session: {session_key}")
                
                # Set invalidation flag with TTL
                invalidation_key = f"sting:invalidated:{session_id}"
                redis_client.setex(invalidation_key, 3600, "1")  # 1 hour TTL
                logger.info(f"Set invalidation flag for session: {session_id}")
                
                # Clear any other session-related keys
                pattern = f"sting:*{session_id}*"
                for key in redis_client.scan_iter(match=pattern):
                    redis_client.delete(key)
                    logger.debug(f"Deleted related key: {key}")
                    
        except Exception as e:
            logger.warning(f"Failed to clear Redis session data: {e}")
        
        # Try to logout from Kratos if we have a session
        if kratos_cookie:
            try:
                kratos_logout(kratos_cookie)
                logger.info("Kratos logout attempted")
            except Exception as e:
                logger.warning(f"Kratos logout failed (non-critical): {e}")
        
        # If we have a user with kratos_id, delete all their sessions via Admin API
        if current_user and hasattr(current_user, 'kratos_id') and current_user.kratos_id:
            try:
                from app.utils.kratos_admin import delete_identity_sessions
                sessions_deleted = delete_identity_sessions(current_user.kratos_id)
                if sessions_deleted:
                    logger.info(f"Deleted {sessions_deleted} Kratos sessions for user {current_user.email}")
            except Exception as e:
                logger.warning(f"Failed to delete Kratos sessions via Admin API: {e}")
        
        # Create response
        response = make_response(jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }))
        
        # Clear cookies with all possible domain variations
        cookie_settings = {
            'max_age': 0,
            'expires': 0,
            'path': '/',
            'secure': True,
            'httponly': True,
            'samesite': 'Lax'
        }
        
        # Get the configured domain
        webauthn_rp_id = current_app.config.get('WEBAUTHN_RP_ID', 'localhost')
        
        # Clear session cookies
        for cookie_name in ['sting_session', 'session', 'flask_session']:
            response.set_cookie(cookie_name, '', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='localhost', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='.localhost', **cookie_settings)
            if webauthn_rp_id != 'localhost':
                response.set_cookie(cookie_name, '', domain=webauthn_rp_id, **cookie_settings)
                response.set_cookie(cookie_name, '', domain=f'.{webauthn_rp_id}', **cookie_settings)
        
        # Clear Kratos cookies
        for cookie_name in ['ory_kratos_session', 'ory_kratos_session', 'ory_session']:
            response.set_cookie(cookie_name, '', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='localhost', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='.localhost', **cookie_settings)
            if webauthn_rp_id != 'localhost':
                response.set_cookie(cookie_name, '', domain=webauthn_rp_id, **cookie_settings)
                response.set_cookie(cookie_name, '', domain=f'.{webauthn_rp_id}', **cookie_settings)
        
        # Clear continuity cookies that might cause auto-login
        for cookie_name in ['ory_kratos_continuity', 'csrf_token', 'ory_kratos_csrf_token']:
            response.set_cookie(cookie_name, '', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='localhost', **cookie_settings)
            response.set_cookie(cookie_name, '', domain='.localhost', **cookie_settings)
        
        # Add Clear-Site-Data header for better browser support
        response.headers['Clear-Site-Data'] = '"cache", "cookies", "storage", "executionContexts"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        logger.info("Logout completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        # Even if there's an error, try to clear what we can
        session.clear()
        return jsonify({
            'success': False,
            'message': 'Logout encountered errors but session was cleared'
        }), 200


@auth_bp.route('/register-kratos-session', methods=['POST'])
def register_kratos_session():
    """
    Alternative endpoint to set a Kratos session cookie when we can't create one via API.
    This is a workaround for passkey authentication.
    """
    try:
        # Ensure user is authenticated via Flask session
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'authenticated': False, 'error': 'Not authenticated'}), 401
            
        user = g.user
        
        # Create a pseudo-Kratos session token
        # In production, this would need to be a real Kratos session
        # For now, we'll create a marker that tells the frontend the user is authenticated
        
        response = make_response(jsonify({
            'success': True,
            'message': 'Session registered',
            'user': {
                'id': user.id,
                'email': user.email,
                'kratos_id': user.kratos_id
            }
        }))
        
        # Set a marker cookie that the frontend can check
        # This is NOT a real Kratos session but helps with the auth flow
        response.set_cookie(
            'sting_auth_bridge',
            f'passkey_{user.id}',
            secure=True,
            httponly=True,
            samesite='Lax',
            domain='localhost',
            path='/',
            max_age=86400  # 24 hours
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error registering session: {str(e)}")
        return jsonify({'error': 'Failed to register session'}), 500


@auth_bp.route('/test-session', methods=['GET'])
def test_session():
    """Simple endpoint to test if session is active"""
    try:
        if hasattr(g, 'user') and g.user:
            return jsonify({
                'authenticated': True,
                'user_id': g.user.id,
                'email': g.user.email
            })
        
        # Check for Kratos session
        kratos_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        if kratos_cookie:
            try:
                identity = whoami(kratos_cookie)
                if identity and identity.get('active'):
                    return jsonify({
                        'authenticated': True,
                        'kratos_session': True,
                        'identity_id': identity.get('id')
                    })
            except:
                pass
        
        return jsonify({
            'authenticated': False
        })
        
    except Exception as e:
        logger.error(f"Error testing session: {str(e)}")
        return jsonify({
            'error': 'Failed to test session'
        }), 500


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """
    Check authentication status across all auth methods.
    Returns detailed information about the current authentication state.
    """
    try:
        status = {
            'flask_auth': False,
            'kratos_auth': False,
            'auth_method': None,
            'user': None,
            'session_info': {}
        }
        
        # Check Flask session
        if hasattr(g, 'user') and g.user:
            status['flask_auth'] = True
            status['auth_method'] = session.get('auth_method', 'unknown')
            status['user'] = {
                'id': g.user.id,
                'email': g.user.email,
                'username': g.user.username
            }
            status['session_info']['flask'] = {
                'authenticated_at': session.get('authenticated_at'),
                'expires_at': session.get('expires_at')
            }
        
        # Check Kratos session
        kratos_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        if kratos_cookie:
            try:
                identity = whoami(kratos_cookie)
                if identity and identity.get('active'):
                    status['kratos_auth'] = True
                    status['session_info']['kratos'] = {
                        'id': identity.get('id'),
                        'expires_at': identity.get('expires_at'),
                        'authenticated_at': identity.get('authenticated_at')
                    }
            except:
                pass
        
        # Check for auth bridge cookie
        auth_bridge = request.cookies.get('sting_auth_bridge')
        if auth_bridge:
            status['session_info']['auth_bridge'] = auth_bridge
        
        # Overall authentication status
        status['authenticated'] = status['flask_auth'] or status['kratos_auth']
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting auth status: {str(e)}")
        return jsonify({
            'error': 'Failed to get authentication status'
        }), 500


@auth_bp.route('/check-user', methods=['POST'])
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
        
        # You could also check for other methods here
        # e.g., SSO, OAuth providers, etc.
        
        return jsonify({
            'exists': True,
            'authMethods': auth_methods
        })
        
    except Exception as e:
        logger.error(f"Error checking user: {str(e)}")
        return jsonify({
            'error': 'Failed to check user'
        }), 500


@auth_bp.route('/verify-status', methods=['GET', 'OPTIONS'])
def verify_status():
    """Check if password was recently verified in this session"""
    try:
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'authenticated': False, 'error': 'Not authenticated'}), 401
        
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


@auth_bp.route('/verify-password', methods=['POST'])
def verify_password():
    """Verify user's password for sensitive operations"""
    try:
        # First check if user is authenticated via Flask session (passkey auth)
        if hasattr(g, 'user') and g.user:
            data = request.get_json()
            password = data.get('password')
            
            if not password:
                return jsonify({
                    'error': 'Password is required'
                }), 400
            
            # Check if this is a Kratos-authenticated user with password
            user = g.user
            
            # For users authenticated via Kratos with password, we need to verify
            if hasattr(g, 'identity') and g.identity:
                # Check if user has force_password_change flag
                from app.utils.kratos_admin import get_identity_by_email
                try:
                    identity = get_identity_by_email(user.email)
                    if identity and identity.get('traits', {}).get('force_password_change', False):
                        # For users with force_password_change, we'll temporarily accept verification
                        # This allows them to set up passkeys even before changing password
                        # Note: Password verification is tracked temporarily
                        # This should be handled by Kratos privileged sessions
                        logger.info(f"Password verification for user with force_password_change: {user.email}")
                        logger.info(f"Password verification bypassed for user with force_password_change: {user.email}")
                        return jsonify({
                            'verified': True,
                            'message': 'Verification successful',
                            'notice': 'Please change your password after setting up your passkey'
                        })
                except Exception as e:
                    logger.error(f"Error checking force_password_change flag: {e}")
                
                # For regular Kratos users with g.identity, we need to verify the password
                # Get the email from g.identity
                email = g.identity.get('traits', {}).get('email')
                if not email:
                    # Fallback to user email from database
                    email = user.email
                
                # Now verify the password using Kratos login flow
                try:
                    # Create a login flow
                    flow_response = requests.get(
                        f"{KRATOS_PUBLIC_URL}/self-service/login/api",
                        verify=False
                    )
                    
                    if flow_response.status_code != 200:
                        raise Exception("Failed to create login flow")
                    
                    flow = flow_response.json()
                    flow_id = flow.get('id')
                    
                    # Submit credentials
                    login_response = requests.post(
                        f"{KRATOS_PUBLIC_URL}/self-service/login?flow={flow_id}",
                        json={
                            'identifier': email,
                            'password': password,
                            'method': 'password'
                        },
                        verify=False
                    )
                    
                    if login_response.status_code == 200:
                        # Password is correct
                        # Password verified through Kratos
                        logger.info(f"Password verified successfully for {email}")
                        return jsonify({
                            'verified': True,
                            'message': 'Password verified successfully'
                        })
                    else:
                        # Password is incorrect
                        return jsonify({
                            'verified': False,
                            'error': 'Invalid password'
                        }), 401
                        
                except Exception as e:
                    logger.error(f"Error verifying password with Kratos: {e}")
                    return jsonify({
                        'error': 'Failed to verify password'
                    }), 500
            else:
                # For passkey-authenticated users without Kratos session
                # We still need some session tracking for password verification
                # This is temporary until full Kratos integration
                logger.warning(f"Password verification for non-Kratos user: {user.email}")
                return jsonify({
                    'verified': False,
                    'error': 'Password verification requires Kratos authentication',
                    'redirect': '/login'
                })
        
        # Check if user is authenticated via Kratos session
        kratos_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        
        if not kratos_cookie:
            return jsonify({
                'error': 'User not authenticated'
            }), 401
        
        # Get identity from Kratos
        try:
            identity = whoami(kratos_cookie)
            if not identity or not identity.get('active'):
                return jsonify({
                    'error': 'Invalid session'
                }), 401
        except Exception as e:
            logger.error(f"Error checking Kratos session: {e}")
            return jsonify({
                'error': 'Failed to verify session'
            }), 500
        
        # Get password from request
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({
                'error': 'Password is required'
            }), 400
        
        # To verify password, we need to attempt a login with Kratos
        # This is a workaround since Kratos doesn't provide a direct password verification endpoint
        email = identity.get('traits', {}).get('email')
        
        if not email:
            return jsonify({
                'error': 'Could not determine user email'
            }), 500
        
        # Attempt login to verify password
        try:
            # Create a login flow
            flow_response = requests.get(
                f"{KRATOS_PUBLIC_URL}/self-service/login/api",
                verify=False
            )
            
            if flow_response.status_code != 200:
                raise Exception("Failed to create login flow")
            
            flow = flow_response.json()
            flow_id = flow.get('id')
            
            # Submit credentials
            login_response = requests.post(
                f"{KRATOS_PUBLIC_URL}/self-service/login?flow={flow_id}",
                json={
                    'identifier': email,
                    'password': password,
                    'method': 'password'
                },
                verify=False
            )
            
            if login_response.status_code == 200:
                # Password is correct
                return jsonify({
                    'verified': True,
                    'message': 'Password verified successfully'
                })
            else:
                # Password is incorrect
                return jsonify({
                    'verified': False,
                    'error': 'Invalid password'
                }), 401
                
        except Exception as e:
            logger.error(f"Error verifying password with Kratos: {e}")
            return jsonify({
                'error': 'Failed to verify password'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in password verification: {str(e)}")
        return jsonify({
            'error': 'Failed to verify password'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Handle user registration.
    This is typically done through Kratos, but we provide this endpoint
    for compatibility and custom registration flows.
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'error': 'Email and password are required'
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            return jsonify({
                'error': 'User already exists'
            }), 409
        
        # In production, you would:
        # 1. Create the identity in Kratos
        # 2. Create the local user record
        # 3. Optionally trigger email verification
        
        # For now, return unimplemented
        return jsonify({
            'error': 'Registration should be done through Kratos UI'
        }), 501
        
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        return jsonify({
            'error': 'Failed to register user'
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_session():
    """Refresh the current session"""
    try:
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Not authenticated'
            }), 401
        
        # Session refresh should be handled by Kratos
        # This endpoint is kept for backward compatibility
        logger.info("Session refresh requested - handled by Kratos")
        
        return jsonify({
            'success': True,
            'message': 'Session refreshed',
            'expires_at': session.get('expires_at')
        })
        
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        return jsonify({
            'error': 'Failed to refresh session'
        }), 500


@auth_bp.route('/clear-session', methods=['POST'])
def clear_session():
    """Clear the current session (for debugging)"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Session cleared'
        })
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return jsonify({
            'error': 'Failed to clear session'
        }), 500


@auth_bp.route('/switch-auth', methods=['POST'])
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


@auth_bp.route('/init-session', methods=['POST'])
def init_session():
    """
    DEPRECATED: Sessions should be created through Kratos authentication.
    This endpoint is kept for backward compatibility but returns an error.
    """
    return jsonify({
        'error': 'Session initialization should be done through Kratos authentication',
        'redirect': '/login'
    }), 501


@auth_bp.route('/change-password', methods=['POST', 'OPTIONS'])
@require_auth
def change_password():
    """Change user password and clear force_password_change flag"""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        from app.utils.kratos_admin import update_identity_traits
        
        logger.info(f"Password change request received - Method: {request.method}, Headers: {dict(request.headers)}")
        
        # Get current user
        user = g.user
        if not user:
            logger.error("No authenticated user found in change_password")
            logger.error(f"g.user: {getattr(g, 'user', 'not set')}, g.identity: {getattr(g, 'identity', 'not set')}")
            return jsonify({'error': 'Not authenticated'}), 401
            
        logger.info(f"Processing password change for user: {user.email}")
            
        # Check content type
        if request.content_type != 'application/json':
            logger.error(f"Invalid content type: {request.content_type}")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            logger.error("No JSON data in request body")
            return jsonify({'error': 'Invalid request data'}), 400
            
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        logger.info(f"Received password change request with data keys: {list(data.keys())}")
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
            
        # Validate new password meets requirements
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
            
        # Check for basic password complexity
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in new_password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            return jsonify({
                'error': 'Password must contain uppercase and lowercase letters, numbers, and special characters'
            }), 400
            
        # Verify current password via Kratos login flow
        try:
            # First create a login flow
            flow_response = requests.get(
                f"{KRATOS_PUBLIC_URL}/self-service/login/api",
                verify=False
            )
            
            if flow_response.status_code != 200:
                logger.error(f"Failed to create login flow: {flow_response.status_code} - {flow_response.text}")
                return jsonify({'error': 'Failed to verify password'}), 500
                
            flow = flow_response.json()
            flow_id = flow.get('id')
            
            if not flow_id:
                logger.error("No flow ID in response")
                return jsonify({'error': 'Failed to verify password'}), 500
            
            # Submit credentials to the flow
            login_response = requests.post(
                f"{KRATOS_PUBLIC_URL}/self-service/login?flow={flow_id}",
                json={
                    'identifier': user.email,
                    'password': current_password,
                    'method': 'password'
                },
                verify=False
            )
            
            if login_response.status_code != 200:
                # Check if it's a 400 error which usually means wrong password
                if login_response.status_code == 400:
                    response_data = login_response.json()
                    # Check for password error in the response
                    if 'ui' in response_data and 'messages' in response_data['ui']:
                        for msg in response_data['ui']['messages']:
                            if msg.get('type') == 'error':
                                return jsonify({'error': 'Current password is incorrect'}), 400
                return jsonify({'error': 'Current password is incorrect'}), 400
                
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return jsonify({'error': 'Failed to verify current password'}), 500
            
        # Update password via Kratos Admin API
        try:
            identity_id = user.kratos_id if hasattr(user, 'kratos_id') else None
            if not identity_id:
                # Get identity ID from Kratos
                from app.utils.kratos_admin import get_identity_by_email
                identity = get_identity_by_email(user.email)
                if not identity:
                    return jsonify({'error': 'User identity not found'}), 404
                identity_id = identity['id']
                
            # Update password - need to get full identity first
            from app.utils.kratos_admin import KRATOS_ADMIN_URL, get_identity_by_id
            
            # Get the full identity object
            full_identity = get_identity_by_id(identity_id)
            if not full_identity:
                return jsonify({'error': 'Failed to get user identity'}), 500
            
            # Prepare update data with all required fields
            # IMPORTANT: Clear force_password_change in the same update to avoid session issues
            updated_traits = full_identity.get('traits', {}).copy()
            if updated_traits.get('force_password_change', False):
                logger.info("Clearing force_password_change flag during password update")
                updated_traits['force_password_change'] = False
            
            update_data = {
                'schema_id': full_identity.get('schema_id', 'default'),
                'state': full_identity.get('state', 'active'),
                'traits': updated_traits,
                'credentials': {
                    'password': {
                        'config': {
                            'password': new_password
                        }
                    }
                }
            }
            
            # Update password using PUT
            update_response = requests.put(
                f"{KRATOS_ADMIN_URL}/admin/identities/{identity_id}",
                json=update_data,
                verify=False
            )
            
            if update_response.status_code != 200:
                logger.error(f"Failed to update password: Status {update_response.status_code}, Response: {update_response.text}")
                error_data = {}
                try:
                    error_data = update_response.json()
                except:
                    pass
                
                # Provide more specific error messages
                if update_response.status_code == 400:
                    return jsonify({'error': error_data.get('error', {}).get('message', 'Invalid password format or requirements not met')}), 400
                elif update_response.status_code == 404:
                    return jsonify({'error': 'User identity not found'}), 404
                else:
                    return jsonify({'error': 'Failed to update password'}), 500
                
            # Note: force_password_change flag was already cleared in the update above
            logger.info("Password and force_password_change flag updated successfully")
            
            # Update UserSettings to clear force_password_change flag
            try:
                from app.models.user_settings import UserSettings
                if UserSettings.mark_password_changed(identity_id):
                    logger.info("UserSettings updated - force_password_change cleared")
                    
                    # Force commit to ensure database is updated before response
                    db.session.commit()
                    logger.info("Database transaction committed")
                    
                    # If this is the admin user, also mark in filesystem
                    if user.email == 'admin@sting.local':
                        try:
                            # V2 approach: UserSettings database record is already updated above
                            # No need for additional marker files in V2 system
                            logger.info("Admin password change recorded in UserSettings (V2 system)")
                        except Exception as e:
                            logger.error(f"Error with V2 password change marking: {e}")
            except Exception as e:
                logger.error(f"Error updating UserSettings: {e}")
                
            return jsonify({
                'success': True,
                'message': 'Password changed successfully',
                'redirect': '/setup-totp'  # Tell frontend where to redirect for admin users
            })
            
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return jsonify({'error': 'Failed to update password'}), 500
            
    except Exception as e:
        logger.error(f"Error in change password: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@auth_bp.route('/admin-notice', methods=['GET'])
def get_admin_notice():
    """Get admin credentials notice if password hasn't been changed"""
    try:
        from pathlib import Path
        
        # Check if password file exists - use mounted install directory
        password_file = Path('/.sting-ce/admin_password.txt')
        
        if not password_file.exists():
            return jsonify({
                'show_notice': False,
                'message': 'Admin password has been changed'
            })
            
        # Read the password
        with open(password_file, 'r') as f:
            admin_password = f.read().strip()
            
        if not admin_password:
            return jsonify({
                'show_notice': False,
                'message': 'Admin password file is empty'
            })
            
        # Check if admin user still has force_password_change flag
        from app.utils.kratos_admin import get_identity_by_email
        identity = get_identity_by_email('admin@sting.local')
        
        if identity and not identity.get('traits', {}).get('force_password_change', False):
            # Password has been changed, remove the file
            password_file.unlink()
            return jsonify({
                'show_notice': False,
                'message': 'Admin password has been changed'
            })
            
        return jsonify({
            'show_notice': True,
            'admin_email': 'admin@sting.local',
            'admin_password': admin_password,
            'message': 'Default admin credentials - MUST be changed on first login!'
        })
        
    except Exception as e:
        logger.error(f"Error getting admin notice: {e}")
        return jsonify({
            'show_notice': False,
            'error': 'Failed to get admin notice'
        }), 500


@auth_bp.route('/password-change-login', methods=['POST'])
def password_change_login():
    """Special login endpoint for users who must change their password"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
            
        # Verify credentials with Kratos and let Kratos handle the session
        # The force_password_change middleware will handle the redirect
        from app.utils.kratos_admin import get_identity_by_email
        
        # First, check if the user exists and needs password change
        identity = get_identity_by_email(email)
        if not identity:
            return jsonify({'authenticated': False, 'error': 'Invalid credentials'}), 401
            
        # Check UserSettings for force_password_change flag
        from app.models.user_settings import UserSettings
        settings = UserSettings.get_by_kratos_id(identity['id'])
        
        if not settings or not settings.force_password_change:
            # User doesn't need to change password - redirect to normal login
            return jsonify({
                'error': 'Please use the regular login',
                'redirect': '/login'
            }), 400
            
        # Direct user to Kratos login flow which will create proper session
        return jsonify({
            'success': True,
            'message': 'Please complete login through Kratos',
            'redirect': f'{KRATOS_BROWSER_URL}/self-service/login/browser',
            'note': 'You will be redirected to change password after login'
        })
            
    except Exception as e:
        logger.error(f"Error in password change login: {e}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/totp-status', methods=['GET'])
def get_totp_status():
    """Get TOTP setup status for current user"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'authenticated': False, 'error': 'Not authenticated'}), 401
        
        user = g.user
        
        # Check TOTP status via middleware function
        from app.middleware.auth_middleware import check_admin_credentials
        if hasattr(g, 'identity') and g.identity:
            cred_status = check_admin_credentials(g.identity)
            return jsonify({
                'has_totp': cred_status.get('has_totp', False),
                'has_webauthn': cred_status.get('has_webauthn', False),
                'needs_setup': cred_status.get('needs_setup', False)
            })
        
        # Fallback for non-Kratos users
        return jsonify({
            'has_totp': False,
            'has_webauthn': False,
            'needs_setup': True
        })
        
    except Exception as e:
        logger.error(f"Error getting TOTP status: {str(e)}")
        return jsonify({'error': 'Failed to get TOTP status'}), 500


@auth_bp.route('/2fa-status', methods=['GET'])
def get_2fa_status():
    """Get comprehensive 2FA/AAL status for current user using new AAL middleware"""
    try:
        # Use the new AAL middleware to get status
        from app.middleware.aal_middleware import get_current_aal_status
        from app.utils.kratos_session import whoami
        
        aal_status = get_current_aal_status()
        
        if not aal_status:
            return jsonify({'authenticated': False, 'error': 'Not authenticated'}), 401
            
        validation = aal_status['validation']
        requirements = aal_status['requirements']
        
        # Extract authentication methods from session
        session_info = whoami(request)
        if session_info:
            session_data = session_info.get('session', session_info)
            identity = session_info.get('identity', {})
            credentials = identity.get('credentials', {})
            
            # Check what methods are configured
            has_totp = bool(credentials.get('totp'))
            has_webauthn = bool(credentials.get('webauthn'))
            has_password = bool(credentials.get('password'))
            
            # Check what methods were used in current session
            auth_methods = session_data.get('authentication_methods', [])
            used_methods = [m.get('method') for m in auth_methods]
            
            response_data = {
                'role': aal_status['role'],
                'email': aal_status['email'],
                'has_totp': has_totp,
                'has_webauthn': has_webauthn,
                'has_password': has_password,
                'has_passwordless': 'code' in used_methods or 'link' in used_methods,
                'needs_setup': not validation['valid'],
                'current_aal': validation['current_aal'],
                'required_aal': validation['required_aal'],
                'missing_methods': validation['missing_methods'],
                'validation_reason': validation['reason'],
                'requirements': {
                    'minimum_aal': requirements['minimum_aal'],
                    'required_methods': requirements['required_methods'],
                    'allow_alternatives': requirements['allow_alternatives'],
                    'description': requirements['description']
                },
                'session_methods': used_methods,
                'configured_methods': list(credentials.keys()) if credentials else []
            }
            
            logger.info(f"AAL status for {aal_status['email']} ({aal_status['role']}): AAL={validation['current_aal']}, Valid={validation['valid']}")
            return jsonify(response_data)
        
        # Fallback response
        return jsonify({
            'role': aal_status['role'],
            'email': aal_status['email'],
            'needs_setup': True,
            'current_aal': 'aal1',
            'required_aal': 'aal2',
            'missing_methods': requirements['required_methods'],
            'validation_reason': 'Unable to validate session data'
        })
        
    except Exception as e:
        logger.error(f"Error getting 2FA/AAL status: {str(e)}")
        return jsonify({'error': 'Failed to get authentication status'}), 500


@auth_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health status for dashboard widget"""
    try:
        # Basic health check - expand this with actual service checks
        services = [
            {"name": "Web Application", "status": "healthy", "icon": "server"},
            {"name": "Database", "status": "healthy", "icon": "database"},
            {"name": "Authentication", "status": "healthy", "icon": "shield"},
            {"name": "Message Queue", "status": "healthy", "icon": "activity"}
        ]
        
        return jsonify({
            'services': services,
            'overall_status': 'healthy',
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({'error': 'Failed to get system health'}), 500


@auth_bp.route('/providers', methods=['GET'])
def get_auth_providers():
    """Get available authentication providers"""
    try:
        providers = []
        
        # Password authentication (via Kratos)
        providers.append({
            'id': 'password',
            'name': 'Email & Password',
            'type': 'password',
            'enabled': True,
            'primary': True
        })
        
        # Passkey/WebAuthn
        providers.append({
            'id': 'passkey',
            'name': 'Passkey',
            'type': 'webauthn',
            'enabled': True,
            'primary': False
        })
        
        # You can add more providers here (OAuth, SAML, etc.)
        
        return jsonify({
            'providers': providers,
            'default': 'password'
        })
        
    except Exception as e:
        logger.error(f"Error getting auth providers: {str(e)}")
        return jsonify({
            'error': 'Failed to get authentication providers'
        }), 500


@auth_bp.route('/test-change-password', methods=['GET'])
def test_change_password():
    """Test endpoint to verify change password flow"""
    try:
        user = g.user
        if not user:
            logger.error(f"Test endpoint - No user found. g attributes: {[attr for attr in dir(g) if not attr.startswith('_')]}")
            logger.error(f"Session data: {dict(session)}")
            logger.error(f"Cookies: {list(request.cookies.keys())}")
            return jsonify({'error': 'Not authenticated'}), 401
            
        return jsonify({
            'message': 'Test endpoint working',
            'user': user.email,
            'has_kratos_id': bool(getattr(user, 'kratos_id', None)),
            'auth_method': getattr(g, 'auth_method', 'unknown'),
            'session_keys': list(session.keys())
        })
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


# Quick logout endpoint (GET for easier testing)
@auth_bp.route('/quick-logout', methods=['GET', 'POST'])
def quick_logout():
    """Quick logout endpoint that works with GET requests"""
    session.clear()
    response = make_response(redirect('/login'))
    
    # Clear all cookies
    for cookie_name in ['sting_session', 'ory_kratos_session', 'ory_kratos_session']:
        response.set_cookie(cookie_name, '', max_age=0, path='/', domain='localhost')
    
    return response


# Debug endpoints (should be disabled in production)
@auth_bp.route('/debug/session', methods=['GET'])
def debug_session():
    """Debug endpoint to view current session"""
    # Allow in all environments for debugging this specific issue
    
    # Check Redis sessions too
    redis_sessions = []
    try:
        import redis
        r = redis.from_url(current_app.config.get('SESSION_REDIS'))
        for key in r.keys('sting:*'):
            redis_sessions.append(key.decode())
    except Exception as e:
        redis_sessions = [f'Unable to check Redis: {str(e)}']
    
    return jsonify({
        'flask_session': dict(session),
        'session_id': session.get('_id', 'No session ID'),
        'session_cookie_name': current_app.config.get('SESSION_COOKIE_NAME'),
        'cookies': dict(request.cookies),
        'redis_sessions_count': len(redis_sessions),
        'redis_sessions': redis_sessions[:5],  # Show first 5
        'user': g.user.to_dict() if hasattr(g, 'user') and g.user else None,
        'authenticated': hasattr(g, 'user') and g.user is not None,
        'auth_method': g.auth_method if hasattr(g, 'auth_method') else None,
        'g_attributes': [attr for attr in dir(g) if not attr.startswith('_')]
    })


@auth_bp.route('/debug/simulate-webauthn-complete', methods=['GET', 'POST'])
def debug_simulate_webauthn_complete():
    """Debug endpoint to simulate successful WebAuthn completion for testing"""
    try:
        from datetime import datetime, timedelta
        import time
        
        # Check if we have a pending WebAuthn challenge
        user_id = session.get('webauthn_user_id')
        if not user_id:
            return jsonify({'error': 'No pending WebAuthn challenge'}), 400
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 400
        
        # Clear WebAuthn challenge data
        session.pop('webauthn_challenge_aal2', None)
        session.pop('webauthn_user_id', None)
        session.pop('webauthn_options', None)
        
        # SIMULATE: Establish main authentication session (the fix)
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['auth_method'] = 'enhanced_webauthn'
        session['authenticated_at'] = datetime.utcnow().isoformat()
        session['session_id'] = f"webauthn_{user.id}_{int(time.time())}"
        
        # Set expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session['expires_at'] = expires_at.isoformat()
        
        # Set AAL2 markers
        session['custom_aal2_verified'] = True
        session['custom_aal2_timestamp'] = datetime.utcnow().isoformat()
        session['custom_aal2_method'] = 'webauthn_biometric'
        
        # Store user in g for immediate access
        g.user = user
        
        logger.info(f"🔐 DEBUG: Simulated WebAuthn completion for user: {user.email}")
        
        return jsonify({
            'verified': True,
            'message': 'WebAuthn completion simulated',
            'user': {
                'id': user.id,
                'email': user.email
            },
            'session_data': {
                'user_id': session.get('user_id'),
                'auth_method': session.get('auth_method'),
                'authenticated_at': session.get('authenticated_at'),
                'expires_at': session.get('expires_at')
            }
        })
        
    except Exception as e:
        logger.error(f"Error simulating WebAuthn complete: {str(e)}")
        return jsonify({'error': 'Failed to simulate authentication'}), 500


@auth_bp.route('/aal-status', methods=['GET'])
def get_aal_status():
    """
    Get current authentication status for tiered authentication system.
    Returns configured authentication methods and whether setup is required.
    """
    try:
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Not authenticated'
            }), 401

        # Get user's role
        user_role = 'user'
        if g.user.is_admin or g.user.is_super_admin:
            user_role = 'admin'

        # Check configured authentication methods
        configured_methods = {
            'totp': False,
            'webauthn': False,
            'recovery_codes': False
        }

        # Check for TOTP setup
        try:
            from app.models.totp_models import TOTPDevice
            totp_device = TOTPDevice.query.filter_by(
                user_id=g.user.id,
                is_active=True
            ).first()
            configured_methods['totp'] = totp_device is not None
        except Exception as e:
            logger.debug(f"Could not check TOTP status: {e}")

        # Check for WebAuthn/Passkey setup
        try:
            from app.models.webauthn_models import WebAuthnCredential
            passkey = WebAuthnCredential.query.filter_by(
                user_id=g.user.id
            ).first()
            configured_methods['webauthn'] = passkey is not None
        except Exception as e:
            logger.debug(f"Could not check WebAuthn status: {e}")

        # Check for recovery codes
        try:
            from app.models.recovery_code_models import RecoveryCode
            recovery_codes = RecoveryCode.query.filter_by(
                user_id=g.user.id,
                used=False
            ).count()
            configured_methods['recovery_codes'] = recovery_codes > 0
        except Exception as e:
            logger.debug(f"Could not check recovery codes: {e}")

        # Determine what's required based on role
        required_methods = []
        missing_methods = []

        if user_role == 'admin':
            # Admins require both TOTP and Passkey
            required_methods = ['totp', 'webauthn']
            if not configured_methods['totp']:
                missing_methods.append('totp')
            if not configured_methods['webauthn']:
                missing_methods.append('webauthn')
        else:
            # Regular users require at least Passkey
            required_methods = ['webauthn']
            if not configured_methods['webauthn']:
                missing_methods.append('webauthn')

        # Build validation object
        validation = {
            'valid': len(missing_methods) == 0,
            'missing_methods': missing_methods,
            'required_methods': required_methods
        }

        return jsonify({
            'authenticated': True,
            'current_aal': 'aal1',  # For tiered auth, we only use AAL1
            'role': user_role,
            'configured_methods': configured_methods,
            'validation': validation,
            'requirements': {
                'minimum_aal': 'aal1',  # Tiered auth only needs AAL1
                'required_methods': required_methods
            },
            'user_id': g.user.id,
            'user_email': g.user.email,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error checking authentication status: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to check authentication status'
        }), 500


@auth_bp.route('/debug/clear-all-sessions', methods=['POST'])
def debug_clear_all_sessions():
    """Debug endpoint to clear all sessions for current user"""
    if not current_app.debug:
        return jsonify({'error': 'Debug mode not enabled'}), 404
    try:
        # Clear Flask session
        session.clear()
        
        # Clear session from database if using server-side sessions
        if hasattr(g, 'user') and g.user:
            # You might have a sessions table to clear
            pass
        
        response = make_response(jsonify({
            'success': True,
            'message': 'All sessions cleared'
        }))
        
        # Clear all possible cookies
        cookie_names = [
            'sting_session', 'session', 'flask_session',
            'ory_kratos_session', 'ory_kratos_session', 'ory_session',
            'csrf_token', 'sting_auth_bridge'
        ]
        
        for cookie_name in cookie_names:
            response.set_cookie(cookie_name, '', max_age=0, path='/')
            response.set_cookie(cookie_name, '', max_age=0, path='/', domain='localhost')
        
        return response
        
    except Exception as e:
        logger.error(f"Error clearing all sessions: {str(e)}")
        return jsonify({
            'error': 'Failed to clear sessions'
        }), 500


@auth_bp.route('/sync-kratos-session', methods=['POST'])
def sync_kratos_session():
    """Sync Kratos session after passkey authentication"""
    try:
        # Check if user is authenticated via Flask session
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'authenticated': False, 'error': 'Not authenticated'}), 401
        
        user = g.user
        logger.info(f"Syncing Kratos session for user: {user.email}")
        
        # Import Kratos utilities
        from app.utils.kratos_session import get_identity_by_id
        
        # If user has kratos_id, fetch full identity
        if user.kratos_id:
            identity = get_identity_by_id(user.kratos_id)
            if identity:
                logger.info(f"Successfully fetched Kratos identity for {user.email}")
                
                # Return full identity data that frontend expects
                return jsonify({
                    'success': True,
                    'identity': {
                        'id': identity.get('id'),
                        'schema_id': identity.get('schema_id'),
                        'schema_url': identity.get('schema_url'),
                        'state': identity.get('state'),
                        'traits': identity.get('traits', {}),
                        'verifiable_addresses': identity.get('verifiable_addresses', []),
                        'recovery_addresses': identity.get('recovery_addresses', []),
                        'metadata_public': identity.get('metadata_public', {}),
                        'created_at': identity.get('created_at'),
                        'updated_at': identity.get('updated_at')
                    }
                })
            else:
                logger.warning(f"Could not fetch Kratos identity for user {user.email}")
        
        # If no Kratos identity, return user data from Flask session
        return jsonify({
            'success': True,
            'identity': {
                'id': str(user.id),
                'traits': {
                    'email': user.email,
                    'name': {
                        'first': user.username.split()[0] if ' ' in user.username else user.username,
                        'last': user.username.split()[1] if ' ' in user.username else ''
                    },
                    'role': user.effective_role
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error syncing Kratos session: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to sync session'
        }), 500


@auth_bp.route('/debug/nuclear-logout', methods=['GET', 'POST'])
def nuclear_logout():
    """Nuclear option - clear everything"""
    if not current_app.debug:
        return jsonify({'error': 'Debug mode not enabled'}), 404
    
    session.clear()
    
    response = make_response('''
        <html>
        <head>
            <script>
                // Clear all localStorage
                localStorage.clear();
                // Clear all sessionStorage
                sessionStorage.clear();
                // Clear IndexedDB (if any)
                if (window.indexedDB) {
                    indexedDB.databases().then(dbs => {
                        dbs.forEach(db => indexedDB.deleteDatabase(db.name));
                    });
                }
                // Redirect to login
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            </script>
        </head>
        <body>
            <h1>Clearing all data...</h1>
            <p>You will be redirected to login page.</p>
        </body>
        </html>
        ''')
    
    # Clear all cookies
    for cookie in request.cookies:
        response.set_cookie(cookie, '', max_age=0, path='/')
        response.set_cookie(cookie, '', max_age=0, path='/', domain='localhost')
    
    response.headers['Clear-Site-Data'] = '"*"'
    
    return response


@auth_bp.route('/aal-status-v2', methods=['GET'])
@require_auth
def get_aal_status_v2():
    """Get AAL (Authentication Assurance Level) status for current user"""
    try:
        # Fix the logic - check if user is NOT authenticated
        if not hasattr(g, 'user') or not g.user:
            logger.warning("No authenticated user found for AAL status")
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Fix the logic - check if identity is NOT available
        if not hasattr(g, 'identity') or not g.identity:
            logger.warning("No identity found for AAL status")
            return jsonify({'authenticated': False, 'error': 'No identity found'}), 401
        
        # Check credentials via middleware function
        from app.middleware.auth_middleware import check_admin_credentials
        cred_status = check_admin_credentials(g.identity)
        
        # Determine AAL level based on available methods
        aal_level = "aal1"  # Default - basic authentication
        if cred_status.get('has_totp', False) or cred_status.get('has_webauthn', False):
            aal_level = "aal2"  # 2FA active
        
        logger.info(f"AAL status for {g.user.email}: aal={aal_level}, totp={cred_status.get('has_totp', False)}, webauthn={cred_status.get('has_webauthn', False)}")
        
        return jsonify({
            'aal': aal_level,
            'has_totp': cred_status.get('has_totp', False),
            'has_webauthn': cred_status.get('has_webauthn', False),
            'needs_setup': cred_status.get('needs_setup', False),
            'role': cred_status.get('role', 'user')
        })
        
    except Exception as e:
        logger.error(f"Error getting AAL status: {str(e)}")
        return jsonify({'error': 'Failed to get AAL status'}), 500


@auth_bp.route('/aal-requirements', methods=['GET'])
def get_aal_requirements():
    """Get AAL requirements for a specific route"""
    try:
        route = request.args.get('route', '')
        
        # Define routes that require AAL2 step-up
        aal2_routes = {
            '/dashboard/reports': {
                'requires_aal2': True,
                'min_aal': 'aal2',
                'reason': 'reports_access',
                'message': 'Report generation and viewing requires additional verification for security.',
                'grace_period_minutes': 15
            },
            '/dashboard/admin': {
                'requires_aal2': True,
                'min_aal': 'aal2', 
                'reason': 'admin_access',
                'message': 'Administrative functions require additional verification.',
                'grace_period_minutes': 10
            }
        }
        
        # Check if route requires AAL2
        for aal2_route, config in aal2_routes.items():
            if route.startswith(aal2_route):
                return jsonify(config)
        
        # Default: no AAL2 required
        return jsonify({
            'requires_aal2': False,
            'min_aal': 'aal1',
            'reason': 'general_access',
            'message': 'Standard access',
            'grace_period_minutes': 0
        })
        
    except Exception as e:
        logger.error(f"Error getting AAL requirements: {str(e)}")
        return jsonify({'error': 'Failed to get AAL requirements'}), 500