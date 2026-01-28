# app/config/config.py
import os
from datetime import timedelta
from typing import Dict, Any

class BaseConfig:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY') or os.urandom(32)
    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = True
    
    # SQLAlchemy configurations (preserved from original)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Security settings (preserved from original)
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT') or os.urandom(32)
    SECURITY_TRACKABLE = True
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_CONFIRMABLE = False
    SECURITY_PASSWORD_HASH = 'bcrypt'
    
    # Unified Session/Cookie Configuration
    # This is the single source of truth for cookie settings
    # Use WEBAUTHN_RP_ID as the cookie domain for consistency
    COOKIE_SETTINGS = {
        'domain': os.getenv('COOKIE_DOMAIN', os.getenv('WEBAUTHN_RP_ID', 'localhost')),
        'secure': True,  # Default to secure
        'httponly': True,
        'samesite': 'Lax',  # Default to Lax
        'lifetime': timedelta(minutes=30)
    }
    
    # Flask Session Settings (derived from COOKIE_SETTINGS)
    SESSION_COOKIE_NAME = 'sting_session'
    SESSION_COOKIE_DOMAIN = COOKIE_SETTINGS['domain']
    SESSION_COOKIE_HTTPONLY = COOKIE_SETTINGS['httponly']
    SESSION_COOKIE_SECURE = COOKIE_SETTINGS['secure']
    SESSION_COOKIE_SAMESITE = COOKIE_SETTINGS['samesite']
    PERMANENT_SESSION_LIFETIME = COOKIE_SETTINGS['lifetime']
    
    # Kratos Configuration
    KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
    KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
    KRATOS_VERIFY_SSL = os.getenv('KRATOS_VERIFY_SSL', 'false').lower() == 'true'
    
    # WebAuthn Configuration
    WEBAUTHN_SETTINGS = {
        'rp_id': os.getenv('WEBAUTHN_RP_ID', 'localhost'),
        'rp_name': os.getenv('WEBAUTHN_RP_NAME', 'STING App'),
        'origins': [
            f"https://{os.getenv('APP_HOST', 'localhost')}:8443",
            f"https://{os.getenv('APP_HOST', 'localhost')}:5050",
        ]
    }
    
    # SuperTokens deprecated - using Kratos for authentication
    
    # Logging
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    DEVELOPMENT = True
    
    # Override cookie settings for development
    COOKIE_SETTINGS = {
        **BaseConfig.COOKIE_SETTINGS,
        'secure': True,  # HTTPS required
        'samesite': 'Lax'  # Match Kratos configuration
    }
    
    # Update session settings based on COOKIE_SETTINGS
    SESSION_COOKIE_SECURE = COOKIE_SETTINGS['secure']
    SESSION_COOKIE_SAMESITE = COOKIE_SETTINGS['samesite']
    
    # SuperTokens deprecated - using Kratos for authentication
    
    LOG_LEVEL = 'DEBUG'
    
    # Override SQLAlchemy options for development (SQLite doesn't support pool options)
    SQLALCHEMY_ENGINE_OPTIONS = {}

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Production cookie settings are inherited from BaseConfig
    # This ensures secure settings in production
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        **BaseConfig.SQLALCHEMY_ENGINE_OPTIONS,
        'pool_size': 20,
        'max_overflow': 5
    }

class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Override cookie settings for testing
    COOKIE_SETTINGS = {
        **BaseConfig.COOKIE_SETTINGS,
        'secure': False,
        'samesite': 'Lax'
    }

def get_config() -> Dict[str, Any]:
    """Get merged configuration dictionary based on environment."""
    config_class = config_dict.get(os.getenv('APP_ENV', 'development').lower(), DevelopmentConfig)
    config_obj = config_class()
    
    # Ensure all cookie-related settings are consistent
    cookie_settings = config_obj.COOKIE_SETTINGS
    config_dict = {
        'SESSION_COOKIE_SECURE': cookie_settings['secure'],
        'SESSION_COOKIE_SAMESITE': cookie_settings['samesite'],
        'SESSION_COOKIE_HTTPONLY': cookie_settings['httponly'],
        'SESSION_COOKIE_DOMAIN': cookie_settings['domain']
        }
    
    return config_dict

# Configuration dictionary
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Get configuration instance
config = config_dict.get(os.getenv('APP_ENV', 'development').lower())