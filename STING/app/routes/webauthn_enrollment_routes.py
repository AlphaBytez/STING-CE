"""
WebAuthn Enrollment Routes - Simplified WebAuthn setup for enrollment
Handles all WebAuthn complexity server-side for reliable passkey registration
"""

import logging
import time
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.middleware.api_key_middleware import api_key_optional
from webauthn import generate_registration_options, verify_registration_response
from webauthn.helpers.structs import (
    PublicKeyCredentialCreationOptions, 
    RegistrationCredential,
    UserVerificationRequirement
)

logger = logging.getLogger(__name__)

webauthn_enrollment_bp = Blueprint('webauthn_enrollment', __name__)

@webauthn_enrollment_bp.route('/setup/begin', methods=['POST'])
@api_key_optional()
def setup_webauthn_begin():
    """
    Generate WebAuthn registration options server-side
    Eliminates frontend complexity and browser compatibility issues
    """
    try:
        # Get user info from session
        user_email = session.get('user_email')
        identity_id = session.get('identity_id')
        
        if not user_email or not identity_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        logger.info(f"🔐 Starting WebAuthn registration for: {user_email}")
        
        # Get device name from request
        data = request.get_json() or {}
        device_name = data.get('device_name', f"{user_email} - Enrollment Device")
        
        # Generate WebAuthn registration options
        options = generate_registration_options(
            rp_id="localhost",
            rp_name="STING Authentication",
            user_id=identity_id.encode(),  # Use Kratos identity ID
            user_name=user_email,
            user_display_name=user_email
        )
        
        # Store challenge and options in session for verification
        session['webauthn_challenge'] = options.challenge
        session['webauthn_user_id'] = identity_id
        session['webauthn_device_name'] = device_name
        
        # Convert options to format expected by @simplewebauthn/browser
        options_dict = {
            'publicKey': {
                'challenge': options.challenge.decode('latin-1'),
                'rp': {
                    'name': options.rp.name,
                    'id': options.rp.id
                },
                'user': {
                    'id': options.user.id.decode('latin-1'),
                    'name': options.user.name,
                    'displayName': options.user.display_name
                },
                'pubKeyCredParams': [
                    {'alg': param.alg, 'type': param.type.value} 
                    for param in options.pub_key_cred_params
                ],
                'timeout': 60000,
                'attestation': options.attestation.value,
                'authenticatorSelection': {
                    'authenticatorAttachment': options.authenticator_selection.authenticator_attachment.value if options.authenticator_selection.authenticator_attachment else None,
                    'userVerification': options.authenticator_selection.user_verification.value,
                    'residentKey': options.authenticator_selection.resident_key.value if options.authenticator_selection.resident_key else 'preferred'
                },
                'excludeCredentials': []
            }
        }
        
        logger.info(f"✅ WebAuthn registration options generated for: {user_email}")
        
        return jsonify({
            'success': True,
            'options': options_dict,
            'device_name': device_name
        })
        
    except Exception as e:
        logger.error(f"Error generating WebAuthn options: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to generate WebAuthn options: {str(e)}'}), 500

@webauthn_enrollment_bp.route('/setup/complete', methods=['POST'])
@api_key_optional()
def setup_webauthn_complete():
    """
    Complete WebAuthn registration server-side
    Handles credential verification and storage
    """
    try:
        # Get credential data from request
        data = request.get_json() or {}
        credential_data = data.get('credential')
        
        if not credential_data:
            return jsonify({'error': 'No credential data provided'}), 400
        
        # Get stored challenge and user info
        challenge = session.get('webauthn_challenge')
        user_id = session.get('webauthn_user_id')
        user_email = session.get('user_email')
        device_name = session.get('webauthn_device_name', 'Enrollment Device')
        
        if not challenge or not user_id or not user_email:
            return jsonify({'error': 'No active WebAuthn registration'}), 400
        
        logger.info(f"🔐 Completing WebAuthn registration for: {user_email}")
        
        # Convert credential data for verification
        credential = RegistrationCredential.parse_raw(json.dumps(credential_data))
        
        # Verify the registration
        verification_result = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin="https://localhost:8443",
            expected_rp_id="localhost"
        )
        
        if verification_result.verified:
            logger.info("✅ WebAuthn credential verification successful")
            
            # Store the passkey in STING database
            from app.models.passkey_models import Passkey
            from app.models.user_models import User  
            from app import db
            
            # Get or create STING user
            user = User.query.filter_by(email=user_email).first()
            if not user:
                # Create STING user record
                user = User(
                    email=user_email,
                    role='admin',  # Default for enrollment
                    status='active'
                )
                db.session.add(user)
                db.session.flush()  # Get ID
            
            # Store the passkey
            new_passkey = Passkey(
                user_id=user.id,
                credential_id=verification_result.credential_id.decode(),
                public_key=verification_result.credential_public_key.decode(),
                sign_count=verification_result.sign_count,
                name=device_name,
                device_type='enrollment',
                status='ACTIVE'
            )
            
            db.session.add(new_passkey)
            db.session.commit()
            
            # CRITICAL: Establish Flask session for immediate dashboard access
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['auth_method'] = 'webauthn_enrollment'
            session['authenticated_at'] = datetime.utcnow().isoformat()
            session['session_id'] = f"enrollment_{user.email}_{int(time.time())}"
            
            # Clear WebAuthn session data
            session.pop('webauthn_challenge', None)
            session.pop('webauthn_user_id', None)
            session.pop('webauthn_device_name', None)
            
            logger.info(f"🔒 WebAuthn enrollment completed and Flask session established: {user_email}")
            
            return jsonify({
                'success': True,
                'message': 'Passkey registered successfully',
                'device_name': device_name,
                'credential_id': verification_result.credential_id.decode()
            })
        else:
            logger.warning("❌ WebAuthn credential verification failed")
            return jsonify({'error': 'Passkey verification failed'}), 400
        
    except Exception as e:
        logger.error(f"Error completing WebAuthn registration: {str(e)}", exc_info=True)
        return jsonify({'error': f'Passkey registration failed: {str(e)}'}), 500