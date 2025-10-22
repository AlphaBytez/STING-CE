"""
Pure Kratos Session Routes
Simplified session management using only Kratos (no Flask sessions)
"""

import logging
import requests
import os
from flask import Blueprint, jsonify, request, g

logger = logging.getLogger(__name__)

kratos_session_bp = Blueprint('kratos_session', __name__)

# Kratos configuration
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')

@kratos_session_bp.route('/me', methods=['GET'])
def get_current_user_simple():
    """
    Get current user information from Kratos session only.
    Pure Kratos approach - no Flask session coordination needed.
    """
    try:
        # Use the user data already loaded by middleware
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = g.user
        session = g.session
        
        # Simple user response using only Kratos data
        user_info = {
            'id': user.kratos_id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'aal': user.aal,
            'session': {
                'id': user.session_id,
                'authenticated_at': user.authenticated_at,
                'expires_at': user.expires_at,
                'aal': user.aal,
                'effective_aal': user.aal  # With pure Kratos, these are the same
            }
        }
        
        logger.info(f"Retrieved pure Kratos session for user: {user.email}")
        return jsonify({'user': user_info})
        
    except Exception as e:
        logger.error(f"Error in pure Kratos session endpoint: {e}")
        return jsonify({'error': 'Session retrieval failed'}), 500

@kratos_session_bp.route('/refresh', methods=['POST'])
def refresh_session():
    """
    Refresh current session.
    With pure Kratos, this just validates the existing session.
    """
    try:
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Not authenticated'}), 401
        
        # With pure Kratos, session refresh is handled by Kratos
        # We just return the current session info
        return get_current_user_simple()
        
    except Exception as e:
        logger.error(f"Error refreshing pure Kratos session: {e}")
        return jsonify({'error': 'Session refresh failed'}), 500

@kratos_session_bp.route('/logout', methods=['POST'])  
def logout():
    """
    Logout by redirecting to Kratos logout flow.
    No Flask session cleanup needed.
    """
    try:
        # With pure Kratos, logout is handled entirely by Kratos
        logout_url = f"{KRATOS_PUBLIC_URL}/self-service/logout/browser"
        
        return jsonify({
            'success': True,
            'logout_url': logout_url,
            'message': 'Redirecting to Kratos logout'
        })
        
    except Exception as e:
        logger.error(f"Error in pure Kratos logout: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@kratos_session_bp.route('/aal-status', methods=['GET'])
def get_aal_status():
    """
    Get Authentication Assurance Level status using pure Kratos data.
    No Flask session coordination needed.
    """
    try:
        if not g.get('is_authenticated', False):
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = g.user
        session = g.session
        
        # Extract configured methods from Kratos identity
        identity = session.get('identity', {})
        credentials = identity.get('credentials', {})
        
        # Simple method detection
        has_totp = 'totp' in credentials
        has_webauthn = 'webauthn' in credentials
        
        aal_status = {
            'user_id': user.kratos_id,
            'email': user.email,
            'current_aal': user.aal,
            'effective_aal': user.aal,  # Same as current_aal with pure Kratos
            'configured_methods': {
                'totp': has_totp,
                'webauthn': has_webauthn
            },
            'needs_aal2': user.aal == 'aal1' and user.role == 'admin' and (has_totp or has_webauthn),
            'can_upgrade_to_aal2': has_totp or has_webauthn,
            'step_up_url': '/security-upgrade'
        }
        
        logger.debug(f"Pure Kratos AAL status for {user.email}: {aal_status}")
        return jsonify(aal_status)
        
    except Exception as e:
        logger.error(f"Error getting pure Kratos AAL status: {e}")
        return jsonify({'error': 'AAL status check failed'}), 500

@kratos_session_bp.route('/grant-aal2-access', methods=['POST'])
def grant_aal2_access():
    """
    Grant AAL2 access after successful 2FA verification.

    In pure Kratos mode, this endpoint acknowledges successful 2FA completion
    and provides session refresh for the frontend to reflect AAL2 status.
    """
    try:
        logger.info("AAL2 access grant requested (pure Kratos mode)")

        if not g.get('is_authenticated', False):
            logger.warning("AAL2 grant failed - no valid session")
            return jsonify({'error': 'Not authenticated', 'details': 'Valid session required for AAL2 grant'}), 401

        user = g.user
        session = g.session

        if not user.email:
            logger.error("AAL2 grant failed - no user email in session")
            return jsonify({'error': 'Invalid session', 'details': 'User email not found'}), 400

        # Get additional data from request
        request_data = request.get_json() or {}
        method = request_data.get('method', 'unknown')  # 'totp' or 'passkey'
        return_to = request_data.get('return_to', '/dashboard')

        # In pure Kratos mode, AAL2 elevation should be handled by Kratos
        # This endpoint mainly serves as a session refresh point

        logger.info(f"AAL2 access acknowledged for user {user.email} via {method} (pure Kratos)")

        return jsonify({
            'success': True,
            'message': f'AAL2 access acknowledged via {method}',
            'effective_aal': user.aal,  # Use current Kratos AAL
            'current_aal': user.aal,
            'method': method,
            'return_to': return_to,
            'note': 'Pure Kratos mode - AAL2 managed by Kratos'
        })

    except Exception as e:
        logger.error(f"Error granting AAL2 access (pure Kratos): {str(e)}", exc_info=True)
        return jsonify({
            'error': 'AAL2 grant failed',
            'details': str(e)
        }), 500