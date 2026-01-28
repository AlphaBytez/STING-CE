"""
User Settings Model
Stores additional user settings that don't belong in Kratos identity traits
"""

from app import db
from datetime import datetime
import json

class UserSettings(db.Model):
    """User settings stored in Flask database"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False)  # Kratos identity ID
    email = db.Column(db.String(255), nullable=False)
    
    # Password management
    force_password_change = db.Column(db.Boolean, default=False)
    password_changed_at = db.Column(db.DateTime, nullable=True)
    
    # Role management
    role = db.Column(db.String(50), default='user')
    
    # UI Preferences (Database-backed settings)
    navigation_config = db.Column(db.JSON, nullable=True)  # Navigation configuration
    navigation_version = db.Column(db.Integer, default=4)  # Version for automatic updates
    theme_preferences = db.Column(db.JSON, nullable=True)  # Theme settings
    ui_preferences = db.Column(db.JSON, nullable=True)     # General UI preferences
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserSettings {self.email}>'
    
    @classmethod
    def get_or_create(cls, user_id, email, role='user'):
        """Get or create user settings"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = cls(
                user_id=user_id,
                email=email,
                role=role
            )
            db.session.add(settings)
            db.session.commit()
        return settings
    
    @classmethod
    def mark_password_changed(cls, user_id):
        """Mark that user has changed their password"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            settings.force_password_change = False
            settings.password_changed_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    
    @classmethod
    def set_force_password_change(cls, user_id, force=True):
        """Set or clear force password change flag"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            settings.force_password_change = force
            db.session.commit()
            return True
        return False
    
    # Preference Management Methods
    
    @classmethod
    def get_navigation_config(cls, user_id):
        """Get user's navigation configuration"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings and settings.navigation_config:
            return settings.navigation_config
        return None
    
    @classmethod
    def update_navigation_config(cls, user_id, config, version=None):
        """Update user's navigation configuration"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            settings.navigation_config = config
            if version:
                settings.navigation_version = version
            db.session.commit()
            return True
        return False
    
    @classmethod
    def get_theme_preferences(cls, user_id):
        """Get user's theme preferences"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings and settings.theme_preferences:
            return settings.theme_preferences
        return None
    
    @classmethod
    def update_theme_preferences(cls, user_id, preferences):
        """Update user's theme preferences"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            settings.theme_preferences = preferences
            db.session.commit()
            return True
        return False
    
    @classmethod
    def get_ui_preferences(cls, user_id):
        """Get user's general UI preferences"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings and settings.ui_preferences:
            return settings.ui_preferences
        return None
    
    @classmethod
    def update_ui_preferences(cls, user_id, preferences):
        """Update user's general UI preferences"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            settings.ui_preferences = preferences
            db.session.commit()
            return True
        return False
    
    @classmethod
    def get_all_preferences(cls, user_id):
        """Get all user preferences in one call"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            return {
                'navigation': settings.navigation_config,
                'navigation_version': settings.navigation_version,
                'theme': settings.theme_preferences,
                'ui': settings.ui_preferences
            }
        return None
    
    @classmethod
    def update_all_preferences(cls, user_id, navigation=None, theme=None, ui=None, nav_version=None):
        """Update all user preferences in one transaction"""
        settings = cls.query.filter_by(user_id=user_id).first()
        if settings:
            if navigation is not None:
                settings.navigation_config = navigation
            if nav_version is not None:
                settings.navigation_version = nav_version
            if theme is not None:
                settings.theme_preferences = theme
            if ui is not None:
                settings.ui_preferences = ui
            db.session.commit()
            return True
        return False
    
    def to_dict(self):
        """Convert settings to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email,
            'role': self.role,
            'force_password_change': self.force_password_change,
            'preferences': {
                'navigation': self.navigation_config,
                'navigation_version': self.navigation_version,
                'theme': self.theme_preferences,
                'ui': self.ui_preferences
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }