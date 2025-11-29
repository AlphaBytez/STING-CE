from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, JSON, ForeignKey, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import db
import uuid
from datetime import datetime
from enum import Enum
import re
import secrets


class BotStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class HandoffStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class HandoffUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NectarBot(db.Model):
    """Nectar Bot configuration model"""
    __tablename__ = 'nectar_bots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text)

    # Organization/User ownership
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    owner_email = Column(String(255), nullable=False)
    
    # Bot configuration
    honey_jar_ids = Column(JSON, default=list)  # List of accessible honey jar IDs
    system_prompt = Column(Text)
    max_conversation_length = Column(Integer, default=20)
    confidence_threshold = Column(Float, default=0.7)
    
    # API configuration
    api_key = Column(String(255), unique=True, nullable=False)
    rate_limit_per_hour = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=1000)
    
    # Status and metadata
    status = Column(String(20), default=BotStatus.ACTIVE.value)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))
    
    # Handoff configuration
    handoff_enabled = Column(Boolean, default=True)
    handoff_keywords = Column(JSON, default=lambda: ["help", "human", "support", "escalate"])
    handoff_confidence_threshold = Column(Float, default=0.6)
    
    # Statistics (updated periodically)
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_handoffs = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    
    # Relationships
    handoffs = relationship("NectarBotHandoff", back_populates="bot", cascade="all, delete-orphan")
    usage_records = relationship("NectarBotUsage", back_populates="bot", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.api_key:
            self.api_key = self.generate_api_key()
        if not self.slug and self.name:
            self.slug = self.generate_slug(self.name)
    
    @staticmethod
    def generate_api_key():
        """Generate a new API key for the bot"""
        return f"nb_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_slug(name):
        """Generate a URL-friendly slug from bot name"""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        # Add random suffix to ensure uniqueness
        random_suffix = secrets.token_hex(4)  # 8 char hex
        return f"{slug}-{random_suffix}"

    @property
    def public_url(self):
        """Get the public URL for this bot (if public)"""
        if self.is_public and self.slug:
            # In production, this would use the actual domain
            # For now, return relative path
            return f"/bot/{self.slug}"
        return None

    @property
    def embed_url(self):
        """Get the embeddable widget URL for this bot (if public)"""
        if self.is_public and self.slug:
            return f"/bot/{self.slug}/embed"
        return None
    
    def to_dict(self, include_api_key=False):
        """Convert to dictionary representation"""
        data = {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'owner_id': str(self.owner_id),
            'owner_email': self.owner_email,
            'honey_jar_ids': self.honey_jar_ids or [],
            'system_prompt': self.system_prompt,
            'max_conversation_length': self.max_conversation_length,
            'confidence_threshold': self.confidence_threshold,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'rate_limit_per_day': self.rate_limit_per_day,
            'status': self.status,
            'is_public': self.is_public,
            'public_url': self.public_url,
            'embed_url': self.embed_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'handoff_enabled': self.handoff_enabled,
            'handoff_keywords': self.handoff_keywords or [],
            'handoff_confidence_threshold': self.handoff_confidence_threshold,
            'total_conversations': self.total_conversations,
            'total_messages': self.total_messages,
            'total_handoffs': self.total_handoffs,
            'average_confidence': self.average_confidence
        }

        if include_api_key:
            data['api_key'] = self.api_key

        return data
    
    def update_stats(self):
        """Update bot statistics from usage data"""
        from sqlalchemy import func
        
        # Update conversation count
        conv_count = db.session.query(func.count(
            func.distinct(NectarBotUsage.conversation_id)
        )).filter(NectarBotUsage.bot_id == self.id).scalar() or 0
        
        # Update message count
        msg_count = db.session.query(func.count(NectarBotUsage.id)).filter(
            NectarBotUsage.bot_id == self.id
        ).scalar() or 0
        
        # Update handoff count
        handoff_count = db.session.query(func.count(NectarBotHandoff.id)).filter(
            NectarBotHandoff.bot_id == self.id
        ).scalar() or 0
        
        # Update average confidence
        avg_confidence = db.session.query(func.avg(NectarBotUsage.confidence_score)).filter(
            NectarBotUsage.bot_id == self.id,
            NectarBotUsage.confidence_score.isnot(None)
        ).scalar() or 0.0
        
        self.total_conversations = conv_count
        self.total_messages = msg_count
        self.total_handoffs = handoff_count
        self.average_confidence = float(avg_confidence) if avg_confidence else 0.0
        self.last_used_at = datetime.utcnow()


class NectarBotHandoff(db.Model):
    """Nectar Bot handoff requests"""
    __tablename__ = 'nectar_bot_handoffs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('nectar_bots.id'), nullable=False)
    
    # Conversation context
    conversation_id = Column(String(255), nullable=False)
    user_id = Column(String(255))  # External user identifier
    user_info = Column(JSON)  # User metadata (name, email, etc.)
    
    # Handoff details
    reason = Column(String(100), nullable=False)  # low_confidence, keyword_detected, etc.
    urgency = Column(String(20), default=HandoffUrgency.MEDIUM.value)
    status = Column(String(20), default=HandoffStatus.PENDING.value)
    
    # Context data
    conversation_history = Column(JSON)  # Full message history
    honey_jars_used = Column(JSON, default=list)  # Knowledge sources referenced
    trigger_message = Column(Text)  # Message that triggered handoff
    bot_response = Column(Text)  # Last bot response
    confidence_score = Column(Float)  # AI confidence when handoff triggered
    
    # Resolution tracking
    assigned_to = Column(String(255))  # Admin user who accepted handoff
    resolved_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    resolution_time_minutes = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bot = relationship("NectarBot", back_populates="handoffs")
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'bot_name': self.bot.name if self.bot else None,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'user_info': self.user_info or {},
            'reason': self.reason,
            'urgency': self.urgency,
            'status': self.status,
            'conversation_history': self.conversation_history or [],
            'honey_jars_used': self.honey_jars_used or [],
            'trigger_message': self.trigger_message,
            'bot_response': self.bot_response,
            'confidence_score': self.confidence_score,
            'assigned_to': self.assigned_to,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes,
            'resolution_time_minutes': self.resolution_time_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_resolution_time(self):
        """Calculate and set resolution time in minutes"""
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            self.resolution_time_minutes = int(delta.total_seconds() / 60)


class NectarBotConversation(db.Model):
    """Nectar Bot conversation tracking for handoff support"""
    __tablename__ = 'nectar_bot_conversations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(255), unique=True, nullable=False, index=True)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('nectar_bots.id'), nullable=False)

    # Session metadata
    user_id = Column(String(255))
    user_ip = Column(String(45))
    user_agent = Column(Text)
    session_metadata = Column(JSON, default=dict)

    # Status for handoff
    status = Column(String(50), default='active')  # active, closed, handed_off
    handed_off_to = Column(String(255))  # User ID if handed off
    handed_off_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Stats
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Relationships
    bot = relationship("NectarBot", backref="conversations")

    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'conversation_id': self.conversation_id,
            'bot_id': str(self.bot_id),
            'user_id': self.user_id,
            'status': self.status,
            'handed_off_to': self.handed_off_to,
            'handed_off_at': self.handed_off_at.isoformat() if self.handed_off_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'message_count': self.message_count,
            'total_tokens': self.total_tokens,
            'session_metadata': self.session_metadata or {}
        }


class NectarBotMessage(db.Model):
    """Individual messages in Nectar Bot conversations"""
    __tablename__ = 'nectar_bot_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(String(255), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    # Metadata
    confidence_score = Column(Float)
    response_time_ms = Column(Integer)
    honey_jars_used = Column(JSON, default=list)
    knowledge_matches = Column(Integer, default=0)

    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'confidence_score': self.confidence_score,
            'response_time_ms': self.response_time_ms,
            'honey_jars_used': self.honey_jars_used or [],
            'knowledge_matches': self.knowledge_matches,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class NectarBotUsage(db.Model):
    """Nectar Bot usage tracking"""
    __tablename__ = 'nectar_bot_usage'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('nectar_bots.id'), nullable=False)
    
    # Request details
    conversation_id = Column(String(255), nullable=False)
    message_id = Column(String(255))
    user_id = Column(String(255))
    user_ip = Column(String(45))  # Support IPv6
    user_agent = Column(Text)
    
    # Message content (optional, for analytics)
    user_message = Column(Text)
    bot_response = Column(Text)
    confidence_score = Column(Float)
    response_time_ms = Column(Integer)
    
    # Honey Jar usage
    honey_jars_queried = Column(JSON, default=list)
    knowledge_matches = Column(Integer, default=0)
    
    # Rate limiting
    rate_limit_hit = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    bot = relationship("NectarBot", back_populates="usage_records")
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'conversation_id': self.conversation_id,
            'message_id': self.message_id,
            'user_id': self.user_id,
            'confidence_score': self.confidence_score,
            'response_time_ms': self.response_time_ms,
            'honey_jars_queried': self.honey_jars_queried or [],
            'knowledge_matches': self.knowledge_matches,
            'rate_limit_hit': self.rate_limit_hit,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Helper functions for bot management
def get_bot_by_api_key(api_key):
    """Get bot by API key"""
    return NectarBot.query.filter_by(api_key=api_key).first()


def get_bot_by_slug(slug):
    """Get bot by slug"""
    return NectarBot.query.filter_by(slug=slug).first()


def get_public_bot_by_slug(slug):
    """Get public bot by slug (only returns if bot is public and active)"""
    return NectarBot.query.filter_by(
        slug=slug,
        is_public=True,
        status=BotStatus.ACTIVE.value
    ).first()


def get_active_bots_for_user(user_id):
    """Get all active bots for a user"""
    return NectarBot.query.filter_by(
        owner_id=user_id,
        status=BotStatus.ACTIVE.value
    ).order_by(NectarBot.created_at.desc()).all()


def get_pending_handoffs():
    """Get all pending handoffs across all bots"""
    return NectarBotHandoff.query.filter_by(
        status=HandoffStatus.PENDING.value
    ).order_by(NectarBotHandoff.created_at.asc()).all()


def get_bot_analytics(bot_id, days=30):
    """Get analytics for a specific bot"""
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(days=days)
    
    usage_query = NectarBotUsage.query.filter(
        NectarBotUsage.bot_id == bot_id,
        NectarBotUsage.created_at >= since
    )
    
    handoff_query = NectarBotHandoff.query.filter(
        NectarBotHandoff.bot_id == bot_id,
        NectarBotHandoff.created_at >= since
    )
    
    return {
        'total_messages': usage_query.count(),
        'unique_conversations': db.session.query(
            func.count(func.distinct(NectarBotUsage.conversation_id))
        ).filter(
            NectarBotUsage.bot_id == bot_id,
            NectarBotUsage.created_at >= since
        ).scalar() or 0,
        'average_confidence': usage_query.filter(
            NectarBotUsage.confidence_score.isnot(None)
        ).with_entities(func.avg(NectarBotUsage.confidence_score)).scalar() or 0.0,
        'average_response_time': usage_query.filter(
            NectarBotUsage.response_time_ms.isnot(None)
        ).with_entities(func.avg(NectarBotUsage.response_time_ms)).scalar() or 0,
        'total_handoffs': handoff_query.count(),
        'resolved_handoffs': handoff_query.filter_by(status=HandoffStatus.RESOLVED.value).count(),
        'average_resolution_time': handoff_query.filter(
            NectarBotHandoff.resolution_time_minutes.isnot(None)
        ).with_entities(func.avg(NectarBotHandoff.resolution_time_minutes)).scalar() or 0
    }