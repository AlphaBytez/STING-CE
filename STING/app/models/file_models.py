"""
File Asset Models for STING-CE
Handles file metadata, permissions, and relationships.
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

Base = declarative_base()

class StorageBackend(Enum):
    """Supported storage backends."""
    VAULT = "vault"
    MINIO = "minio"
    FILESYSTEM = "filesystem"

class AccessLevel(Enum):
    """File access levels."""
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"

class PermissionType(Enum):
    """File permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"

class FileAsset(Base):
    """File asset metadata model."""

    __tablename__ = 'file_assets'

    # Primary key (matches actual database schema)
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    
    # File identification
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, index=True)
    
    # File properties
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100))
    checksum = Column(String(64), index=True)  # SHA-256 hash (maps to existing checksum column)
    
    # Storage information
    storage_backend = Column(String(20), nullable=False, default=StorageBackend.VAULT.value)
    storage_path = Column(String(1000), nullable=False)
    
    # Ownership and access (matches actual database schema)
    owner_id = Column(String(255), nullable=True, index=True)
    access_level = Column(String(20), nullable=False, default=AccessLevel.PRIVATE.value)
    
    # Metadata (maps to database 'metadata' column, but using different name to avoid SQLAlchemy conflict)
    file_metadata = Column('metadata', JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    permissions = relationship("FilePermission", back_populates="file_asset", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_file_owner_type', 'owner_id', 'file_type'),
        Index('idx_file_created', 'created_at'),
        Index('idx_file_storage', 'storage_backend', 'storage_path'),
        Index('idx_file_active', 'deleted_at', postgresql_where=Column('deleted_at').is_(None)),
    )
    
    def __repr__(self):
        return f"<FileAsset(id={self.id}, filename='{self.filename}', owner_id={self.owner_id})>"
    
    @property
    def is_deleted(self) -> bool:
        """Check if file is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def storage_backend_enum(self) -> StorageBackend:
        """Get storage backend as enum."""
        return StorageBackend(self.storage_backend)
    
    @property
    def access_level_enum(self) -> AccessLevel:
        """Get access level as enum."""
        return AccessLevel(self.access_level)
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = {
            'id': str(self.id),
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'content_hash': self.content_hash,
            'storage_backend': self.storage_backend,
            'access_level': self.access_level,
            'owner_id': str(self.owner_id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }
        
        if include_metadata and self.file_metadata:
            data['metadata'] = self.file_metadata
            
        return data

class FilePermission(Base):
    """File permission model for access control."""

    __tablename__ = 'file_permissions'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys (match actual database schema)
    file_id = Column(UUID(as_uuid=True), ForeignKey('file_assets.file_id', ondelete='CASCADE'), nullable=False)
    grantee_id = Column(String(255), nullable=False, index=True)  # Matches actual database
    grantee_type = Column(String(50))  # Matches actual database

    # Permission details (match actual database)
    permission_type = Column(String(50))
    can_read = Column(Boolean, default=False)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_share = Column(Boolean, default=False)
    access_level = Column(String(50), default='viewer')

    # Timestamps (match actual database)
    valid_from = Column(DateTime, server_default=func.now())
    valid_until = Column(DateTime, nullable=True)
    shared_by = Column(String(255))
    share_link = Column(String(500))
    link_password_hash = Column(String(255))
    max_downloads = Column(Integer)
    download_count = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    file_asset = relationship("FileAsset", back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_permission_file_user', 'file_id', 'grantee_id'),
        Index('idx_permission_user_type', 'grantee_id', 'permission_type'),
        Index('idx_permission_active', 'valid_until', postgresql_where=Column('valid_until').is_(None)),
    )
    
    def __repr__(self):
        return f"<FilePermission(file_id={self.file_id}, grantee_id={self.grantee_id}, type='{self.permission_type}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if permission is currently active."""
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    @property
    def permission_type_enum(self) -> PermissionType:
        """Get permission type as enum."""
        return PermissionType(self.permission_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'file_id': str(self.file_id),
            'grantee_id': str(self.grantee_id),
            'grantee_type': self.grantee_type,
            'permission_type': self.permission_type,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active
        }

class FileUploadSession(Base):
    """Track file upload sessions for large files."""
    
    __tablename__ = 'file_upload_sessions'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Session details
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    total_size = Column(BigInteger, nullable=False)
    uploaded_size = Column(BigInteger, default=0)
    
    # Upload state
    status = Column(String(20), default='pending')  # pending, uploading, completed, failed
    chunk_count = Column(Integer, default=0)
    
    # Storage information
    temp_storage_path = Column(Text)
    final_file_id = Column(UUID(as_uuid=True), ForeignKey('file_assets.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_upload_session_user', 'user_id', 'status'),
        Index('idx_upload_session_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<FileUploadSession(id={self.id}, user_id={self.user_id}, status='{self.status}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if upload session is expired."""
        return self.expires_at < datetime.utcnow()
    
    @property
    def upload_progress(self) -> float:
        """Get upload progress as percentage."""
        if self.total_size == 0:
            return 0.0
        return (self.uploaded_size / self.total_size) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'filename': self.filename,
            'file_type': self.file_type,
            'total_size': self.total_size,
            'uploaded_size': self.uploaded_size,
            'status': self.status,
            'chunk_count': self.chunk_count,
            'upload_progress': self.upload_progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired
        }

# Database initialization functions
def create_file_tables(engine):
    """Create file-related tables."""
    Base.metadata.create_all(engine)

def get_file_by_id(session, file_id: str, user_id: str = None) -> Optional[FileAsset]:
    """Get file by ID with optional user ownership check."""
    query = session.query(FileAsset).filter(
        FileAsset.file_id == file_id,
        FileAsset.deleted_at.is_(None)
    )
    
    if user_id:
        query = query.filter(FileAsset.owner_id == user_id)
    
    return query.first()

def get_user_files(session, user_id: str, file_type: str = None, 
                  limit: int = 50, offset: int = 0) -> List[FileAsset]:
    """Get files owned by a user."""
    query = session.query(FileAsset).filter(
        FileAsset.owner_id == user_id,
        FileAsset.deleted_at.is_(None)
    )
    
    if file_type:
        query = query.filter(FileAsset.file_type == file_type)
    
    return query.order_by(FileAsset.created_at.desc()).offset(offset).limit(limit).all()

def check_file_permission(session, file_id: str, user_id: str,
                         permission_type: str) -> bool:
    """Check if user has specific permission for a file."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[PERMISSION_CHECK] Checking permission: file_id={file_id}, user_id={user_id}, type={permission_type}")

    # Check if user owns the file
    file_asset = session.query(FileAsset).filter(
        FileAsset.file_id == file_id,
        FileAsset.owner_id == user_id,
        FileAsset.deleted_at.is_(None)
    ).first()

    if file_asset:
        logger.info(f"[PERMISSION_CHECK] User {user_id} owns file {file_id} - permission granted")
        return True  # Owner has all permissions

    # Check for admin API key access to demo reports
    from flask import g
    if hasattr(g, 'api_key') and g.api_key and 'admin' in g.api_key.scopes:
        demo_file = session.query(FileAsset).filter(
            FileAsset.file_id == file_id,
            FileAsset.deleted_at.is_(None)
        ).first()
        if demo_file and 'Demo' in demo_file.filename:
            logger.info(f"[PERMISSION_CHECK] Admin API key access granted for demo file {file_id}")
            return True

    # Check if file exists at all (for debugging)
    any_file = session.query(FileAsset).filter(
        FileAsset.file_id == file_id,
        FileAsset.deleted_at.is_(None)
    ).first()

    if not any_file:
        logger.warning(f"[PERMISSION_CHECK] File {file_id} does not exist or is deleted")
        return False

    logger.info(f"[PERMISSION_CHECK] File {file_id} exists but is owned by {any_file.owner_id}, not {user_id}")

    # Check explicit permissions (match actual database schema)
    permission = session.query(FilePermission).filter(
        FilePermission.file_id == file_id,
        FilePermission.grantee_id == user_id,
        FilePermission.permission_type == permission_type
    ).first()

    if permission:
        # Check if permission is active based on actual schema
        is_active = permission.can_read if permission_type == 'read' else False
        logger.info(f"[PERMISSION_CHECK] Found explicit permission for user {user_id} on file {file_id}: active={is_active}")
        return is_active
    else:
        logger.info(f"[PERMISSION_CHECK] No explicit permission found for user {user_id} on file {file_id}")
        return False