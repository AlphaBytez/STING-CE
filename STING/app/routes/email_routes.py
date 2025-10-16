"""
Email Notification Routes for STING-CE
Provides API endpoints for sending email notifications.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

from app.services.email_service import get_email_service
from app.utils.decorators import require_auth

logger = logging.getLogger(__name__)

# Create blueprint
email_bp = Blueprint('email', __name__, url_prefix='/api/email')

@email_bp.route('/document/approval', methods=['POST'])
@require_auth
def send_document_approval_notification():
    """
    Send document approval notification email.
    
    JSON body:
    - recipient_email: Email address to send to
    - document_name: Name of the approved document
    - honey_jar_name: Name of the honey jar
    - approver_name: Name of the person who approved
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400
        
        # Validate required fields
        required_fields = ['recipient_email', 'document_name', 'honey_jar_name', 'approver_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Send email
        email_service = get_email_service()
        success = email_service.send_document_approval_notification(
            recipient_email=data['recipient_email'],
            document_name=data['document_name'],
            honey_jar_name=data['honey_jar_name'],
            approver_name=data['approver_name']
        )
        
        if success:
            logger.info(f"📧 Document approval notification sent to {data['recipient_email']}")
            return jsonify({'success': True, 'message': 'Approval notification sent successfully'})
        else:
            logger.warning(f"📧 Failed to send approval notification to {data['recipient_email']}")
            return jsonify({'success': False, 'error': 'Failed to send email'}), 500
            
    except Exception as e:
        logger.error(f"Error sending document approval notification: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@email_bp.route('/document/rejection', methods=['POST'])
@require_auth
def send_document_rejection_notification():
    """
    Send document rejection notification email.
    
    JSON body:
    - recipient_email: Email address to send to
    - document_name: Name of the rejected document
    - honey_jar_name: Name of the honey jar
    - reviewer_name: Name of the person who rejected
    - rejection_reason: Reason for rejection
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400
        
        # Validate required fields
        required_fields = ['recipient_email', 'document_name', 'honey_jar_name', 'reviewer_name', 'rejection_reason']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Send email
        email_service = get_email_service()
        success = email_service.send_document_rejection_notification(
            recipient_email=data['recipient_email'],
            document_name=data['document_name'],
            honey_jar_name=data['honey_jar_name'],
            reviewer_name=data['reviewer_name'],
            rejection_reason=data['rejection_reason']
        )
        
        if success:
            logger.info(f"📧 Document rejection notification sent to {data['recipient_email']}")
            return jsonify({'success': True, 'message': 'Rejection notification sent successfully'})
        else:
            logger.warning(f"📧 Failed to send rejection notification to {data['recipient_email']}")
            return jsonify({'success': False, 'error': 'Failed to send email'}), 500
            
    except Exception as e:
        logger.error(f"Error sending document rejection notification: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@email_bp.route('/document/pending-approval', methods=['POST'])
@require_auth
def send_pending_approval_notification():
    """
    Send pending approval notification email to admins.
    
    JSON body:
    - admin_email: Email address of admin to notify
    - document_name: Name of the document needing approval
    - honey_jar_name: Name of the honey jar
    - uploader_name: Name of the person who uploaded
    - pending_count: Number of total pending documents (optional)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400
        
        # Validate required fields
        required_fields = ['admin_email', 'document_name', 'honey_jar_name', 'uploader_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Send email
        email_service = get_email_service()
        success = email_service.send_pending_approval_notification(
            admin_email=data['admin_email'],
            document_name=data['document_name'],
            honey_jar_name=data['honey_jar_name'],
            uploader_name=data['uploader_name'],
            pending_count=data.get('pending_count', 1)
        )
        
        if success:
            logger.info(f"📧 Pending approval notification sent to {data['admin_email']}")
            return jsonify({'success': True, 'message': 'Pending approval notification sent successfully'})
        else:
            logger.warning(f"📧 Failed to send pending approval notification to {data['admin_email']}")
            return jsonify({'success': False, 'error': 'Failed to send email'}), 500
            
    except Exception as e:
        logger.error(f"Error sending pending approval notification: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@email_bp.route('/system/alert', methods=['POST'])
@require_auth
def send_system_alert():
    """
    Send system alert email to admins.
    
    JSON body:
    - admin_emails: List of admin email addresses
    - alert_type: Type of alert
    - alert_message: Alert message
    - severity: Alert severity (low, medium, high, critical)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'JSON data required'}), 400
        
        # Validate required fields
        required_fields = ['admin_emails', 'alert_type', 'alert_message']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        admin_emails = data['admin_emails']
        if not isinstance(admin_emails, list):
            return jsonify({'success': False, 'error': 'admin_emails must be a list'}), 400
        
        # Send email to each admin
        email_service = get_email_service()
        results = []
        for admin_email in admin_emails:
            success = email_service.send_system_alert(
                admin_emails=[admin_email],
                alert_type=data['alert_type'],
                alert_message=data['alert_message'],
                severity=data.get('severity', 'medium')
            )
            results.append({
                'email': admin_email,
                'success': success
            })
        
        successful_sends = sum(1 for result in results if result['success'])
        
        if successful_sends > 0:
            logger.info(f"📧 System alert sent to {successful_sends}/{len(admin_emails)} admins")
            return jsonify({
                'success': True, 
                'message': f'System alert sent to {successful_sends}/{len(admin_emails)} admins',
                'results': results
            })
        else:
            logger.warning(f"📧 Failed to send system alert to any admins")
            return jsonify({
                'success': False, 
                'error': 'Failed to send email to any admins',
                'results': results
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending system alert: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@email_bp.route('/test', methods=['POST'])
@require_auth
def send_test_email():
    """
    Send a test email to verify email service is working.
    
    JSON body:
    - recipient_email: Email address to send test to
    """
    try:
        data = request.get_json()
        if not data or 'recipient_email' not in data:
            return jsonify({'success': False, 'error': 'recipient_email is required'}), 400
        
        # Send a simple test email using the document approval template
        email_service = get_email_service()
        success = email_service.send_document_approval_notification(
            recipient_email=data['recipient_email'],
            document_name='Test Document',
            honey_jar_name='Test Honey Jar',
            approver_name='STING System Test'
        )
        
        if success:
            logger.info(f"📧 Test email sent to {data['recipient_email']}")
            return jsonify({'success': True, 'message': 'Test email sent successfully'})
        else:
            logger.warning(f"📧 Failed to send test email to {data['recipient_email']}")
            return jsonify({'success': False, 'error': 'Failed to send test email'}), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Health check endpoint
@email_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for email service."""
    try:
        email_service = get_email_service()
        # Try to get service status without sending actual email
        smtp_config = {
            'server': email_service.smtp_server,
            'port': email_service.smtp_port,
            'use_tls': email_service.smtp_use_tls
        }
        
        return jsonify({
            'status': 'healthy',
            'service': 'email',
            'smtp_configured': bool(email_service.smtp_server),
            'smtp_config': smtp_config
        })
        
    except Exception as e:
        logger.error(f"Email health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500