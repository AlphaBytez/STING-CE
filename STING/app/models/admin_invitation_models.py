"""
Admin Invitation Models - Secure admin-to-admin invitation system
"""

from datetime import datetime, timedelta
import secrets
from sqlalchemy import Column, String, DateTime, Boolean, Text
from app.extensions import db

class AdminInvitation(db.Model):
    """
    Secure admin invitation tokens.
    
    Features:
    - Time-limited tokens (24 hour expiry)
    - Single-use invitations
    - Full audit trail
    - Secure random tokens
    """
    __tablename__ = 'admin_invitations'
    
    # Primary key
    id = Column(String(36), primary_key=True)
    
    # Invitation details
    token = Column(String(64), unique=True, nullable=False, index=True)
    invited_email = Column(String(255), nullable=False)
    invited_by_email = Column(String(255), nullable=False)
    invited_by_id = Column(String(36), nullable=False)  # Kratos identity ID
    
    # Security features
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used_by_identity = Column(String(36), nullable=True)  # Kratos identity ID of user who claimed
    
    # Audit trail
    invitation_reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Optional metadata
    invitation_metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    def __init__(self, invited_email, invited_by_email, invited_by_id, 
                 expiry_hours=24, reason=None, ip_address=None, user_agent=None):
        """
        Create a new admin invitation.
        
        Args:
            invited_email: Email address of the person being invited
            invited_by_email: Email of the admin creating the invitation
            invited_by_id: Kratos identity ID of the inviting admin
            expiry_hours: Hours until invitation expires (default 24)
            reason: Optional reason for invitation
            ip_address: IP address of inviting admin
            user_agent: Browser user agent of inviting admin
        """
        self.id = secrets.token_urlsafe(27)  # ~36 chars base64
        self.token = secrets.token_urlsafe(48)  # ~64 chars base64
        self.invited_email = invited_email.lower()
        self.invited_by_email = invited_by_email
        self.invited_by_id = invited_by_id
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=expiry_hours)
        self.invitation_reason = reason
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.used = False
    
    def is_valid(self):
        """Check if invitation is still valid."""
        if self.used:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def mark_used(self, identity_id):
        """Mark invitation as used."""
        self.used = True
        self.used_at = datetime.utcnow()
        self.used_by_identity = identity_id
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'invited_email': self.invited_email,
            'invited_by': self.invited_by_email,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_valid': self.is_valid(),
            'used': self.used,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'reason': self.invitation_reason
        }
    
    def __repr__(self):
        return f"<AdminInvitation {self.invited_email} by {self.invited_by_email}>"


class AdminInvitationAudit(db.Model):
    """
    Audit log for all admin invitation activities.
    
    Tracks:
    - Invitation creation
    - Invitation usage
    - Failed attempts
    - Expiration events
    """
    __tablename__ = 'admin_invitation_audit'
    
    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # created, used, expired, failed_attempt
    invitation_id = Column(String(36), nullable=True)
    invitation_token = Column(String(64), nullable=True)  # Hashed version for security
    
    # Actor information
    actor_email = Column(String(255), nullable=True)
    actor_identity_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Event data
    details = Column(Text, nullable=True)  # JSON string
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    def __init__(self, event_type, invitation_id=None, actor_email=None, 
                 actor_identity_id=None, ip_address=None, user_agent=None,
                 details=None, success=True, error_message=None):
        """Create audit log entry."""
        self.id = secrets.token_urlsafe(27)
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.invitation_id = invitation_id
        self.actor_email = actor_email
        self.actor_identity_id = actor_identity_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details
        self.success = success
        self.error_message = error_message
    
    def __repr__(self):
        return f"<AdminInvitationAudit {self.event_type} at {self.timestamp}>"