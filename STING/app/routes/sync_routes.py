"""
User Sync API Routes
Provides endpoints for managing user synchronization between Kratos and STING
"""

import logging
from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from app.services.user_sync_service import sync_service
from app.middleware.auth_middleware import require_admin

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)


@sync_bp.route('/api/sync/status', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_admin
def get_sync_status():
    """Get current sync status between Kratos and STING"""
    try:
        status = sync_service.get_sync_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/all', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_admin
def sync_all_users():
    """Perform full user sync between Kratos and STING"""
    try:
        results = sync_service.sync_all_users()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error syncing all users: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/user', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_admin
def sync_single_user():
    """Sync a single user by email"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        success = sync_service.sync_single_user(email)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'User {email} synced successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to sync user {email}'
            }), 400
            
    except Exception as e:
        logger.error(f"Error syncing user: {e}")
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/api/sync/webhook', methods=['POST'])
@cross_origin(supports_credentials=True)
def kratos_webhook():
    """
    Webhook endpoint for Kratos events
    Can be configured in Kratos to auto-sync on registration/updates
    """
    try:
        # Verify webhook signature if configured
        # signature = request.headers.get('X-Webhook-Signature')
        
        data = request.get_json()
        event_type = data.get('type')
        
        logger.info(f"🔄 Received Kratos webhook: {event_type}")
        
        if event_type == 'identity.created':
            # New user registered in Kratos
            identity = data.get('identity', {})
            email = identity.get('traits', {}).get('email')
            if email:
                sync_service.sync_single_user(email)
                
        elif event_type == 'identity.updated':
            # User updated in Kratos
            identity = data.get('identity', {})
            email = identity.get('traits', {}).get('email')
            if email:
                sync_service.sync_single_user(email)
                
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({'error': str(e)}), 500