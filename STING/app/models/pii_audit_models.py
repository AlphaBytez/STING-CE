#!/usr/bin/env python3
"""
PII Audit and Retention Models
Database models for PII detection audit logging and compliance retention
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import json

from app.database import db

class PIIDetectionRecord(db.Model):
    """
    Audit record for each PII detection event
    Stores metadata about detected PII without storing actual values (for security)
    """
    __tablename__ = 'pii_detection_records'
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detection_id = Column(String(50), unique=True, nullable=False)  # Unique detection identifier
    
    # Source information
    document_id = Column(String(100), nullable=True)  # Reference to source document
    honey_jar_id = Column(String(100), nullable=True)  # Reference to honey jar
    user_id = Column(String(100), nullable=False)     # User who uploaded/processed
    
    # Detection metadata
    pii_type = Column(String(50), nullable=False)     # Type of PII detected
    risk_level = Column(String(20), nullable=False)   # high, medium, low
    confidence_score = Column(Integer, nullable=False) # Confidence as integer (0-100)
    
    # Position and context (without actual values)
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    context_hash = Column(String(64), nullable=True)  # SHA-256 hash of context
    value_hash = Column(String(64), nullable=True)    # SHA-256 hash of detected value
    
    # Compliance and retention
    compliance_frameworks = Column(JSON, nullable=True)  # List of applicable frameworks
    detection_mode = Column(String(20), nullable=False)  # general, medical, legal, financial
    
    # Timestamps
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)       # When this record should be deleted
    
    # Audit trail
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)       # Soft delete timestamp
    
    # Processing status
    processed = Column(Boolean, default=False)         # Whether this detection was processed
    notified = Column(Boolean, default=False)          # Whether notifications were sent

    # Admin flagging for review
    flagged_for_review = Column(Boolean, default=False)  # Whether flagged by admin/system
    flagged_by = Column(String(100), nullable=True)      # User ID who flagged it
    flagged_at = Column(DateTime, nullable=True)         # When it was flagged
    flag_reason = Column(Text, nullable=True)            # Reason for flagging
    admin_notes = Column(Text, nullable=True)            # Admin notes/comments
    severity_override = Column(String(20), nullable=True)  # Admin can override risk_level
    action_required = Column(String(50), nullable=True)    # none, investigate, delete, escalate, redact
    review_status = Column(String(20), default='pending')  # pending, in_review, resolved, dismissed
    reviewed_by = Column(String(100), nullable=True)       # User ID who resolved
    reviewed_at = Column(DateTime, nullable=True)          # When it was resolved

    # Indexes for performance
    __table_args__ = (
        Index('idx_pii_user_detected', 'user_id', 'detected_at'),
        Index('idx_pii_type_risk', 'pii_type', 'risk_level'),
        Index('idx_pii_expires', 'expires_at'),
        Index('idx_pii_compliance', 'compliance_frameworks'),
        Index('idx_pii_honey_jar', 'honey_jar_id'),
        Index('idx_pii_flagged', 'flagged_for_review', 'review_status'),
        Index('idx_pii_action_required', 'action_required'),
    )
    
    def to_dict(self, include_admin_fields=False):
        """Convert to dictionary for API responses

        Args:
            include_admin_fields: If True, include admin flagging fields (for admin API)
        """
        result = {
            'id': str(self.id),
            'detection_id': self.detection_id,
            'pii_type': self.pii_type,
            'risk_level': self.risk_level,
            'confidence_score': self.confidence_score,
            'compliance_frameworks': self.compliance_frameworks,
            'detection_mode': self.detection_mode,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'document_id': self.document_id,
            'honey_jar_id': self.honey_jar_id
        }

        if include_admin_fields:
            result.update({
                'flagged_for_review': self.flagged_for_review,
                'flagged_by': self.flagged_by,
                'flagged_at': self.flagged_at.isoformat() if self.flagged_at else None,
                'flag_reason': self.flag_reason,
                'admin_notes': self.admin_notes,
                'severity_override': self.severity_override,
                'action_required': self.action_required,
                'review_status': self.review_status,
                'reviewed_by': self.reviewed_by,
                'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
                'effective_risk_level': self.severity_override or self.risk_level
            })

        return result

class PIIRetentionPolicy(db.Model):
    """
    Configurable retention policies for different PII types and compliance frameworks
    """
    __tablename__ = 'pii_retention_policies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Policy identification
    policy_name = Column(String(100), nullable=False, unique=True)
    compliance_framework = Column(String(50), nullable=False)  # hipaa, gdpr, pci_dss, etc.
    pii_type = Column(String(50), nullable=True)  # Specific PII type, null for default
    
    # Retention settings
    retention_days = Column(Integer, nullable=False)
    auto_deletion_enabled = Column(Boolean, default=True)
    grace_period_days = Column(Integer, default=30)
    immediate_deletion_on_request = Column(Boolean, default=False)
    
    # Policy metadata
    description = Column(Text, nullable=True)
    legal_basis = Column(Text, nullable=True)  # Legal justification for retention
    created_by = Column(String(100), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Status
    active = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_retention_framework_type', 'compliance_framework', 'pii_type'),
        Index('idx_retention_active', 'active', 'effective_date'),
    )

class PIIAuditLog(db.Model):
    """
    Comprehensive audit log for all PII-related operations
    """
    __tablename__ = 'pii_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event information
    event_type = Column(String(50), nullable=False)  # detection, deletion, access, export
    event_description = Column(Text, nullable=True)
    
    # Related records
    detection_record_id = Column(UUID(as_uuid=True), ForeignKey('pii_detection_records.id'), nullable=True)
    detection_record = relationship("PIIDetectionRecord", backref="audit_logs")
    
    # User and system context
    user_id = Column(String(100), nullable=True)     # User who triggered the event
    system_component = Column(String(50), nullable=True)  # Which STING component
    ip_address = Column(String(45), nullable=True)   # IPv4/IPv6 address
    user_agent = Column(Text, nullable=True)         # Browser/client info
    
    # Event metadata
    event_data = Column(JSON, nullable=True)         # Additional event-specific data
    compliance_impact = Column(String(20), nullable=True)  # high, medium, low, none
    
    # Timestamps
    event_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for audit queries
    __table_args__ = (
        Index('idx_audit_event_time', 'event_type', 'event_timestamp'),
        Index('idx_audit_user', 'user_id', 'event_timestamp'),
        Index('idx_audit_detection', 'detection_record_id'),
        Index('idx_audit_compliance', 'compliance_impact', 'event_timestamp'),
    )

class PIIDeletionRequest(db.Model):
    """
    Tracks deletion requests for GDPR/CCPA compliance
    """
    __tablename__ = 'pii_deletion_requests'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request information
    request_type = Column(String(30), nullable=False)  # gdpr_erasure, ccpa_deletion, manual
    requester_email = Column(String(255), nullable=False)
    user_id = Column(String(100), nullable=True)      # If known user
    
    # Request details
    reason = Column(Text, nullable=True)
    scope = Column(String(50), nullable=False)        # all_data, specific_types, date_range
    specific_pii_types = Column(JSON, nullable=True)  # If scope is specific_types
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    
    # Processing status
    status = Column(String(30), nullable=False, default='pending')  # pending, processing, completed, rejected
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(String(100), nullable=True)
    
    # Results
    records_deleted = Column(Integer, default=0)
    deletion_report = Column(JSON, nullable=True)    # Detailed report of what was deleted
    
    # Timestamps
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deadline_at = Column(DateTime, nullable=True)    # Compliance deadline (e.g., 30 days for GDPR)
    
    # Verification
    verification_token = Column(String(100), nullable=True)  # For email verification
    verified_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_deletion_status', 'status', 'requested_at'),
        Index('idx_deletion_deadline', 'deadline_at'),
        Index('idx_deletion_user', 'user_id'),
    )

class PIIComplianceReport(db.Model):
    """
    Periodic compliance reports for audit purposes
    """
    __tablename__ = 'pii_compliance_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Report metadata
    report_type = Column(String(50), nullable=False)  # weekly, monthly, quarterly, annual, ad_hoc
    compliance_framework = Column(String(50), nullable=False)
    reporting_period_start = Column(DateTime, nullable=False)
    reporting_period_end = Column(DateTime, nullable=False)
    
    # Report content
    total_detections = Column(Integer, default=0)
    high_risk_detections = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)
    deletion_requests_processed = Column(Integer, default=0)
    
    # Detailed statistics
    statistics = Column(JSON, nullable=True)         # Detailed breakdown by PII type, etc.
    compliance_violations = Column(JSON, nullable=True)  # Any identified violations
    
    # Report file
    report_file_path = Column(String(500), nullable=True)  # Path to generated report file
    report_file_hash = Column(String(64), nullable=True)   # SHA-256 of report file
    
    # Generation info
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    generated_by = Column(String(100), nullable=False)
    generation_time_seconds = Column(Integer, nullable=True)
    
    __table_args__ = (
        Index('idx_compliance_framework_period', 'compliance_framework', 'reporting_period_start'),
        Index('idx_compliance_generated', 'generated_at'),
    )

# Database initialization function
def create_pii_audit_tables():
    """Create all PII audit tables"""
    db.create_all()
    
def get_retention_policy(compliance_framework: str, pii_type: str = None) -> PIIRetentionPolicy:
    """
    Get the applicable retention policy for a PII type and compliance framework
    """
    # Try to find specific policy first
    if pii_type:
        policy = PIIRetentionPolicy.query.filter_by(
            compliance_framework=compliance_framework,
            pii_type=pii_type,
            active=True
        ).first()
        if policy:
            return policy
    
    # Fall back to default policy for framework
    return PIIRetentionPolicy.query.filter_by(
        compliance_framework=compliance_framework,
        pii_type=None,
        active=True
    ).first()

def calculate_expiration_date(compliance_frameworks: list, pii_type: str, detected_at: datetime = None) -> datetime:
    """
    Calculate the expiration date for a PII detection based on applicable compliance frameworks
    Returns the SHORTEST retention period (most restrictive)
    """
    if not detected_at:
        detected_at = datetime.utcnow()
    
    min_retention_days = None
    
    for framework in compliance_frameworks:
        policy = get_retention_policy(framework, pii_type)
        if policy:
            if min_retention_days is None or policy.retention_days < min_retention_days:
                min_retention_days = policy.retention_days
    
    # Default to 3 years if no policy found
    if min_retention_days is None:
        min_retention_days = 1095
    
    return detected_at + timedelta(days=min_retention_days)