"""
Admin Invitation Routes - Secure admin-to-admin invitation system

This module provides secure endpoints for administrators to invite other administrators
with time-limited tokens, full audit logging, and AAL2 security requirements.
"""

from flask import Blueprint, request, jsonify, current_app, g
from functools import wraps
import logging
from datetime import datetime
import json

# Import models and utilities
from app.models.admin_invitation_models import AdminInvitation, AdminInvitationAudit
from app.extensions import db
from app.middleware.auth_middleware import require_admin

# Create blueprint
admin_invitation_bp = Blueprint('admin_invitation', __name__, url_prefix='/api/admin/invitations')

# Set up logging
logger = logging.getLogger(__name__)

def get_client_info():
    """Extract client information for audit logging."""
    return {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', '')
    }

def log_invitation_event(event_type, invitation_id=None, actor_email=None, 
                        actor_identity_id=None, details=None, success=True, error_message=None):
    """Log invitation events for audit trail."""
    try:
        client_info = get_client_info()
        audit_entry = AdminInvitationAudit(
            event_type=event_type,
            invitation_id=invitation_id,
            actor_email=actor_email,
            actor_identity_id=actor_identity_id,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent'],
            details=json.dumps(details) if details else None,
            success=success,
            error_message=error_message
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log invitation event: {str(e)}")

@admin_invitation_bp.route('/create', methods=['POST'])
@require_admin
def create_admin_invitation():
    """
    Create a new admin invitation.
    
    Requires AAL2 authentication and admin role.
    Creates a secure, time-limited invitation token.
    """
    try:
        # Get current identity from Flask g (set by middleware)
        if not g.identity:
            return jsonify({'error': 'Invalid session'}), 401
            
        current_email = g.identity.get('traits', {}).get('email')
        current_id = g.identity.get('id')
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        invited_email = data.get('email', '').strip().lower()
        reason = data.get('reason', '').strip()
        expiry_hours = data.get('expiry_hours', 24)
        
        # Validate input
        if not invited_email:
            return jsonify({'error': 'Email address is required'}), 400
            
        if '@' not in invited_email:
            return jsonify({'error': 'Invalid email address'}), 400
            
        if expiry_hours < 1 or expiry_hours > 168:  # Max 1 week
            return jsonify({'error': 'Expiry hours must be between 1 and 168'}), 400
            
        # Check if invitation already exists for this email
        existing_invitation = AdminInvitation.query.filter_by(
            invited_email=invited_email,
            used=False
        ).filter(AdminInvitation.expires_at > datetime.utcnow()).first()
        
        if existing_invitation:
            return jsonify({
                'error': 'An active invitation already exists for this email address'
            }), 409
            
        # Get client info for audit
        client_info = get_client_info()
        
        # Create invitation
        invitation = AdminInvitation(
            invited_email=invited_email,
            invited_by_email=current_email,
            invited_by_id=current_id,
            expiry_hours=expiry_hours,
            reason=reason,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        # Log the event
        log_invitation_event(
            event_type='created',
            invitation_id=invitation.id,
            actor_email=current_email,
            actor_identity_id=current_id,
            details={
                'invited_email': invited_email,
                'expiry_hours': expiry_hours,
                'reason': reason
            }
        )
        
        logger.info(f"Admin invitation created: {invitation.id} for {invited_email} by {current_email}")
        
        return jsonify({
            'success': True,
            'invitation': invitation.to_dict(),
            'message': f'Invitation created for {invited_email}'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating admin invitation: {str(e)}")
        
        # Log failed attempt
        try:
            current_email = g.identity.get('traits', {}).get('email') if g.identity else None
            current_id = g.identity.get('id') if g.identity else None
            
            log_invitation_event(
                event_type='creation_failed',
                actor_email=current_email,
                actor_identity_id=current_id,
                success=False,
                error_message=str(e)
            )
        except:
            pass
            
        return jsonify({'error': 'Failed to create invitation'}), 500

@admin_invitation_bp.route('/list', methods=['GET'])
@require_admin
def list_admin_invitations():
    """
    List admin invitations.
    
    Requires AAL2 authentication and admin role.
    Returns paginated list of invitations with status.
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status', 'all')  # all, active, used, expired
        
        # Build query
        query = AdminInvitation.query
        
        if status == 'active':
            query = query.filter(
                AdminInvitation.used == False,
                AdminInvitation.expires_at > datetime.utcnow()
            )
        elif status == 'used':
            query = query.filter(AdminInvitation.used == True)
        elif status == 'expired':
            query = query.filter(
                AdminInvitation.used == False,
                AdminInvitation.expires_at <= datetime.utcnow()
            )
            
        # Order by creation date (newest first)
        query = query.order_by(AdminInvitation.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'invitations': [inv.to_dict() for inv in pagination.items],
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing admin invitations: {str(e)}")
        return jsonify({'error': 'Failed to list invitations'}), 500

@admin_invitation_bp.route('/<invitation_id>', methods=['DELETE'])
@require_admin
def revoke_admin_invitation(invitation_id):
    """
    Revoke (delete) an admin invitation.
    
    Requires AAL2 authentication and admin role.
    Marks invitation as used to prevent future use.
    """
    try:
        # Get current identity from Flask g (set by middleware)
        if not g.identity:
            return jsonify({'error': 'Invalid session'}), 401
            
        current_email = g.identity.get('traits', {}).get('email')
        current_id = g.identity.get('id')
        
        # Find invitation
        invitation = AdminInvitation.query.filter_by(id=invitation_id).first()
        if not invitation:
            return jsonify({'error': 'Invitation not found'}), 404
            
        if invitation.used:
            return jsonify({'error': 'Invitation has already been used'}), 410
            
        # Mark as used (soft delete)
        invitation.used = True
        invitation.used_at = datetime.utcnow()
        invitation.used_by_identity = 'revoked'
        
        db.session.commit()
        
        # Log the event
        log_invitation_event(
            event_type='revoked',
            invitation_id=invitation.id,
            actor_email=current_email,
            actor_identity_id=current_id,
            details={
                'invited_email': invitation.invited_email,
                'revoked_by': current_email
            }
        )
        
        logger.info(f"Admin invitation revoked: {invitation_id} by {current_email}")
        
        return jsonify({
            'success': True,
            'message': f'Invitation for {invitation.invited_email} has been revoked'
        }), 200
        
    except Exception as e:
        logger.error(f"Error revoking admin invitation: {str(e)}")
        return jsonify({'error': 'Failed to revoke invitation'}), 500

@admin_invitation_bp.route('/audit', methods=['GET'])
@require_admin
def get_audit_log():
    """
    Get audit log for admin invitations.
    
    Requires AAL2 authentication and admin role.
    Returns paginated audit trail.
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        event_type = request.args.get('event_type')
        
        # Build query
        query = AdminInvitationAudit.query
        
        if event_type:
            query = query.filter(AdminInvitationAudit.event_type == event_type)
            
        # Order by timestamp (newest first)
        query = query.order_by(AdminInvitationAudit.timestamp.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        audit_entries = []
        for entry in pagination.items:
            audit_data = {
                'id': entry.id,
                'timestamp': entry.timestamp.isoformat(),
                'event_type': entry.event_type,
                'actor_email': entry.actor_email,
                'ip_address': entry.ip_address,
                'success': entry.success,
                'error_message': entry.error_message
            }
            
            # Parse details if present
            if entry.details:
                try:
                    audit_data['details'] = json.loads(entry.details)
                except:
                    audit_data['details_raw'] = entry.details
                    
            audit_entries.append(audit_data)
        
        return jsonify({
            'audit_entries': audit_entries,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        return jsonify({'error': 'Failed to get audit log'}), 500

# Health check endpoint
@admin_invitation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for admin invitation service."""
    return jsonify({
        'status': 'healthy',
        'service': 'admin_invitations',
        'timestamp': datetime.utcnow().isoformat()
    }), 200