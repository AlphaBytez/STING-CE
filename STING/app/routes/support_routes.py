"""
Support ticket API routes for the Bee-powered support system
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import uuid
import os
import json
from sqlalchemy import desc

from app.database import db
from app.models.support_ticket_models import (
    SupportTicket, SupportSession, BeeAnalysisResult,
    SupportTicketStatus, SupportTicketPriority, SupportTier,
    IssueType, SupportSessionType, SupportSessionStatus
)
from app.models.user_models import User, UserRole
from app.utils.auth import require_admin
from app.utils.logging import setup_logging

# Set up logging
logger = setup_logging(__name__)

# Create blueprint
support_bp = Blueprint('support', __name__, url_prefix='/api/support')


def generate_ticket_id() -> str:
    """Generate a unique support ticket ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = str(uuid.uuid4())[:8].upper()
    return f"ST-{timestamp}-{suffix}"


def generate_session_id() -> str:
    """Generate a unique support session ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
    suffix = str(uuid.uuid4())[:8].upper()
    return f"SS-{timestamp}-{suffix}"


def analyze_issue_description(description: str) -> Dict[str, Any]:
    """
    Analyze issue description and categorize it
    This is a simplified version - in the future could use actual AI/ML
    """
    description_lower = description.lower()
    
    # Initialize analysis result
    analysis = {
        'issue_type': IssueType.GENERAL,
        'primary_services': [],
        'secondary_services': [],
        'diagnostic_flags': [],
        'confidence_score': 0.5,
        'issue_patterns': [],
        'suggested_actions': []
    }
    
    # Authentication issues
    if any(keyword in description_lower for keyword in ['login', 'auth', 'session', 'password', 'kratos', 'aal2']):
        analysis.update({
            'issue_type': IssueType.AUTHENTICATION,
            'primary_services': ['kratos', 'app'],
            'secondary_services': ['db', 'vault'],
            'diagnostic_flags': ['--auth-focus', '--include-startup'],
            'confidence_score': 0.8,
            'issue_patterns': ['authentication_failure'],
            'suggested_actions': [
                'Check Kratos service logs',
                'Verify database connectivity',
                'Review AAL2 configuration'
            ]
        })
    
    # Frontend issues
    elif any(keyword in description_lower for keyword in ['frontend', 'ui', 'dashboard', 'loading', 'react', 'build']):
        analysis.update({
            'issue_type': IssueType.FRONTEND,
            'primary_services': ['frontend'],
            'secondary_services': ['nginx', 'app'],
            'diagnostic_flags': ['--include-startup'],
            'confidence_score': 0.8,
            'issue_patterns': ['ui_loading_failure'],
            'suggested_actions': [
                'Check frontend build logs',
                'Verify nginx proxy configuration',
                'Test API connectivity'
            ]
        })
    
    # AI/Chat issues
    elif any(keyword in description_lower for keyword in ['bee', 'chat', 'ai', 'llm', 'model', 'ollama']):
        analysis.update({
            'issue_type': IssueType.AI_CHAT,
            'primary_services': ['chatbot', 'external-ai'],
            'secondary_services': ['ollama', 'knowledge'],
            'diagnostic_flags': ['--llm-focus', '--performance'],
            'confidence_score': 0.8,
            'issue_patterns': ['ai_service_failure'],
            'suggested_actions': [
                'Check chatbot service connectivity',
                'Verify Ollama model availability',
                'Review external AI service logs'
            ]
        })
    
    # Database issues
    elif any(keyword in description_lower for keyword in ['database', 'db', 'postgres', 'connection', 'sql']):
        analysis.update({
            'issue_type': IssueType.DATABASE,
            'primary_services': ['db'],
            'secondary_services': ['app', 'kratos'],
            'diagnostic_flags': ['--include-startup'],
            'confidence_score': 0.9,
            'issue_patterns': ['database_connectivity'],
            'suggested_actions': [
                'Check PostgreSQL service status',
                'Verify database connection credentials',
                'Review database migration status'
            ]
        })
    
    # Performance issues
    elif any(keyword in description_lower for keyword in ['slow', 'performance', 'memory', 'cpu', 'timeout']):
        analysis.update({
            'issue_type': IssueType.PERFORMANCE,
            'primary_services': ['all'],
            'secondary_services': [],
            'diagnostic_flags': ['--performance', '--hours', '2'],
            'confidence_score': 0.7,
            'issue_patterns': ['performance_degradation'],
            'suggested_actions': [
                'Monitor system resource usage',
                'Review service performance metrics',
                'Check for memory leaks or CPU spikes'
            ]
        })
    
    return analysis


@support_bp.route('/tickets', methods=['GET'])
@login_required
def list_tickets():
    """List support tickets for the current user (or all if admin)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        
        # Build query
        query = SupportTicket.query
        
        # Filter by user unless admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(SupportTicket.user_id == current_user.id)
        
        # Apply filters
        if status_filter:
            query = query.filter(SupportTicket.status == status_filter)
        if priority_filter:
            query = query.filter(SupportTicket.priority == priority_filter)
        
        # Order by creation date (newest first)
        query = query.order_by(desc(SupportTicket.created_at))
        
        # Paginate
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        tickets = [ticket.to_dict() for ticket in pagination.items]
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing support tickets: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve support tickets'
        }), 500


@support_bp.route('/tickets', methods=['POST'])
@login_required
@require_admin
def create_ticket():
    """Create a new support ticket with AI analysis"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not data.get('description'):
            return jsonify({
                'success': False,
                'error': 'Issue description is required'
            }), 400
        
        # Generate ticket ID
        ticket_id = generate_ticket_id()
        
        # Analyze the issue description
        analysis = analyze_issue_description(data['description'])
        
        # Determine support tier (for now, default to community)
        support_tier = data.get('support_tier', SupportTier.COMMUNITY)
        
        # Create the ticket
        ticket = SupportTicket(
            ticket_id=ticket_id,
            user_id=current_user.id,
            created_by_email=current_user.email,
            title=data.get('title', f"Support Request - {analysis['issue_type'].value.title()}"),
            description=data['description'],
            issue_type=analysis['issue_type'],
            priority=data.get('priority', SupportTicketPriority.NORMAL),
            support_tier=support_tier,
            bee_analysis=analysis,
            suggested_services=analysis['primary_services'] + analysis['secondary_services'],
            diagnostic_flags=analysis['diagnostic_flags'],
            chat_transcript=data.get('chat_transcript'),
            bee_session_id=data.get('bee_session_id'),
            honey_jar_created=data.get('honey_jar_created', False),
            honey_jar_refs=data.get('honey_jar_refs', [])
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        # Create detailed analysis record
        bee_analysis = BeeAnalysisResult(
            ticket_id=ticket.id,
            analysis_version='1.0',
            issue_patterns=analysis.get('issue_patterns', []),
            confidence_score=analysis.get('confidence_score', 0.5),
            primary_services=analysis.get('primary_services', []),
            secondary_services=analysis.get('secondary_services', []),
            recommended_flags=analysis.get('diagnostic_flags', []),
            log_sources=analysis.get('primary_services', []),
            suggested_actions=analysis.get('suggested_actions', []),
            knowledge_base_version='1.0.0'
        )
        
        db.session.add(bee_analysis)
        db.session.commit()
        
        logger.info(f"Created support ticket {ticket_id} for user {current_user.email}")
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict(),
            'analysis': bee_analysis.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating support ticket: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to create support ticket'
        }), 500


@support_bp.route('/tickets/<ticket_id>', methods=['GET'])
@login_required
def get_ticket(ticket_id: str):
    """Get a specific support ticket"""
    try:
        # Build query
        query = SupportTicket.query.filter(SupportTicket.ticket_id == ticket_id)
        
        # Filter by user unless admin
        if current_user.role != UserRole.ADMIN:
            query = query.filter(SupportTicket.user_id == current_user.id)
        
        ticket = query.first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Support ticket not found'
            }), 404
        
        # Get analysis results
        analyses = BeeAnalysisResult.query.filter(
            BeeAnalysisResult.ticket_id == ticket.id
        ).all()
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict(),
            'analyses': [analysis.to_dict() for analysis in analyses],
            'sessions': [session.to_dict() for session in ticket.support_sessions]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving support ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve support ticket'
        }), 500


@support_bp.route('/tickets/<ticket_id>/status', methods=['PATCH'])
@login_required
@require_admin
def update_ticket_status(ticket_id: str):
    """Update support ticket status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status or new_status not in [status.value for status in SupportTicketStatus]:
            return jsonify({
                'success': False,
                'error': 'Valid status is required'
            }), 400
        
        ticket = SupportTicket.query.filter(SupportTicket.ticket_id == ticket_id).first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Support ticket not found'
            }), 404
        
        old_status = ticket.status
        ticket.status = SupportTicketStatus(new_status)
        
        # Set resolved timestamp if closing
        if new_status in ['resolved', 'closed'] and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Updated ticket {ticket_id} status from {old_status} to {new_status}")
        
        return jsonify({
            'success': True,
            'ticket': ticket.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating ticket status for {ticket_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to update ticket status'
        }), 500


@support_bp.route('/tickets/<ticket_id>/sessions', methods=['POST'])
@login_required
@require_admin
def create_support_session(ticket_id: str):
    """Create a secure support session for a ticket"""
    try:
        data = request.get_json()
        
        # Validate session type
        session_type = data.get('session_type', SupportSessionType.MANUAL)
        if session_type not in [t.value for t in SupportSessionType]:
            return jsonify({
                'success': False,
                'error': 'Valid session_type is required'
            }), 400
        
        # Find the ticket
        ticket = SupportTicket.query.filter(SupportTicket.ticket_id == ticket_id).first()
        if not ticket:
            return jsonify({
                'success': False,
                'error': 'Support ticket not found'
            }), 404
        
        # Generate session ID
        session_id = generate_session_id()
        
        # Calculate expiration based on support tier
        hours_mapping = {
            SupportTier.COMMUNITY: 2,
            SupportTier.PROFESSIONAL: 24,
            SupportTier.ENTERPRISE: 72
        }
        
        duration_hours = hours_mapping.get(ticket.support_tier, 2)
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        
        # Create session
        session = SupportSession(
            session_id=session_id,
            ticket_id=ticket.id,
            session_type=SupportSessionType(session_type),
            access_granted_by=current_user.id,
            expires_at=expires_at,
            connection_details=data.get('connection_details', {}),
            support_engineer_info=data.get('engineer_info', {}),
            audit_log=[]
        )
        
        # Add initial audit event
        session.add_audit_event(
            'session_created',
            f"Support session created by {current_user.email}",
            current_user.id
        )
        
        db.session.add(session)
        
        # Update ticket with session reference
        ticket.tailscale_session_id = session_id
        ticket.secure_access_granted = True
        ticket.access_expires_at = expires_at
        
        db.session.commit()
        
        logger.info(f"Created support session {session_id} for ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'session': session.to_dict(),
            'ticket': ticket.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating support session for ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to create support session'
        }), 500


@support_bp.route('/sessions/<session_id>/close', methods=['POST'])
@login_required
@require_admin
def close_support_session(session_id: str):
    """Close a support session"""
    try:
        session = SupportSession.query.filter(SupportSession.session_id == session_id).first()
        if not session:
            return jsonify({
                'success': False,
                'error': 'Support session not found'
            }), 404
        
        # Close the session
        session.status = SupportSessionStatus.CLOSED
        session.ended_at = datetime.utcnow()
        
        # Add audit event
        session.add_audit_event(
            'session_closed',
            f"Support session closed by {current_user.email}",
            current_user.id
        )
        
        # Update related ticket
        ticket = session.ticket
        ticket.secure_access_granted = False
        ticket.tailscale_session_id = None
        ticket.access_expires_at = None
        
        db.session.commit()
        
        logger.info(f"Closed support session {session_id}")
        
        return jsonify({
            'success': True,
            'session': session.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error closing support session {session_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to close support session'
        }), 500


@support_bp.route('/analytics', methods=['GET'])
@login_required
@require_admin
def get_support_analytics():
    """Get support system analytics"""
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        
        # Basic ticket stats
        total_tickets = SupportTicket.query.count()
        recent_tickets = SupportTicket.query.filter(SupportTicket.created_at >= since).count()
        open_tickets = SupportTicket.query.filter(SupportTicket.status == SupportTicketStatus.OPEN).count()
        
        # Status breakdown
        status_counts = {}
        for status in SupportTicketStatus:
            count = SupportTicket.query.filter(SupportTicket.status == status).count()
            status_counts[status.value] = count
        
        # Issue type breakdown
        issue_type_counts = {}
        for issue_type in IssueType:
            count = SupportTicket.query.filter(SupportTicket.issue_type == issue_type).count()
            issue_type_counts[issue_type.value] = count
        
        # Support tier breakdown
        tier_counts = {}
        for tier in SupportTier:
            count = SupportTicket.query.filter(SupportTicket.support_tier == tier).count()
            tier_counts[tier.value] = count
        
        # Active sessions
        active_sessions = SupportSession.query.filter(
            SupportSession.status == SupportSessionStatus.ACTIVE
        ).count()
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_tickets': total_tickets,
                'recent_tickets': recent_tickets,
                'open_tickets': open_tickets,
                'active_sessions': active_sessions,
                'status_breakdown': status_counts,
                'issue_type_breakdown': issue_type_counts,
                'tier_breakdown': tier_counts,
                'period_days': days
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving support analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve analytics'
        }), 500


@support_bp.route('/health', methods=['GET'])
def health_check():
    """Support system health check"""
    try:
        # Check database connectivity
        ticket_count = SupportTicket.query.count()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'stats': {
                'total_tickets': ticket_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Support system health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500