"""
User models for Kratos-based authentication
"""
from datetime import datetime
from enum import Enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import event
from app.database import db


class UserRole(str, Enum):
    """User role enumeration - matches database schema"""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(db.Model):
    """User model integrated with Ory Kratos"""
    __tablename__ = 'users'
    
    # Primary key - internal ID
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Kratos integration
    kratos_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
    # Basic user information
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=True)
    
    # Profile information
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    display_name = db.Column(db.String(200), nullable=True)
    organization = db.Column(db.String(200), nullable=True)
    
    # Role and permissions
    role = db.Column(db.Enum(UserRole, name='user_role', values_callable=lambda obj: [e.value for e in obj]), default=UserRole.USER, nullable=False)
    status = db.Column(db.Enum(UserStatus, name='user_status', values_callable=lambda obj: [e.value for e in obj]), default=UserStatus.ACTIVE, nullable=False)
    
    # Admin flags
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Security flags
    requires_password_change = db.Column(db.Boolean, default=False, nullable=False)
    is_first_user = db.Column(db.Boolean, default=False, nullable=False)
    
    # Emergency recovery
    emergency_recovery_codes = db.Column(db.JSON, nullable=True)  # Encrypted recovery codes
    recovery_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    
    # Additional metadata
    user_metadata = db.Column(db.JSON, nullable=True)
    
    # Relationships
    sessions = db.relationship('UserSession', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'kratos_id': self.kratos_id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'display_name': self.display_name,
            'organization': self.organization,
            'role': self.role.value if self.role else None,
            'status': self.status.value if self.status else None,
            'is_admin': self.is_admin,
            'is_super_admin': self.is_super_admin,
            'requires_password_change': self.requires_password_change,
            'is_first_user': self.is_first_user,
            'recovery_email_verified': self.recovery_email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None,
        }
    
    @hybrid_property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.username or self.email
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role"""
        if self.role == UserRole.SUPER_ADMIN:
            return True  # Super admin has all roles
        if role == UserRole.ADMIN and self.is_admin:
            return True
        return self.role == role
    
    def update_from_kratos(self, kratos_traits: dict):
        """Update user from Kratos traits"""
        self.email = kratos_traits.get('email', self.email)
        self.first_name = kratos_traits.get('name', {}).get('first', self.first_name)
        self.last_name = kratos_traits.get('name', {}).get('last', self.last_name)
        self.username = kratos_traits.get('username', self.username)
        self.updated_at = datetime.utcnow()
    
    def promote_to_admin(self):
        """Promote user to admin role"""
        self.is_admin = True
        self.role = UserRole.ADMIN
        self.updated_at = datetime.utcnow()
    
    def promote_to_super_admin(self):
        """Promote user to super admin role"""
        self.is_super_admin = True
        self.is_admin = True  # Super admin is also admin
        self.role = UserRole.SUPER_ADMIN
        self.updated_at = datetime.utcnow()
    
    def demote_from_admin(self):
        """Remove admin privileges"""
        self.is_admin = False
        self.is_super_admin = False
        self.role = UserRole.USER
        self.updated_at = datetime.utcnow()
    
    def check_and_promote_first_user(self):
        """Check if this should be the first super admin user"""
        from app.database import db
        
        # Check if any super admin exists
        existing_super_admin = User.query.filter_by(is_super_admin=True).first()
        
        if not existing_super_admin:
            # Check if this is truly the first user or a migration scenario
            total_users = User.query.count()
            
            if total_users == 1:
                # Truly first user - fresh install
                self._setup_as_first_super_admin("FRESH_INSTALL")
                return True
            else:
                # Migration scenario - existing users but no super admin
                oldest_user = User.query.order_by(User.created_at.asc()).first()
                
                if oldest_user.id == self.id:
                    # This is the oldest user - promote them
                    self._setup_as_first_super_admin("MIGRATION_OLDEST_USER")
                    return True
                else:
                    # Not the oldest user - check if they should be admin based on other criteria
                    return self._handle_migration_promotion()
        return False
    
    def _setup_as_first_super_admin(self, scenario_type):
        """Set up user as first super admin"""
        from app.database import db
        
        self.promote_to_super_admin()
        self.is_first_user = True
        self.requires_password_change = True  # Always force password change
        self.generate_emergency_recovery_codes()
        
        # Set system setting to track first admin creation
        SystemSetting.set(
            'first_super_admin_created',
            True,
            f'First super admin created - scenario: {scenario_type}',
            f'auto_promotion_{datetime.utcnow().isoformat()}'
        )
        
        # Log the scenario for audit purposes
        SystemSetting.set(
            'super_admin_creation_scenario',
            scenario_type,
            f'How the first super admin was determined: {scenario_type}',
            f'scenario_{datetime.utcnow().isoformat()}'
        )
        
        db.session.commit()
    
    def _handle_migration_promotion(self):
        """Handle super admin promotion in migration scenarios"""
        from app.database import db
        
        # Check if system is configured to allow multiple super admin candidates
        migration_mode = SystemSetting.get('migration_super_admin_mode', False)
        
        if migration_mode:
            # In migration mode, any admin can become super admin
            if self.is_admin:
                self._setup_as_first_super_admin("MIGRATION_EXISTING_ADMIN")
                return True
            
            # Check if user has certain email patterns that suggest admin role
            admin_email_patterns = ['admin@', 'administrator@', 'root@', 'superuser@']
            for pattern in admin_email_patterns:
                if self.email.lower().startswith(pattern):
                    self._setup_as_first_super_admin("MIGRATION_ADMIN_EMAIL_PATTERN")
                    return True
        
        # If no migration promotion criteria met, require manual intervention
        self._log_migration_candidate()
        return False
    
    def _log_migration_candidate(self):
        """Log this user as a potential super admin candidate"""
        from app.database import db
        
        # Store potential candidates for manual review
        existing_candidates = SystemSetting.get('super_admin_candidates', [])
        
        candidate_info = {
            'user_id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_admin': self.is_admin,
            'candidate_timestamp': datetime.utcnow().isoformat()
        }
        
        if candidate_info not in existing_candidates:
            existing_candidates.append(candidate_info)
            
            SystemSetting.set(
                'super_admin_candidates',
                existing_candidates,
                'Users who could potentially be promoted to super admin',
                f'candidate_logged_{datetime.utcnow().isoformat()}'
            )
    
    def generate_emergency_recovery_codes(self):
        """Generate emergency recovery codes for account recovery"""
        import secrets
        import hashlib
        
        # Generate 8 recovery codes
        codes = []
        for _ in range(8):
            code = '-'.join([
                secrets.token_hex(3).upper(),
                secrets.token_hex(3).upper(),
                secrets.token_hex(3).upper()
            ])
            codes.append(code)
        
        # Hash the codes for storage (like passwords)
        hashed_codes = []
        for code in codes:
            hash_obj = hashlib.sha256(code.encode()).hexdigest()
            hashed_codes.append({
                'hash': hash_obj,
                'used': False,
                'created_at': datetime.utcnow().isoformat()
            })
        
        self.emergency_recovery_codes = {
            'codes': hashed_codes,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return codes  # Return plain codes for user to save
    
    def verify_recovery_code(self, provided_code):
        """Verify an emergency recovery code"""
        import hashlib
        
        if not self.emergency_recovery_codes:
            return False
        
        provided_hash = hashlib.sha256(provided_code.encode()).hexdigest()
        
        for code_data in self.emergency_recovery_codes.get('codes', []):
            if code_data['hash'] == provided_hash and not code_data['used']:
                # Mark as used
                code_data['used'] = True
                code_data['used_at'] = datetime.utcnow().isoformat()
                self.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def force_password_change(self):
        """Mark user as requiring password change"""
        self.requires_password_change = True
        self.updated_at = datetime.utcnow()
    
    def complete_password_change(self):
        """Mark password change as completed"""
        self.requires_password_change = False
        self.password_changed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    @property
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.is_admin or self.is_super_admin
    
    @property
    def can_manage_llm(self):
        """Check if user can manage LLM settings - only super admins"""
        return self.is_super_admin
    
    @property
    def effective_role(self):
        """Get the effective role string for frontend"""
        if self.is_super_admin:
            return 'super_admin'
        elif self.is_admin:
            return 'admin'
        else:
            return 'user'


class UserSession(db.Model):
    """User session tracking"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Session information
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='sessions')
    
    def __repr__(self):
        return f'<UserSession {self.session_id}>'
    
    def is_expired(self):
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()


class SystemSetting(db.Model):
    """System-wide settings"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.JSON, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<SystemSetting {self.key}>'
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set(cls, key: str, value, description: str = None, updated_by: str = None):
        """Set or update a setting"""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key)
            db.session.add(setting)
        
        setting.value = value
        if description:
            setting.description = description
        if updated_by:
            setting.updated_by = updated_by
        setting.updated_at = datetime.utcnow()
        
        db.session.commit()
        return setting


# Event listeners
@event.listens_for(User, 'before_update')
def user_before_update(mapper, connection, target):
    """Update timestamp before user update"""
    target.updated_at = datetime.utcnow()