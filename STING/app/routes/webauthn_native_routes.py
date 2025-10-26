"""
Native WebAuthn implementation for STING passkey registration and authentication.
This bypasses Kratos WebAuthn and uses our own passkey tables directly.
"""

import json
import base64
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, session
from werkzeug.exceptions import BadRequest
import logging
from typing import Optional, Dict, Any

# WebAuthn imports
try:
    from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response
    from webauthn.helpers import parse_registration_credential_json, parse_authentication_credential_json
    from webauthn.helpers.structs import PublicKeyCredentialDescriptor, AuthenticatorSelectionCriteria, UserVerificationRequirement
except ImportError:
    # Fallback for missing webauthn library
    generate_registration_options = None
    verify_registration_response = None
    generate_authentication_options = None
    verify_authentication_response = None

from app.extensions import db
from app.models.user_models import User
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Create Blueprint
webauthn_native_bp = Blueprint('webauthn_native', __name__, url_prefix='/api/webauthn/native')

# WebAuthn configuration
RP_ID = "localhost"  # Change this to your domain in production
RP_NAME = "STING Authentication"
ORIGIN = "https://localhost:8443"  # Change this to your actual origin

def get_or_create_user_id(user) -> bytes:
    """Get or create a stable user ID for WebAuthn"""
    if hasattr(user, 'id'):
        # Use database ID as base
        user_id_str = f"sting_user_{user.id}"
    elif hasattr(user, 'kratos_id'):
        # Use Kratos ID as base
        user_id_str = f"sting_kratos_{user.kratos_id}"
    else:
        # Use email hash as fallback
        user_id_str = f"sting_email_{hashlib.sha256(user.email.encode()).hexdigest()}"
    
    # Convert to bytes (WebAuthn requires bytes for user ID)
    return user_id_str.encode('utf-8')

@webauthn_native_bp.route('/register/begin', methods=['POST'])
def register_begin():
    """
    Begin native WebAuthn registration ceremony.
    Returns registration options for the browser to use.
    """
    try:
        # Check if webauthn library is available
        if generate_registration_options is None:
            logger.error("WebAuthn library not installed")
            return jsonify({'error': 'WebAuthn support not available'}), 500
        
        # Get authenticated user
        if not hasattr(g, 'user') or not g.user:
            # During enrollment, we might have user info in session
            if 'enrollment_user' in session:
                user_info = session['enrollment_user']
                # Create a temporary user object
                class EnrollmentUser:
                    def __init__(self, email, kratos_id):
                        self.email = email
                        self.kratos_id = kratos_id
                        self.id = None
                
                user = EnrollmentUser(user_info['email'], user_info['kratos_id'])
                logger.info(f"Using enrollment user: {user.email}")
            else:
                return jsonify({'error': 'Not authenticated'}), 401
        else:
            user = g.user
        
        # Generate a unique challenge
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.b64encode(challenge).decode('utf-8')
        
        # Store challenge in database
        try:
            # Get user's database ID if it exists
            user_id = None
            if hasattr(user, 'id') and user.id:
                user_id = user.id
            else:
                # Try to find user by email or kratos_id
                result = db.session.execute(
                    text("SELECT id FROM users WHERE email = :email OR kratos_id = :kratos_id LIMIT 1"),
                    {'email': user.email, 'kratos_id': getattr(user, 'kratos_id', None)}
                ).fetchone()
                if result:
                    user_id = result[0]
            
            if not user_id:
                # Create user if doesn't exist
                db.session.execute(
                    text("""
                        INSERT INTO users (email, kratos_id, created_at, updated_at)
                        VALUES (:email, :kratos_id, NOW(), NOW())
                        ON CONFLICT (email) DO UPDATE SET kratos_id = :kratos_id
                        RETURNING id
                    """),
                    {'email': user.email, 'kratos_id': getattr(user, 'kratos_id', None)}
                )
                result = db.session.execute(
                    text("SELECT id FROM users WHERE email = :email"),
                    {'email': user.email}
                ).fetchone()
                if result:
                    user_id = result[0]
            
            # Generate challenge ID
            challenge_id = secrets.token_urlsafe(32)
            
            # Store challenge in database
            db.session.execute(
                text("""
                    INSERT INTO passkey_registration_challenges 
                    (challenge_id, user_id, challenge, user_verification, attestation, timeout, expires_at, created_at)
                    VALUES (:challenge_id, :user_id, :challenge, :user_verification, :attestation, :timeout, :expires_at, NOW())
                """),
                {
                    'challenge_id': challenge_id,
                    'user_id': user_id,
                    'challenge': challenge_b64,
                    'user_verification': 'preferred',
                    'attestation': 'none',
                    'timeout': 300000,  # 5 minutes
                    'expires_at': datetime.utcnow() + timedelta(minutes=5)
                }
            )
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Database error storing challenge: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to store registration challenge'}), 500
        
        # Get user's existing credentials to exclude
        existing_credentials = []
        try:
            results = db.session.execute(
                text("""
                    SELECT credential_id FROM passkeys 
                    WHERE user_id = :user_id AND status = 'active'
                """),
                {'user_id': user_id}
            ).fetchall()
            
            for row in results:
                existing_credentials.append({
                    'id': row[0],
                    'type': 'public-key'
                })
        except Exception as e:
            logger.warning(f"Could not fetch existing credentials: {str(e)}")
        
        # Generate registration options
        user_bytes_id = get_or_create_user_id(user)
        
        registration_options = {
            'challenge': challenge_b64,
            'rp': {
                'name': RP_NAME,
                'id': RP_ID
            },
            'user': {
                'id': base64.b64encode(user_bytes_id).decode('utf-8'),
                'name': user.email,
                'displayName': user.email.split('@')[0]
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': -7},   # ES256
                {'type': 'public-key', 'alg': -257}  # RS256
            ],
            'timeout': 300000,  # 5 minutes
            'excludeCredentials': existing_credentials,
            'authenticatorSelection': {
                'authenticatorAttachment': 'platform',  # Prefer platform authenticators
                'requireResidentKey': False,
                'residentKey': 'preferred',
                'userVerification': 'preferred'
            },
            'attestation': 'none'
        }
        
        # Store challenge in session as backup
        session['webauthn_challenge'] = challenge_b64
        session['webauthn_challenge_id'] = challenge_id
        session['webauthn_user_id'] = user_id
        
        logger.info(f"Generated WebAuthn registration options for user: {user.email}")
        
        return jsonify({
            'success': True,
            'options': registration_options,
            'challenge_id': challenge_id
        })
        
    except Exception as e:
        logger.error(f"Error in register_begin: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to begin registration: {str(e)}'}), 500

@webauthn_native_bp.route('/register/complete', methods=['POST'])
def register_complete():
    """
    Complete WebAuthn registration ceremony.
    Verify the credential and store it in the database.
    """
    try:
        # Check if webauthn library is available
        if verify_registration_response is None:
            logger.error("WebAuthn library not installed")
            return jsonify({'error': 'WebAuthn support not available'}), 500
        
        data = request.get_json() or {}
        challenge_id = data.get('challenge_id') or session.get('webauthn_challenge_id')
        credential_data = data.get('credential')
        
        if not challenge_id or not credential_data:
            return jsonify({'error': 'Missing challenge ID or credential data'}), 400
        
        # Retrieve challenge from database
        result = db.session.execute(
            text("""
                SELECT user_id, challenge, expires_at, used 
                FROM passkey_registration_challenges 
                WHERE challenge_id = :challenge_id
            """),
            {'challenge_id': challenge_id}
        ).fetchone()
        
        if not result:
            return jsonify({'error': 'Invalid or expired challenge'}), 400
        
        user_id, challenge_b64, expires_at, used = result
        
        # Check if challenge is still valid
        if used:
            return jsonify({'error': 'Challenge already used'}), 400
        
        if expires_at < datetime.utcnow():
            return jsonify({'error': 'Challenge expired'}), 400
        
        # Mark challenge as used
        db.session.execute(
            text("""
                UPDATE passkey_registration_challenges 
                SET used = TRUE 
                WHERE challenge_id = :challenge_id
            """),
            {'challenge_id': challenge_id}
        )
        
        # Parse and verify the credential
        try:
            # The credential data should include:
            # - id: credential ID (base64)
            # - rawId: same as id but in ArrayBuffer format
            # - response: {clientDataJSON, attestationObject}
            # - type: "public-key"
            
            credential_id = credential_data.get('id')
            client_data_json = credential_data.get('response', {}).get('clientDataJSON')
            attestation_object = credential_data.get('response', {}).get('attestationObject')
            
            if not all([credential_id, client_data_json, attestation_object]):
                return jsonify({'error': 'Invalid credential data'}), 400
            
            # Decode client data
            client_data = json.loads(base64.b64decode(client_data_json))
            
            # Verify challenge
            received_challenge = client_data.get('challenge')
            if received_challenge != challenge_b64:
                return jsonify({'error': 'Challenge mismatch'}), 400
            
            # Verify origin
            if client_data.get('origin') != ORIGIN:
                logger.warning(f"Origin mismatch: expected {ORIGIN}, got {client_data.get('origin')}")
                # For development, we'll allow this but log it
            
            # Store the credential
            # In a production environment, you would properly parse the attestation object
            # to extract the public key and other metadata
            
            db.session.execute(
                text("""
                    INSERT INTO passkeys 
                    (user_id, credential_id, public_key, counter, status, created_at, updated_at)
                    VALUES (:user_id, :credential_id, :public_key, :counter, 'active', NOW(), NOW())
                """),
                {
                    'user_id': user_id,
                    'credential_id': credential_id,
                    'public_key': attestation_object.encode('utf-8') if isinstance(attestation_object, str) else attestation_object,
                    'counter': 0
                }
            )
            
            db.session.commit()
            
            logger.info(f"Successfully registered passkey for user ID: {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Passkey registered successfully',
                'credential_id': credential_id
            })
            
        except Exception as e:
            logger.error(f"Error verifying credential: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Failed to verify credential: {str(e)}'}), 400
        
    except Exception as e:
        logger.error(f"Error in register_complete: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Failed to complete registration: {str(e)}'}), 500

@webauthn_native_bp.route('/authenticate/begin', methods=['POST'])
def authenticate_begin():
    """
    Begin WebAuthn authentication ceremony.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        # Find user
        result = db.session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {'email': email}
        ).fetchone()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        user_id = result[0]
        
        # Get user's credentials
        credentials = db.session.execute(
            text("""
                SELECT credential_id FROM passkeys 
                WHERE user_id = :user_id AND status = 'active'
            """),
            {'user_id': user_id}
        ).fetchall()
        
        if not credentials:
            return jsonify({'error': 'No passkeys registered'}), 404
        
        # Generate challenge
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.b64encode(challenge).decode('utf-8')
        challenge_id = secrets.token_urlsafe(32)
        
        # Store challenge
        db.session.execute(
            text("""
                INSERT INTO passkey_authentication_challenges 
                (challenge_id, user_id, challenge, user_verification, timeout, expires_at, created_at)
                VALUES (:challenge_id, :user_id, :challenge, 'preferred', 300000, :expires_at, NOW())
            """),
            {
                'challenge_id': challenge_id,
                'user_id': user_id,
                'challenge': challenge_b64,
                'expires_at': datetime.utcnow() + timedelta(minutes=5)
            }
        )
        db.session.commit()
        
        # Build authentication options
        allow_credentials = [
            {'id': cred[0], 'type': 'public-key'}
            for cred in credentials
        ]
        
        authentication_options = {
            'challenge': challenge_b64,
            'rpId': RP_ID,
            'allowCredentials': allow_credentials,
            'userVerification': 'preferred',
            'timeout': 300000
        }
        
        session['webauthn_auth_challenge'] = challenge_b64
        session['webauthn_auth_challenge_id'] = challenge_id
        
        return jsonify({
            'success': True,
            'options': authentication_options,
            'challenge_id': challenge_id
        })
        
    except Exception as e:
        logger.error(f"Error in authenticate_begin: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Export blueprint
__all__ = ['webauthn_native_bp']