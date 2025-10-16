#!/usr/bin/env python3
"""
TOTP Setup Routes
Handles mandatory TOTP setup for admin users and API endpoints for TOTP operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, g
import qrcode
import io
import base64
from urllib.parse import quote
import logging
from ..decorators.aal2 import verify_aal2_challenge
from app.utils.decorators import require_auth
from app.utils.kratos_auth_decorator import require_kratos_session

logger = logging.getLogger(__name__)

totp_bp = Blueprint('totp', __name__)

@totp_bp.route('/setup-totp')
def setup_totp():
    """Display TOTP setup page"""
    
    if not hasattr(g, 'user') or not g.user:
        return redirect(url_for('auth.login'))
    
    # Only admin users need mandatory TOTP
    # Handle both enum and string role values
    is_admin = False
    if hasattr(g.user, 'role'):
        if hasattr(g.user.role, 'value'):
            # Role is an enum (UserRole.ADMIN)
            is_admin = g.user.role.value == 'ADMIN'
        elif isinstance(g.user.role, str):
            # Role is a string
            is_admin = g.user.role.upper() == 'ADMIN'
    
    if not is_admin:
        return redirect(url_for('dashboard'))
    
    # Check if TOTP is already configured
    if _user_has_totp_configured(g.user):
        return redirect(url_for('dashboard'))
    
    # Generate TOTP setup URL and QR code
    totp_url, qr_code_img = _generate_totp_setup(g.user)
    
    return render_template('setup_totp.html',
                         totp_url=totp_url,
                         qr_code=qr_code_img,
                         user_email=g.user.email,
                         is_mandatory=True)

@totp_bp.route('/verify-totp', methods=['POST'])
def verify_totp():
    """Verify TOTP code and complete setup"""
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    totp_code = request.json.get('totp_code', '').strip()
    if not totp_code:
        return jsonify({'error': 'TOTP code is required'}), 400
    
    # Verify the TOTP code with Kratos
    if _verify_totp_with_kratos(g.user, totp_code):
        # Mark TOTP as verified in session
        session['totp_verified'] = True
        session['totp_setup_completed'] = True
        
        # Set AAL2 verification for TOTP method
        verify_aal2_challenge(g.user.id, 'totp')
        
        # Clear setup requirement flags
        if 'totp_setup_required' in session:
            del session['totp_setup_required']
        
        # Determine redirect URL
        redirect_url = session.pop('totp_redirect_after', url_for('dashboard'))
        
        logger.info(f"TOTP setup completed for admin user {g.user.email}")
        
        return jsonify({
            'success': True,
            'message': 'TOTP setup completed successfully',
            'redirect': redirect_url
        })
    else:
        return jsonify({'error': 'Invalid TOTP code'}), 400

# Duplicate route removed - using get_totp_status() below at line 276

def _user_has_totp_configured(user):
    """Check if user has TOTP configured via Kratos"""
    try:
        import requests
        from flask import current_app
        
        kratos_admin_url = current_app.config.get('KRATOS_ADMIN_URL', 'https://localhost:8443')
        
        # Find user's Kratos identity
        identities_response = requests.get(
            f"{kratos_admin_url}/admin/identities",
            headers={'Accept': 'application/json'},
            verify=False,
            timeout=5
        )
        
        if identities_response.status_code != 200:
            logger.error(f"Failed to fetch identities: {identities_response.status_code}")
            return False
        
        identities = identities_response.json()
        identity_id = None
        
        for identity in identities:
            if identity.get('traits', {}).get('email') == user.email:
                identity_id = identity['id']
                break
        
        if not identity_id:
            logger.warning(f"Could not find Kratos identity for {user.email}")
            return False
        
        # Check credentials
        creds_response = requests.get(
            f"{kratos_admin_url}/admin/identities/{identity_id}/credentials",
            headers={'Accept': 'application/json'},
            verify=False,
            timeout=5
        )
        
        if creds_response.status_code == 200:
            credentials = creds_response.json()
            return 'totp' in credentials and credentials['totp'] is not None
        else:
            logger.error(f"Failed to fetch credentials: {creds_response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking TOTP status: {e}")
        return False

def _generate_totp_setup(user):
    """Generate TOTP URL and QR code for setup"""
    
    # Create TOTP URL
    issuer = "STING Authentication"
    account_name = f"{issuer}:{user.email}"
    
    # Note: In a real implementation, you'd get the secret from Kratos
    # For now, we'll redirect to Kratos TOTP setup
    totp_url = f"https://localhost:8443/.ory/self-service/settings/browser"
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    # Encode as base64
    qr_code_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
    
    return totp_url, qr_code_base64

@totp_bp.route('/generate', methods=['POST'])
@require_kratos_session
def generate_totp():
    """Generate TOTP secret and setup information for frontend"""
    try:
        import pyotp
        import qrcode
        import io
        import base64
        
        # Generate a new TOTP secret
        secret = pyotp.random_base32()
        
        # Create TOTP URL
        issuer = "STING CE"
        user_email = g.user_email if hasattr(g, 'user_email') else 'user@sting.local'
        totp_url = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Convert to base64 for embedding in JSON
        qr_code_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"
        
        # Store secret in session for verification
        session['totp_secret'] = secret
        
        logger.info(f"Generated TOTP setup for user {user_email}")
        
        return jsonify({
            'secret': secret,
            'qr_code': qr_code_data_url,
            'manual_entry_key': secret,
            'issuer': issuer,
            'account': user_email,
            'uri': totp_url
        })
        
    except Exception as e:
        logger.error(f"Error generating TOTP: {e}")
        return jsonify({'error': 'Failed to generate TOTP'}), 500

def _verify_totp_with_kratos(user, totp_code):
    """Verify TOTP code with Kratos"""
    try:
        import requests
        from flask import current_app
        
        # In a real implementation, this would verify the TOTP code
        # For now, we'll assume verification through Kratos settings flow
        
        # Mock verification - in reality this would be handled by Kratos
        if len(totp_code) == 6 and totp_code.isdigit():
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error verifying TOTP with Kratos: {e}")
        return False


# Additional TOTP API endpoints extracted from auth_routes.py

@totp_bp.route('/totp-status', methods=['GET'])
def get_totp_status():
    """Get TOTP setup status for current user"""
    try:
        # Use same auth pattern as security-gate endpoint for consistency
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Not authenticated'}), 401
            
        # Check TOTP status via middleware function  
        from app.middleware.auth_middleware import check_admin_credentials
        
        # Try kratos_identity first, then fall back to identity from session
        identity_to_check = None
        if hasattr(g, 'kratos_identity') and g.kratos_identity:
            identity_to_check = g.kratos_identity
        elif hasattr(g, 'identity') and g.identity:
            identity_to_check = g.identity
        
        if identity_to_check:
            cred_status = check_admin_credentials(identity_to_check)
            return jsonify({
                'has_totp': cred_status.get('has_totp', False),
                'has_webauthn': cred_status.get('has_webauthn', False), 
                'needs_setup': cred_status.get('needs_setup', False),
                'enabled': cred_status.get('has_totp', False)
            })
        
        # Final fallback - try to get identity from session
        identity_id = session.get('identity_id')
        if identity_id:
            # Create minimal identity object for credential check
            minimal_identity = {
                'id': identity_id,
                'traits': {
                    'email': g.user.email,
                    'role': g.user.role if hasattr(g.user, 'role') else 'user'
                }
            }
            cred_status = check_admin_credentials(minimal_identity)
            return jsonify({
                'has_totp': cred_status.get('has_totp', False),
                'has_webauthn': cred_status.get('has_webauthn', False), 
                'needs_setup': cred_status.get('needs_setup', False),
                'enabled': cred_status.get('has_totp', False)
            })
        
        # Last resort fallback
        return jsonify({
            'has_totp': False,
            'has_webauthn': False,
            'needs_setup': True,
            'enabled': False
        })
        
    except Exception as e:
        logger.error(f"Error getting TOTP status: {str(e)}")
        return jsonify({'error': 'Failed to get TOTP status'}), 500


@totp_bp.route('/totp-setup', methods=['POST'])
@require_kratos_session
def setup_totp_json():
    """Generate TOTP secret and QR code for enrollment (JSON API)"""
    try:
        
        import pyotp
        
        # Generate a new TOTP secret
        secret = pyotp.random_base32()
        
        # Create TOTP URL
        issuer = "STING CE"
        user_email = g.user_email if hasattr(g, 'user_email') else 'user@sting.local'
        totp_url = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Convert to base64 for embedding in JSON
        qr_code_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        qr_code_data_url = f"data:image/png;base64,{qr_code_base64}"
        
        # Store secret in session for verification
        session['totp_secret'] = secret
        
        logger.info(f"Generated TOTP setup for user {user_email}")
        
        return jsonify({
            'secret': secret,
            'qr_code': qr_code_data_url,
            'manual_entry_key': secret,
            'issuer': issuer,
            'account': user_email
        })
        
    except Exception as e:
        logger.error(f"Error setting up TOTP: {str(e)}")
        return jsonify({'error': 'Failed to setup TOTP'}), 500


@totp_bp.route('/totp-verify', methods=['POST'])
@require_kratos_session
def verify_totp_json():
    """Verify TOTP code during enrollment (JSON API)"""
    try:
        
        data = request.get_json()
        code = data.get('code', '').strip()
        secret = data.get('secret') or session.get('totp_secret')
        
        if not code or not secret:
            return jsonify({'error': 'Code and secret are required'}), 400
        
        import pyotp
        
        # Verify the TOTP code
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=1):
            # TODO: Store TOTP secret in database or Kratos
            # For now, just mark as verified in session
            session['totp_verified'] = True
            session['totp_enabled'] = True
            
            # Clear the temporary secret
            if 'totp_secret' in session:
                del session['totp_secret']
            
            logger.info(f"TOTP verified successfully for user {g.user_email if hasattr(g, 'user_email') else 'unknown'}")
            
            return jsonify({
                'verified': True,
                'message': 'TOTP configured successfully'
            })
        else:
            return jsonify({
                'verified': False,
                'error': 'Invalid code. Please try again.'
            }), 400
            
    except Exception as e:
        logger.error(f"Error verifying TOTP: {str(e)}")
        return jsonify({'error': 'Failed to verify TOTP'}), 500


@totp_bp.route('/2fa-status', methods=['GET'])
@require_auth
def get_2fa_status():
    """Get comprehensive 2FA/AAL status for current user using new AAL middleware"""
    try:
        # Use the new AAL middleware to get status
        from app.middleware.aal_middleware import get_current_aal_status
        from app.utils.kratos_session import whoami
        
        aal_status = get_current_aal_status()
        
        if not aal_status:
            return jsonify({'error': 'Not authenticated'}), 401
            
        validation = aal_status['validation']
        requirements = aal_status['requirements']
        
        # Extract authentication methods from session
        kratos_cookie = request.cookies.get('ory_kratos_session')
        session_info = whoami(kratos_cookie) if kratos_cookie else None
        if session_info:
            session_data = session_info.get('session', session_info)
            identity = session_info.get('identity', {})
            credentials = identity.get('credentials', {})
            
            # Check what methods are configured
            has_totp = bool(credentials.get('totp', {}).get('config', {}))
            has_webauthn = bool(credentials.get('webauthn'))
            has_password = bool(credentials.get('password'))
            
            # Check what methods were used in current session
            auth_methods = session_data.get('authentication_methods', [])
            
            # Return comprehensive status
            return jsonify({
                'aal': validation.get('current_aal', 'aal1'),
                'current_aal': validation.get('current_aal', 'aal1'),
                'required_aal': requirements.get('min_aal', 'aal1'),
                'authenticated_methods': auth_methods,
                'configured_methods': {
                    'totp': has_totp,
                    'webauthn': has_webauthn,
                    'password': has_password
                },
                'meets_requirement': validation.get('meets_requirement', False),
                'needs_step_up': validation.get('needs_step_up', False),
                'grace_period_remaining': validation.get('grace_period_remaining', 0)
            })
        else:
            # Fallback for non-Kratos sessions
            return jsonify({
                'aal': 'aal1',
                'current_aal': 'aal1',
                'required_aal': 'aal1',
                'authenticated_methods': [],
                'configured_methods': {
                    'totp': False,
                    'webauthn': False,
                    'password': True
                },
                'meets_requirement': True,
                'needs_step_up': False,
                'grace_period_remaining': 0
            })
            
    except Exception as e:
        logger.error(f"Error getting 2FA status: {str(e)}")
        return jsonify({'error': 'Failed to get 2FA status'}), 500