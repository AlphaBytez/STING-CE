from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import secrets
import hashlib

# Import db from database module to avoid circular imports
from app.database import db

class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = Column(String(36), primary_key=True, default=lambda: secrets.token_urlsafe(16))
    
    # Key identification
    name = Column(String(255), nullable=False)  # User-provided name for the key
    key_id = Column(String(64), unique=True, nullable=False, index=True)  # Public identifier
    key_hash = Column(String(128), nullable=False, index=True)  # SHA-256 hash of the secret
    
    # User association
    user_id = Column(String(255), nullable=False, index=True)  # Kratos identity ID
    user_email = Column(String(255), nullable=False, index=True)  # For quick lookups
    
    # Key permissions and scope
    permissions = Column(JSON, nullable=False, default=dict)  # Scoped permissions
    scopes = Column(JSON, nullable=False, default=list)  # API scopes (read, write, admin)
    
    # Key lifecycle
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Usage tracking
    usage_count = Column(db.Integer, nullable=False, default=0)
    rate_limit_per_minute = Column(db.Integer, nullable=False, default=60)  # Default rate limit
    
    # Metadata
    description = Column(Text, nullable=True)
    key_metadata = Column(JSON, nullable=False, default=dict)
    
    @classmethod
    def generate_key(cls, user_id, user_email, name, scopes=None, permissions=None, expires_in_days=None, description=None):
        """Generate a new API key with secure random values"""
        # Generate the actual secret key (this is what users will use)
        secret = f"sk_{secrets.token_urlsafe(32)}"
        
        # Generate public key identifier
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        
        # Hash the secret for storage
        key_hash = hashlib.sha256(secret.encode()).hexdigest()
        
        # Set expiration if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create the API key record
        api_key = cls(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            user_email=user_email,
            name=name,
            scopes=scopes or ['read'],
            permissions=permissions or {},
            expires_at=expires_at,
            description=description
        )
        
        # Return both the model and the secret (secret is only available at creation time)
        return api_key, secret
    
    @classmethod
    def verify_key(cls, secret_key):
        """Verify an API key and return the associated record"""
        if not secret_key or not secret_key.startswith('sk_'):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(secret_key.encode()).hexdigest()
        
        # Find the key in database
        api_key = cls.query.filter_by(key_hash=key_hash, is_active=True).first()
        
        if not api_key:
            return None
        
        # Check if key has expired
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Update last used timestamp and usage count
        api_key.last_used_at = datetime.utcnow()
        api_key.usage_count += 1
        db.session.commit()
        
        return api_key
    
    def has_scope(self, scope):
        """Check if the API key has a specific scope"""
        return scope in self.scopes
    
    def has_permission(self, resource, action):
        """Check if the API key has permission for a specific resource/action"""
        if 'admin' in self.scopes:
            return True
        
        resource_perms = self.permissions.get(resource, {})
        if isinstance(resource_perms, list):
            return action in resource_perms
        elif isinstance(resource_perms, dict):
            return resource_perms.get(action, False)
        
        return False
    
    def is_expired(self):
        """Check if the API key has expired"""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'key_id': self.key_id,
            'name': self.name,
            'scopes': self.scopes,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'description': self.description,
            'is_expired': self.is_expired()
        }
        
        if include_sensitive:
            data['user_id'] = self.user_id
            data['user_email'] = self.user_email
            data['key_hash'] = self.key_hash
        
        return data

class ApiKeyUsage(db.Model):
    __tablename__ = 'api_key_usage'
    
    id = Column(String(36), primary_key=True, default=lambda: secrets.token_urlsafe(16))
    
    # Key reference
    api_key_id = Column(String(36), ForeignKey('api_keys.id'), nullable=False, index=True)
    key_id = Column(String(64), nullable=False, index=True)  # Denormalized for quick lookups
    
    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(db.Integer, nullable=False)
    response_time_ms = Column(db.Integer, nullable=True)
    
    # Request metadata
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    request_size_bytes = Column(db.Integer, nullable=True)
    response_size_bytes = Column(db.Integer, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationships
    api_key = relationship("ApiKey", backref="usage_logs")
    
    @classmethod
    def log_usage(cls, api_key, endpoint, method, status_code, **kwargs):
        """Log API key usage"""
        usage = cls(
            api_key_id=api_key.id,
            key_id=api_key.key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            **kwargs
        )
        
        db.session.add(usage)
        db.session.commit()
        
        return usage
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'key_id': self.key_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ip_address': self.ip_address,
            'error_message': self.error_message
        }