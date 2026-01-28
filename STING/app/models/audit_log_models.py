# app/models/audit_log_models.py
"""
Audit logging models for STING application.
Tracks authentication events, security operations, and user actions for compliance and security monitoring.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import db
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of events that can be audited"""
    # Authentication Events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    SESSION_EXPIRED = "session_expired"

    # Two-Factor Authentication
    TOTP_SETUP = "totp_setup"
    TOTP_SUCCESS = "totp_success"
    TOTP_FAILED = "totp_failed"
    TOTP_DISABLED = "totp_disabled"

    # Passkey/WebAuthn Events
    PASSKEY_REGISTERED = "passkey_registered"
    PASSKEY_AUTH_SUCCESS = "passkey_auth_success"
    PASSKEY_AUTH_FAILED = "passkey_auth_failed"
    PASSKEY_DELETED = "passkey_deleted"

    # Recovery Codes
    RECOVERY_CODES_GENERATED = "recovery_codes_generated"
    RECOVERY_CODE_USED = "recovery_code_used"
    RECOVERY_CODES_REVOKED = "recovery_codes_revoked"

    # API Key Management
    API_KEY_CREATED = "api_key_created"
    API_KEY_DELETED = "api_key_deleted"
    API_KEY_USED = "api_key_used"
    API_KEY_AUTH_FAILED = "api_key_auth_failed"

    # AAL/Tiered Authentication
    AAL2_STEP_UP_SUCCESS = "aal2_step_up_success"
    AAL2_STEP_UP_FAILED = "aal2_step_up_failed"
    TIERED_AUTH_CHALLENGE = "tiered_auth_challenge"
    TIERED_AUTH_SUCCESS = "tiered_auth_success"
    TIERED_AUTH_FAILED = "tiered_auth_failed"

    # Account Management
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFIED = "email_verified"

    # Administrative Actions
    ADMIN_LOGIN = "admin_login"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    ROLE_CHANGED = "role_changed"

    # Data Access
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"

    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_TOKEN = "invalid_token"

class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"           # Routine operations
    MEDIUM = "medium"     # Important operations
    HIGH = "high"         # Security-sensitive operations
    CRITICAL = "critical" # Security incidents

class AuditLog(db.Model):
    """
    Audit log entries for security and compliance monitoring.

    This table stores all significant authentication and security events
    for audit trails, compliance reporting, and security incident investigation.
    """
    __tablename__ = 'audit_logs'

    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_severity', 'severity'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_ip_address', 'ip_address'),
    )

    id = Column(Integer, primary_key=True)

    # Event Information
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default=AuditSeverity.LOW.value)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # User Information
    user_id = Column(String(255), nullable=True, index=True)  # Kratos user ID (nullable for anonymous events)
    user_email = Column(String(255), nullable=True, index=True)
    user_role = Column(String(50), nullable=True)

    # Request Information
    ip_address = Column(String(45), nullable=True, index=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True)  # For correlating requests
    session_id = Column(String(100), nullable=True)

    # Event Details
    message = Column(Text, nullable=False)  # Human-readable description
    details = Column(JSON, nullable=True)  # Structured event data

    # Authentication Method Details
    auth_method = Column(String(50), nullable=True)  # webauthn, totp, email, recovery_code
    auth_tier = Column(Integer, nullable=True)  # 1-4 for tiered auth

    # Success/Failure
    success = Column(Boolean, nullable=False, default=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional Context
    resource = Column(String(255), nullable=True)  # Resource being accessed
    action = Column(String(100), nullable=True)    # Action being performed

    def __init__(self, event_type, message, **kwargs):
        """Initialize audit log entry"""
        self.event_type = event_type.value if isinstance(event_type, AuditEventType) else event_type
        self.message = message

        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def log_event(cls, event_type, message, user=None, request=None, **kwargs):
        """
        Create and save an audit log entry.

        Args:
            event_type: AuditEventType or string
            message: Human-readable description
            user: User object (optional)
            request: Flask request object (optional)
            **kwargs: Additional fields
        """
        try:
            # Extract user information
            user_id = None
            user_email = None
            user_role = None

            if user:
                user_id = getattr(user, 'kratos_id', None) or getattr(user, 'id', None)
                user_email = getattr(user, 'email', None)
                user_role = getattr(user, 'effective_role', None) or getattr(user, 'role', None)

            # Extract request information
            ip_address = None
            user_agent = None
            session_id = None

            if request:
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent')
                # Try to get session ID if available
                try:
                    from flask import session
                    session_id = session.get('session_id')
                except:
                    pass

            # Create audit log entry
            audit_entry = cls(
                event_type=event_type,
                message=message,
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                **kwargs
            )

            # Add to database
            db.session.add(audit_entry)
            db.session.commit()

            logger.info(f"Audit log created: {event_type.value if isinstance(event_type, AuditEventType) else event_type} - {message}")
            return audit_entry

        except Exception as e:
            logger.error(f"Failed to create audit log entry: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return None

    @classmethod
    def log_auth_success(cls, user, auth_method, tier=None, request=None, details=None):
        """Log successful authentication"""
        message = f"User {user.email} authenticated successfully using {auth_method}"
        if tier:
            message += f" (Tier {tier})"

        return cls.log_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            message=message,
            user=user,
            request=request,
            severity=AuditSeverity.MEDIUM.value,
            auth_method=auth_method,
            auth_tier=tier,
            success=True,
            details=details
        )

    @classmethod
    def log_auth_failure(cls, email, auth_method, reason, request=None, details=None):
        """Log failed authentication attempt"""
        message = f"Authentication failed for {email} using {auth_method}: {reason}"

        return cls.log_event(
            event_type=AuditEventType.LOGIN_FAILED,
            message=message,
            user_email=email,
            request=request,
            severity=AuditSeverity.HIGH.value,
            auth_method=auth_method,
            success=False,
            error_message=reason,
            details=details
        )

    @classmethod
    def log_tiered_auth_challenge(cls, user, operation, tier, request=None):
        """Log tiered authentication challenge"""
        message = f"Tiered auth challenge (Tier {tier}) for {operation} by {user.email}"

        return cls.log_event(
            event_type=AuditEventType.TIERED_AUTH_CHALLENGE,
            message=message,
            user=user,
            request=request,
            severity=AuditSeverity.MEDIUM.value,
            auth_tier=tier,
            action=operation,
            details={'operation': operation, 'tier': tier}
        )

    @classmethod
    def log_api_key_creation(cls, user, api_key_name, scopes, request=None):
        """Log API key creation"""
        message = f"API key '{api_key_name}' created by {user.email}"

        return cls.log_event(
            event_type=AuditEventType.API_KEY_CREATED,
            message=message,
            user=user,
            request=request,
            severity=AuditSeverity.HIGH.value,
            resource=f"api_key:{api_key_name}",
            action="create",
            details={'api_key_name': api_key_name, 'scopes': scopes}
        )

    @classmethod
    def log_recovery_codes_generated(cls, user, count, request=None):
        """Log recovery codes generation"""
        message = f"Generated {count} recovery codes for {user.email}"

        return cls.log_event(
            event_type=AuditEventType.RECOVERY_CODES_GENERATED,
            message=message,
            user=user,
            request=request,
            severity=AuditSeverity.HIGH.value,
            action="generate_recovery_codes",
            details={'code_count': count}
        )

    @classmethod
    def log_suspicious_activity(cls, description, user=None, request=None, details=None):
        """Log suspicious security activity"""
        return cls.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            message=description,
            user=user,
            request=request,
            severity=AuditSeverity.CRITICAL.value,
            details=details
        )

    @classmethod
    def get_user_activity(cls, user_id, days=30, limit=100):
        """Get recent activity for a user"""
        since_date = datetime.utcnow() - timedelta(days=days)

        return cls.query.filter_by(user_id=user_id).filter(
            cls.timestamp >= since_date
        ).order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_security_events(cls, severity=None, days=7, limit=100):
        """Get recent security events"""
        since_date = datetime.utcnow() - timedelta(days=days)

        query = cls.query.filter(cls.timestamp >= since_date)

        if severity:
            query = query.filter_by(severity=severity.value if isinstance(severity, AuditSeverity) else severity)

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def cleanup_old_logs(cls, days=365):
        """Remove audit logs older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = cls.query.filter(cls.timestamp < cutoff_date).delete()
        db.session.commit()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} audit log entries older than {days} days")

        return deleted_count

    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        result = {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_email': self.user_email,
            'user_role': self.user_role,
            'message': self.message,
            'auth_method': self.auth_method,
            'auth_tier': self.auth_tier,
            'success': self.success,
            'resource': self.resource,
            'action': self.action,
            'details': self.details
        }

        if include_sensitive:
            result.update({
                'user_id': self.user_id,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'session_id': self.session_id,
                'request_id': self.request_id,
                'error_code': self.error_code,
                'error_message': self.error_message
            })

        return result

    def __repr__(self):
        return f'<AuditLog {self.id}: {self.event_type} - {self.user_email or "anonymous"} at {self.timestamp}>'