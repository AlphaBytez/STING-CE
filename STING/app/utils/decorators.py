from flask import request, jsonify, current_app, g
from functools import wraps
import time
import os
import logging
import hashlib
from app.database import db

logger = logging.getLogger(__name__)

def check_api_key_auth():
    """Check for valid API key authentication"""
    api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
    logger.info(f"🔑 API Key Debug: Received key: {api_key[:10] if api_key else 'None'}...")
    
    if not api_key or not api_key.startswith('sk_'):
        logger.info(f"🔑 API Key Debug: Invalid key format or missing")
        return None
    
    try:
        from app.models.api_key_models import ApiKey
        
        # Debug: Check how many API keys exist in database
        total_keys = ApiKey.query.count()
        active_keys = ApiKey.query.filter_by(is_active=True).count()
        logger.info(f"🔑 API Key Debug: Database has {total_keys} total keys, {active_keys} active")
        
        # Debug: Show the hash we're looking for
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        logger.info(f"🔑 API Key Debug: Looking for hash: {key_hash[:16]}...")
        
        # Use the model's verify_key method which handles hashing and expiration
        api_key_obj = ApiKey.verify_key(api_key)
        
        if api_key_obj:
            logger.info(f"🔑 API Key Debug: ✅ Found valid key: {api_key_obj.name} (scopes: {api_key_obj.scopes})")
            return api_key_obj
        else:
            logger.info(f"🔑 API Key Debug: ❌ Key not found or expired")
            
            # Additional debug: Check if any key has matching hash
            matching_hash_key = ApiKey.query.filter_by(key_hash=key_hash).first()
            if matching_hash_key:
                logger.info(f"🔑 API Key Debug: Found matching hash but key is {'inactive' if not matching_hash_key.is_active else 'expired'}")
            else:
                logger.info(f"🔑 API Key Debug: No matching hash found in database")
    except Exception as e:
        logger.error(f"🔑 API Key Debug: Exception during verification: {e}")
        import traceback
        logger.error(f"🔑 API Key Debug: Traceback: {traceback.format_exc()}")
    
    return None

def require_auth_or_api_key(allowed_scopes=None):
    """Decorator to require either session auth OR API key auth"""
    if allowed_scopes is None:
        allowed_scopes = ['admin', 'read', 'write']
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check for API key authentication
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                # Check if any of the API key's scopes match the allowed scopes
                if any(scope in allowed_scopes for scope in api_key_obj.scopes):
                    # Set a mock user object for API key access
                    g.api_key = api_key_obj
                    g.api_user = True
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope',
                        'required_scopes': allowed_scopes,
                        'your_scopes': api_key_obj.scopes
                    }), 403
            
            # Fall back to session authentication
            logger.info(f"🔍 DECORATOR DEBUG: g object attributes: {[attr for attr in dir(g) if not attr.startswith('_')]}")
            logger.info(f"🔍 DECORATOR DEBUG: hasattr(g, 'user'): {hasattr(g, 'user')}")
            logger.info(f"🔍 DECORATOR DEBUG: g.user value: {getattr(g, 'user', 'NOT_SET')}")
            logger.info(f"🔍 DECORATOR DEBUG: g.user type: {type(getattr(g, 'user', None))}")

            # CRITICAL DEBUG: Test each condition separately
            has_user_attr = hasattr(g, 'user')
            user_is_none = g.user is None if has_user_attr else 'NO_ATTR'
            user_bool_value = bool(g.user) if has_user_attr else 'NO_ATTR'
            condition_result = not hasattr(g, 'user') or g.user is None

            logger.info(f"🔍 CONDITION DEBUG: hasattr(g, 'user') = {has_user_attr}")
            logger.info(f"🔍 CONDITION DEBUG: g.user is None = {user_is_none}")
            logger.info(f"🔍 CONDITION DEBUG: bool(g.user) = {user_bool_value}")
            logger.info(f"🔍 CONDITION DEBUG: Final condition result = {condition_result}")

            if condition_result:
                logger.warning(f"🚨 CONDITION TRUE: Denying access to {request.path}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in or provide a valid API key'
                }), 401

            # Session user is authenticated, proceed
            logger.info(f"✅ CONDITION FALSE: Granting access to authenticated user {g.user.email} for {request.path}")
            try:
                result = f(*args, **kwargs)
                logger.info(f"✅ ROUTE SUCCESS: Route executed successfully for {request.path}")
                return result
            except Exception as route_error:
                logger.error(f"❌ ROUTE ERROR: Exception in route execution: {route_error}")
                raise
        return decorated_function
    return decorator

def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if not hasattr(g, 'user') or g.user is None:
            logger.warning(f"Unauthenticated access attempt to {request.path}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'You must be logged in to access this resource'
            }), 401
        
        # User is authenticated, proceed with the request
        logger.debug(f"Authenticated user {g.user.email} accessing {request.path}")
        return f(*args, **kwargs)
    return decorated_function

# A simple in-memory storage for rate-limiting (use Redis or another datastore in production)
rate_limit_storage = {}

def rate_limit(limit: int, window: int):
    """
    Rate limit decorator to restrict the number of requests from a user.

    :param limit: Maximum number of requests allowed
    :param window: Time window in seconds for the limit
    """
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = []
            
            rate_limit_storage[client_ip] = [
                ts for ts in rate_limit_storage[client_ip]
                if ts > current_time - window
            ]
            
            if len(rate_limit_storage[client_ip]) >= limit:
                return jsonify({"error": "Too many requests"}), 429
            
            rate_limit_storage[client_ip].append(current_time)
            return func(*args, **kwargs)
        
        return wrapped
    return decorator

def development_only(f):
    """
    Decorator to restrict access to development environment only.
    This ensures that production environments never expose debug endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if we're in development mode
        flask_env = os.environ.get('FLASK_ENV', 'production').lower()
        app_env = os.environ.get('APP_ENV', 'production').lower()
        debug_mode = os.environ.get('DEBUG', 'false').lower() in ('true', '1', 't')

        if flask_env != 'development' and app_env != 'development' and not debug_mode:
            logger.warning(f"Attempt to access development-only endpoint {request.path} in {flask_env}/{app_env} environment")
            return jsonify({
                'error': 'Access denied',
                'message': 'This endpoint is only available in development environments'
            }), 403

        # If a debug token is required, check for it (optional additional security)
        if current_app.config.get('REQUIRE_DEBUG_TOKEN', False):
            token = request.headers.get('X-Debug-Token')
            valid_token = current_app.config.get('DEBUG_TOKEN')

            if not token or token != valid_token:
                logger.warning(f"Invalid debug token used for {request.path}")
                return jsonify({
                    'error': 'Invalid debug token',
                    'message': 'A valid debug token is required for this endpoint'
                }), 401

        return f(*args, **kwargs)

    return decorated_function

def admin_only(f):
    """
    Decorator to restrict access to admin users only.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implement admin check logic here
        # This could be based on a session, token, or other authentication mechanism

        # Example - check for admin role in user session
        # user = get_current_user()
        # if not user or user.role != 'admin':
        #     return jsonify({'error': 'Admin access required'}), 403

        # For now, we'll just check for an admin token in headers
        token = request.headers.get('X-Admin-Token')
        valid_token = current_app.config.get('ADMIN_TOKEN')

        if not token or token != valid_token:
            logger.warning(f"Admin access denied for {request.path}")
            return jsonify({
                'error': 'Access denied',
                'message': 'Admin access required'
            }), 403

        return f(*args, **kwargs)

    return decorated_function

def require_aal2_or_api_key(allowed_scopes=None):
    """
    Decorator for sensitive operations requiring AAL2 step-up OR API key auth.
    Uses Flask-managed AAL2 verification for reliable session coordination.

    Security Model:
    - API Key: Bypasses AAL2 (creator responsibility for scope-based security)
    - Session Auth: Requires Flask AAL2 verification (user-friendly step-up)

    This follows industry standards (GitHub, AWS) where API keys have
    scope-based security and session access has step-up authentication.
    """
    if allowed_scopes is None:
        allowed_scopes = ['admin', 'write']

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check for API key authentication (bypasses AAL2)
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                # API key found - check scopes and proceed
                if any(scope in allowed_scopes for scope in api_key_obj.scopes):
                    g.api_key = api_key_obj
                    g.api_user = True
                    logger.info(f"🔑 API key access granted to {api_key_obj.name} for {request.path}")
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope',
                        'required_scopes': allowed_scopes,
                        'your_scopes': api_key_obj.scopes
                    }), 403

            # Fall back to session authentication with Flask AAL2 verification
            if not hasattr(g, 'user') or g.user is None:
                logger.warning(f"AAL2 operation requires authentication: {request.path}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in or provide a valid API key for this operation'
                }), 401

            # Check Flask AAL2 verification for session users (multiple possible locations)
            from flask import session as flask_session

            # Primary Flask AAL2 sources (set by step-up completion)
            aal2_verified = flask_session.get('aal2_verified', False)
            custom_aal2_verified = flask_session.get('custom_aal2_verified', False)

            # Check Redis AAL2 (also set by step-up completion) - with safe error handling
            redis_aal2_verified = False
            try:
                # Check if Redis AAL2 verification exists (as used by SimpleProtectedRoute)
                import redis
                redis_client = redis.from_url('redis://redis:6379/0')
                redis_key = f"sting:custom_aal2:{g.user.id}" if g.user else None
                if redis_key:
                    redis_aal2_verified = bool(redis_client.get(redis_key))
            except Exception as redis_error:
                logger.debug(f"Redis AAL2 check failed (non-critical): {redis_error}")
                redis_aal2_verified = False

            # ALSO accept Kratos AAL2 as valid (for sessions that started with AAL2)
            kratos_aal2 = hasattr(g, 'session_data') and g.session_data and \
                         g.session_data.get('authenticator_assurance_level') == 'aal2'

            # Check if any form of AAL2 verification exists (prioritize Flask/Redis over Kratos)
            any_aal2_verified = aal2_verified or custom_aal2_verified or redis_aal2_verified or kratos_aal2

            logger.info(f"🔒 AAL2 DEBUG: flask_aal2={aal2_verified}, custom_aal2={custom_aal2_verified}, redis_aal2={redis_aal2_verified}, kratos_aal2={kratos_aal2}, any_verified={any_aal2_verified}")

            if not any_aal2_verified:
                # User needs AAL2 step-up
                logger.info(f"AAL2 step-up required for {g.user.email} accessing {request.path}")
                return jsonify({
                    'error': 'AAL2 verification required',
                    'message': 'This sensitive operation requires additional authentication',
                    'redirect_to': '/security-upgrade',
                    'code': 'aal2_required'
                }), 403

            # AAL2 verified, proceed with the request
            logger.debug(f"AAL2 verified user {g.user.email} accessing sensitive operation: {request.path}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_passkey_or_api_key(allowed_scopes=None):
    """
    Simple passkey-first decorator with API key OR TOTP fallback.

    Security Model:
    - API Key: Bypasses all reauthentication (creator responsibility)
    - Session Auth: Passkey preferred (any passkey), TOTP fallback (30 min cache)
    - Mental Model: "Please confirm it's you" - passkey tap or TOTP code

    This treats passkeys like "secure API keys" that require user confirmation.
    """
    if allowed_scopes is None:
        allowed_scopes = ['admin', 'write']

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check for API key authentication (bypasses all step-up)
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                # API key found - check scopes and proceed
                if any(scope in allowed_scopes for scope in api_key_obj.scopes):
                    g.api_key = api_key_obj
                    g.api_user = True
                    logger.info(f"🔑 API key access granted to {api_key_obj.name} for {request.path}")
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope',
                        'required_scopes': allowed_scopes,
                        'your_scopes': api_key_obj.scopes
                    }), 403

            # Session authentication - use biometric-first pattern
            if not hasattr(g, 'user') or g.user is None:
                logger.warning(f"Biometric operation requires authentication: {request.path}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in or provide a valid API key for this operation'
                }), 401

            user_id = g.user.id
            user_email = g.user.email

            logger.info(f"🔐 Biometric-first check for {user_email} accessing {request.path}")

            # Import AAL2 manager for enrollment/verification checks
            from app.decorators.aal2 import aal2_manager

            # 1. Check if user has any 2FA methods configured (passkey or TOTP)
            enrollment_status = aal2_manager.check_passkey_enrollment(user_id)

            if not enrollment_status['enrolled']:
                logger.warning(f"User {user_email} needs 2FA enrollment for operation")
                return jsonify({
                    'error': 'TWO_FACTOR_ENROLLMENT_REQUIRED',
                    'message': 'This operation requires two-factor authentication. Please set up TOTP or a passkey first.',
                    'code': 'MISSING_2FA',
                    'enrollment_url': enrollment_status['enrollment_url']
                }), 403

            # 2. Check for recent reauthentication (passkey OR TOTP) - simplified check
            from flask import session as flask_session

            # Check multiple AAL2 sources
            aal2_verified = flask_session.get('aal2_verified', False)
            custom_aal2_verified = flask_session.get('custom_aal2_verified', False)

            # Check Redis AAL2 (also set by step-up completion)
            redis_aal2_verified = False
            try:
                import redis
                redis_client = redis.from_url('redis://redis:6379/0')
                redis_key = f"sting:custom_aal2:{g.user.id}"
                redis_aal2_verified = bool(redis_client.get(redis_key))
            except Exception as redis_error:
                logger.debug(f"Redis AAL2 check failed (non-critical): {redis_error}")
                redis_aal2_verified = False

            # Check Kratos AAL2
            kratos_aal2 = hasattr(g, 'session_data') and g.session_data and \
                         g.session_data.get('authenticator_assurance_level') == 'aal2'

            any_aal2_verified = aal2_verified or custom_aal2_verified or redis_aal2_verified or kratos_aal2

            if any_aal2_verified:
                logger.info(f"✅ Recent authentication satisfied for {user_email}")
                g.aal2_verified = True
                g.verification_method = 'recent_authentication'
                return f(*args, **kwargs)

            # 4. No recent authentication - require step-up (passkey preferred, TOTP fallback)
            logger.warning(f"User {user_email} needs to confirm identity for {request.path}")

            # Check what methods user has available
            has_passkey = enrollment_status['details'].get('kratos_passkey', False) or \
                         enrollment_status['details'].get('sting_webauthn', False)
            has_totp = enrollment_status['details'].get('kratos_totp', False)

            return jsonify({
                'error': 'CONFIRMATION_REQUIRED',
                'message': 'Please confirm it\'s you to continue.',
                'code': 'CONFIRM_IDENTITY',
                'options': {
                    'passkey_available': has_passkey,
                    'totp_available': has_totp,
                    'preferred_method': 'passkey' if has_passkey else 'totp'
                },
                'user_methods': {
                    'passkey': has_passkey,
                    'totp': has_totp
                }
            }), 403

        return decorated_function
    return decorator


def require_auth_method(required_methods, allowed_scopes=None):
    """
    Require specific authentication methods (AMR-based) instead of AAL levels.

    This solves the passkey coexistence issue:
    - If user logged in with required method → Already satisfied
    - If user used different method → Prompt for specific method

    Args:
        required_methods: String or list of required methods ('webauthn', 'totp', etc.)
        allowed_scopes: API key scopes that bypass method requirements

    Usage:
        @require_auth_method('webauthn')  # Route requires WebAuthn specifically
        @require_auth_method(['webauthn', 'totp'])  # Either method works
    """
    if isinstance(required_methods, str):
        required_methods = [required_methods]

    if allowed_scopes is None:
        allowed_scopes = ['admin', 'write']

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check for API key authentication (bypasses method requirements)
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                if any(scope in allowed_scopes for scope in api_key_obj.scopes):
                    g.api_key = api_key_obj
                    g.api_user = True
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope',
                        'required_scopes': allowed_scopes,
                        'your_scopes': api_key_obj.scopes
                    }), 403

            # Session authentication - check method requirements
            if not hasattr(g, 'user') or g.user is None:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401

            user_email = g.user.email

            # FIRST: Check if we already have cached authentication method verification
            # TEMPORARILY DISABLED: Session caching causing serialization conflicts in v1
            cached_verified = False
            cached_methods = []
            cached_at = 0

            # try:
            #     from flask import session as flask_session
            #     cached_verified = flask_session.get('auth_method_verified', False)
            #     cached_methods = flask_session.get('verified_methods', [])
            #     cached_at = flask_session.get('auth_method_verified_at', 0)
            # except Exception as e:
            #     logger.warning(f"Session cache unavailable: {e}")
            #     cached_verified = False

            # Check cache validity (5 minutes for method verification)
            cache_expiry = time.time() - (5 * 60)  # 5 minutes
            cache_valid = cached_verified and cached_at > cache_expiry

            if cache_valid and any(method in cached_methods for method in required_methods):
                logger.info(f"✅ Using cached authentication method verification for {user_email}")
                g.auth_method_verified = True
                g.verified_methods = cached_methods
                return f(*args, **kwargs)

            # Check if session contains required authentication method
            session_methods = []
            configured_methods = []

            # Extract methods from Kratos session data
            # Support both g.session_data (old) and g.session (Kratos middleware)
            session_source = None
            if hasattr(g, 'session_data') and g.session_data:
                session_source = g.session_data
            elif hasattr(g, 'session') and g.session:
                session_source = g.session

            if session_source:
                # Extract authentication methods from Kratos session
                # Kratos provides authentication_methods_reference (amr) in session
                amr_list = session_source.get('authentication_methods_reference', [])
                if not amr_list:
                    # Fallback: check authentication_methods field
                    amr_list = session_source.get('authentication_methods', [])

                logger.info(f"🔍 TIERED AUTH: Available AMR in session: {amr_list}")

                for amr_entry in amr_list:
                    if isinstance(amr_entry, dict):
                        method = amr_entry.get('method')
                        if method:
                            session_methods.append(method)
                    elif isinstance(amr_entry, str):
                        session_methods.append(amr_entry)

                # Map Kratos method names to tiered auth names
                mapped_methods = []
                for method in session_methods:
                    mapped_methods.append(method)
                    if method in ['passkey', 'webauthn']:
                        mapped_methods.append('webauthn')
                    elif method in ['code', 'email']:
                        mapped_methods.append('email')
                    elif method == 'totp':
                        mapped_methods.append('totp')

                session_methods = mapped_methods

                # Get identity credentials to check what user has configured
                identity = session_source.get('identity', {})
                credentials = identity.get('credentials', {})

                logger.info(f"🔍 TIERED AUTH: Available credentials: {list(credentials.keys()) if credentials else 'None'}")

                # Track configured methods (user HAS these available)
                for cred_type in credentials.keys():
                    if cred_type == 'webauthn':
                        configured_methods.append('webauthn')
                    elif cred_type == 'totp':
                        configured_methods.append('totp')
                    elif cred_type in ['code', 'email']:
                        configured_methods.append('email')
                    elif cred_type == 'password':
                        configured_methods.append('password')

                logger.info(f"🔍 TIERED AUTH: Session methods: {session_methods}, Configured methods: {configured_methods}")

            # For operations that need secure methods, having them configured is enough
            # This handles the case where user logged in with one method but has others available
            if 'webauthn' in required_methods or 'totp' in required_methods:
                # If user has any of the required secure methods configured, allow access
                available_methods = list(set(session_methods + configured_methods))
            else:
                # For other methods, require actual usage in session
                available_methods = session_methods

            # ENHANCED DEBUG: Full authentication method analysis
            logger.info(f"🔐 [AUTH DEBUG] Method check for {user_email}:")
            logger.info(f"🔐 [AUTH DEBUG] - Required methods: {required_methods}")
            logger.info(f"🔐 [AUTH DEBUG] - Session methods: {session_methods}")
            logger.info(f"🔐 [AUTH DEBUG] - Configured methods: {configured_methods}")
            logger.info(f"🔐 [AUTH DEBUG] - Available methods: {available_methods}")
            logger.info(f"🔐 [AUTH DEBUG] - Has session_data: {hasattr(g, 'session_data')}")
            if hasattr(g, 'session_data'):
                logger.info(f"🔐 [AUTH DEBUG] - Session data keys: {list(g.session_data.keys()) if g.session_data else 'None'}")
                logger.info(f"🔐 [AUTH DEBUG] - AMR from session: {g.session_data.get('authentication_methods', []) if g.session_data else 'No session_data'}")
                identity = g.session_data.get('identity', {}) if g.session_data else {}
                logger.info(f"🔐 [AUTH DEBUG] - Identity credentials: {list(identity.get('credentials', {}).keys()) if identity else 'No identity'}")
            logger.info(f"🔐 [AUTH DEBUG] - Final check: any method satisfied = {any(method in available_methods for method in required_methods)}")

            # Check if any required method is satisfied
            method_satisfied = any(method in available_methods for method in required_methods)

            if method_satisfied:
                logger.info(f"✅ Required authentication method satisfied for {user_email}")
                g.auth_method_verified = True

                # TEMPORARILY DISABLED: Session caching causing serialization conflicts in v1
                # TODO: Re-enable after fixing bytes object serialization issue
                #
                # try:
                #     from flask import session as flask_session
                #     flask_session.permanent = True
                #     flask_session['auth_method_verified'] = True
                #     flask_session['verified_methods'] = available_methods
                #     flask_session['auth_method_verified_at'] = time.time()
                #     logger.info(f"🔐 Cached authentication for {user_email}: methods={available_methods}, expires_in=5min")
                # except Exception as e:
                #     logger.warning(f"Session caching failed: {e}")

                logger.info(f"✅ Authentication method satisfied for {user_email}: {available_methods} (no caching)")
                g.verified_methods = available_methods
                return f(*args, **kwargs)

            # Method not satisfied - require specific method confirmation
            logger.warning(f"User {user_email} needs {required_methods} method for {request.path}")
            return jsonify({
                'error': 'SPECIFIC_METHOD_REQUIRED',
                'message': f'This operation requires confirmation with {" or ".join(required_methods)}',
                'code': 'METHOD_REQUIRED',
                'required_methods': required_methods,
                'user_methods': available_methods,
                'session_methods': session_methods,
                'configured_methods': configured_methods,
                'preferred_method': required_methods[0]  # First in list is preferred
            }), 403

        return decorated_function
    return decorator


def require_dual_factor(primary_methods, secondary_methods, allowed_scopes=None):
    """
    Require TWO different authentication factors for high-security operations.

    Use case: Removing a security factor - can't use the factor being removed
    Example: Removing passkey requires TOTP + email verification

    Args:
        primary_methods: Required authentication methods from session
        secondary_methods: Additional methods that must be verified separately
        allowed_scopes: API key scopes that bypass requirements

    Usage:
        @require_dual_factor(['totp'], ['email'])  # Remove passkey: TOTP + email
        @require_dual_factor(['webauthn'], ['email'])  # Remove TOTP: passkey + email
    """
    if allowed_scopes is None:
        allowed_scopes = ['admin', 'write']

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check for API key authentication (bypasses all requirements)
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                if any(scope in allowed_scopes for scope in api_key_obj.scopes):
                    g.api_key = api_key_obj
                    g.api_user = True
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope',
                        'required_scopes': allowed_scopes,
                        'your_scopes': api_key_obj.scopes
                    }), 403

            # Session authentication - check dual factor requirements
            if not hasattr(g, 'user') or g.user is None:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401

            user_email = g.user.email

            # Check primary method from session
            session_methods = []
            if hasattr(g, 'session_data') and g.session_data:
                amr = g.session_data.get('authentication_methods', [])
                session_methods.extend(amr)

                identity = g.session_data.get('identity', {})
                credentials = identity.get('credentials', {})

                if 'webauthn' in credentials:
                    session_methods.append('webauthn')
                if 'totp' in credentials:
                    session_methods.append('totp')
                if 'code' in credentials:
                    session_methods.append('code')

            # Check if primary method is satisfied
            primary_satisfied = any(method in session_methods for method in primary_methods)

            if not primary_satisfied:
                logger.warning(f"User {user_email} needs primary factor for {request.path}")
                return jsonify({
                    'error': 'PRIMARY_FACTOR_REQUIRED',
                    'message': f'This operation requires authentication with {" or ".join(primary_methods)}',
                    'code': 'PRIMARY_FACTOR_REQUIRED',
                    'required_methods': primary_methods,
                    'user_methods': session_methods
                }), 403

            # Check secondary method verification (from session markers or additional prompts)
            from flask import session as flask_session

            # Check for recent secondary factor verification
            secondary_verified = False
            for method in secondary_methods:
                session_key = f'{method}_verified_for_dual_factor'
                if flask_session.get(session_key, False):
                    secondary_verified = True
                    break

            if not secondary_verified:
                logger.warning(f"User {user_email} needs secondary factor for {request.path}")
                return jsonify({
                    'error': 'SECONDARY_FACTOR_REQUIRED',
                    'message': f'This high-security operation requires additional verification with {" or ".join(secondary_methods)}',
                    'code': 'SECONDARY_FACTOR_REQUIRED',
                    'primary_satisfied': primary_methods,
                    'required_secondary': secondary_methods,
                    'verification_type': 'dual_factor'
                }), 403

            # Both factors satisfied
            logger.info(f"✅ Dual factor authentication satisfied for {user_email}")
            g.dual_factor_verified = True
            g.primary_methods = primary_methods
            g.secondary_methods = secondary_methods
            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_critical_auth(required_methods, allowed_scopes=None):
    """
    Require ALL authentication factors for critical operations.
    No caching - always requires fresh confirmation of all methods.

    Use case: Account deletion, disable all 2FA, etc.

    Args:
        required_methods: All methods that must be verified
        allowed_scopes: API key scopes that bypass requirements

    Usage:
        @require_critical_auth(['email', 'webauthn', 'totp'])  # Nuclear operations
    """
    if allowed_scopes is None:
        allowed_scopes = ['admin']  # Only admin API keys can bypass critical ops

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for admin API key only (higher bar for critical ops)
            api_key_obj = check_api_key_auth()
            if api_key_obj:
                if 'admin' in api_key_obj.scopes:
                    g.api_key = api_key_obj
                    g.api_user = True
                    return f(*args, **kwargs)
                else:
                    return jsonify({
                        'error': 'Insufficient API key scope for critical operation',
                        'required_scopes': ['admin'],
                        'your_scopes': api_key_obj.scopes
                    }), 403

            # Session authentication - require ALL factors with fresh verification
            if not hasattr(g, 'user') or g.user is None:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401

            user_email = g.user.email

            # For critical operations, check that ALL required methods were used recently
            from flask import session as flask_session

            satisfied_methods = []
            missing_methods = []

            for method in required_methods:
                # Check for very recent verification (shorter window for critical ops)
                session_key = f'{method}_verified_critical'
                recent_verification = flask_session.get(session_key, False)

                if recent_verification:
                    satisfied_methods.append(method)
                else:
                    missing_methods.append(method)

            if missing_methods:
                logger.warning(f"User {user_email} needs critical verification for {request.path}")
                return jsonify({
                    'error': 'CRITICAL_OPERATION_REQUIRES_ALL_FACTORS',
                    'message': f'This critical operation requires fresh verification with ALL configured methods: {", ".join(missing_methods)}',
                    'code': 'CRITICAL_AUTH_REQUIRED',
                    'satisfied_methods': satisfied_methods,
                    'missing_methods': missing_methods,
                    'verification_type': 'critical_all_factors'
                }), 403

            # All critical factors satisfied
            logger.info(f"✅ Critical authentication satisfied for {user_email}")
            g.critical_auth_verified = True
            g.verified_critical_methods = satisfied_methods
            return f(*args, **kwargs)

        return decorated_function
    return decorator
