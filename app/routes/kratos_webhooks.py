"""
Kratos webhook handlers following best practices
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
import os
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
    """Check webhook authentication"""
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

@kratos_webhooks_bp.route('/health', methods=['GET'])
def webhook_health():
    """Health check for webhooks (doesn't require auth)"""
    return jsonify({"status": "healthy", "service": "kratos-webhooks"})