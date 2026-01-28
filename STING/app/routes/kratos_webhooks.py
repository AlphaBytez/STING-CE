"""
Kratos webhook handlers following best practices
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import os
import redis
import json
from app.database import db
from app.models.user_models import User

logger = logging.getLogger(__name__)

kratos_webhooks_bp = Blueprint('kratos_webhooks', __name__, url_prefix='/api/kratos/webhooks')

# Webhook token for security
WEBHOOK_TOKEN = os.environ.get('KRATOS_WEBHOOK_TOKEN', 'secure-webhook-token')

def verify_webhook_token():
    """Verify the webhook token"""
    token = request.headers.get('X-Webhook-Token')
    if token != WEBHOOK_TOKEN:
        logger.warning("Invalid webhook token")
        return False
    return True

@kratos_webhooks_bp.before_request
def check_webhook_auth():
    """Check webhook authentication (skip for health endpoint)"""
    # Skip auth check for health endpoint
    if request.endpoint and 'health' in request.endpoint:
        return None

    if not verify_webhook_token():
        return jsonify({"error": "Unauthorized"}), 401

@kratos_webhooks_bp.route('/user-registered', methods=['POST'])
def user_registered():
    """
    Called by Kratos after successful user registration
    """
    try:
        data = request.json
        identity = data.get('identity', {})
        
        logger.info(f"User registered webhook received for identity: {identity.get('id')}")
        
        # Create or update user in our database
        user = User.query.filter_by(kratos_id=identity['id']).first()
        
        if not user:
            # Create new user record
            user = User(
                kratos_id=identity['id'],
                email=identity['traits']['email'],
                first_name=identity['traits'].get('name', {}).get('first', ''),
                last_name=identity['traits'].get('name', {}).get('last', ''),
                status='ACTIVE',
                role='USER',  # Default role
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            logger.info(f"Created new user record for {user.email}")
        else:
            # Update existing user
            user.email = identity['traits']['email']
            user.first_name = identity['traits'].get('name', {}).get('first', '')
            user.last_name = identity['traits'].get('name', {}).get('last', '')
            user.updated_at = datetime.utcnow()
            logger.info(f"Updated user record for {user.email}")
        
        db.session.commit()
        
        # Here you can add additional logic like:
        # - Send welcome email
        # - Create default settings
        # - Initialize user workspace
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error in user_registered webhook: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@kratos_webhooks_bp.route('/password-changed', methods=['POST'])
def password_changed():
    """
    Called by Kratos after successful password change
    """
    try:
        data = request.json
        identity = data.get('identity', {})
        
        logger.info(f"Password changed webhook received for identity: {identity.get('id')}")
        
        # Update user record
        user = User.query.filter_by(kratos_id=identity['id']).first()
        
        if user:
            # Clear any password reset flags
            user.updated_at = datetime.utcnow()
            
            # Log the password change for audit
            logger.info(f"Password changed for user {user.email}")
            
            # Here you can add additional logic like:
            # - Send notification email
            # - Log security event
            # - Invalidate other sessions
            
            db.session.commit()
        else:
            logger.warning(f"User not found for kratos_id: {identity['id']}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error in password_changed webhook: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@kratos_webhooks_bp.route('/session-created', methods=['POST'])
def session_created():
    """
    Called by Kratos after successful login (optional)
    """
    try:
        data = request.json
        session = data.get('session', {})
        identity = session.get('identity', {})
        
        logger.info(f"Session created for identity: {identity.get('id')}")
        
        # Here you can add logic like:
        # - Log login event
        # - Update last login timestamp
        # - Check for suspicious activity
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error in session_created webhook: {e}")
        return jsonify({"error": str(e)}), 500

@kratos_webhooks_bp.route('/account-recovery', methods=['POST'])
def account_recovery():
    """
    Called by Kratos after successful account recovery.
    Sets a Redis flag to block credential addition until email is re-verified.

    Security: Prevents attackers from adding credentials immediately after
    account takeover via recovery flow.
    """
    try:
        data = request.json
        identity = data.get('identity', {})
        identity_id = identity.get('id')
        user_email = identity.get('traits', {}).get('email', 'unknown')

        if not identity_id:
            logger.error("Missing identity ID in recovery webhook")
            return jsonify({"error": "Invalid payload"}), 400

        logger.info(f"Account recovery completed for: {user_email} (ID: {identity_id})")

        # Set Redis flag to block credential addition
        redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))

        flag_data = {
            'user_id': identity_id,
            'email': user_email,
            'recovery_time': datetime.utcnow().isoformat(),
            'reason': 'account_recovery',
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }

        # Store flag with 7-day TTL (604800 seconds)
        redis_client.setex(
            f"sting:block_credentials:{identity_id}",
            604800,  # 7 days in seconds
            json.dumps(flag_data)
        )

        logger.info(f"Credential block flag set for {user_email} (7 day TTL)")
        logger.info(f"User must verify email before adding passkeys/TOTP")

        return jsonify({
            "success": True,
            "user_id": identity_id,
            "blocked_until_verification": True
        })

    except Exception as e:
        logger.error(f"Error in account recovery webhook: {e}", exc_info=True)
        # Still return success to Kratos - don't block recovery flow
        # But log error for monitoring
        return jsonify({"error": str(e)}), 500


@kratos_webhooks_bp.route('/email-verified', methods=['POST'])
def email_verified():
    """
    Called by Kratos after email verification.
    Clears the credential block flag set by account recovery.
    """
    try:
        data = request.json
        identity = data.get('identity', {})
        identity_id = identity.get('id')
        user_email = identity.get('traits', {}).get('email', 'unknown')

        if not identity_id:
            logger.error("Missing identity ID in verification webhook")
            return jsonify({"error": "Invalid payload"}), 400

        logger.info(f"Email verified for: {user_email} (ID: {identity_id})")

        # Clear the credential block flag
        redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
        block_key = f"sting:block_credentials:{identity_id}"

        if redis_client.exists(block_key):
            # Get flag data for logging
            flag_data_raw = redis_client.get(block_key)
            if flag_data_raw:
                flag_data = json.loads(flag_data_raw.decode('utf-8'))
                recovery_time = flag_data.get('recovery_time', 'unknown')
                logger.info(f"Clearing credential block from recovery at {recovery_time}")

            redis_client.delete(block_key)
            logger.info(f"Credential block flag cleared for {user_email}")
            logger.info(f"User can now add passkeys/TOTP")
        else:
            logger.debug(f"No credential block flag found for {user_email} (already cleared or never set)")

        return jsonify({
            "success": True,
            "user_id": identity_id,
            "credentials_unblocked": True
        })

    except Exception as e:
        logger.error(f"Error in email verification webhook: {e}", exc_info=True)
        # Still return success to Kratos - don't block verification flow
        return jsonify({"error": str(e)}), 500


@kratos_webhooks_bp.route('/health', methods=['GET'])
def webhook_health():
    """Health check for webhooks (doesn't require auth)"""
    return jsonify({"status": "healthy", "service": "kratos-webhooks"})