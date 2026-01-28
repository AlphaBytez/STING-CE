"""
Nectar Bot Models - SQLAlchemy models for AI-as-a-Service Nectar Bots
"""

from enum import Enum
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import db
import uuid
import secrets
import logging

logger = logging.getLogger(__name__)


# Enums for bot status and handoff management
class BotStatus(Enum):
    """Status of a Nectar Bot"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PAUSED = 'paused'
    MAINTENANCE = 'maintenance'


class HandoffStatus(Enum):
    """Status of a handoff request"""
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    RESOLVED = 'resolved'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class HandoffUrgency(Enum):
    """Urgency level for handoff requests"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class NectarBot(db.Model):
    """
    Nectar Bot model for AI-as-a-Service chatbots
    """
    __tablename__ = 'nectar_bots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), index=True)
    owner_email = Column(String(255))
    honey_jar_ids = Column(JSONB, default=[])
    system_prompt = Column(Text)
    max_conversation_length = Column(Integer, default=10)
    confidence_threshold = Column(Float, default=0.7)
    api_key = Column(String(255), unique=True, index=True)
    rate_limit_per_hour = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=1000)
    status = Column(String(50), default='active')
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))
    handoff_enabled = Column(Boolean, default=False)
    handoff_keywords = Column(JSONB, default=[])
    handoff_confidence_threshold = Column(Float, default=0.5)
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_handoffs = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.0)
    
    def to_dict(self):
        """Convert bot to dictionary for API responses"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'owner_id': str(self.owner_id) if self.owner_id else None,
            'owner_email': self.owner_email,
            'honey_jar_ids': self.honey_jar_ids or [],
            'system_prompt': self.system_prompt,
            'max_conversation_length': self.max_conversation_length,
            'confidence_threshold': self.confidence_threshold,
            'api_key': self.api_key,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'rate_limit_per_day': self.rate_limit_per_day,
            'status': self.status,
            'is_public': self.is_public,
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
    
    @staticmethod
    def generate_api_key():
        """Generate a unique API key for a bot"""
        return f"nb_{secrets.token_urlsafe(32)}"


class NectarBotUsage(db.Model):
    """
    Track usage of Nectar Bots for analytics
    """
    __tablename__ = 'nectar_bot_usage'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('nectar_bots.id', ondelete='CASCADE'), nullable=False)
    conversation_id = Column(String(255))
    message_id = Column(String(255))
    user_id = Column(String(255))
    user_ip = Column(String(50))
    user_agent = Column(Text)
    user_message = Column(Text)
    bot_response = Column(Text)
    confidence_score = Column(Float)
    response_time_ms = Column(Integer)
    honey_jars_queried = Column(JSONB, default=[])
    knowledge_matches = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'conversation_id': self.conversation_id,
            'message_id': self.message_id,
            'user_id': self.user_id,
            'user_ip': self.user_ip,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'confidence_score': self.confidence_score,
            'response_time_ms': self.response_time_ms,
            'honey_jars_queried': self.honey_jars_queried,
            'knowledge_matches': self.knowledge_matches,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NectarBotHandoff(db.Model):
    """
    Track handoffs from Nectar Bots to human agents
    """
    __tablename__ = 'nectar_bot_handoffs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey('nectar_bots.id', ondelete='CASCADE'), nullable=False)
    conversation_id = Column(String(255))
    user_id = Column(String(255))
    trigger_type = Column(String(50))  # 'keyword', 'confidence', 'explicit'
    trigger_value = Column(Text)
    status = Column(String(50), default='pending')  # pending, accepted, resolved, expired
    assigned_to = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'trigger_type': self.trigger_type,
            'trigger_value': self.trigger_value,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


def get_bot_by_api_key(api_key):
    """Get a NectarBot by its API key"""
    try:
        return NectarBot.query.filter_by(api_key=api_key).first()
    except Exception as e:
        logger.error(f"Error getting bot by API key: {e}")
        return None


def get_bot_by_slug(slug):
    """Get a NectarBot by its slug"""
    try:
        return NectarBot.query.filter_by(slug=slug).first()
    except Exception as e:
        logger.error(f"Error getting bot by slug: {e}")
        return None


def get_public_bot_by_slug(slug):
    """Get a public NectarBot by its slug"""
    try:
        return NectarBot.query.filter_by(slug=slug, is_public=True, status='active').first()
    except Exception as e:
        logger.error(f"Error getting public bot by slug: {e}")
        return None


def get_bots_by_owner(owner_id):
    """Get all bots owned by a user"""
    try:
        return NectarBot.query.filter_by(owner_id=owner_id).all()
    except Exception as e:
        logger.error(f"Error getting bots by owner: {e}")
        return []


def get_all_bots():
    """Get all Nectar Bots (admin only)"""
    try:
        return NectarBot.query.order_by(NectarBot.created_at.desc()).all()
    except Exception as e:
        logger.error(f"Error getting all bots: {e}")
        return []
