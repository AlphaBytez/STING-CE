#!/usr/bin/env python3
"""
QE Bee (Quality Engineering Bee) Review Models
Database models for the review agent queue and results
"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import db


# Helper to create Enum that uses enum values (not names) for PostgreSQL
def PGEnum(enum_class, **kwargs):
    """Create a PostgreSQL-compatible Enum that uses value strings"""
    return SQLEnum(
        enum_class,
        values_callable=lambda obj: [e.value for e in obj],
        **kwargs
    )


class ReviewTargetType(enum.Enum):
    """Types of items that can be reviewed"""
    REPORT = "report"
    MESSAGE = "message"
    DOCUMENT = "document"
    PII_DETECTION = "pii_detection"


class ReviewType(enum.Enum):
    """Types of reviews QE Bee can perform"""
    OUTPUT_VALIDATION = "output_validation"      # Check output completeness/quality
    PII_CHECK = "pii_check"                      # Verify PII deserialization complete
    QUALITY_CHECK = "quality_check"              # Content quality assessment
    FORMAT_VALIDATION = "format_validation"      # Structure/format correctness
    COMPLIANCE_CHECK = "compliance_check"        # Compliance requirements met


class ReviewStatus(enum.Enum):
    """Status of a review job"""
    PENDING = "pending"
    REVIEWING = "reviewing"
    PASSED = "passed"
    FAILED = "failed"
    ESCALATED = "escalated"
    SKIPPED = "skipped"


class ReviewResultCode(enum.Enum):
    """Standardized result codes for review outcomes"""
    # Pass codes
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"

    # Fail codes - PII related
    PII_TOKENS_REMAINING = "PII_TOKENS_REMAINING"
    PII_DESERIALIZATION_INCOMPLETE = "PII_DESERIALIZATION_INCOMPLETE"

    # Fail codes - Output related
    OUTPUT_TRUNCATED = "OUTPUT_TRUNCATED"
    OUTPUT_EMPTY = "OUTPUT_EMPTY"
    OUTPUT_MALFORMED = "OUTPUT_MALFORMED"
    GENERATION_ERROR = "GENERATION_ERROR"

    # Fail codes - Quality related
    QUALITY_LOW = "QUALITY_LOW"
    CONTENT_INCOHERENT = "CONTENT_INCOHERENT"
    OFF_TOPIC = "OFF_TOPIC"

    # Fail codes - Format related
    FORMAT_INVALID = "FORMAT_INVALID"
    MISSING_SECTIONS = "MISSING_SECTIONS"

    # System codes
    REVIEW_TIMEOUT = "REVIEW_TIMEOUT"
    REVIEW_ERROR = "REVIEW_ERROR"
    SKIPPED_BY_CONFIG = "SKIPPED_BY_CONFIG"


class ReviewQueue(db.Model):
    """
    Queue of items awaiting QE Bee review.
    Lightweight model for fast queue processing.
    """
    __tablename__ = 'review_queue'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Target identification
    target_type = Column(PGEnum(ReviewTargetType, name='review_target_type', create_type=False), nullable=False)
    target_id = Column(String(100), nullable=False)  # UUID or ID of the item to review

    # Review configuration
    review_type = Column(PGEnum(ReviewType, name='review_type', create_type=False), nullable=False, default=ReviewType.OUTPUT_VALIDATION)
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest

    # Status tracking
    status = Column(PGEnum(ReviewStatus, name='review_status', create_type=False), nullable=False, default=ReviewStatus.PENDING)

    # Results
    result_code = Column(PGEnum(ReviewResultCode, name='review_result_code', create_type=False), nullable=True)
    result_message = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    review_details = Column(JSON, nullable=True)  # Detailed findings from review

    # Webhook tracking
    webhook_url = Column(String(500), nullable=True)
    webhook_sent = Column(Boolean, default=False)
    webhook_sent_at = Column(DateTime, nullable=True)
    webhook_response_code = Column(Integer, nullable=True)

    # Processing metadata
    worker_id = Column(String(100), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # User context
    user_id = Column(String(100), nullable=True)  # User who owns the target item

    # Indexes for efficient queue processing
    __table_args__ = (
        Index('idx_review_queue_status_priority', 'status', 'priority', 'created_at'),
        Index('idx_review_queue_target', 'target_type', 'target_id'),
        Index('idx_review_queue_user', 'user_id', 'status'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'target_type': self.target_type.value if self.target_type else None,
            'target_id': self.target_id,
            'review_type': self.review_type.value if self.review_type else None,
            'priority': self.priority,
            'status': self.status.value if self.status else None,
            'result_code': self.result_code.value if self.result_code else None,
            'result_message': self.result_message,
            'confidence_score': self.confidence_score,
            'review_details': self.review_details,
            'webhook_sent': self.webhook_sent,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'user_id': self.user_id
        }


class ReviewHistory(db.Model):
    """
    Historical record of all reviews performed.
    Kept separate from queue for analytics and audit purposes.
    """
    __tablename__ = 'review_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference to original queue item
    queue_id = Column(UUID(as_uuid=True), nullable=True)

    # Target identification
    target_type = Column(PGEnum(ReviewTargetType, name='review_target_type', create_type=False), nullable=False)
    target_id = Column(String(100), nullable=False)

    # Review details
    review_type = Column(PGEnum(ReviewType, name='review_type', create_type=False), nullable=False)
    result_code = Column(PGEnum(ReviewResultCode, name='review_result_code', create_type=False), nullable=False)
    result_message = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    review_details = Column(JSON, nullable=True)

    # Processing metadata
    worker_id = Column(String(100), nullable=True)
    model_used = Column(String(100), nullable=True)  # LLM model used for review
    processing_time_ms = Column(Integer, nullable=True)

    # Context
    user_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes for analytics queries
    __table_args__ = (
        Index('idx_review_history_result', 'result_code', 'created_at'),
        Index('idx_review_history_target', 'target_type', 'target_id'),
        Index('idx_review_history_user', 'user_id', 'created_at'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'queue_id': str(self.queue_id) if self.queue_id else None,
            'target_type': self.target_type.value if self.target_type else None,
            'target_id': self.target_id,
            'review_type': self.review_type.value if self.review_type else None,
            'result_code': self.result_code.value if self.result_code else None,
            'result_message': self.result_message,
            'confidence_score': self.confidence_score,
            'review_details': self.review_details,
            'model_used': self.model_used,
            'processing_time_ms': self.processing_time_ms,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WebhookConfig(db.Model):
    """
    User/org webhook configuration for notifications.
    CE: Local webhooks only
    Enterprise: External integrations (Slack, Teams, etc.)
    """
    __tablename__ = 'webhook_configs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner
    user_id = Column(String(100), nullable=False)

    # Configuration
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=True)  # For HMAC signing

    # Event filters
    event_types = Column(JSON, nullable=True)  # List of event types to receive
    target_types = Column(JSON, nullable=True)  # List of target types to receive
    result_codes = Column(JSON, nullable=True)  # Filter by result codes (e.g., only failures)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Statistics
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    last_sent_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_webhook_user_active', 'user_id', 'is_active'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'name': self.name,
            'url': self.url,
            'event_types': self.event_types,
            'target_types': self.target_types,
            'result_codes': self.result_codes,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'last_sent_at': self.last_sent_at.isoformat() if self.last_sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
