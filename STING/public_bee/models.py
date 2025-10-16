"""
Database models for Public Bee service
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class PublicBot(Base):
    """Public bot configuration model"""
    __tablename__ = 'public_bots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)  # User-friendly name
    description = Column(Text)
    
    # Configuration
    honey_jar_ids = Column(JSON, default=[])  # List of honey jar IDs to use
    system_prompt = Column(Text, default="You are a helpful AI assistant.")
    response_guidelines = Column(JSON, default={})  # Custom response rules
    
    # Access control
    api_keys = Column(JSON, default=[])  # List of API keys that can access this bot
    allowed_domains = Column(JSON, default=[])  # Domains allowed for CORS
    rate_limit = Column(Integer, default=100)  # Requests per hour
    max_concurrent = Column(Integer, default=5)  # Max concurrent sessions
    
    # Status and metadata
    enabled = Column(Boolean, default=True)
    public = Column(Boolean, default=False)  # Whether bot is publicly discoverable
    created_by = Column(String(255), nullable=False)  # User ID who created the bot
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Usage tracking
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'honey_jar_ids': self.honey_jar_ids,
            'system_prompt': self.system_prompt,
            'response_guidelines': self.response_guidelines,
            'allowed_domains': self.allowed_domains,
            'rate_limit': self.rate_limit,
            'max_concurrent': self.max_concurrent,
            'enabled': self.enabled,
            'public': self.public,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'stats': {
                'total_conversations': self.total_conversations,
                'total_messages': self.total_messages,
                'total_tokens': self.total_tokens
            }
        }
    
    def public_dict(self):
        """Public-safe dictionary (no sensitive info)"""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'enabled': self.enabled
        }


class PublicBotUsage(Base):
    """Usage tracking for public bot interactions"""
    __tablename__ = 'public_bot_usage'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Request metadata
    api_key = Column(String(255), index=True)  # API key used (hashed)
    ip_address = Column(String(45))  # IPv4/IPv6 address
    user_agent = Column(Text)
    referer = Column(String(500))
    
    # Usage metrics
    conversation_id = Column(String(255), index=True)
    message_count = Column(Integer, default=1)
    tokens_used = Column(Integer, default=0)
    response_time_ms = Column(Integer)
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'api_key': self.api_key[:8] + '...' if self.api_key else None,  # Masked
            'ip_address': self.ip_address,
            'conversation_id': self.conversation_id,
            'message_count': self.message_count,
            'tokens_used': self.tokens_used,
            'response_time_ms': self.response_time_ms,
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class PublicBotAPIKey(Base):
    """API keys for accessing public bots"""
    __tablename__ = 'public_bot_api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Key details
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for display
    name = Column(String(255), nullable=False)  # User-friendly name
    
    # Permissions
    rate_limit = Column(Integer)  # Override bot's rate limit
    max_concurrent = Column(Integer)  # Override bot's concurrent limit
    allowed_ips = Column(JSON, default=[])  # IP whitelist
    
    # Status
    enabled = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))  # Optional expiration
    
    # Tracking
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'bot_id': str(self.bot_id),
            'key_prefix': self.key_prefix,
            'name': self.name,
            'rate_limit': self.rate_limit,
            'max_concurrent': self.max_concurrent,
            'allowed_ips': self.allowed_ips,
            'enabled': self.enabled,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count
        }