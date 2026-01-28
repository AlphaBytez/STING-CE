"""
Database models for Bee conversation management
"""

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean, 
    ForeignKey, JSON, UUID, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

Base = declarative_base()


class Conversation(Base):
    """Model for conversation sessions"""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    model_type = Column(String(50), default='bee')
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    status = Column(String(20), default='active')  # active, archived, deleted
    metadata = Column(JSON, default={})
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Token tracking columns
    total_tokens = Column(Integer, default=0)
    active_tokens = Column(Integer, default=0)
    pruning_strategy = Column(String(50), default='sliding_window')
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    summaries = relationship("ConversationSummary", back_populates="conversation", cascade="all, delete-orphan")
    context = relationship("ConversationContext", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, status={self.status})>"


class Message(Base):
    """Model for individual messages in conversations"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default={})
    sentiment = Column(JSON, nullable=True)
    tools_used = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    token_count = Column(Integer, default=0)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="check_role"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class ConversationSummary(Base):
    """Model for storing summaries of pruned conversation segments"""
    __tablename__ = 'conversation_summaries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    message_count = Column(Integer, nullable=False)  # Number of messages summarized
    start_timestamp = Column(DateTime(timezone=True), nullable=False)  # First message timestamp
    end_timestamp = Column(DateTime(timezone=True), nullable=False)    # Last message timestamp
    metadata = Column(JSON, default={})  # Additional metadata (topics, entities, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="summaries")
    
    def __repr__(self):
        return f"<ConversationSummary(id={self.id}, conversation_id={self.conversation_id}, messages={self.message_count})>"


class ConversationContext(Base):
    """Model for caching conversation context"""
    __tablename__ = 'conversation_context'
    
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), primary_key=True)
    context_data = Column(JSON, nullable=False)
    last_summary = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="context")
    
    def __repr__(self):
        return f"<ConversationContext(conversation_id={self.conversation_id}, message_count={self.message_count})>"


class UserPreference(Base):
    """Model for storing user preferences across conversations"""
    __tablename__ = 'user_preferences'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    preference_type = Column(String(50), nullable=False)  # setting, style, topic, feature
    preference_key = Column(String(255), nullable=False)
    preference_value = Column(JSON, nullable=False)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        Index('idx_user_preference_unique', 'user_id', 'preference_type', 'preference_key', unique=True),
    )
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, type={self.preference_type}, key={self.preference_key})>"


class MemoryEntry(Base):
    """Model for long-term memory storage"""
    __tablename__ = 'memory_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)  # fact, preference, interaction, learned
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    metadata = Column(JSON, default={})
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("importance >= 0 AND importance <= 1", name="check_importance"),
        Index('idx_memory_importance', 'importance', postgresql_using='btree'),
    )
    
    def __repr__(self):
        return f"<MemoryEntry(id={self.id}, user_id={self.user_id}, type={self.memory_type}, importance={self.importance})>"