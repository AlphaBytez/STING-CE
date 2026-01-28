"""
Profile Models for STING-CE Profile Service
Extended profile data models that complement Kratos identity.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()

class UserProfile(Base):
    """Extended user profile model."""
    
    __tablename__ = 'user_profiles'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to Kratos identity
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # Profile information
    display_name = Column(String(100))
    first_name = Column(String(50))
    last_name = Column(String(50))
    bio = Column(Text)
    location = Column(String(100))
    website = Column(String(255))
    phone = Column(String(20))
    
    # Profile picture (links to file service)
    profile_picture_file_id = Column(UUID(as_uuid=True))
    
    # Preferences
    timezone = Column(String(50), default='UTC')
    language = Column(String(10), default='en')
    preferences = Column(JSONB, default=dict)
    privacy_settings = Column(JSONB, default=dict)
    
    # Metadata
    profile_completion = Column(String(20), default='incomplete')  # incomplete, partial, complete
    last_activity = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_profiles_user_id', 'user_id'),
        Index('idx_user_profiles_display_name', 'display_name'),
        Index('idx_user_profiles_active', 'deleted_at', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_user_profiles_completion', 'profile_completion'),
    )
    
    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, display_name='{self.display_name}')>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if profile is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.display_name or "Unknown User"
    
    def calculate_completion(self) -> str:
        """Calculate profile completion status."""
        score = 0
        total_fields = 8
        
        # Check required/important fields
        if self.display_name: score += 1
        if self.first_name: score += 1
        if self.last_name: score += 1
        if self.bio: score += 1
        if self.location: score += 1
        if self.profile_picture_file_id: score += 1
        if self.timezone and self.timezone != 'UTC': score += 1
        if self.preferences: score += 1
        
        if score >= 7:
            return 'complete'
        elif score >= 4:
            return 'partial'
        else:
            return 'incomplete'
    
    def to_dict(self, include_private: bool = True) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'display_name': self.display_name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'profile_picture_file_id': str(self.profile_picture_file_id) if self.profile_picture_file_id else None,
            'timezone': self.timezone,
            'language': self.language,
            'profile_completion': self.calculate_completion(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_deleted': self.is_deleted
        }
        
        # Include private data only if requested
        if include_private:
            data.update({
                'phone': self.phone,
                'preferences': self.preferences or {},
                'privacy_settings': self.privacy_settings or {}
            })
        
        return data

class ProfileExtension(Base):
    """Profile extensions for custom fields."""
    
    __tablename__ = 'profile_extensions'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to profile
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id', ondelete='CASCADE'), nullable=False)
    
    # Extension data
    extension_type = Column(String(50), nullable=False)  # e.g., 'social_links', 'skills', 'certifications'
    extension_data = Column(JSONB, nullable=False)
    
    # Metadata
    is_public = Column(Boolean, default=True)
    sort_order = Column(String(10), default='0')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_profile_extensions_profile', 'profile_id', 'extension_type'),
        Index('idx_profile_extensions_type', 'extension_type'),
        Index('idx_profile_extensions_public', 'is_public'),
    )
    
    def __repr__(self):
        return f"<ProfileExtension(id={self.id}, profile_id={self.profile_id}, type='{self.extension_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'extension_type': self.extension_type,
            'extension_data': self.extension_data,
            'is_public': self.is_public,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProfileActivity(Base):
    """Track profile activity and changes."""
    
    __tablename__ = 'profile_activities'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to profile
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id', ondelete='CASCADE'), nullable=False)
    
    # Activity details
    activity_type = Column(String(50), nullable=False)  # e.g., 'profile_updated', 'picture_changed'
    activity_data = Column(JSONB)
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_profile_activities_profile', 'profile_id', 'created_at'),
        Index('idx_profile_activities_type', 'activity_type'),
        Index('idx_profile_activities_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ProfileActivity(id={self.id}, profile_id={self.profile_id}, type='{self.activity_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'activity_type': self.activity_type,
            'activity_data': self.activity_data,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Database initialization functions
def create_profile_tables(engine):
    """Create profile-related tables."""
    Base.metadata.create_all(engine)

def get_profile_by_user_id(session, user_id: str) -> Optional[UserProfile]:
    """Get profile by user ID."""
    return session.query(UserProfile).filter(
        UserProfile.user_id == user_id,
        UserProfile.deleted_at.is_(None)
    ).first()

def get_profile_extensions(session, profile_id: str, extension_type: str = None) -> list:
    """Get profile extensions."""
    query = session.query(ProfileExtension).filter(
        ProfileExtension.profile_id == profile_id
    )
    
    if extension_type:
        query = query.filter(ProfileExtension.extension_type == extension_type)
    
    return query.order_by(ProfileExtension.sort_order, ProfileExtension.created_at).all()

def log_profile_activity(session, profile_id: str, activity_type: str, 
                        activity_data: Dict[str, Any] = None, 
                        ip_address: str = None, user_agent: str = None):
    """Log profile activity."""
    activity = ProfileActivity(
        profile_id=profile_id,
        activity_type=activity_type,
        activity_data=activity_data,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    session.add(activity)
    session.commit()
    
    return activity