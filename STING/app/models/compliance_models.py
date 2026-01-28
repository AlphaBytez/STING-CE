#!/usr/bin/env python3
"""
Compliance Profile Models
Enhanced compliance management for PII detection and handling
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db
import uuid
from datetime import datetime
from enum import Enum


class ComplianceFramework(str, Enum):
    """Regulatory compliance frameworks"""
    HIPAA = "hipaa"
    GDPR = "gdpr"
    CCPA = "ccpa"
    PCI_DSS = "pci_dss"
    ATTORNEY_CLIENT = "attorney_client"
    GLBA = "glba"
    FERPA = "ferpa"
    SOX = "sox"


class SensitivityLevel(str, Enum):
    """Detection sensitivity levels"""
    STRICT = "strict"      # High precision, low false positives
    MODERATE = "moderate"  # Balanced approach
    RELAXED = "relaxed"    # High recall, may have false positives


class ActionType(str, Enum):
    """Actions to take when PII is detected"""
    MASK = "mask"          # Replace with masked value
    REDACT = "redact"      # Remove completely
    ENCRYPT = "encrypt"    # Encrypt in place
    FLAG = "flag"          # Mark for review
    BLOCK = "block"        # Prevent access
    AUDIT = "audit"        # Log only


class RiskLevel(str, Enum):
    """Risk classification levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceProfile(db.Model):
    """
    Main compliance profile configuration
    Designed to work with future agent service for verification
    """
    __tablename__ = 'compliance_profiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    framework = Column(SQLEnum(ComplianceFramework), nullable=False)
    industry = Column(String(100))  # healthcare, legal, financial, etc.
    
    # Core Settings
    sensitivity_level = Column(SQLEnum(SensitivityLevel), default=SensitivityLevel.MODERATE)
    confidence_threshold = Column(Float, default=0.85)
    default_action = Column(SQLEnum(ActionType), default=ActionType.MASK)
    
    # Operational Settings
    auto_quarantine = Column(Boolean, default=False)
    notify_on_detection = Column(Boolean, default=True)
    require_approval = Column(Boolean, default=False)
    
    # Retention & Audit
    log_retention_days = Column(Integer, default=365)
    audit_trail_enabled = Column(Boolean, default=True)
    
    # Technical Settings
    scan_file_types = Column(JSON)  # ['pdf', 'docx', 'txt']
    exclude_system_files = Column(Boolean, default=True)
    scan_depth = Column(String(20), default="normal")  # surface, normal, deep
    
    # Geographic & Jurisdiction
    jurisdictions = Column(JSON)  # ['US', 'EU', 'UK']
    data_residency = Column(String(50))  # us-east-1, eu-west-1, etc.
    
    # Agent Service Integration (Future)
    agent_verification_enabled = Column(Boolean, default=False)
    agent_escalation_threshold = Column(Float, default=0.7)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    custom_rules = relationship("CustomRule", back_populates="profile")
    profile_patterns = relationship("ProfilePatternMapping", back_populates="profile")


class CustomRule(db.Model):
    """
    Custom detection rules that extend base PII patterns
    Built on foundation of existing PII patterns with enhanced logic
    """
    __tablename__ = 'custom_rules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('compliance_profiles.id'), nullable=False)
    
    # Rule Definition
    name = Column(String(255), nullable=False)
    description = Column(Text)
    based_on_pattern = Column(String(100))  # References PIIType enum value
    
    # Enhanced Logic
    conditions = Column(JSON)  # Complex conditions array
    # Example: [
    #   {"type": "pattern_match", "required": True},
    #   {"type": "context_keywords", "keywords": ["patient", "medical"], "min_matches": 1},
    #   {"type": "file_path", "contains": ["/medical/", "/patient/"]},
    #   {"type": "file_size", "min_kb": 10, "max_mb": 50}
    # ]
    
    # Actions Configuration
    primary_action = Column(SQLEnum(ActionType), nullable=False)
    secondary_action = Column(SQLEnum(ActionType))
    escalation_action = Column(SQLEnum(ActionType))
    
    # Overrides
    risk_level_override = Column(SQLEnum(RiskLevel))
    confidence_override = Column(Float)
    
    # Exceptions
    exceptions = Column(JSON)  # User roles, IP ranges, time windows, etc.
    # Example: [
    #   {"type": "user_role", "values": ["compliance_officer", "admin"]},
    #   {"type": "ip_range", "values": ["192.168.1.0/24"]},
    #   {"type": "time_window", "days": ["monday", "tuesday"], "hours": "09:00-17:00"}
    # ]
    
    # Performance & Monitoring
    execution_count = Column(Integer, default=0)
    last_triggered = Column(DateTime)
    false_positive_count = Column(Integer, default=0)
    
    # Agent Integration
    agent_review_required = Column(Boolean, default=False)
    agent_confidence_threshold = Column(Float, default=0.8)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("ComplianceProfile", back_populates="custom_rules")


class ProfilePatternMapping(db.Model):
    """
    Maps PII patterns to compliance profiles with specific settings
    """
    __tablename__ = 'profile_pattern_mappings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('compliance_profiles.id'), nullable=False)
    
    # Pattern Configuration
    pattern_name = Column(String(100), nullable=False)  # Maps to PIIType enum
    is_enabled = Column(Boolean, default=True)
    
    # Pattern-specific overrides
    action_override = Column(SQLEnum(ActionType))
    risk_level_override = Column(SQLEnum(RiskLevel))
    confidence_threshold_override = Column(Float)
    
    # Context-specific settings
    context_keywords = Column(JSON)  # Additional context clues
    exclusion_patterns = Column(JSON)  # Patterns to exclude
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("ComplianceProfile", back_populates="profile_patterns")


class ComplianceEvent(db.Model):
    """
    Audit trail for compliance events and violations
    Designed for agent service monitoring and verification
    """
    __tablename__ = 'compliance_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('compliance_profiles.id'))
    
    # Event Details
    event_type = Column(String(50), nullable=False)  # detection, violation, action, review
    pii_type = Column(String(100))
    rule_id = Column(UUID(as_uuid=True), ForeignKey('custom_rules.id'))
    
    # Detection Details
    content_snippet = Column(Text)  # Anonymized/redacted sample
    detection_confidence = Column(Float)
    detection_method = Column(String(50))  # pattern_match, ml_detection, etc.
    
    # Action Taken
    action_taken = Column(SQLEnum(ActionType))
    action_successful = Column(Boolean, default=True)
    action_details = Column(JSON)
    
    # Context
    source_file = Column(String(500))
    source_location = Column(String(100))  # line number, page, etc.
    user_id = Column(String(255))
    user_role = Column(String(50))
    
    # Agent Verification (Future)
    agent_reviewed = Column(Boolean, default=False)
    agent_verdict = Column(String(50))  # compliant, violation, needs_review
    agent_confidence = Column(Float)
    agent_notes = Column(Text)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)


class ProfileTemplate(db.Model):
    """
    Pre-configured compliance profile templates for common industries
    """
    __tablename__ = 'profile_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template Definition
    name = Column(String(255), nullable=False)
    description = Column(Text)
    industry = Column(String(100), nullable=False)
    framework = Column(SQLEnum(ComplianceFramework), nullable=False)
    
    # Template Configuration (JSON representation of profile settings)
    template_config = Column(JSON, nullable=False)
    default_patterns = Column(JSON)  # Default pattern configurations
    recommended_rules = Column(JSON)  # Suggested custom rules
    
    # Usage Statistics
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), default="system")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)