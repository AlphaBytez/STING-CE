"""
AAL (Authentication Assurance Level) Management Routes
Handles Kratos webhooks and AAL validation for proper multi-factor authentication enforcement
"""

from flask import Blueprint, request, jsonify, session
from flask_cors import cross_origin
import logging
from app.middleware.aal_middleware import AALRequirement, get_current_aal_status
from app.utils.kratos_session import whoami
from app.utils.response_helpers import success_response, error_response

# Configure logging
logger = logging.getLogger(__name__)

aal_bp = Blueprint('aal', __name__)

@aal_bp.route('/api/auth/aal-check', methods=['POST'])
@cross_origin(supports_credentials=True)
def aal_check_webhook():
    """
    Kratos webhook to check AAL requirements after login
    This determines if user needs additional authentication factors
    """
    try:
        # Get webhook data from Kratos
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.error("No webhook data received from Kratos")
            return jsonify({"continue": True}), 200
            
        logger.info(f"🔒 AAL check webhook called with data: {webhook_data.keys()}")
        
        # Extract identity and session information
        identity = webhook_data.get('identity', {})
        session_data = webhook_data.get('session', {})
        
        if not identity:
            logger.error("No identity found in webhook data")
            return jsonify({"continue": True}), 200
            
        # Get user role and email
        traits = identity.get('traits', {})
        user_role = traits.get('role', 'user')
        user_email = traits.get('email', 'unknown')
        
        logger.info(f"🔒 Checking AAL requirements for {user_email} (role: {user_role})")
        
        # Check current authentication assurance level
        current_aal = session_data.get('authenticator_assurance_level', 'aal1')
        auth_methods = session_data.get('authentication_methods', [])
        
        logger.info(f"🔒 Current AAL: {current_aal}, Methods: {[m.get('method') for m in auth_methods]}")
        
        # Get 2FA requirements for this user
        try:
            # Use identity data directly instead of making another call to Kratos
            identity_credentials = identity.get('credentials', {})
            
            # Check what authentication methods the user has configured
            has_totp = bool(identity_credentials.get('totp'))
            has_webauthn = bool(identity_credentials.get('webauthn'))
            has_password = bool(identity_credentials.get('password'))
            
            # Determine missing factors
            missing_factors = []
            if not has_totp:
                missing_factors.append('totp')
            if not has_webauthn:
                missing_factors.append('webauthn')
            
            # Check requirements based on role
            needs_additional_auth = False
            
            if user_role == 'admin':
                # Admins MUST have both TOTP and WebAuthn for AAL2
                if current_aal == 'aal1':
                    # Only completed first factor - need second factor
                    if not (has_totp and has_webauthn):
                        needs_additional_auth = True
                        logger.info(f"🔒 Admin {user_email} needs additional 2FA setup: TOTP={has_totp}, WebAuthn={has_webauthn}")
                    else:
                        # Admin has both factors configured, allow AAL2 progression
                        logger.info(f"🔒 Admin {user_email} has required factors, allowing AAL2 progression")
                elif current_aal == 'aal2':
                    # Already at AAL2, check if all required methods were used
                    used_methods = [m.get('method') for m in auth_methods]
                    # Admin users must have BOTH totp AND webauthn (3FA)
                    if not ('totp' in used_methods and 'webauthn' in used_methods):
                        needs_additional_auth = True
                        logger.info(f"🔒 Admin {user_email} at AAL2 but missing required methods. Used: {used_methods}, Required: ['totp', 'webauthn']")
            else:
                # Regular users need AAL2 with any second factor (passkey preferred)
                if current_aal == 'aal1':
                    if not has_webauthn:
                        needs_additional_auth = True
                        logger.info(f"🔒 User {user_email} needs passkey setup for AAL2")
                    else:
                        logger.info(f"🔒 User {user_email} has passkey, allowing AAL2 progression")
            
            if needs_additional_auth:
                logger.info(f"🔒 User {user_email} needs AAL2 setup - allowing login to complete, will redirect to enrollment")
                
                # Allow login to continue for first-time users
                # The frontend will handle redirecting to enrollment/setup
                return jsonify({
                    "continue": True,
                    "messages": [{
                        "id": 4000011,
                        "text": f"Welcome! Please complete your security setup for {user_role} accounts.",
                        "type": "info",
                        "context": {
                            "requires_enrollment": True,
                            "missing_methods": missing_factors,
                            "user_role": user_role
                        }
                    }]
                }), 200
            else:
                logger.info(f"🔒 Allowing login completion for {user_email} - AAL requirements met")
                
                # Allow login to continue
                return jsonify({"continue": True}), 200
                
        except Exception as e:
            logger.error(f"Error checking 2FA requirements: {str(e)}")
            # On error, allow login to continue to avoid blocking legitimate users
            return jsonify({"continue": True}), 200
            
    except Exception as e:
        logger.error(f"AAL check webhook error: {str(e)}")
        # On error, allow login to continue
        return jsonify({"continue": True}), 200


@aal_bp.route('/api/auth/aal-status', methods=['GET'])
@cross_origin(supports_credentials=True)
def get_aal_status():
    """
    Get current user's AAL status and requirements using proper AAL middleware
    Returns unauthenticated status for login page access (no 401 error)
    """
    try:
        # Use the AAL middleware function for consistent logic
        aal_status = get_current_aal_status()
        
        # Handle unauthenticated users gracefully (important for login page)
        if not aal_status:
            logger.debug("AAL status check for unauthenticated user - returning default status")
            return success_response({
                "authenticated": False,
                "role": None,
                "email": None,
                "current_aal": None,
                "required_aal": None,
                "missing_methods": [],
                "validation": {
                    "valid": False,
                    "current_aal": None,
                    "required_aal": None,
                    "missing_methods": [],
                    "reason": "Not authenticated"
                },
                "requirements": {},
                "can_access_dashboard": False
            })
            
        # Extract validation and requirements for authenticated users
        validation = aal_status.get('validation', {})
        requirements = aal_status.get('requirements', {})
        
        # Determine if user can access dashboard
        # SECURITY FIX: Only allow dashboard access if validation is truly valid
        # Enrollment access should redirect to enrollment, NOT grant dashboard access
        can_access = validation.get('valid', False) and not validation.get('enrollment_allowed', False)
        
        # If enrollment is allowed but validation isn't valid, they need to complete enrollment
        if validation.get('enrollment_allowed', False) and not validation.get('valid', False):
            can_access = False
        
        response_data = {
            "authenticated": aal_status.get('authenticated', False),
            "role": aal_status.get('role', 'user'),
            "email": aal_status.get('email', 'unknown'),
            "current_aal": validation.get('current_aal', 'aal1'),
            "required_aal": validation.get('required_aal', 'aal2'),
            "missing_methods": validation.get('missing_methods', []),
            "validation": validation,
            "requirements": requirements,
            "can_access_dashboard": can_access,
            "configured_methods": aal_status.get('configured_methods', {})  # Include configured methods for frontend
        }
        
        logger.info(f"🔐 AAL status response - configured_methods: {response_data.get('configured_methods')}")
        
        return success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting AAL status: {str(e)}")
        return error_response("Failed to get AAL status", 500)


@aal_bp.route('/api/auth/aal-step-up', methods=['POST'])
@cross_origin(supports_credentials=True)
def initiate_aal_step_up():
    """
    Initiate AAL step-up authentication for users who need additional factors
    """
    try:
        # Get current user session
        session_info = whoami(request)
        
        if not session_info:
            return error_response("Not authenticated", 401)
            
        # Get requested AAL level
        data = request.get_json() or {}
        target_aal = data.get('target_aal', 'aal2')
        
        if target_aal not in ['aal1', 'aal2']:
            return error_response("Invalid AAL level", 400)
            
        # Create step-up flow URL
        step_up_url = f"/self-service/login/browser?aal={target_aal}&return_to=" + \
                     f"{request.headers.get('Referer', 'https://localhost:8443/dashboard')}"
        
        return success_response({
            "step_up_url": step_up_url,
            "target_aal": target_aal
        })
        
    except Exception as e:
        logger.error(f"Error initiating AAL step-up: {str(e)}")
        return error_response("Failed to initiate step-up", 500)


@aal_bp.route('/api/auth/refresh-session', methods=['POST'])
@cross_origin(supports_credentials=True)
def refresh_session_status():
    """
    Force refresh of session and AAL status after MFA setup completion.
    This helps sync the backend with recently completed MFA setup in Kratos.
    """
    try:
        # Get current user session with fresh data from Kratos
        session_info = whoami(request)
        
        if not session_info:
            return error_response("Not authenticated", 401)
        
        # Force clear any cached data
        session.modified = True
        
        # Get fresh AAL status with updated credentials
        logger.info("🔄 About to call get_current_aal_status()")
        aal_status = get_current_aal_status()
        logger.info(f"🔄 get_current_aal_status() returned: {aal_status}")
        
        if not aal_status:
            return error_response("Failed to get AAL status", 500)
        
        # Log the refresh for debugging
        logger.info(f"🔄 Session refresh for user {aal_status.get('email')}")
        logger.info(f"🔄 Current AAL: {aal_status.get('validation', {}).get('current_aal')}")
        logger.info(f"🔄 Missing methods: {aal_status.get('validation', {}).get('missing_methods')}")
        logger.info(f"🔄 Configured methods: {aal_status.get('configured_methods')}")
        
        return success_response({
            "message": "Session refreshed successfully",
            "aal_status": aal_status,
            "can_access_dashboard": aal_status.get('validation', {}).get('valid', False)
        })
        
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        return error_response("Failed to refresh session", 500)


@aal_bp.route('/api/auth/check-configured-methods', methods=['POST'])
@cross_origin(supports_credentials=True)
def check_configured_auth_methods_by_email():
    """
    Check what authentication methods are configured for a user by email.
    Used for the ideal login flow to determine if passkey login should be offered.
    
    SECURITY: This endpoint is intentionally designed to be called without authentication
    for the login flow, but only returns boolean flags, not sensitive data.
    """
    logger.info("🔍 METHODS: check-configured-methods endpoint called")
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return error_response("Email is required", 400)
            
        email = data.get('email').lower().strip()
        
        logger.info(f"🔍 METHODS: Checking configured methods for email: {email}")
        
        # Import requirements at the top of the function to avoid global import issues
        import requests
        import os
        
        KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
        
        # Search for identity by email using Kratos Admin API
        try:
            search_response = requests.get(
                f"{KRATOS_ADMIN_URL}/admin/identities",
                params={'credentials_identifier': email},
                verify=False,
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            if search_response.status_code != 200:
                logger.warning(f"🔍 METHODS: Could not search identities for {email}: {search_response.status_code}")
                # Return "no methods configured" rather than error for security
                return success_response({
                    "email": email,
                    "has_totp": False,
                    "has_webauthn": False,
                    "has_password": False,
                    "has_any_2fa": False,
                    "exists": False,
                    "passkey_details": {
                        "custom_passkeys": 0,
                        "kratos_webauthn": False
                    },
                    "available_methods": {
                        "totp": False,
                        "passkeys": False
                    }
                })
                
            identities = search_response.json()
            
            # Find identity with matching email
            target_identity = None
            for identity in identities:
                traits = identity.get('traits', {})
                if traits.get('email', '').lower() == email:
                    target_identity = identity
                    break
                    
            if not target_identity:
                logger.info(f"🔍 METHODS: No identity found for {email}")
                return success_response({
                    "email": email,
                    "has_totp": False,
                    "has_webauthn": False,
                    "has_password": False,
                    "has_any_2fa": False,
                    "exists": False,
                    "passkey_details": {
                        "custom_passkeys": 0,
                        "kratos_webauthn": False
                    },
                    "available_methods": {
                        "totp": False,
                        "passkeys": False
                    }
                })
                
            identity_id = target_identity.get('id')
            traits = target_identity.get('traits', {})
            user_role = traits.get('role', 'user')  # Default to 'user' if no role set
            logger.info(f"🔍 METHODS: Found identity {identity_id} for {email} with role {user_role}")
            
            # Import the function locally to avoid module loading issues
            try:
                from app.utils.kratos_session import get_configured_auth_methods
                configured_methods = get_configured_auth_methods(identity_id)
            except ImportError as import_err:
                logger.error(f"🔍 METHODS: Import error: {import_err}")
                # Fallback to checking credentials directly from identity
                credentials = target_identity.get('credentials', {})
                # FIXED: Check for ACTUAL credentials, not just presence of config
                webauthn_creds = credentials.get('webauthn', {})
                has_actual_webauthn = bool(
                    webauthn_creds and 
                    webauthn_creds.get('credentials') and 
                    len(webauthn_creds.get('credentials', [])) > 0
                )
                configured_methods = {
                    'totp': bool(credentials.get('totp')),
                    'webauthn': has_actual_webauthn,  
                    'password': bool(credentials.get('password'))
                }
            
            logger.info(f"🔍 METHODS: Configured methods for {email}: {configured_methods}")
            
            has_totp = configured_methods.get('totp', False)
            has_webauthn = configured_methods.get('webauthn', False)
            has_password = configured_methods.get('password', False)
            
            # CRITICAL FIX: Also check custom STING passkeys (not just Kratos WebAuthn)
            custom_passkeys_count = 0
            try:
                from app.models.passkey_models import Passkey
                from app.models.user_models import User
                
                # Find STING user by email
                user = User.query.filter_by(email=email).first()
                if user:
                    # Count active custom passkeys
                    custom_passkeys_count = Passkey.query.filter_by(
                        user_id=user.id, 
                        status='ACTIVE'
                    ).count()
                    logger.info(f"🔍 METHODS: Found {custom_passkeys_count} custom passkeys for {email}")
                
            except Exception as passkey_err:
                logger.error(f"🔍 METHODS: Error checking custom passkeys for {email}: {passkey_err}")
                custom_passkeys_count = 0
            
            has_any_passkeys = has_webauthn or (custom_passkeys_count > 0)
            has_any_2fa = has_totp or has_any_passkeys
            
            return success_response({
                "email": email,
                "has_totp": has_totp,
                "has_webauthn": has_webauthn,
                "has_password": has_password,
                "has_any_2fa": has_any_2fa,
                "exists": True,
                "role": user_role,
                "identity_id": identity_id,  # Include for debugging (remove in production)
                "passkey_details": {
                    "custom_passkeys": custom_passkeys_count,
                    "kratos_webauthn": has_webauthn
                },
                "available_methods": {
                    "totp": has_totp,
                    "passkeys": has_any_passkeys  # Combined passkey availability
                }
            })
            
        except requests.exceptions.RequestException as e:
            logger.error(f"🔍 METHODS: Network error checking methods for {email}: {e}")
            # Return "no methods configured" rather than error for security
            return success_response({
                "email": email,
                "has_totp": False,
                "has_webauthn": False,  
                "has_password": False,
                "has_any_2fa": False,
                "exists": False,
                "passkey_details": {
                    "custom_passkeys": 0,
                    "kratos_webauthn": False
                },
                "available_methods": {
                    "totp": False,
                    "passkeys": False
                }
            })
        except Exception as e:
            logger.error(f"🔍 METHODS: Error checking methods for {email}: {e}")
            # Return "no methods configured" rather than error for security
            return success_response({
                "email": email,
                "has_totp": False,
                "has_webauthn": False,
                "has_password": False, 
                "has_any_2fa": False,
                "exists": False,
                "passkey_details": {
                    "custom_passkeys": 0,
                    "kratos_webauthn": False
                },
                "available_methods": {
                    "totp": False,
                    "passkeys": False
                }
            })
            
    except Exception as e:
        logger.error(f"🔍 METHODS: Endpoint error: {str(e)}")
        return error_response("Failed to check authentication methods", 500)


@aal_bp.route('/api/auth/test-endpoint', methods=['GET'])
@cross_origin(supports_credentials=True) 
def test_endpoint():
    """Simple test endpoint to verify route registration works"""
    return success_response({"message": "Test endpoint working", "timestamp": str(__import__('datetime').datetime.now())})