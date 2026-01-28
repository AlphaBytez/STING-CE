# app/routes/recovery_routes.py
"""
Recovery codes routes for STING application.
Handles generation, verification, and management of recovery codes for backup authentication.
"""

from flask import Blueprint, request, jsonify, g, session
from flask_cors import CORS
from app.models.recovery_code_models import RecoveryCode
from app.utils.decorators import require_auth_method, require_dual_factor
from app import db
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
recovery_bp = Blueprint('recovery', __name__, url_prefix='/api/recovery')
CORS(recovery_bp, supports_credentials=True)

@recovery_bp.route('/codes/status', methods=['GET'])
@require_auth_method(['webauthn', 'totp'])  # Tier 2: Requires secure authentication
def get_recovery_codes_status():
    """Get status of recovery codes for the current user"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401

        user_id = g.user.kratos_id
        user_email = g.user.email

        status = RecoveryCode.get_user_codes_status(user_id)

        return jsonify({
            'status': status,
            'user_email': user_email,
            'recommendation': _get_recommendation(status)
        })

    except Exception as e:
        logger.error(f"Error getting recovery codes status: {str(e)}")
        return jsonify({'error': 'Failed to get recovery codes status'}), 500

@recovery_bp.route('/codes/generate', methods=['POST'])
@require_dual_factor(['webauthn', 'totp'], ['email'])  # Tier 3: Critical operation
def generate_recovery_codes():
    """Generate new recovery codes for the current user"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401

        user_id = g.user.kratos_id
        user_email = g.user.email

        # Parse request data
        data = request.get_json() or {}
        count = data.get('count', 10)

        # Validate count
        if not isinstance(count, int) or count < 1 or count > 20:
            return jsonify({
                'error': 'Invalid count',
                'message': 'Count must be between 1 and 20'
            }), 400

        # Generate codes
        recovery_codes, plaintext_codes = RecoveryCode.generate_codes_for_user(
            user_id=user_id,
            user_email=user_email,
            count=count
        )

        # Commit to database
        db.session.commit()

        logger.info(f"Generated {count} recovery codes for user {user_email}")

        return jsonify({
            'message': f'Successfully generated {count} recovery codes',
            'codes': plaintext_codes,
            'warning': 'Store these codes safely. They will not be shown again.',
            'count': len(plaintext_codes),
            'expires_in_days': 365
        }), 201

    except Exception as e:
        logger.error(f"Error generating recovery codes: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to generate recovery codes'}), 500

@recovery_bp.route('/codes/verify', methods=['POST'])
def verify_recovery_code():
    """Verify a recovery code for authentication"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400

        code = data.get('code', '').strip()
        user_id = data.get('user_id', '').strip()

        if not code or not user_id:
            return jsonify({
                'error': 'Code and user_id are required'
            }), 400

        # Get client IP and user agent for audit
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        # Verify the code
        is_valid = RecoveryCode.verify_user_code(
            user_id=user_id,
            code=code,
            ip_address=client_ip,
            user_agent=user_agent
        )

        if is_valid:
            # Get updated status
            status = RecoveryCode.get_user_codes_status(user_id)

            logger.info(f"Recovery code verified successfully for user {user_id}")
            return jsonify({
                'valid': True,
                'message': 'Recovery code verified successfully',
                'remaining_codes': status['valid_codes']
            })
        else:
            logger.warning(f"Invalid recovery code attempt for user {user_id} from IP {client_ip}")
            return jsonify({
                'valid': False,
                'message': 'Invalid or expired recovery code'
            }), 401

    except Exception as e:
        logger.error(f"Error verifying recovery code: {str(e)}")
        return jsonify({'error': 'Failed to verify recovery code'}), 500

@recovery_bp.route('/codes/list', methods=['GET'])
@require_auth_method(['webauthn', 'totp'])  # Tier 2: View recovery codes metadata
def list_recovery_codes():
    """List recovery codes metadata (not the actual codes)"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401

        user_id = g.user.kratos_id

        # Get all recovery codes for user (without sensitive data)
        codes = RecoveryCode.query.filter_by(user_id=user_id).order_by(
            RecoveryCode.created_at.desc()
        ).all()

        return jsonify({
            'codes': [code.to_dict(include_sensitive=False) for code in codes],
            'status': RecoveryCode.get_user_codes_status(user_id)
        })

    except Exception as e:
        logger.error(f"Error listing recovery codes: {str(e)}")
        return jsonify({'error': 'Failed to list recovery codes'}), 500

@recovery_bp.route('/codes/revoke', methods=['POST'])
@require_dual_factor(['webauthn', 'totp'], ['email'])  # Tier 3: Critical operation
def revoke_recovery_codes():
    """Revoke all unused recovery codes for the current user"""
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401

        user_id = g.user.kratos_id
        user_email = g.user.email

        # Mark all unused codes as used (effectively revoking them)
        unused_codes = RecoveryCode.query.filter_by(
            user_id=user_id,
            is_used=False
        ).filter(
            RecoveryCode.expires_at > RecoveryCode.created_at  # Not expired
        ).all()

        revoked_count = 0
        for code in unused_codes:
            code.mark_as_used(
                ip_address=request.remote_addr,
                user_agent="REVOKED_BY_USER"
            )
            revoked_count += 1

        db.session.commit()

        logger.info(f"Revoked {revoked_count} recovery codes for user {user_email}")

        return jsonify({
            'message': f'Successfully revoked {revoked_count} recovery codes',
            'revoked_count': revoked_count,
            'remaining_codes': 0
        })

    except Exception as e:
        logger.error(f"Error revoking recovery codes: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to revoke recovery codes'}), 500

def _get_recommendation(status):
    """Get recommendation based on recovery codes status"""
    if status['valid_codes'] == 0:
        return "Generate recovery codes for account backup access"
    elif status['valid_codes'] < 3:
        return "Consider generating more recovery codes"
    elif status['valid_codes'] > 15:
        return "You have many recovery codes - consider using some or revoking old ones"
    else:
        return "Recovery codes are properly configured"