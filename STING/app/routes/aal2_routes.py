"""
Custom AAL2 API Routes

Provides endpoints for:
- AAL2 status checking
- Biometric challenge verification
- Passkey enrollment status
- AAL2 session management
"""

import logging
from flask import Blueprint, request, jsonify, g
from app.decorators.aal2 import (
    aal2_manager,
    get_aal2_status,
    verify_aal2_challenge
)
from app.middleware.auth_middleware import require_admin
from app.utils.decorators import require_auth, require_auth_method

logger = logging.getLogger(__name__)

# Create blueprint for AAL2 routes
aal2_bp = Blueprint('aal2', __name__, url_prefix='/api/aal2')


@aal2_bp.route('/status', methods=['GET'])
def get_user_aal2_status():
    """
    Get current user's AAL2 status including enrollment and verification
    
    Returns:
        JSON with enrollment status, verification status, and action needed
    """
    try:
        # Ensure user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401
        
        user_id = g.user.id
        logger.info(f"🔐 AAL2 status check for user {g.user.email} (ID: {user_id})")
        
        status = get_aal2_status(user_id)
        
        return jsonify({
            'success': True,
            'status': status,
            'message': 'AAL2 status retrieved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting AAL2 status: {str(e)}")
        return jsonify({
            'error': 'Failed to get AAL2 status',
            'code': 'STATUS_CHECK_FAILED'
        }), 500


@aal2_bp.route('/step-up/begin', methods=['POST'])
@aal2_bp.route('/challenge/begin', methods=['POST'])
def begin_aal2_challenge():
    """
    Begin AAL2 biometric challenge flow
    
    This endpoint prepares for WebAuthn authentication for AAL2 step-up
    
    Expected JSON:
        {
            "operation": "aal2_verification",
            "return_url": "optional_return_url"
        }
    
    Returns:
        WebAuthn challenge options for biometric authentication
    """
    try:
        # Ensure user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401
        
        user_id = g.user.id
        user_email = g.user.email
        
        # Check if user has passkey enrolled
        enrollment_status = aal2_manager.check_passkey_enrollment(user_id)
        
        if not enrollment_status['enrolled']:
            return jsonify({
                'error': 'Passkey not enrolled',
                'code': 'MISSING_PASSKEY',
                'enrollment_url': enrollment_status['enrollment_url']
            }), 403
        
        # TODO: Integrate with existing WebAuthn challenge generation
        # For MVP, we'll use the existing webauthn authentication flow
        
        logger.info(f"🔐 Beginning AAL2 challenge for {user_email}")
        
        # Return challenge initiation response
        # The frontend should use this to trigger the existing WebAuthn flow
        return jsonify({
            'success': True,
            'challenge_type': 'webauthn',
            'operation': 'aal2_verification',
            'user_id': user_id,
            'message': 'Use existing WebAuthn authentication flow for AAL2',
            'webauthn_endpoint': '/api/webauthn/authentication/begin'
        }), 200
        
    except Exception as e:
        logger.error(f"Error beginning AAL2 challenge: {str(e)}")
        return jsonify({
            'error': 'Failed to begin AAL2 challenge',
            'code': 'CHALLENGE_BEGIN_FAILED'
        }), 500


@aal2_bp.route('/challenge/complete', methods=['POST'])
def complete_aal2_challenge():
    """
    Complete AAL2 biometric challenge

    This should be called after successful WebAuthn authentication
    to mark the user as AAL2 verified

    Expected JSON:
        {
            "verification_method": "webauthn",
            "flow_id": "kratos_flow_id",
            "webauthn_credential": {
                "id": "...",
                "rawId": "...",
                "type": "public-key",
                "response": {...}
            }
        }

    Returns:
        AAL2 verification confirmation
    """
    try:
        # Ensure user is authenticated
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401

        data = request.get_json() or {}
        user_id = g.user.id
        user_email = g.user.email
        verification_method = data.get('verification_method', 'webauthn')
        flow_id = data.get('flow_id')
        webauthn_credential = data.get('webauthn_credential')

        logger.info(f"🔐 Completing AAL2 challenge for {user_email} using {verification_method}")

        # If WebAuthn credential provided, validate it with Kratos first
        if verification_method == 'webauthn' and webauthn_credential and flow_id:
            import requests
            import json
            from flask import session

            logger.info(f"🔐 Submitting WebAuthn credential to Kratos for validation...")

            try:
                # Get the Kratos session cookie from the user's session
                kratos_cookie = request.cookies.get('ory_kratos_session')

                if not kratos_cookie:
                    logger.error("❌ No Kratos session cookie found")
                    return jsonify({
                        'error': 'No active session',
                        'code': 'NO_SESSION'
                    }), 401

                # Submit the WebAuthn credential to Kratos
                kratos_url = f"/.ory/self-service/login?flow={flow_id}"
                kratos_headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'Cookie': f'ory_kratos_session={kratos_cookie}'
                }

                kratos_data = {
                    'webauthn_login': json.dumps(webauthn_credential),
                    'method': 'webauthn'
                }

                # Use internal Kratos URL (kratos:4433) for backend-to-backend communication
                internal_kratos_url = f"https://kratos:4433/self-service/login?flow={flow_id}"

                logger.info(f"🔐 Submitting to Kratos: {internal_kratos_url}")

                kratos_response = requests.post(
                    internal_kratos_url,
                    data=kratos_data,
                    headers=kratos_headers,
                    verify=False,  # Kratos uses self-signed cert internally
                    allow_redirects=False
                )

                logger.info(f"🔐 Kratos response status: {kratos_response.status_code}")

                # Check if Kratos accepted the credential
                if kratos_response.status_code not in [200, 303]:
                    logger.error(f"❌ Kratos rejected WebAuthn credential: {kratos_response.status_code}")
                    logger.error(f"❌ Kratos response: {kratos_response.text[:500]}")
                    return jsonify({
                        'error': 'WebAuthn credential validation failed',
                        'code': 'KRATOS_VALIDATION_FAILED'
                    }), 401

                logger.info(f"✅ Kratos validated WebAuthn credential successfully!")

            except Exception as kratos_error:
                logger.error(f"❌ Error validating with Kratos: {str(kratos_error)}")
                return jsonify({
                    'error': 'Failed to validate with Kratos',
                    'code': 'KRATOS_ERROR',
                    'details': str(kratos_error)
                }), 500

        # Mark user as AAL2 verified in our system
        success = verify_aal2_challenge(user_id, verification_method)

        if success:
            logger.info(f"✅ AAL2 verification successful for {user_email}")

            # Get updated status
            status = get_aal2_status(user_id)

            return jsonify({
                'success': True,
                'verified': True,
                'method': verification_method,
                'status': status,
                'message': 'AAL2 verification completed successfully'
            }), 200
        else:
            logger.error(f"❌ AAL2 verification failed for {user_email}")
            return jsonify({
                'error': 'AAL2 verification failed',
                'code': 'VERIFICATION_FAILED'
            }), 500

    except Exception as e:
        logger.error(f"Error completing AAL2 challenge: {str(e)}")
        return jsonify({
            'error': 'Failed to complete AAL2 challenge',
            'code': 'CHALLENGE_COMPLETE_FAILED'
        }), 500


@aal2_bp.route('/verify', methods=['POST'])
def verify_aal2():
    """
    Verify current AAL2 status (for testing/debugging)
    
    Returns current verification status without performing authentication
    """
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401
        
        user_id = g.user.id
        status = get_aal2_status(user_id)
        
        return jsonify({
            'success': True,
            'status': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying AAL2 status: {str(e)}")
        return jsonify({
            'error': 'Failed to verify AAL2 status',
            'code': 'VERIFICATION_CHECK_FAILED'
        }), 500


@aal2_bp.route('/clear', methods=['POST'])
@require_auth
def clear_aal2():
    """
    Clear AAL2 verification for current user (used on logout)
    
    Provides immediate AAL2 cleanup for security hygiene
    """
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({
                'error': 'Authentication required',
                'code': 'NOT_AUTHENTICATED'
            }), 401
            
        user_id = g.user.id
        user_email = g.user.email
        
        logger.info(f"🧹 Clearing AAL2 verification for {user_email} on logout")
        
        # Import AAL2 cleanup function
        from app.decorators.aal2 import clear_user_aal2_on_logout
        
        # Clear Redis AAL2 verification
        success = clear_user_aal2_on_logout(user_id)
        
        if success:
            logger.info(f"✅ AAL2 verification cleared for {user_email}")
            return jsonify({
                'success': True,
                'cleared': True,
                'message': 'AAL2 verification cleared successfully'
            }), 200
        else:
            logger.warning(f"⚠️ AAL2 clear failed for {user_email}")
            return jsonify({
                'success': False,
                'cleared': False,
                'message': 'AAL2 clear failed but not critical'
            }), 200  # Not a critical error
        
    except Exception as e:
        logger.error(f"Error clearing AAL2: {str(e)}")
        return jsonify({
            'error': 'Failed to clear AAL2',
            'code': 'CLEAR_FAILED'
        }), 500


# Example of how to use the decorator on sensitive endpoints
@aal2_bp.route('/test-sensitive', methods=['GET'])
@require_auth_method(['webauthn', 'totp'])
def test_sensitive_operation():
    """
    Test endpoint that requires custom AAL2 verification
    
    This demonstrates how to protect sensitive operations
    """
    return jsonify({
        'success': True,
        'message': 'You have successfully accessed a sensitive operation!',
        'aal2_info': {
            'verified': getattr(g, 'aal2_verified', False),
            'method': getattr(g, 'aal2_method', None),
            'verified_at': getattr(g, 'aal2_verified_at', None)
        }
    }), 200


# Admin endpoint with both role and AAL2 requirements
@aal2_bp.route('/admin-sensitive', methods=['GET'])
@require_admin
@require_auth_method(['webauthn', 'totp'])
def admin_sensitive_operation():
    """
    Admin endpoint that requires both admin role and AAL2 verification
    """
    return jsonify({
        'success': True,
        'message': 'Admin AAL2 operation completed',
        'user': {
            'email': g.user.email,
            'role': g.user.role,
            'is_admin': g.user.is_admin
        },
        'aal2_info': {
            'verified': getattr(g, 'aal2_verified', False),
            'method': getattr(g, 'aal2_method', None),
            'verified_at': getattr(g, 'aal2_verified_at', None)
        }
    }), 200