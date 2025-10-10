"""
Authentication middleware for STING
Handles Kratos session validation, user loading, and API key authentication
"""

import logging
import time
from datetime import datetime
from flask import g, request, session, current_app, redirect, url_for, jsonify
from app.utils.kratos_client import whoami
from app.utils.kratos_admin import get_session_by_id, extract_session_id_from_cookie
from app.services.user_service import UserService
from app.models.user_models import User
from app.models.api_key_models import ApiKey
import redis
import requests
import os

logger = logging.getLogger(__name__)

def load_user_from_session():
    """
    Middleware to load user from API key, Kratos session, or Flask session (for passkey auth)
    This should be called before each request
    """
    # Clear any existing user
    g.user = None
    g.identity = None
    g.kratos_identity = None
    g.api_key = None

    # Skip authentication for OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        logger.debug(f"Skipping auth for OPTIONS request: {request.path}")
        return

    # Log the request path for debugging
    logger.info(f"[AUTH MIDDLEWARE] Loading user for request: {request.path}")
    logger.info(f"[AUTH MIDDLEWARE] Request cookies: {list(request.cookies.keys())}")
    logger.info(f"[AUTH MIDDLEWARE] Request headers: {list(request.headers.keys())}")

    # Check for API key FIRST (before Kratos session)
    auth_header = request.headers.get('Authorization', '')
    x_api_key = request.headers.get('X-API-Key', '')

    # Support both Authorization: Bearer and X-API-Key headers
    api_key_value = None
    if auth_header.startswith('Bearer sk_'):
        # This is an API key, not a Kratos session token
        api_key_value = auth_header[7:]  # Remove 'Bearer ' prefix
    elif x_api_key and x_api_key.startswith('sk_'):
        api_key_value = x_api_key

    if api_key_value:
        logger.info(f"[AUTH MIDDLEWARE] Found API key in request")
        try:
            api_key = ApiKey.verify_key(api_key_value)
            if api_key:
                # Load the user associated with this API key (by Kratos ID)
                user = User.query.filter_by(kratos_id=api_key.user_id).first()
                if user:
                    g.user = user
                    g.api_key = api_key
                    g.auth_method = 'api_key'
                    logger.info(f"[AUTH MIDDLEWARE] Authenticated via API key for user: {user.email}")
                    return
                else:
                    logger.warning(f"[AUTH MIDDLEWARE] API key valid but user {api_key.user_id} not found")
            else:
                logger.warning(f"[AUTH MIDDLEWARE] Invalid API key provided")
        except Exception as e:
            logger.error(f"[AUTH MIDDLEWARE] Error verifying API key: {e}")

    # Check for Kratos session cookie or token
    # Try multiple possible cookie names that Kratos might use
    session_cookie = (
        request.cookies.get('ory_kratos_session') or
        request.cookies.get('ory_session') or
        request.cookies.get('kratos_session') or
        request.cookies.get('ory_session_cookie')
    )

    # Check for session tokens in headers (but only if not an API key)
    session_token = request.headers.get('X-Session-Token')
    if not session_token and auth_header.startswith('Bearer ') and not auth_header.startswith('Bearer sk_'):
        # This is a session token, not an API key
        session_token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Find which cookie name was actually used for better logging
    cookie_name = None
    for name in ['ory_kratos_session', 'ory_session', 'kratos_session', 'ory_session_cookie']:
        if request.cookies.get(name):
            cookie_name = name
            break
    
    logger.info(f"Session cookie found: {bool(session_cookie)}, cookie name: {cookie_name}")
    
    if not session_cookie and not session_token:
        logger.info(f"[AUTH MIDDLEWARE] No Kratos session cookie or token found for {request.path}")
        
        # FALLBACK: Check Flask session for WebAuthn authentication
        if session.get('user_id') and session.get('auth_method') == 'enhanced_webauthn':
            logger.info(f"[AUTH MIDDLEWARE] Found Flask session for WebAuthn auth")
            try:
                user_id = session.get('user_id')
                user = User.query.get(user_id)
                if user:
                    g.user = user
                    logger.info(f"[AUTH MIDDLEWARE] Loaded user {user.email} from Flask session (WebAuthn)")
                    return
                else:
                    logger.warning(f"[AUTH MIDDLEWARE] User ID {user_id} not found in database")
            except Exception as e:
                logger.error(f"[AUTH MIDDLEWARE] Error loading user from Flask session: {e}")
        
        return
    
    # Use token if no cookie
    session_credential = session_cookie or session_token
    
    try:
        # Get identity from Kratos (timeout is handled in the whoami function itself)
        logger.info(f"[AUTH MIDDLEWARE] Calling Kratos whoami with credential")
        identity_data = whoami(session_credential, is_token=(session_token is not None))
        
        logger.info(f"[AUTH MIDDLEWARE] Kratos response: {identity_data}")
        
        # ENHANCED: Check if response contains AAL2 error before proceeding
        if identity_data and isinstance(identity_data, dict) and 'error' in identity_data:
            error_info = identity_data.get('error', {})
            if error_info.get('id') == 'session_aal2_required' or 'aal2' in str(error_info).lower():
                logger.info("[AUTH MIDDLEWARE] Kratos AAL2 error detected in response, falling back to Flask session")
                
                # Try Flask session fallback for WebAuthn authentication
                if session.get('user_id') and session.get('auth_method') == 'enhanced_webauthn':
                    logger.info(f"[AUTH MIDDLEWARE] Found Flask session for WebAuthn auth (AAL2 response fallback)")
                    try:
                        user_id = session.get('user_id')
                        user = User.query.get(user_id)
                        if user:
                            g.user = user
                            logger.info(f"[AUTH MIDDLEWARE] Loaded user {user.email} from Flask session (AAL2 response fallback)")
                            return
                        else:
                            logger.warning(f"[AUTH MIDDLEWARE] User ID {user_id} not found in database (AAL2 response fallback)")
                    except Exception as flask_error:
                        logger.error(f"[AUTH MIDDLEWARE] Error loading user from Flask session (AAL2 response fallback): {flask_error}")
        
        if not identity_data or not identity_data.get('identity'):
            logger.info("[AUTH MIDDLEWARE] No valid Kratos identity found")
            return
        
        identity = identity_data['identity']
        g.identity = identity
        g.session_data = identity_data  # Store full session data including AAL
        logger.info(f"[AUTH MIDDLEWARE] Got identity: {identity.get('id')}, email: {identity.get('traits', {}).get('email')}")
        
        # Get or create user from Kratos identity
        user = UserService.get_or_create_user_from_kratos(identity)
        g.user = user
        
        logger.info(f"[AUTH MIDDLEWARE] Loaded user {user.email} with ID {user.id} from Kratos session")
    except Exception as e:
        logger.error(f"Error loading user from session: {e}", exc_info=True)
        
        # ENHANCED: Check for AAL2 errors and fall back to Flask sessions
        error_msg = str(e).lower()
        if 'aal2' in error_msg or 'authenticator assurance level' in error_msg or '403' in error_msg:
            logger.info("[AUTH MIDDLEWARE] Kratos AAL2 error detected, falling back to Flask session")
            
            # Try Flask session fallback for WebAuthn authentication
            if session.get('user_id') and session.get('auth_method') == 'enhanced_webauthn':
                logger.info(f"[AUTH MIDDLEWARE] Found Flask session for WebAuthn auth (AAL2 fallback)")
                try:
                    user_id = session.get('user_id')
                    user = User.query.get(user_id)
                    if user:
                        g.user = user
                        logger.info(f"[AUTH MIDDLEWARE] Loaded user {user.email} from Flask session (AAL2 fallback)")
                        return
                    else:
                        logger.warning(f"[AUTH MIDDLEWARE] User ID {user_id} not found in database (AAL2 fallback)")
                except Exception as flask_error:
                    logger.error(f"[AUTH MIDDLEWARE] Error loading user from Flask session (AAL2 fallback): {flask_error}")
        
        g.user = None
        g.identity = None
        g.kratos_identity = None


def get_2fa_requirements(role):
    """
    Get 2FA requirements based on user role - INDUSTRY STANDARD MODEL
    
    Returns:
        dict: Requirements for the role
    """
    if role == 'admin':
        return {
            "required_factors": ["webauthn OR totp"],
            "description": "Admins require either Passkey or TOTP for enhanced security (industry standard)"
        }
    else:
        return {
            "required_factors": ["webauthn OR totp"],  # Changed from "optional"
            "description": "STING requires either Passkey or TOTP for secure AI operations"
        }


def check_admin_credentials(identity, require_all_factors=False):
    """
    Check if an identity has the required credentials set up.
    For admin users, both TOTP and WebAuthn must be configured.
    For regular users, only WebAuthn is required.
    
    Args:
        identity: The Kratos identity object
        require_all_factors: If True, requires TOTP + WebAuthn + Password (3FA)
                           If False, checks based on role requirements
    
    Returns:
        dict: {"has_totp": bool, "has_webauthn": bool, "has_password": bool, "needs_setup": bool, "missing_factors": list}
    """
    if not identity:
        return {"has_totp": False, "has_webauthn": False, "needs_setup": False}
    
    # Get user role
    traits = identity.get('traits', {})
    user_role = traits.get('role', 'user')
    logger.info(f"🔍 User role check: email={traits.get('email', 'unknown')}, role='{user_role}', traits={traits}")
    
    # Since whoami doesn't return credentials, we need to fetch the full identity
    identity_id = identity.get('id')
    if identity_id:
        try:
            # Make admin API call to get full identity with credentials
            kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'https://kratos:4434')
            response = requests.get(
                f"{kratos_admin_url}/admin/identities/{identity_id}",
                verify=False,
                timeout=5
            )
            if response.status_code == 200:
                full_identity = response.json()
                credentials = full_identity.get('credentials', {})
            else:
                logger.warning(f"Failed to fetch full identity: {response.status_code}")
                credentials = {}
        except Exception as e:
            logger.error(f"Error fetching full identity: {e}")
            credentials = {}
    else:
        credentials = identity.get('credentials', {})
    
    # Check TOTP setup
    has_totp = 'totp' in credentials and bool(credentials.get('totp', {}).get('identifiers', []))
    
    # Check WebAuthn setup  
    has_webauthn = 'webauthn' in credentials and bool(credentials.get('webauthn', {}).get('identifiers', []))
    
    # Check Password setup (admin should have this, but check to be complete)
    has_password = 'password' in credentials and bool(credentials.get('password', {}).get('identifiers', []))
    
    # Determine missing factors
    missing_factors = []
    if not has_password:
        missing_factors.append('password')
    if not has_totp:
        missing_factors.append('totp')
    if not has_webauthn:
        missing_factors.append('webauthn')
    
    # Check requirements based on role - INDUSTRY STANDARD MODEL
    if user_role == 'admin':
        # UPDATED: Admins need EITHER TOTP OR WebAuthn (GitHub/AWS standard)
        # This follows industry best practices: passwordless + one second factor + recovery codes
        if require_all_factors:
            # Full 3FA: Password + TOTP + WebAuthn (rarely used)
            needs_setup = not (has_totp and has_webauthn and has_password)
            logger.info(f"Admin 3FA check for {traits.get('email')}: Password={has_password}, TOTP={has_totp}, WebAuthn={has_webauthn}, needs_setup={needs_setup}")
        else:
            # Industry standard: Passwordless + (TOTP OR WebAuthn) = 2FA
            # Changed from AND to OR - follows GitHub, AWS, Google patterns
            needs_setup = not (has_totp or has_webauthn)
            logger.info(f"Admin 2FA enforcement (industry standard) for {traits.get('email')}: TOTP={has_totp}, WebAuthn={has_webauthn}, needs_setup={needs_setup}")
    else:
        # STING SECURITY MODEL: All users need 2FA for AI operations (matches AAL middleware)
        needs_setup = not (has_totp or has_webauthn)  # Require at least one 2FA method
        logger.info(f"User 2FA enforcement for {traits.get('email')}: TOTP={has_totp}, WebAuthn={has_webauthn}, needs_setup={needs_setup}")
    
    return {
        "has_totp": has_totp,
        "has_webauthn": has_webauthn,
        "has_password": has_password,
        "needs_setup": needs_setup,
        "missing_factors": missing_factors,
        "role": user_role
    }


def enforce_passkey_only():
    """
    Enforce passkey-only authentication for sensitive operations.
    Used for reporting functions and viewing sensitive data.
    More user-friendly than full 3FA.
    """
    from flask import request, jsonify, g, redirect
    
    if not hasattr(g, 'user') or not g.user:
        logger.info("⚪ Skipping passkey enforcement - no authenticated user")
        return
    
    # Skip for certain paths (to avoid redirect loops)
    skip_paths = [
        '/logout',
        '/api/health', 
        '/api/auth/',
        '/dashboard/settings/security',
        '/dashboard/security-setup',
        '/.ory/',
        '/static/',
        '/favicon.ico'
    ]
    
    if any(request.path.startswith(path) for path in skip_paths):
        return
    
    # Check if user has passkey (WebAuthn) set up
    cred_status = check_admin_credentials(g.identity, require_all_factors=False)
    
    if not cred_status["has_webauthn"]:
        logger.warning(f"User {g.user.email} missing required passkey for sensitive operation")
        
        # For API requests, return JSON error
        if request.path.startswith('/api/') or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                "error": "PASSKEY_REQUIRED",
                "message": "This operation requires passkey authentication for security",
                "redirect_url": "/enrollment",
                "missing_factors": ["webauthn"]
            }), 403
        
        # For web requests, redirect to enrollment
        return redirect('/enrollment')


def check_biometric_or_aal2_for_api():
    """
    Check biometric verification first, fall back to AAL2 if needed

    This implements the biometric-first security model:
    1. Check for recent biometric verification (30 minutes)
    2. If no biometric, check traditional AAL2 (15 minutes)
    3. Return appropriate error response if neither is satisfied

    Returns:
        Response object if verification required, None if allowed to proceed
    """
    try:
        # Get current user
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'AUTHENTICATION_REQUIRED',
                'message': 'You must be logged in to access this resource',
                'code': 'NOT_AUTHENTICATED'
            }), 401

        user_id = g.user.id
        user_email = g.user.email

        logger.info(f"🔐 Biometric-first API check for {user_email} on {request.path}")

        # Import AAL2 manager
        from app.decorators.aal2 import aal2_manager

        # 1. Check biometric verification first (30 minute window)
        biometric_status = aal2_manager.check_biometric_verified(user_id)

        if biometric_status['verified']:
            logger.info(f"✅ Biometric verification satisfied for {user_email}")
            # Store in g for request context
            g.biometric_verified = True
            g.verification_method = 'biometric'
            return None  # Allow request to proceed

        # 2. Check enrollment status - user needs 2FA configured
        enrollment_status = aal2_manager.check_passkey_enrollment(user_id)

        if not enrollment_status['enrolled']:
            logger.warning(f"User {user_email} needs 2FA enrollment for API access")
            return jsonify({
                'error': 'TWO_FACTOR_ENROLLMENT_REQUIRED',
                'message': 'This API requires two-factor authentication. Please set up TOTP or a passkey first.',
                'code': 'MISSING_2FA',
                'enrollment_url': enrollment_status['enrollment_url']
            }), 403

        # 3. Fall back to traditional AAL2 check (TOTP)
        aal2_status = aal2_manager.check_aal2_verified(user_id)

        if aal2_status['verified']:
            logger.info(f"✅ AAL2 verification satisfied for {user_email}")
            # Store in g for request context
            g.aal2_verified = True
            g.verification_method = 'aal2'
            g.aal2_method = aal2_status['method']
            return None  # Allow request to proceed

        # 4. Neither biometric nor AAL2 satisfied - require step-up
        logger.warning(f"User {user_email} needs step-up authentication for {request.path}")
        return jsonify({
            'error': 'STEP_UP_AUTHENTICATION_REQUIRED',
            'message': 'This operation requires additional verification. Use biometric authentication or enter your TOTP code.',
            'code': 'STEP_UP_REQUIRED',
            'options': {
                'biometric_available': True,
                'totp_available': True,
                'preferred_method': 'biometric'
            },
            'biometric_reason': biometric_status.get('reason'),
            'aal2_reason': aal2_status.get('reason')
        }), 403

    except Exception as e:
        logger.error(f"Error in biometric-first API check: {str(e)}")
        return jsonify({
            'error': 'SECURITY_CHECK_FAILED',
            'message': 'Unable to verify security level. Please try again.',
            'code': 'SYSTEM_ERROR'
        }), 500


def check_aal2_for_api_only():
    """
    IMPROVED: Check AAL2 for API endpoints only - returns JSON errors only
    No redirects, just proper API error responses for frontend handling
    """
    from flask import request, jsonify, g
    
    # Only check API endpoints
    if not request.path.startswith('/api/'):
        return
    
    if not hasattr(g, 'user') or not g.user:
        return  # Already handled by other auth middleware
    
    # Define sensitive API operations that require AAL2
    sensitive_api_paths = [
        '/api/reports',
        '/api/bee-reports', 
        '/api/admin'
    ]
    
    # Check if current API path requires AAL2
    requires_aal2 = any(request.path.startswith(path) for path in sensitive_api_paths)
    if not requires_aal2:
        return
    
    # Get current AAL level from session data
    current_aal = 'aal1'  # default
    if hasattr(g, 'session_data') and g.session_data:
        current_aal = g.session_data.get('authenticator_assurance_level', 'aal1')
    
    # Check if user has 2FA methods configured
    cred_status = check_admin_credentials(g.identity)
    user_role = cred_status.get("role", "user")
    
    logger.info(f"🔒 API AAL2 check for {request.path}: current_aal={current_aal}, user_role={user_role}, has_2fa={not cred_status['needs_setup']}")
    
    # If user doesn't have 2FA setup
    if cred_status["needs_setup"]:
        logger.warning(f"API request from {g.user.email} missing 2FA for sensitive operation")
        return jsonify({
            "error": "2FA_SETUP_REQUIRED",
            "message": "This operation requires 2FA setup for security",
            "code": "MISSING_2FA",
            "missing_factors": cred_status["missing_factors"]
        }), 403
    
    # SIMPLIFIED: Check for recent confirmation (AAL2 OR recent passkey use) instead of strict AAL2
    from flask import session as flask_session

    # Check multiple sources of "recent confirmation"
    aal2_verified = flask_session.get('aal2_verified', False)
    custom_aal2_verified = flask_session.get('custom_aal2_verified', False)

    # Check Redis for recent confirmation
    redis_confirmed = False
    try:
        import redis
        redis_client = redis.from_url('redis://redis:6379/0')
        redis_key = f"sting:custom_aal2:{g.user.id}"
        redis_confirmed = bool(redis_client.get(redis_key))
    except:
        redis_confirmed = False

    # Accept either AAL2 OR recent confirmation
    has_recent_confirmation = current_aal == 'aal2' or aal2_verified or custom_aal2_verified or redis_confirmed

    if not has_recent_confirmation:
        logger.warning(f"API request from {g.user.email} needs confirmation for sensitive operation")
        return jsonify({
            "error": "CONFIRMATION_REQUIRED",
            "message": "Please confirm it's you to continue",
            "code": "CONFIRM_IDENTITY",
            "current_aal": current_aal,
            "required_aal": "aal2",
            "action": "frontend_step_up"  # Tell frontend to handle the step-up
        }), 403
    
    logger.info(f"✅ API AAL2 requirement satisfied for {g.user.email}")


def enforce_2fa():
    """
    Middleware to enforce 2FA for all users based on their role.
    - Regular users: WebAuthn/Passkey OR TOTP
    - Admin users: WebAuthn/Passkey OR TOTP (industry standard)
    Must be called after load_user_from_session().
    """
    logger.info(f"🔒 enforce_2fa called for path: {request.path}")
    
    # Skip for non-authenticated users
    if not g.user or not g.identity:
        logger.info("⚪ Skipping 2FA enforcement - no authenticated user")
        return
    
    # CRITICAL FIX: Skip for certain paths (to avoid redirect loops)
    skip_paths = [
        '/logout',
        '/api/health', 
        '/api/auth/',
        '/api/auth/2fa-status',  # Allow checking status
        '/enrollment',  # Allow access to enrollment page
        '/settings',    # CRITICAL: Allow access to settings during setup
        '/.ory/',       # Allow Kratos endpoints
        '/static/',
        '/favicon.ico'
    ]
    
    if any(request.path.startswith(path) for path in skip_paths):
        logger.info(f"⚪ Skipping 2FA enforcement for whitelisted path: {request.path}")
        return
    
    # CRITICAL FIX: Check for session refresh indicators to prevent redirect loops
    user_agent = request.headers.get('User-Agent', '')
    referer = request.headers.get('Referer', '')
    
    # Detect if this is a session refresh or navigation from enrollment/settings
    is_session_refresh = (
        referer.endswith('/enrollment') or 
        referer.endswith('/settings') or 
        '/settings' in referer or
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'  # AJAX request
    )
    
    if is_session_refresh:
        logger.info(f"⚪ Skipping 2FA enforcement - detected session refresh from: {referer}")
        return
    
    # CRITICAL FIX: Add grace period after credential setup
    # Check if we're within a grace period after recent authentication
    current_time = time.time()
    last_auth_time = session.get('last_2fa_check', 0)
    grace_period = 60  # 60 seconds grace period
    
    if current_time - last_auth_time < grace_period:
        logger.info(f"⚪ Skipping 2FA enforcement - within grace period ({grace_period}s)")
        return
    
    # Check credentials based on user role
    cred_status = check_admin_credentials(g.identity)
    user_role = cred_status.get("role", "user")
    
    if cred_status["needs_setup"]:
        requirements = get_2fa_requirements(user_role)
        logger.warning(f"{user_role.title()} user {g.user.email} missing required 2FA: {requirements['required_factors']}")
        
        # For API requests, return JSON error
        if request.path.startswith('/api/') or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                "error": "2FA_SETUP_REQUIRED",
                "message": requirements['description'],
                "redirect_url": "/enrollment",
                "role": user_role,
                "required_factors": requirements['required_factors'],
                "missing_factors": cred_status["missing_factors"]
            }), 403
        
        # For web requests, redirect to enrollment page
        logger.info(f"🔒 Redirecting {user_role} user to enrollment: missing {cred_status['missing_factors']}")
        return redirect('/enrollment')
    else:
        # CRITICAL FIX: Set grace period timestamp when 2FA check passes
        session['last_2fa_check'] = current_time
        logger.info(f"✅ 2FA enforcement passed for {user_role} user {g.user.email}")


def require_admin(f):
    """Decorator to require admin privileges"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user exists in g.user (set by auth middleware)
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not g.user.is_admin and not g.user.is_super_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

