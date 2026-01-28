"""
Passkey models for WebAuthn credential management
"""
from datetime import datetime
from enum import Enum
from app.database import db


class PasskeyStatus(str, Enum):
    """Passkey status enumeration"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class Passkey(db.Model):
    """Passkey credential model for WebAuthn"""
    __tablename__ = 'passkeys'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # WebAuthn credential data
    credential_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    public_key = db.Column(db.Text, nullable=False)  # Base64 encoded public key
    sign_count = db.Column(db.Integer, default=0, nullable=False)
    
    # User-friendly information
    name = db.Column(db.String(100), nullable=False)  # User-defined name like "iPhone 15", "MacBook Pro"
    device_type = db.Column(db.String(50), nullable=True)  # "platform", "cross-platform", "security_key"
    
    # Metadata
    user_agent = db.Column(db.String(500), nullable=True)  # Browser/device info when created
    ip_address = db.Column(db.String(45), nullable=True)  # IP when created
    
    # Status and security
    status = db.Column(db.Enum(PasskeyStatus), default=PasskeyStatus.ACTIVE, nullable=False)
    is_backup_eligible = db.Column(db.Boolean, default=False, nullable=False)
    is_backup_state = db.Column(db.Boolean, default=False, nullable=False)
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('passkeys', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Passkey {self.name} for user {self.user_id}>'
    
    def to_dict(self):
        """Convert passkey to dictionary for API responses"""
        return {
            'id': self.id,
            'credential_id': self.credential_id,
            'name': self.name,
            'device_type': self.device_type,
            'status': self.status.value,
            'is_backup_eligible': self.is_backup_eligible,
            'is_backup_state': self.is_backup_state,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
        }
    
    def record_usage(self):
        """Record that this passkey was used for authentication"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def revoke(self):
        """Revoke this passkey"""
        self.status = PasskeyStatus.REVOKED
        self.revoked_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def is_active(self):
        """Check if passkey is active and usable"""
        return self.status == PasskeyStatus.ACTIVE
    
    @classmethod
    def get_user_passkeys(cls, user_id, include_revoked=False):
        """Get all passkeys for a user"""
        query = cls.query.filter_by(user_id=user_id)
        if not include_revoked:
            query = query.filter_by(status=PasskeyStatus.ACTIVE)
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def count_user_passkeys(cls, user_id):
        """Count active passkeys for a user"""
        return cls.query.filter_by(user_id=user_id, status=PasskeyStatus.ACTIVE).count()
    
    @classmethod
    def find_by_credential_id(cls, credential_id):
        """Find passkey by credential ID - handles both base64 and base64url formats"""
        import base64
        
        # First try direct match
        passkey = cls.query.filter_by(credential_id=credential_id, status=PasskeyStatus.ACTIVE).first()
        if passkey:
            return passkey
        
        # Try converting between base64 and base64url formats
        try:
            # If it's base64url (no padding, has - or _), convert to base64
            if '-' in credential_id or '_' in credential_id:
                # Convert base64url to base64
                base64_id = credential_id.replace('-', '+').replace('_', '/')
                # Add padding if needed
                padding = 4 - (len(base64_id) % 4)
                if padding != 4:
                    base64_id += '=' * padding
                passkey = cls.query.filter_by(credential_id=base64_id, status=PasskeyStatus.ACTIVE).first()
                if passkey:
                    return passkey
            else:
                # Try converting base64 to base64url
                base64url_id = credential_id.rstrip('=').replace('+', '-').replace('/', '_')
                passkey = cls.query.filter_by(credential_id=base64url_id, status=PasskeyStatus.ACTIVE).first()
                if passkey:
                    return passkey
        except Exception:
            pass
        
        return None


class PasskeyAuthenticationChallenge(db.Model):
    """Temporary storage for passkey authentication challenges"""
    __tablename__ = 'passkey_authentication_challenges'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge = db.Column(db.String(512), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Can be null for usernameless
    username = db.Column(db.String(255), nullable=True)  # Store username for lookup
    
    # Keep model simple for now
    
    # Expiration
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    
    def is_valid(self):
        """Check if challenge is valid (not used and not expired)"""
        return not self.used and datetime.utcnow() <= self.expires_at
    
    def mark_used(self):
        """Mark challenge as used"""
        self.used = True
        self.used_at = datetime.utcnow()
    
    @classmethod  
    def create_challenge(cls, challenge, username=None, user_id=None, expires_in_minutes=5):
        """Create a new authentication challenge"""
        from datetime import timedelta
        
        auth_challenge = cls(
            challenge=challenge,
            username=username,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        )
        
        db.session.add(auth_challenge)
        db.session.commit()
        
        return auth_challenge
    
    @classmethod
    def get_valid_challenge(cls, challenge):
        """Get a valid challenge by challenge string"""
        auth_challenge = cls.query.filter_by(
            challenge=challenge,
            used=False
        ).first()
        
        if auth_challenge and auth_challenge.is_valid():
            return auth_challenge
        return None
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired challenges"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for challenge in expired:
            db.session.delete(challenge)
        db.session.commit()
        return len(expired)


class PasskeyRegistrationChallenge(db.Model):
    """Temporary storage for passkey registration challenges"""
    __tablename__ = 'passkey_registration_challenges'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Challenge data
    challenge = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Allow nullable for demo users
    
    # Registration context
    user_agent = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    # Expiration
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('passkey_challenges', lazy=True))
    
    def __repr__(self):
        return f'<PasskeyChallenge {self.challenge[:8]}... for user {self.user_id}>'
    
    def is_expired(self):
        """Check if challenge is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if challenge is valid (not used and not expired)"""
        return not self.used and not self.is_expired()
    
    def mark_used(self):
        """Mark challenge as used"""
        self.used = True
        self.used_at = datetime.utcnow()
    
    @property
    def challenge_id(self):
        """Provide challenge_id property for compatibility with webauthn_routes"""
        return self.challenge
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired challenges"""
        expired_challenges = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for challenge in expired_challenges:
            db.session.delete(challenge)
        db.session.commit()
        return len(expired_challenges)
    
    @classmethod
    def create_challenge(cls, user_id, challenge, registration_options, expires_in_minutes=10):
        """Create a new registration challenge"""
        from datetime import timedelta
        
        challenge_record = cls(
            challenge=challenge,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        )
        
        db.session.add(challenge_record)
        db.session.commit()
        
        return challenge_record
    
    @classmethod
    def get_valid_challenge(cls, challenge_id):
        """Get a valid (non-expired, unused) challenge by challenge ID"""
        challenge_record = cls.query.filter_by(challenge=challenge_id).first()
        
        if challenge_record and challenge_record.is_valid():
            return challenge_record
        
        return None


# Note: PasskeyAuthenticationChallenge model already exists above at line 140
# We can extend it if needed for AAL2 functionality
