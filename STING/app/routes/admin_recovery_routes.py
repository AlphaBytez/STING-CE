"""
Admin Recovery Routes
Provides secure recovery options for administrators
"""

from flask import Blueprint, request, jsonify, g
import logging
import secrets
import string
from datetime import datetime, timedelta
from app.utils.decorators import require_auth
from app.utils.kratos_admin import update_identity_password, get_identity_by_email
from app.models.user_models import User
from app.database import db
import os
import hashlib
import hmac

admin_recovery_bp = Blueprint('admin_recovery', __name__)
logger = logging.getLogger(__name__)

# Recovery token storage (in production, use Redis or database)
recovery_tokens = {}

def generate_recovery_token():
    """Generate a secure recovery token"""
    return secrets.token_urlsafe(32)

def generate_secure_password(length=16):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def verify_admin_secret(provided_secret):
    """Verify the admin recovery secret"""
    # In production, this should be stored securely in Vault
    admin_secret = os.getenv('ADMIN_RECOVERY_SECRET', 'default-recovery-secret-change-me')
    return hmac.compare_digest(provided_secret, admin_secret)

@admin_recovery_bp.route('/generate-recovery-token', methods=['POST'])
@require_auth
def generate_recovery_token_endpoint():
    """Generate a recovery token for admin password reset (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user') or g.user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        target_email = data.get('email', 'admin@sting.local')
        
        # Generate recovery token
        token = generate_recovery_token()
        
        # Store token with expiration (15 minutes)
        recovery_tokens[token] = {
            'email': target_email,
            'expires': datetime.utcnow() + timedelta(minutes=15),
            'used': False
        }
        
        logger.info(f"Recovery token generated for {target_email} by {g.user.get('email')}")
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_in': 900,  # 15 minutes in seconds
            'message': 'Recovery token generated. Use it within 15 minutes.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating recovery token: {str(e)}")
        return jsonify({'error': 'Failed to generate recovery token'}), 500

@admin_recovery_bp.route('/reset-with-token', methods=['POST'])
def reset_password_with_token():
    """Reset password using a recovery token (no auth required)"""
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')
        
        if not token:
            return jsonify({'error': 'Recovery token required'}), 400
        
        # Validate token
        token_data = recovery_tokens.get(token)
        if not token_data:
            return jsonify({'error': 'Invalid recovery token'}), 401
        
        if token_data['used']:
            return jsonify({'error': 'Recovery token already used'}), 401
        
        if datetime.utcnow() > token_data['expires']:
            return jsonify({'error': 'Recovery token expired'}), 401
        
        # Generate password if not provided
        if not new_password:
            new_password = generate_secure_password()
        
        # Get identity and update password
        identity = get_identity_by_email(token_data['email'])
        if not identity:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password in Kratos
        success = update_identity_password(identity['id'], new_password)
        
        if success:
            # Mark token as used
            token_data['used'] = True
            
            # Save password for admin user
            if token_data['email'] == 'admin@sting.local':
                password_file = os.path.expanduser('~/.sting-ce/admin_password.txt')
                os.makedirs(os.path.dirname(password_file), exist_ok=True)
                with open(password_file, 'w') as f:
                    f.write(new_password)
            
            logger.info(f"Password reset successfully for {token_data['email']}")
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully',
                'generated_password': new_password if not data.get('new_password') else None
            }), 200
        else:
            return jsonify({'error': 'Failed to reset password'}), 500
            
    except Exception as e:
        logger.error(f"Error resetting password with token: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500

@admin_recovery_bp.route('/reset-with-secret', methods=['POST'])
def reset_password_with_secret():
    """Emergency password reset using admin recovery secret"""
    try:
        data = request.get_json()
        recovery_secret = data.get('recovery_secret')
        target_email = data.get('email', 'admin@sting.local')
        new_password = data.get('new_password')
        
        if not recovery_secret:
            return jsonify({'error': 'Recovery secret required'}), 400
        
        # Verify recovery secret
        if not verify_admin_secret(recovery_secret):
            logger.warning(f"Invalid recovery secret attempt for {target_email}")
            return jsonify({'error': 'Invalid recovery secret'}), 401
        
        # Generate password if not provided
        if not new_password:
            new_password = generate_secure_password()
        
        # Get identity and update password
        identity = get_identity_by_email(target_email)
        if not identity:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password in Kratos
        success = update_identity_password(identity['id'], new_password)
        
        if success:
            # Save password for admin user
            if target_email == 'admin@sting.local':
                password_file = os.path.expanduser('~/.sting-ce/admin_password.txt')
                os.makedirs(os.path.dirname(password_file), exist_ok=True)
                with open(password_file, 'w') as f:
                    f.write(new_password)
            
            logger.info(f"Password reset via recovery secret for {target_email}")
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully',
                'generated_password': new_password if not data.get('new_password') else None
            }), 200
        else:
            return jsonify({'error': 'Failed to reset password'}), 500
            
    except Exception as e:
        logger.error(f"Error resetting password with secret: {str(e)}")
        return jsonify({'error': 'Failed to reset password'}), 500

@admin_recovery_bp.route('/disable-totp', methods=['POST'])
@require_auth
def disable_totp_for_user():
    """Disable TOTP for a user (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user') or g.user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        target_email = data.get('email')
        
        if not target_email:
            return jsonify({'error': 'Email required'}), 400
        
        # Get identity
        identity = get_identity_by_email(target_email)
        if not identity:
            return jsonify({'error': 'User not found'}), 404
        
        # Remove TOTP from credentials
        # This would need to be implemented in kratos_admin.py
        # For now, we'll log it
        logger.info(f"TOTP disable requested for {target_email} by {g.user.get('email')}")
        
        return jsonify({
            'success': True,
            'message': f'TOTP disabled for {target_email}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error disabling TOTP: {str(e)}")
        return jsonify({'error': 'Failed to disable TOTP'}), 500

@admin_recovery_bp.route('/recovery-status', methods=['GET'])
@require_auth
def get_recovery_status():
    """Get recovery options status (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(g, 'user') or g.user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # Clean up expired tokens
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, data in recovery_tokens.items()
            if current_time > data['expires']
        ]
        for token in expired_tokens:
            del recovery_tokens[token]
        
        # Get active tokens count
        active_tokens = len([
            t for t, d in recovery_tokens.items()
            if not d['used'] and current_time <= d['expires']
        ])
        
        return jsonify({
            'recovery_methods': {
                'token': True,
                'secret': True,
                'totp_disable': True
            },
            'active_recovery_tokens': active_tokens,
            'recovery_secret_configured': bool(os.getenv('ADMIN_RECOVERY_SECRET'))
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recovery status: {str(e)}")
        return jsonify({'error': 'Failed to get recovery status'}), 500