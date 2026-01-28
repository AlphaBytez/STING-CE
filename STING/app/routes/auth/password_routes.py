"""
Password Management Routes

Handles password change, verification, and admin password notice operations.
"""

from flask import Blueprint, request, jsonify, session, g
import logging
import os

from app.utils.decorators import require_auth
from app.services.password_service import PasswordService
from app.utils.kratos_client import whoami

logger = logging.getLogger(__name__)

password_bp = Blueprint('password', __name__)

# Get Kratos URLs from config
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
KRATOS_BROWSER_URL = os.getenv('KRATOS_BROWSER_URL', 'https://kratos:4433')


@password_bp.after_request
def after_request(response):
    """Add CORS headers specifically for password endpoints"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@password_bp.route('/change-password', methods=['POST', 'OPTIONS'])
@require_auth
def change_password():
    """Change user password and clear force_password_change flag"""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        logger.info(f"Password change request received - Method: {request.method}, Headers: {dict(request.headers)}")
        
        # Get current user
        user = g.user
        if not user:
            logger.error("No authenticated user found in change_password")
            logger.error(f"g.user: {getattr(g, 'user', 'not set')}, g.identity: {getattr(g, 'identity', 'not set')}")
            return jsonify({'error': 'Not authenticated'}), 401
            
        logger.info(f"Processing password change for user: {user.email}")
            
        # Check content type
        if request.content_type != 'application/json':
            logger.error(f"Invalid content type: {request.content_type}")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        if not data:
            logger.error("No JSON data in request body")
            return jsonify({'error': 'Invalid request data'}), 400
            
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        logger.info(f"Received password change request with data keys: {list(data.keys())}")
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Use password service to change password
        success, error_message = PasswordService.change_password(user, current_password, new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Password changed successfully',
                'redirect': '/setup-totp'  # Tell frontend where to redirect for admin users
            })
        else:
            return jsonify({'error': error_message}), 400
            
    except Exception as e:
        logger.error(f"Error in change password: {e}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@password_bp.route('/verify-password', methods=['POST'])
def verify_password():
    """Verify user's password for sensitive operations"""
    try:
        # First check if user is authenticated via Flask session (passkey auth)
        if hasattr(g, 'user') and g.user:
            data = request.get_json()
            password = data.get('password')
            
            if not password:
                return jsonify({
                    'error': 'Password is required'
                }), 400
            
            # Check if this is a Kratos-authenticated user with password
            user = g.user
            
            # For users authenticated via Kratos with password, we need to verify
            if hasattr(g, 'identity') and g.identity:
                # Check if user has force_password_change flag
                from app.utils.kratos_admin import get_identity_by_email
                try:
                    identity = get_identity_by_email(user.email)
                    if identity and identity.get('traits', {}).get('force_password_change', False):
                        # For users with force_password_change, we'll temporarily accept verification
                        # This allows them to set up passkeys even before changing password
                        logger.info(f"Password verification bypassed for user with force_password_change: {user.email}")
                        return jsonify({
                            'verified': True,
                            'message': 'Verification successful',
                            'notice': 'Please change your password after setting up your passkey'
                        })
                except Exception as e:
                    logger.error(f"Error checking force_password_change flag: {e}")
                
                # For regular Kratos users with g.identity, we need to verify the password
                # Get the email from g.identity
                email = g.identity.get('traits', {}).get('email')
                if not email:
                    # Fallback to user email from database
                    email = user.email
                
                # Verify password using service
                is_valid, error_message = PasswordService.verify_password_for_session(email, password)
                
                if is_valid:
                    logger.info(f"Password verified successfully for {email}")
                    return jsonify({
                        'verified': True,
                        'message': 'Password verified successfully'
                    })
                else:
                    return jsonify({
                        'verified': False,
                        'error': error_message or 'Invalid password'
                    }), 401
            else:
                # For passkey-authenticated users without Kratos session
                logger.warning(f"Password verification for non-Kratos user: {user.email}")
                return jsonify({
                    'verified': False,
                    'error': 'Password verification requires Kratos authentication',
                    'redirect': '/login'
                })
        
        # Check if user is authenticated via Kratos session
        kratos_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        
        if not kratos_cookie:
            return jsonify({
                'error': 'User not authenticated'
            }), 401
        
        # Get identity from Kratos
        try:
            identity = whoami(kratos_cookie)
            if not identity or not identity.get('active'):
                return jsonify({
                    'error': 'Invalid session'
                }), 401
        except Exception as e:
            logger.error(f"Error checking Kratos session: {e}")
            return jsonify({
                'error': 'Failed to verify session'
            }), 500
        
        # Get password from request
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({
                'error': 'Password is required'
            }), 400
        
        # Get email from identity
        email = identity.get('traits', {}).get('email')
        if not email:
            return jsonify({
                'error': 'Could not determine user email'
            }), 500
        
        # Verify password using service
        is_valid, error_message = PasswordService.verify_password_for_session(email, password)
        
        if is_valid:
            return jsonify({
                'verified': True,
                'message': 'Password verified successfully'
            })
        else:
            return jsonify({
                'verified': False,
                'error': error_message or 'Invalid password'
            }), 401
            
    except Exception as e:
        logger.error(f"Error in password verification: {str(e)}")
        return jsonify({
            'error': 'Failed to verify password'
        }), 500


@password_bp.route('/admin-notice', methods=['GET'])
def get_admin_notice():
    """Get admin credentials notice if password hasn't been changed"""
    try:
        notice_data = PasswordService.check_admin_password_notice()
        
        if 'error' in notice_data:
            return jsonify(notice_data), 500
        else:
            return jsonify(notice_data)
        
    except Exception as e:
        logger.error(f"Error getting admin notice: {e}")
        return jsonify({
            'show_notice': False,
            'error': 'Failed to get admin notice'
        }), 500


@password_bp.route('/password-change-login', methods=['POST'])
def password_change_login():
    """Special login endpoint for users who must change their password"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Check if user needs password change
        needs_change, error_message = PasswordService.check_force_password_change(email)
        
        if error_message and 'not found' in error_message:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not needs_change:
            # User doesn't need to change password - redirect to normal login
            return jsonify({
                'error': 'Please use the regular login',
                'redirect': '/login'
            }), 400
        
        # Direct user to Kratos login flow which will create proper session
        return jsonify({
            'success': True,
            'message': 'Please complete login through Kratos',
            'redirect': f'{KRATOS_BROWSER_URL}/self-service/login/browser',
            'note': 'You will be redirected to change password after login'
        })
        
    except Exception as e:
        logger.error(f"Error in password change login: {e}")
        return jsonify({'error': 'Login failed'}), 500


@password_bp.route('/test-change-password', methods=['GET'])
def test_change_password():
    """Test endpoint for password change functionality"""
    try:
        # This is a test endpoint to verify password change flow
        return jsonify({
            'message': 'Password change endpoint is working',
            'available_endpoints': [
                '/change-password',
                '/verify-password',
                '/admin-notice',
                '/password-change-login'
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in test change password: {e}")
        return jsonify({
            'error': 'Test failed'
        }), 500