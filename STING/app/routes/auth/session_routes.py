"""
Simplified Session Management Routes for Kratos

This module provides robust, simplified session management by treating Kratos
as the single source of truth. It proxies session information requests
directly to Kratos, avoiding complex and error-prone session synchronization.
"""

from flask import Blueprint, request, jsonify, current_app
import requests
import logging
import os

logger = logging.getLogger(__name__)

session_bp = Blueprint('auth_session', __name__)

# Get Kratos public URL from environment or use a default for development
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')

@session_bp.after_request
def add_cors_headers(response):
    """Ensure CORS headers are set for all responses from this blueprint."""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@session_bp.route('/me', methods=['GET'])
def get_current_user():
    """
    Get current authenticated user information by proxying the request to Kratos.
    This is the primary endpoint for checking a user's session status.
    """
    try:
        # Forward browser cookies to Kratos to validate the session
        cookies = {key: value for key, value in request.cookies.items()}
        
        # Call Kratos' whoami endpoint, which is the definitive source of session state
        kratos_response = requests.get(
            f"{KRATOS_PUBLIC_URL}/sessions/whoami",
            cookies=cookies,
            headers={'Accept': 'application/json'},
            verify=False  # In production, this should be True with valid SSL certs
        )

        if kratos_response.status_code != 200:
            logger.warning(f"Kratos whoami check failed with status {kratos_response.status_code}: {kratos_response.text}")
            return jsonify({'error': 'Not authenticated', 'details': 'No valid session found'}), 401

        session_data = kratos_response.json()
        
        # Extract user traits and other relevant info from the Kratos session
        identity = session_data.get('identity', {})
        traits = identity.get('traits', {})
        if not traits:
            logger.error("Kratos session is valid, but user traits are missing.")
            return jsonify({'error': 'Invalid identity configuration', 'details': 'User traits not found in session'}), 500

        # Check for Flask-side AAL2 verification
        from flask import session as flask_session
        from datetime import datetime, timezone
        effective_aal = session_data.get('authenticator_assurance_level', 'aal1')
        aal2_verified = flask_session.get('aal2_verified', False)
        aal2_method = flask_session.get('aal2_method')
        aal2_verified_at = flask_session.get('aal2_verified_at')
        
        # DISABLED: Auto-sync from Kratos AAL2
        # STING uses a custom AAL2 tier system stored in Redis, not Kratos native AAL2.
        # Kratos may report AAL2 after email+TOTP or email+WebAuthn login, but that should
        # NOT automatically grant custom AAL2 status which is reserved for step-up verification.
        #
        # The custom AAL2 system requires explicit verification via:
        # - /api/aal2/challenge/complete (after TOTP/WebAuthn step-up)
        # - aal2_manager.set_aal2_verified() in Redis
        #
        # Commenting out auto-sync to prevent bypassing custom AAL2 requirements:
        # if session_data.get('authenticator_assurance_level') == 'aal2' and not aal2_verified:
        #     flask_session['aal2_verified'] = True
        #     flask_session['aal2_method'] = 'kratos_native'
        #     flask_session['aal2_verified_at'] = datetime.now(timezone.utc).isoformat()
        #     aal2_verified = True
        #     aal2_method = 'kratos_native'
        #     logger.info(f"Auto-synced Kratos AAL2 session to Flask for user: {traits.get('email')}")
        
        # If AAL2 is verified in Flask session, use that as effective AAL
        if aal2_verified:
            effective_aal = 'aal2'
        
        # Construct a consistent user object for the frontend
        user_info = {
            'id': identity.get('id'),
            'email': traits.get('email'),
            'name': f"{traits.get('name', {}).get('first', '')} {traits.get('name', {}).get('last', '')}".strip(),
            'role': traits.get('role', 'user'),
            'aal': effective_aal,  # Use effective AAL (Kratos + Flask verification)
            'auth_methods': {
                'totp': 'totp' in identity.get('credentials', {}),
                'webauthn': 'webauthn' in identity.get('credentials', {}),
                'passkeys': [pk.get('id') for pk in identity.get('credentials', {}).get('webauthn', {}).get('identifiers', [])]
            },
            'session': {
                'id': session_data.get('id'),
                'authenticated_at': session_data.get('authenticated_at'),
                'expires_at': session_data.get('expires_at'),
                'aal': session_data.get('authenticator_assurance_level', 'aal1'),  # Original Kratos AAL
                'effective_aal': effective_aal,  # Flask + Kratos combined AAL
                'aal2_verified': aal2_verified,
                'aal2_method': aal2_method,
                'aal2_verified_at': aal2_verified_at
            }
        }

        logger.info(f"Successfully retrieved session for user: {user_info.get('email')}")
        return jsonify({'user': user_info})

    except requests.exceptions.RequestException as e:
        logger.error(f"Could not connect to Kratos: {e}")
        return jsonify({'error': 'Authentication service unavailable', 'details': str(e)}), 503
        
    except Exception as e:
        logger.error(f"Error in /api/auth/me: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error processing user session',
            'details': str(e) if current_app.debug else 'An unexpected error occurred'
        }), 500

@session_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    """
    Handles user logout by initiating the Kratos logout flow and clearing session cookies.
    Also clears custom AAL2 verification from Redis.
    """
    try:
        logger.info("Starting logout process")

        # Clear custom AAL2 verification from Redis if user is authenticated
        if hasattr(g, 'user') and g.user and hasattr(g, 'session_data') and g.session_data:
            try:
                from app.decorators.aal2 import aal2_manager
                user_id = g.user.id
                session_id = g.session_data.get('id')

                # Delete session-specific AAL2 verification from Redis
                if aal2_manager.redis_client and session_id:
                    key = f"{aal2_manager.aal2_prefix}{user_id}:{session_id}"
                    aal2_manager.redis_client.delete(key)
                    logger.info(f"Cleared AAL2 verification for user {user_id} session {session_id[:8]}... during logout")
            except Exception as e:
                logger.warning(f"Failed to clear AAL2 verification during logout: {e}")

        # Get the Kratos session cookie to initiate the logout flow
        cookies = {key: value for key, value in request.cookies.items()}

        # Initiate the Kratos self-service logout flow
        flow_response = requests.get(
            f"{KRATOS_PUBLIC_URL}/self-service/logout/browser",
            cookies=cookies,
            allow_redirects=False, # We want to handle the flow ourselves
            verify=False
        )

        logout_token = ""
        if flow_response.status_code == 200:
            logout_token = flow_response.json().get('logout_token')
        else:
            logger.warning("Could not get Kratos logout flow. Proceeding to clear cookies.")

        # Prepare the response to clear all relevant session cookies
        response = jsonify({
            'success': True,
            'message': 'Logout process initiated. Clearing session cookies.',
            'redirect_url': '/login' # Advise frontend to redirect
        })
        
        # Define all cookies that should be cleared on logout
        cookie_names = ['session', 'ory_kratos_session', 'csrf_token']
        cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')

        for cookie_name in cookie_names:
            response.set_cookie(cookie_name, '', expires=0, path='/', domain=cookie_domain)

        logger.info("Logout completed, all session cookies cleared.")
        return response
        
    except Exception as e:
        logger.error(f"An error occurred during logout: {e}", exc_info=True)
        return jsonify({
            'error': 'Logout failed',
            'message': str(e)
        }), 500

@session_bp.route('/refresh', methods=['POST'])
def refresh_session():
    """
    Force a session refresh by re-validating with Kratos.
    This is useful after enrollment or other session-modifying operations.
    """
    try:
        # Forward browser cookies to Kratos to validate the session
        cookies = {key: value for key, value in request.cookies.items()}
        
        # Call Kratos' whoami endpoint to get fresh session data
        kratos_response = requests.get(
            f"{KRATOS_PUBLIC_URL}/sessions/whoami",
            cookies=cookies,
            headers={'Accept': 'application/json'},
            verify=False
        )

        if kratos_response.status_code != 200:
            logger.warning(f"Session refresh failed with status {kratos_response.status_code}")
            return jsonify({'error': 'Session refresh failed'}), 401

        session_data = kratos_response.json()
        
        # Extract user traits and other relevant info from the Kratos session
        identity = session_data.get('identity', {})
        traits = identity.get('traits', {})
        
        # Check for Flask-side AAL2 verification (same as /me endpoint)
        from flask import session as flask_session
        effective_aal = session_data.get('authenticator_assurance_level', 'aal1')
        aal2_verified = flask_session.get('aal2_verified', False)
        aal2_method = flask_session.get('aal2_method')
        aal2_verified_at = flask_session.get('aal2_verified_at')
        
        # If AAL2 is verified in Flask session, use that as effective AAL
        if aal2_verified:
            effective_aal = 'aal2'
        
        # Construct refreshed user object
        user_info = {
            'id': identity.get('id'),
            'email': traits.get('email'),
            'name': f"{traits.get('name', {}).get('first', '')} {traits.get('name', {}).get('last', '')}".strip(),
            'role': traits.get('role', 'user'),
            'aal': effective_aal,  # Use effective AAL (Kratos + Flask verification)
            'auth_methods': {
                'totp': 'totp' in identity.get('credentials', {}),
                'webauthn': 'webauthn' in identity.get('credentials', {}),
                'passkeys': [pk.get('id') for pk in identity.get('credentials', {}).get('webauthn', {}).get('identifiers', [])]
            },
            'session': {
                'id': session_data.get('id'),
                'authenticated_at': session_data.get('authenticated_at'),
                'expires_at': session_data.get('expires_at'),
                'aal': session_data.get('authenticator_assurance_level', 'aal1'),  # Original Kratos AAL
                'effective_aal': effective_aal,  # Flask + Kratos combined AAL
                'aal2_verified': aal2_verified,
                'aal2_method': aal2_method,
                'aal2_verified_at': aal2_verified_at
            }
        }

        logger.info(f"Session refreshed successfully for user: {user_info.get('email')}")
        return jsonify({'user': user_info, 'refreshed': True})

    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}", exc_info=True)
        return jsonify({'error': 'Session refresh failed', 'details': str(e)}), 500

@session_bp.route('/grant-aal2-access', methods=['POST'])
def grant_aal2_access():
    """
    Grant AAL2 access after successful 2FA verification.
    
    This endpoint provides a Flask-side AAL2 equivalency system where successful
    AAL1 + 2FA verification grants AAL2 privileges without complex Kratos session elevation.
    """
    try:
        logger.info("AAL2 access grant requested")
        
        # Verify current session exists and is valid
        cookies = {key: value for key, value in request.cookies.items()}
        
        kratos_response = requests.get(
            f"{KRATOS_PUBLIC_URL}/sessions/whoami",
            cookies=cookies,
            headers={'Accept': 'application/json'},
            verify=False
        )

        if kratos_response.status_code != 200:
            logger.warning(f"AAL2 grant failed - no valid session: {kratos_response.status_code}")
            return jsonify({'error': 'Not authenticated', 'details': 'Valid session required for AAL2 grant'}), 401

        session_data = kratos_response.json()
        identity = session_data.get('identity', {})
        traits = identity.get('traits', {})
        user_email = traits.get('email')
        
        if not user_email:
            logger.error("AAL2 grant failed - no user email in session")
            return jsonify({'error': 'Invalid session', 'details': 'User email not found'}), 400

        # Get additional data from request
        request_data = request.get_json() or {}
        method = request_data.get('method', 'unknown')  # 'totp' or 'passkey'
        return_to = request_data.get('return_to', '/dashboard')
        
        # TODO: In the future, we could store AAL2 verification in Redis or session
        # For now, we'll rely on the fact that the 2FA verification just succeeded
        # since this endpoint should only be called immediately after successful verification
        
        from flask import session as flask_session
        from datetime import datetime, timezone
        
        # Store AAL2 verification in Flask session
        flask_session['aal2_verified'] = True
        flask_session['aal2_verified_at'] = datetime.now(timezone.utc).isoformat()
        flask_session['aal2_method'] = method
        flask_session['effective_aal'] = 'aal2'
        flask_session.permanent = True
        
        logger.info(f"AAL2 access granted for user {user_email} via {method}")
        
        return jsonify({
            'success': True,
            'message': f'AAL2 access granted via {method}',
            'effective_aal': 'aal2',
            'verified_at': flask_session['aal2_verified_at'],
            'method': method,
            'return_to': return_to
        })

    except Exception as e:
        logger.error(f"Error granting AAL2 access: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'AAL2 grant failed',
            'details': str(e) if current_app.debug else 'An unexpected error occurred'
        }), 500