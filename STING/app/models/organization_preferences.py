"""
Organization Preferences Model
Stores organization-wide default preferences that can be pushed to users
"""

from app import db
from datetime import datetime


class OrganizationPreferences(db.Model):
    """Organization-wide preference defaults"""
    __tablename__ = 'organization_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    preference_type = db.Column(db.String(50), nullable=False, unique=True)  # 'navigation', 'theme', 'ui'
    config = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, default=4, nullable=False)
    created_by = db.Column(db.String(255), nullable=False)  # user_id who created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f'<OrganizationPreferences {self.preference_type}>'
    
    @classmethod
    def get_by_type(cls, preference_type):
        """Get active organization preference by type"""
        return cls.query.filter_by(preference_type=preference_type, is_active=True).first()
    
    @classmethod
    def get_navigation_default(cls):
        """Get default navigation configuration"""
        pref = cls.get_by_type('navigation')
        return pref.config if pref else None
    
    @classmethod
    def get_theme_default(cls):
        """Get default theme configuration"""
        pref = cls.get_by_type('theme')
        return pref.config if pref else None
    
    @classmethod
    def get_ui_default(cls):
        """Get default UI configuration"""
        pref = cls.get_by_type('ui')
        return pref.config if pref else None
    
    @classmethod
    def update_preference(cls, preference_type, config, version, created_by):
        """Update or create organization preference"""
        pref = cls.query.filter_by(preference_type=preference_type).first()
        if pref:
            pref.config = config
            pref.version = version
            pref.created_by = created_by
            pref.updated_at = datetime.utcnow()
        else:
            pref = cls(
                preference_type=preference_type,
                config=config,
                version=version,
                created_by=created_by
            )
            db.session.add(pref)
        
        db.session.commit()
        return pref
    
    @classmethod
    def get_all_active(cls):
        """Get all active organization preferences"""
        return cls.query.filter_by(is_active=True).all()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'preference_type': self.preference_type,
            'config': self.config,
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }


class UserPreferenceHistory(db.Model):
    """Audit trail for user preference changes"""
    __tablename__ = 'user_preference_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    preference_type = db.Column(db.String(50), nullable=False)  # 'navigation', 'theme', 'ui'
    old_config = db.Column(db.JSON, nullable=True)
    new_config = db.Column(db.JSON, nullable=True)
    old_version = db.Column(db.Integer, nullable=True)
    new_version = db.Column(db.Integer, nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changed_by = db.Column(db.String(255), nullable=True)  # for admin-initiated changes
    change_reason = db.Column(db.String(255), nullable=True)  # 'user_update', 'admin_push', 'migration', etc.
    
    def __repr__(self):
        return f'<UserPreferenceHistory {self.user_id} {self.preference_type}>'
    
    @classmethod
    def log_change(cls, user_id, preference_type, old_config=None, new_config=None, 
                   old_version=None, new_version=None, changed_by=None, reason=None):
        """Log a preference change"""
        history = cls(
            user_id=user_id,
            preference_type=preference_type,
            old_config=old_config,
            new_config=new_config,
            old_version=old_version,
            new_version=new_version,
            changed_by=changed_by,
            change_reason=reason
        )
        db.session.add(history)
        db.session.commit()
        return history
    
    @classmethod
    def get_user_history(cls, user_id, limit=10):
        """Get user's preference change history"""
        return cls.query.filter_by(user_id=user_id)\
                       .order_by(cls.changed_at.desc())\
                       .limit(limit).all()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_type': self.preference_type,
            'old_config': self.old_config,
            'new_config': self.new_config,
            'old_version': self.old_version,
            'new_version': self.new_version,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'changed_by': self.changed_by,
            'change_reason': self.change_reason
        }