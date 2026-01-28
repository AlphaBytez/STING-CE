"""
AAL (Authentication Assurance Level) Management Routes

Handles AAL status checking, requirements, and security gate operations.
"""

from flask import Blueprint, request, jsonify, session, g
import logging
from datetime import datetime

from app.utils.decorators import require_auth
from app.utils.kratos_client import whoami

logger = logging.getLogger(__name__)

aal_bp = Blueprint('aal', __name__)


@aal_bp.after_request
def after_request(response):
    """Add CORS headers specifically for AAL endpoints"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@aal_bp.route('/aal-status', methods=['GET'])
def get_aal_status():
    """
    Get current Authentication Assurance Level (AAL) status
    Checks both Kratos session and custom Flask session AAL2 markers
    """
    try:
        # Check if user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'authenticated': False,
                'aal_level': None,
                'message': 'Not authenticated'
            }), 401
        
        # Default AAL level
        aal_level = 'aal1'
        auth_source = 'flask_session'
        additional_info = {}
        
        # Check for custom AAL2 markers from enhanced WebAuthn
        if session.get('custom_aal2_verified'):
            aal_level = 'aal2'
            auth_source = 'enhanced_webauthn'
            additional_info = {
                'aal2_method': session.get('custom_aal2_method'),
                'aal2_timestamp': session.get('custom_aal2_timestamp'),
                'auth_method': session.get('auth_method', 'unknown')
            }
            logger.info(f"🔐 AAL2 verified via enhanced WebAuthn for user: {g.user.email}")
        
        # Also check Kratos session if available (for comparison)
        kratos_aal = None
        try:
            if hasattr(g, 'session_data') and g.session_data:
                kratos_aal = g.session_data.get('authenticator_assurance_level', 'aal1')
                logger.info(f"🔐 Kratos AAL level: {kratos_aal}")
        except Exception as e:
            logger.debug(f"Could not check Kratos AAL: {e}")
        
        return jsonify({
            'authenticated': True,
            'aal_level': aal_level,
            'auth_source': auth_source,
            'kratos_aal': kratos_aal,
            'user_id': g.user.id,
            'user_email': g.user.email,
            'additional_info': additional_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking AAL status: {str(e)}", exc_info=True)
        return jsonify({
            'authenticated': False,
            'aal_level': None,
            'error': 'Failed to check AAL status'
        }), 500


@aal_bp.route('/aal-status-v2', methods=['GET'])
@require_auth
def get_aal_status_v2():
    """Get AAL (Authentication Assurance Level) status for current user"""
    try:
        # Check if user is NOT authenticated
        if not hasattr(g, 'user') or not g.user:
            logger.warning("No authenticated user found for AAL status")
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Check if identity is NOT available
        if not hasattr(g, 'identity') or not g.identity:
            logger.warning("No identity found for AAL status")
            return jsonify({'error': 'No identity found'}), 401
        
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


@aal_bp.route('/aal-requirements', methods=['GET'])
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


@aal_bp.route('/security-gate/status', methods=['GET'])
def security_gate_status():
    """
    Check security gate status for authenticated user.
    Returns enrollment and AAL requirements.
    """
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Check if user has configured methods
    from app.middleware.auth_middleware import check_admin_credentials
    
    if hasattr(g, 'identity'):
        cred_status = check_admin_credentials(g.identity)
        has_totp = cred_status.get('has_totp', False)
        has_passkey = cred_status.get('has_webauthn', False)
    else:
        has_totp = False
        has_passkey = False
    
    # Check if user is admin
    is_admin = False
    if hasattr(g, 'identity') and g.identity:
        is_admin = g.identity.get('traits', {}).get('role') == 'admin'
    
    return jsonify({
        'authenticated': True,
        'is_admin': is_admin,
        'has_totp': has_totp,
        'has_passkey': has_passkey,
        'requires_enrollment': is_admin and (not has_totp or not has_passkey),
        'enrollment_complete': has_totp and has_passkey
    })


@aal_bp.route('/settings', methods=['GET'])
def get_settings_flow():
    """Proxy to Kratos settings flow with enhanced WebAuthn support"""
    try:
        # Manual authentication check (avoid decorator enum issues)
        if not (hasattr(g, 'user') and g.user and hasattr(g.user, 'email')):
            # Try to get Kratos session directly
            from app.utils.flexible_auth import check_kratos_session
            user_info = check_kratos_session()
            if not user_info:
                logger.warning("No valid session for settings flow")
                return jsonify({'error': 'Authentication required'}), 401
            
            # Get existing user from database
            from app.models.user_models import User
            user = User.query.filter_by(email=user_info['email']).first()
            if not user:
                logger.warning(f"No database user found for {user_info['email']}")
                return jsonify({'error': 'User not found'}), 401
                
            g.user = user
        
        # Check multiple authentication sources for better compatibility
        identity = None
        use_admin_api = False
        
        # 1. Check Flask session first
        identity = session.get('identity')
        
        # 2. Check g.user from middleware (most reliable)
        if not identity and hasattr(g, 'user') and g.user:
            logger.info(f"Using g.user for settings flow: {g.user.email}")
            # Get Kratos identity for this user
            if hasattr(g, 'identity'):
                identity = g.identity
            else:
                # Reconstruct basic identity from user
                identity = {
                    'id': g.user.kratos_id or g.user.id,
                    'traits': {'email': g.user.email}
                }
        
        # 3. Check for enhanced WebAuthn session and biometric AAL2 eligibility
        from app.utils.enhanced_aal2_check import should_bypass_aal_requirement, get_effective_aal
        
        # Combine session data for enhanced AAL checking
        session_dict = dict(session)  # Convert Redis session to dict
        combined_session_data = {
            **session_dict,  # Flask session
            'identity': identity,
            'auth_method': session.get('auth_method')
        }
        
        # Check if we should bypass AAL requirement due to biometric authentication
        should_bypass = should_bypass_aal_requirement(combined_session_data, 'aal2')
        
        if session.get('auth_method') == 'enhanced_webauthn' or should_bypass:
            effective_aal = get_effective_aal(combined_session_data, session_dict)
            logger.info(f"Enhanced WebAuthn session detected (effective AAL: {effective_aal}), using Admin API to bypass AAL requirement")
            use_admin_api = True
            
            # For enhanced WebAuthn, get identity from our session
            if not identity and session.get('user_email'):
                # Use Kratos Admin API to get identity by email
                from app.utils.kratos_admin import get_identity_by_email
                try:
                    identity = get_identity_by_email(session.get('user_email'))
                    if identity:
                        logger.info(f"Retrieved identity via Admin API for enhanced WebAuthn user: {session.get('user_email')}")
                except Exception as e:
                    logger.warning(f"Failed to get identity via Admin API: {e}")
        
        # 4. Check Kratos session directly as fallback
        if not identity:
            kratos_cookie = request.cookies.get('ory_kratos_session')
            if kratos_cookie:
                try:
                    kratos_session = whoami(kratos_cookie)
                    if kratos_session and kratos_session.get('identity'):
                        identity = kratos_session['identity']
                        # Store in Flask session for next time
                        session['identity'] = identity
                        logger.info(f"Retrieved and stored identity for {identity.get('traits', {}).get('email')}")
                except Exception as e:
                    logger.warning(f"Failed to get identity from Kratos: {e}")
        
        if not identity:
            logger.error("No identity found in any authentication source")
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Special handling for API key authentication (no real Kratos identity)
        if hasattr(g, 'api_key') and g.api_key:
            logger.info(f"API key authentication detected for settings flow: {g.user.email}")
            # For API key users, create a minimal mock settings flow
            mock_flow = {
                'id': f'api-settings-{g.user.id}',
                'type': 'settings',
                'identity': identity,
                'ui': {
                    'nodes': [],
                    'action': '/self-service/settings',
                    'method': 'POST'
                },
                'state': 'show_form',
                'has_webauthn': False,  # API key users typically don't have WebAuthn via Kratos
                'has_totp': False       # API key users typically don't have TOTP via Kratos
            }
            return jsonify(mock_flow)
        
        # For now, return a basic settings response
        # This would need full implementation based on your Kratos setup
        return jsonify({
            'id': f'settings-{identity.get("id")}',
            'type': 'settings',
            'identity': identity,
            'state': 'show_form',
            'ui': {
                'nodes': [],
                'action': '/self-service/settings',
                'method': 'POST'
            }
        })
        
    except Exception as e:
        logger.error(f"Error in settings flow: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get settings flow'}), 500


@aal_bp.route('/aal2/status', methods=['GET', 'POST'])
@require_auth
def get_aal2_method_status():
    """
    Check what auth methods the current authenticated user has configured.
    Used by enrollment page to detect existing methods after AAL1 authentication.
    Secure: only shows methods for current user, requires AAL1 authentication.
    """
    try:
        from app.utils.kratos_session import get_configured_auth_methods

        # User is already authenticated (AAL1) via @require_auth
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401

        user_email = g.user.email
        kratos_id = g.user.kratos_id  # Get the Kratos identity ID

        logger.info(f"🔐 AAL2 method detection for authenticated user: {user_email} (kratos_id: {kratos_id})")

        # Use the working function from kratos_session.py that correctly detects methods
        if kratos_id:
            configured_methods = get_configured_auth_methods(kratos_id)

            has_totp = configured_methods.get('totp', False)
            has_webauthn = configured_methods.get('webauthn', False)

            logger.info(f"🔐 Method detection for {user_email}: TOTP={has_totp}, WebAuthn={has_webauthn}")

            return jsonify({
                'configured_methods': {
                    'webauthn': has_webauthn,
                    'totp': has_totp
                },
                'has_webauthn': has_webauthn,
                'has_totp': has_totp,
                'user_exists': True,
                'user_id': kratos_id,
                'email': user_email
            }), 200
        else:
            # Fallback if no Kratos ID
            logger.error(f"No Kratos ID found for user {user_email}")
            return jsonify({
                'configured_methods': {
                    'webauthn': False,
                    'totp': False
                },
                'has_webauthn': False,
                'has_totp': False,
                'error': 'Kratos ID not found'
            }), 404

    except Exception as e:
        logger.error(f"Error in AAL2 method detection: {str(e)}")
        return jsonify({
            'error': 'Failed to check AAL2 status',
            'code': 'STATUS_CHECK_FAILED'
        }), 500