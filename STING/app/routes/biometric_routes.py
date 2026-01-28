#!/usr/bin/env python3
"""
Biometric Authentication Routes
Purpose: Handle biometric authentication recording and credential metadata
Context: Track UV flag authentications to enable proper AAL2 recognition
"""

import logging
from flask import Blueprint, request, jsonify, g, session
from app.services.authorization_service import authorization_service

logger = logging.getLogger(__name__)

# Create blueprint
biometric_bp = Blueprint('biometric', __name__, url_prefix='/api/biometric')

@biometric_bp.route('/record-auth', methods=['POST'])
def record_biometric_auth():
    """Record biometric authentication event (UV flag = true)"""
    logger.info("🔒 Recording biometric authentication")
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        credential_id = data.get('credential_id')
        user_verified = data.get('user_verified', False)
        authenticator_type = data.get('authenticator_type', 'platform')
        session_id = data.get('session_id') or session.get('_session_id', 'unknown')
        
        if not credential_id:
            return jsonify({'error': 'credential_id is required'}), 400
        
        # Record the biometric authentication
        success = authorization_service.record_biometric_auth(
            identity_id=g.user.id,
            credential_id=credential_id,
            session_id=session_id,
            user_verified=user_verified,
            authenticator_type=authenticator_type
        )
        
        if success:
            logger.info(f"🔒 Recorded biometric auth for {g.user.email} (UV: {user_verified})")
            
            # Update session to reflect AAL2 if biometric was used
            if user_verified:
                session['biometric_verified'] = True
                session['biometric_timestamp'] = int(time.time())
                session.modified = True
            
            return jsonify({
                'success': True,
                'message': 'Biometric authentication recorded',
                'aal_upgraded': user_verified,
                'effective_aal': 'aal2' if user_verified else 'aal1'
            })
        else:
            return jsonify({'error': 'Failed to record biometric authentication'}), 500
            
    except Exception as e:
        logger.error(f"Error recording biometric auth: {e}")
        return jsonify({'error': f'Failed to record authentication: {str(e)}'}), 500

@biometric_bp.route('/record-credential', methods=['POST'])
def record_credential_metadata():
    """Record metadata about a credential for UI display"""
    logger.info("🔒 Recording credential metadata")
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        credential_id = data.get('credential_id')
        credential_name = data.get('credential_name')
        is_biometric = data.get('is_biometric', False)
        authenticator_type = data.get('authenticator_type', 'platform')
        
        if not credential_id:
            return jsonify({'error': 'credential_id is required'}), 400
        
        # Record credential metadata
        success = authorization_service.record_credential_metadata(
            credential_id=credential_id,
            identity_id=g.user.id,
            credential_name=credential_name,
            is_biometric=is_biometric,
            authenticator_type=authenticator_type
        )
        
        if success:
            logger.info(f"🔒 Recorded credential metadata for {credential_id} (biometric: {is_biometric})")
            
            return jsonify({
                'success': True,
                'message': 'Credential metadata recorded',
                'credential_id': credential_id,
                'is_biometric': is_biometric
            })
        else:
            return jsonify({'error': 'Failed to record credential metadata'}), 500
            
    except Exception as e:
        logger.error(f"Error recording credential metadata: {e}")
        return jsonify({'error': f'Failed to record credential: {str(e)}'}), 500

@biometric_bp.route('/credentials', methods=['GET'])
def get_user_credentials():
    """Get user's credentials separated by biometric capability"""
    logger.info("🔒 Getting user credentials")
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        credentials = authorization_service.get_user_credentials(g.user.id)
        
        return jsonify({
            'success': True,
            'credentials': credentials,
            'biometric_count': len(credentials['biometric']),
            'standard_count': len(credentials['standard'])
        })
        
    except Exception as e:
        logger.error(f"Error getting user credentials: {e}")
        return jsonify({'error': f'Failed to get credentials: {str(e)}'}), 500

@biometric_bp.route('/aal-status', methods=['GET'])
def get_biometric_aal_status():
    """Get AAL status including biometric authentication detection"""
    logger.info("🔒 Getting biometric AAL status")
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get Kratos session info if available
        kratos_session = getattr(g, 'kratos_session', {})
        
        # Calculate effective AAL using our authorization service
        effective_aal = authorization_service.get_effective_aal(kratos_session, g.user.id)
        
        # Check biometric auth status
        has_biometric = authorization_service.has_biometric_auth(
            g.user.id, 
            kratos_session.get('id')
        )
        
        # Check if user can access sensitive data
        can_access, reason = authorization_service.can_access_sensitive_data(
            g.user.id, kratos_session
        )
        
        return jsonify({
            'success': True,
            'user_id': g.user.id,
            'kratos_aal': kratos_session.get('authenticator_assurance_level', 'aal1'),
            'effective_aal': effective_aal,
            'has_biometric_auth': has_biometric,
            'can_access_sensitive': can_access,
            'access_reason': reason,
            'session_info': {
                'kratos_session_id': kratos_session.get('id'),
                'biometric_verified': session.get('biometric_verified', False),
                'biometric_timestamp': session.get('biometric_timestamp')
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting biometric AAL status: {e}")
        return jsonify({'error': f'Failed to get AAL status: {str(e)}'}), 500

@biometric_bp.route('/cleanup', methods=['POST'])
def cleanup_old_records():
    """Clean up old biometric authentication records"""
    logger.info("🧹 Cleaning up old biometric records")
    
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Check if user is admin (only admins can trigger cleanup)
    if not hasattr(g.user, 'role') or g.user.role.upper() != 'ADMIN':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json() if request.is_json else {}
        days = data.get('days', 30)
        
        # Validate days parameter
        if not isinstance(days, int) or days < 1 or days > 365:
            return jsonify({'error': 'Days must be between 1 and 365'}), 400
        
        deleted_count = authorization_service.cleanup_old_biometric_records(days)
        
        logger.info(f"🧹 Cleaned up {deleted_count} old biometric records (older than {days} days)")
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {deleted_count} old records',
            'deleted_count': deleted_count,
            'retention_days': days
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up biometric records: {e}")
        return jsonify({'error': f'Failed to cleanup records: {str(e)}'}), 500

# Import time for session timestamps
import time