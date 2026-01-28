"""
TOTP Enrollment Routes - Simplified TOTP setup for enrollment
Handles all Kratos complexity server-side for reliable TOTP registration
"""

import logging
import requests
import os
from flask import Blueprint, request, jsonify, session
from app.middleware.api_key_middleware import api_key_optional

logger = logging.getLogger(__name__)

totp_enrollment_bp = Blueprint('totp_enrollment', __name__)

# Use internal container URL for backend-to-Kratos communication
KRATOS_INTERNAL_URL = os.getenv('KRATOS_ADMIN_URL', 'http://kratos:4434')  # Admin API for settings flows

@totp_enrollment_bp.route('/setup/begin', methods=['POST'])
@api_key_optional()
def setup_totp_begin():
    """
    Initialize TOTP setup - handle all Kratos flow complexity server-side
    Returns QR code and secret for frontend display
    """
    try:
        # Get user info from Flask session or fallback to Kratos session
        user_email = session.get('user_email')
        identity_id = session.get('identity_id')
        
        # If no Flask session, try to get from Kratos session (enrollment scenario)
        if not user_email or not identity_id:
            logger.info("No Flask session found, checking Kratos session for enrollment...")
            
            # Check for Kratos session cookie
            session_cookie = request.cookies.get('ory_kratos_session')
            if session_cookie:
                try:
                    from app.utils.kratos_client import whoami
                    kratos_response = whoami(session_cookie)
                    
                    if kratos_response and kratos_response.get('identity'):
                        identity = kratos_response['identity']
                        user_email = identity.get('traits', {}).get('email')
                        identity_id = identity.get('id')
                        
                        # Store in session for subsequent requests
                        session['user_email'] = user_email
                        session['identity_id'] = identity_id
                        session['user_role'] = identity.get('traits', {}).get('role', 'user')
                        
                        logger.info(f"Retrieved user from Kratos session: {user_email}")
                except Exception as e:
                    logger.error(f"Failed to get user from Kratos session: {e}")
        
        if not user_email or not identity_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Create Kratos settings flow using internal container URL
        settings_response = requests.get(
            f"{KRATOS_INTERNAL_URL.replace('4434', '4433')}/self-service/settings/browser",
            headers={'Accept': 'application/json'},
            cookies=request.cookies,
            verify=False
        )
        
        if not settings_response.ok:
            logger.error(f"Failed to create settings flow: {settings_response.status_code}")
            return jsonify({'error': 'Failed to initialize TOTP setup'}), 500
        
        flow_data = settings_response.json()
        
        # Store flow data in session for completion
        session['totp_flow_id'] = flow_data.get('id')
        session['totp_flow_data'] = flow_data
        
        # Request TOTP setup by submitting method selection
        form_data = {
            'method': 'totp',
            'csrf_token': None
        }
        
        # Extract CSRF token
        csrf_node = None
        for node in flow_data.get('ui', {}).get('nodes', []):
            if node.get('attributes', {}).get('name') == 'csrf_token':
                form_data['csrf_token'] = node.get('attributes', {}).get('value')
                break
        
        if not form_data['csrf_token']:
            logger.error("No CSRF token found in settings flow")
            return jsonify({'error': 'Invalid settings flow - no CSRF token'}), 500
        
        # Submit method selection to get TOTP secret
        setup_response = requests.post(
            flow_data['ui']['action'],
            data=form_data,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            cookies=request.cookies,
            verify=False
        )
        
        if not setup_response.ok:
            logger.error(f"TOTP setup failed: {setup_response.status_code} - {setup_response.text}")
            return jsonify({'error': f'TOTP setup failed: {setup_response.status_code}'}), 500
        
        setup_data = setup_response.json()
        
        # Extract TOTP details
        totp_secret = None
        qr_code_url = None
        
        for node in setup_data.get('ui', {}).get('nodes', []):
            attrs = node.get('attributes', {})
            if attrs.get('name') == 'totp_secret_key':
                totp_secret = attrs.get('value')
            elif attrs.get('name') == 'totp_qr':
                qr_code_url = attrs.get('src')
        
        if not totp_secret:
            logger.error("No TOTP secret returned from Kratos")
            return jsonify({'error': 'Failed to generate TOTP secret'}), 500
        
        # Update session with TOTP info for verification
        session['totp_secret'] = totp_secret
        session['totp_flow_data'] = setup_data
        
        return jsonify({
            'success': True,
            'totp_secret': totp_secret,
            'qr_code_url': qr_code_url,
            'flow_id': flow_data.get('id')
        })
        
    except Exception as e:
        logger.error(f"Error in TOTP setup begin: {str(e)}", exc_info=True)
        return jsonify({'error': f'TOTP setup failed: {str(e)}'}), 500

@totp_enrollment_bp.route('/setup/verify', methods=['POST'])
@api_key_optional()
def setup_totp_verify():
    """
    Verify TOTP code and complete registration
    Handles all Kratos submission complexity server-side
    """
    try:
        data = request.get_json() or {}
        totp_code = data.get('totp_code')
        
        if not totp_code:
            return jsonify({'error': 'TOTP code required'}), 400
        
        # Get user info (same fallback logic as begin endpoint)
        user_email = session.get('user_email')
        if not user_email:
            session_cookie = request.cookies.get('ory_kratos_session')
            if session_cookie:
                try:
                    from app.utils.kratos_client import whoami
                    kratos_response = whoami(session_cookie)
                    if kratos_response and kratos_response.get('identity'):
                        user_email = kratos_response['identity'].get('traits', {}).get('email')
                        session['user_email'] = user_email
                except Exception as e:
                    logger.error(f"Failed to get user from Kratos: {e}")
        
        # Get flow data from session
        flow_data = session.get('totp_flow_data')
        flow_id = session.get('totp_flow_id')
        
        if not flow_data or not flow_id:
            return jsonify({'error': 'No active TOTP setup flow'}), 400
        
        # Build verification form data
        form_data = {
            'totp_code': totp_code,
            'method': 'totp'
        }
        
        # Extract CSRF token from current flow
        for node in flow_data.get('ui', {}).get('nodes', []):
            if node.get('attributes', {}).get('name') == 'csrf_token':
                form_data['csrf_token'] = node.get('attributes', {}).get('value')
                break
        
        if not form_data['csrf_token']:
            logger.error("No CSRF token found for TOTP verification")
            return jsonify({'error': 'Invalid flow state - missing CSRF token'}), 500
        
        # Submit verification to Kratos
        verify_response = requests.post(
            flow_data['ui']['action'],
            data=form_data,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            cookies=request.cookies,
            verify=False
        )
        
        logger.info(f"TOTP verification response: {verify_response.status_code}")
        
        if verify_response.ok and (verify_response.json().get('state') == 'success'):
            # TOTP successfully registered
            logger.info("TOTP registration completed successfully")
            
            # Clear flow data from session
            session.pop('totp_flow_id', None)
            session.pop('totp_flow_data', None)
            
            return jsonify({
                'success': True,
                'message': 'TOTP setup completed successfully'
            })
        else:
            # Handle specific error cases
            if verify_response.status_code == 400:
                verify_data = verify_response.json()
                error_msg = "Invalid TOTP code"
                
                # Extract specific error from Kratos
                if verify_data.get('ui', {}).get('messages'):
                    for msg in verify_data['ui']['messages']:
                        if msg.get('type') == 'error':
                            error_msg = msg.get('text', error_msg)
                            break
                
                logger.warning(f"TOTP verification failed: {error_msg}")
                return jsonify({'error': error_msg}), 400
            else:
                logger.error(f"TOTP verification failed: {verify_response.status_code} - {verify_response.text}")
                return jsonify({'error': 'TOTP verification failed'}), 500
        
    except Exception as e:
        logger.error(f"Error in TOTP verification: {str(e)}", exc_info=True)
        return jsonify({'error': f'TOTP verification failed: {str(e)}'}), 500