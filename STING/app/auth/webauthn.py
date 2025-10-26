"""
Custom WebAuthn implementation for passkey management
"""
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
import base64
import json
import uuid
from datetime import datetime
from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response
from webauthn.helpers.structs import PublicKeyCredentialDescriptor
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from app.database import db
from app.models.passkey_models import Passkey, PasskeyRegistrationChallenge

webauthn_bp = Blueprint('webauthn', __name__)

# WebAuthn configuration
RP_ID = "localhost"
RP_NAME = "STING Platform"
ORIGIN = "https://localhost:8443"

def kratos_required(f):
    """Decorator to require Kratos authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'kratos_identity') or not g.kratos_identity:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

@webauthn_bp.route('/passkeys', methods=['GET'])
@kratos_required
def get_passkeys():
    """Get all passkeys for the current user"""
    try:
        passkeys = Passkey.query.filter_by(
            user_id=str(g.kratos_identity['id'])
        ).all()
        
        return jsonify({
            'passkeys': [{
                'id': pk.id,
                'name': pk.name,
                'credential_id': pk.credential_id,
                'created_at': pk.created_at.isoformat(),
                'last_used_at': pk.last_used_at.isoformat() if pk.last_used_at else None,
                'usage_count': pk.usage_count,
                'device_type': pk.device_type,
                'status': 'active'
            } for pk in passkeys]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/passkeys/add/begin', methods=['POST'])
@kratos_required
def register_begin():
    """Begin passkey registration"""
    try:
        data = request.get_json()
        name = data.get('name', 'My Passkey')
        
        # Get existing credentials to exclude
        existing_credentials = Passkey.query.filter_by(
            user_id=str(g.kratos_identity['id'])
        ).all()
        
        exclude_credentials = []
        for cred in existing_credentials:
            exclude_credentials.append(
                PublicKeyCredentialDescriptor(
                    id=base64.b64decode(cred.credential_id),
                    type="public-key"
                )
            )
        
        # Generate registration options
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=str(g.kratos_identity['id']).encode(),
            user_name=g.kratos_identity['traits'].get('email', 'user@example.com'),
            user_display_name=g.kratos_identity['traits'].get('display_name', g.kratos_identity['traits'].get('email', 'user@example.com')),
            exclude_credentials=exclude_credentials,
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256
            ]
        )
        
        # Store challenge in session
        session['webauthn_challenge'] = base64.b64encode(options.challenge).decode()
        session['passkey_name'] = name
        
        # Convert to JSON-friendly format
        return jsonify({
            'challenge': base64.b64encode(options.challenge).decode(),
            'rp': {
                'id': options.rp.id,
                'name': options.rp.name
            },
            'user': {
                'id': base64.b64encode(options.user.id).decode(),
                'name': options.user.name,
                'displayName': options.user.display_name
            },
            'pubKeyCredParams': [
                {'type': 'public-key', 'alg': alg}
                for alg in options.pub_key_cred_params
            ],
            'excludeCredentials': [
                {
                    'id': base64.b64encode(cred.id).decode(),
                    'type': cred.type
                }
                for cred in options.exclude_credentials
            ],
            'authenticatorSelection': {
                'authenticatorAttachment': 'platform',
                'userVerification': 'preferred'
            },
            'attestation': 'none',
            'timeout': options.timeout
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/passkeys/add/complete', methods=['POST'])
@kratos_required
def register_complete():
    """Complete passkey registration"""
    try:
        data = request.get_json()
        credential = data.get('credential')
        
        if not credential:
            return jsonify({'error': 'No credential provided'}), 400
        
        # Get challenge from session
        challenge = session.get('webauthn_challenge')
        if not challenge:
            return jsonify({'error': 'No challenge found'}), 400
        
        # Verify registration
        verification = verify_registration_response(
            credential={
                'id': credential['id'],
                'rawId': credential['rawId'],
                'response': {
                    'clientDataJSON': credential['response']['clientDataJSON'],
                    'attestationObject': credential['response']['attestationObject']
                },
                'type': credential['type']
            },
            expected_challenge=base64.b64decode(challenge),
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID
        )
        
        if verification.verified:
            # Save credential
            new_credential = Passkey(
                user_id=str(g.kratos_identity['id']),
                name=session.get('passkey_name', 'My Passkey'),
                credential_id=base64.b64encode(verification.credential_id).decode(),
                public_key=base64.b64encode(verification.credential_public_key).decode(),
                device_type='platform' if 'platform' in credential.get('authenticatorAttachment', '') else 'cross-platform',
                is_backup_eligible=verification.backup_eligible if hasattr(verification, 'backup_eligible') else False,
                is_backup_state=verification.backup_state if hasattr(verification, 'backup_state') else False
            )
            db.session.add(new_credential)
            db.session.commit()
            
            # Clean up session
            session.pop('webauthn_challenge', None)
            session.pop('passkey_name', None)
            
            return jsonify({
                'success': True,
                'passkey': {
                    'id': new_credential.id,
                    'name': new_credential.name,
                    'created_at': new_credential.created_at.isoformat()
                }
            })
        else:
            return jsonify({'error': 'Verification failed'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/passkeys/<int:passkey_id>', methods=['DELETE'])
@kratos_required
def delete_passkey(passkey_id):
    """Delete a passkey"""
    try:
        passkey = Passkey.query.filter_by(
            id=passkey_id,
            user_id=str(g.kratos_identity['id'])
        ).first()
        
        if not passkey:
            return jsonify({'error': 'Passkey not found'}), 404
        
        db.session.delete(passkey)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/passkeys/<int:passkey_id>/rename', methods=['PUT'])
@kratos_required
def rename_passkey(passkey_id):
    """Rename a passkey"""
    try:
        data = request.get_json()
        new_name = data.get('name')
        
        if not new_name:
            return jsonify({'error': 'Name is required'}), 400
        
        passkey = Passkey.query.filter_by(
            id=passkey_id,
            user_id=str(g.kratos_identity['id'])
        ).first()
        
        if not passkey:
            return jsonify({'error': 'Passkey not found'}), 404
        
        passkey.name = new_name
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@webauthn_bp.route('/passkeys/stats', methods=['GET'])
@kratos_required
def get_passkey_stats():
    """Get passkey statistics for the current user"""
    try:
        passkeys = Passkey.query.filter_by(
            user_id=str(g.kratos_identity['id'])
        ).all()
        
        total = len(passkeys)
        platform_count = sum(1 for pk in passkeys if pk.device_type == 'platform')
        cross_platform_count = total - platform_count
        
        return jsonify({
            'total': total,
            'platform': platform_count,
            'cross_platform': cross_platform_count,
            'last_added': max([pk.created_at for pk in passkeys]).isoformat() if passkeys else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500