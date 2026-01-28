"""
Support Ticket models for the Bee-powered support system
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import JSON
from app.database import db


class SupportTicketStatus(str, Enum):
    """Support ticket status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress" 
    WAITING_FOR_RESPONSE = "waiting_for_response"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class SupportTicketPriority(str, Enum):
    """Support ticket priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class SupportTier(str, Enum):
    """Support tier enumeration"""
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class IssueType(str, Enum):
    """Issue type enumeration for AI categorization"""
    AUTHENTICATION = "authentication"
    FRONTEND = "frontend"
    API = "api"
    AI_CHAT = "ai_chat"
    DATABASE = "database"
    PERFORMANCE = "performance"
    GENERAL = "general"


class SupportTicket(db.Model):
    """Support ticket model for tracking user support requests"""
    __tablename__ = 'support_tickets'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Ticket identification
    ticket_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_email = db.Column(db.String(255), nullable=False)  # Backup email reference
    
    # Ticket details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    issue_type = db.Column(db.Enum(IssueType, name='issue_type', values_callable=lambda obj: [e.value for e in obj]), 
                          default=IssueType.GENERAL, nullable=False)
    
    # Status and priority
    status = db.Column(db.Enum(SupportTicketStatus, name='support_ticket_status', values_callable=lambda obj: [e.value for e in obj]), 
                      default=SupportTicketStatus.OPEN, nullable=False)
    priority = db.Column(db.Enum(SupportTicketPriority, name='support_ticket_priority', values_callable=lambda obj: [e.value for e in obj]), 
                        default=SupportTicketPriority.NORMAL, nullable=False)
    
    # Support tier
    support_tier = db.Column(db.Enum(SupportTier, name='support_tier', values_callable=lambda obj: [e.value for e in obj]), 
                           default=SupportTier.COMMUNITY, nullable=False)
    
    # AI Analysis data
    bee_analysis = db.Column(JSON)  # Stores AI analysis results
    suggested_services = db.Column(JSON)  # Array of services to examine
    diagnostic_flags = db.Column(JSON)  # Array of diagnostic flags used
    
    # Honey jar references
    honey_jar_refs = db.Column(JSON)  # Array of honey jar file paths
    honey_jar_created = db.Column(db.Boolean, default=False)
    
    # Chat integration
    chat_transcript = db.Column(JSON)  # Array of chat messages that led to ticket
    bee_session_id = db.Column(db.String(255), nullable=True)  # Reference to Bee chat session
    
    # Secure access
    tailscale_session_id = db.Column(db.String(255), nullable=True)
    secure_access_granted = db.Column(db.Boolean, default=False)
    access_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref='support_tickets', lazy='select')
    support_sessions = db.relationship('SupportSession', backref='ticket', lazy='dynamic', 
                                     cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SupportTicket {self.ticket_id}: {self.title}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary for API responses"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'user_id': self.user_id,
            'created_by_email': self.created_by_email,
            'title': self.title,
            'description': self.description,
            'issue_type': self.issue_type.value if self.issue_type else None,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'support_tier': self.support_tier.value if self.support_tier else None,
            'bee_analysis': self.bee_analysis,
            'suggested_services': self.suggested_services,
            'diagnostic_flags': self.diagnostic_flags,
            'honey_jar_refs': self.honey_jar_refs,
            'honey_jar_created': self.honey_jar_created,
            'chat_transcript': self.chat_transcript,
            'bee_session_id': self.bee_session_id,
            'tailscale_session_id': self.tailscale_session_id,
            'secure_access_granted': self.secure_access_granted,
            'access_expires_at': self.access_expires_at.isoformat() if self.access_expires_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class SupportSessionType(str, Enum):
    """Support session type enumeration"""
    MANUAL = "manual"
    TAILSCALE = "tailscale"
    WIREGUARD = "wireguard"


class SupportSessionStatus(str, Enum):
    """Support session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"
    FAILED = "failed"


class SupportSession(db.Model):
    """Support session model for tracking secure access sessions"""
    __tablename__ = 'support_sessions'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Session identification
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Related ticket
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    
    # Session details
    session_type = db.Column(db.Enum(SupportSessionType, name='support_session_type', values_callable=lambda obj: [e.value for e in obj]), 
                           nullable=False)
    status = db.Column(db.Enum(SupportSessionStatus, name='support_session_status', values_callable=lambda obj: [e.value for e in obj]), 
                      default=SupportSessionStatus.ACTIVE, nullable=False)
    
    # Connection details (stored as JSON for flexibility)
    connection_details = db.Column(JSON)  # Tailscale auth keys, tunnel info, etc.
    
    # Access control
    access_granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    support_engineer_info = db.Column(JSON)  # Engineer name, contact info, etc.
    
    # Session timing
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    
    # Audit trail
    audit_log = db.Column(JSON)  # Array of audit events
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships  
    granted_by_user = db.relationship('User', foreign_keys=[access_granted_by], backref='granted_support_sessions')
    
    def __repr__(self):
        return f'<SupportSession {self.session_id}: {self.session_type}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for API responses"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'ticket_id': self.ticket_id,
            'session_type': self.session_type.value if self.session_type else None,
            'status': self.status.value if self.status else None,
            'connection_details': self.connection_details,
            'access_granted_by': self.access_granted_by,
            'support_engineer_info': self.support_engineer_info,
            'started_at': self.started_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'audit_log': self.audit_log,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.utcnow() > self.expires_at
    
    def add_audit_event(self, event_type: str, description: str, user_id: Optional[int] = None):
        """Add an audit event to the session"""
        if self.audit_log is None:
            self.audit_log = []
        
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'description': description,
            'user_id': user_id
        }
        
        self.audit_log.append(event)
        db.session.commit()


class BeeAnalysisResult(db.Model):
    """Model for storing Bee AI analysis results for support tickets"""
    __tablename__ = 'bee_analysis_results'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Related ticket
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    
    # Analysis data
    analysis_version = db.Column(db.String(20), default='1.0')  # Version of analysis algorithm
    issue_patterns = db.Column(JSON)  # Detected patterns in issue description
    confidence_score = db.Column(db.Float)  # AI confidence in analysis (0.0-1.0)
    
    # Service correlation
    primary_services = db.Column(JSON)  # Array of primary services identified
    secondary_services = db.Column(JSON)  # Array of secondary services to check
    
    # Diagnostic recommendations
    recommended_flags = db.Column(JSON)  # Array of diagnostic flags to use
    log_sources = db.Column(JSON)  # Array of log sources to capture
    
    # Troubleshooting suggestions
    suggested_actions = db.Column(JSON)  # Array of suggested troubleshooting steps
    similar_tickets = db.Column(JSON)  # References to similar historical tickets
    
    # Analysis metadata
    analysis_duration_ms = db.Column(db.Integer)  # Time taken for analysis
    knowledge_base_version = db.Column(db.String(50))  # Version of STING architecture knowledge
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ticket = db.relationship('SupportTicket', backref='bee_analyses')
    
    def __repr__(self):
        return f'<BeeAnalysisResult for ticket {self.ticket_id}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'analysis_version': self.analysis_version,
            'issue_patterns': self.issue_patterns,
            'confidence_score': self.confidence_score,
            'primary_services': self.primary_services,
            'secondary_services': self.secondary_services,
            'recommended_flags': self.recommended_flags,
            'log_sources': self.log_sources,
            'suggested_actions': self.suggested_actions,
            'similar_tickets': self.similar_tickets,
            'analysis_duration_ms': self.analysis_duration_ms,
            'knowledge_base_version': self.knowledge_base_version,
            'created_at': self.created_at.isoformat(),
        }