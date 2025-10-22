"""
Config routes for frontend configuration including theme settings, SMTP, and auth modes
"""
from flask import Blueprint, jsonify, request
from flask_cors import CORS
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api/config')
CORS(config_bp, supports_credentials=True)

@config_bp.route('/theme', methods=['GET'])
def get_theme_config():
    """Get theme configuration from config.yml"""
    try:
        # Try to get config from app config first
        from flask import current_app
        
        # Get theme settings from config
        config = current_app.config.get('CONFIG', {})
        frontend_config = config.get('frontend', {})
        theme_config = frontend_config.get('theme', {})
        
        # Default theme settings if not configured
        default_theme_config = {
            'default': 'modern-lite',
            'user_selectable': True,
            'force_default': False
        }
        
        # Merge with defaults
        theme_settings = {**default_theme_config, **theme_config}
        
        return jsonify({
            'success': True,
            'theme': theme_settings
        })
        
    except Exception as e:
        logger.error(f"Error getting theme config: {str(e)}")
        # Return defaults on error
        return jsonify({
            'success': True,
            'theme': {
                'default': 'modern-lite',
                'user_selectable': True,
                'force_default': False
            }
        })

@config_bp.route('/frontend', methods=['GET'])
def get_frontend_config():
    """Get all frontend configuration"""
    try:
        from flask import current_app
        
        config = current_app.config.get('CONFIG', {})
        frontend_config = config.get('frontend', {})
        
        # Remove sensitive information
        safe_config = {
            'theme': frontend_config.get('theme', {
                'default': 'modern-lite',
                'user_selectable': True,
                'force_default': False
            }),
            'development': frontend_config.get('development', {
                'hot_reload': False,
                'debug_tools': False
            })
        }
        
        return jsonify({
            'success': True,
            'config': safe_config
        })
        
    except Exception as e:
        logger.error(f"Error getting frontend config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load frontend configuration'
        }), 500

@config_bp.route('/smtp/status', methods=['GET'])
def get_smtp_status():
    """Check current SMTP configuration status."""
    try:
        # Check if we're in development or production mode
        email_mode = os.getenv('EMAIL_MODE', 'development')
        
        if email_mode == 'development':
            # Check if Mailpit is accessible
            import requests
            try:
                response = requests.get('http://mailpit:8025/api/v1/messages', timeout=2)
                mailpit_accessible = response.status_code == 200
                # Get message count
                message_count = len(response.json().get('messages', [])) if mailpit_accessible else 0
            except:
                mailpit_accessible = False
                message_count = 0
            
            return jsonify({
                'mode': 'development',
                'provider': 'mailpit',
                'configured': True,
                'accessible': mailpit_accessible,
                'mailpit_url': 'http://localhost:8026',
                'message_count': message_count,
                'message': 'Using Mailpit for email capture (development mode)'
            })
        else:
            # Check production SMTP settings
            smtp_host = os.getenv('SMTP_HOST')
            smtp_configured = bool(smtp_host)
            
            return jsonify({
                'mode': 'production',
                'provider': os.getenv('EMAIL_PROVIDER', 'smtp'),
                'configured': smtp_configured,
                'host': smtp_host if smtp_configured else None,
                'message': 'Production SMTP configured' if smtp_configured else 'No SMTP configuration found'
            })
            
    except Exception as e:
        logger.error(f"Failed to get SMTP status: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@config_bp.route('/auth/mode', methods=['GET'])
def get_auth_mode():
    """Get current authentication mode and available options."""
    try:
        # Determine auth capabilities
        email_mode = os.getenv('EMAIL_MODE', 'development')
        smtp_configured = bool(os.getenv('SMTP_HOST')) if email_mode == 'production' else True
        
        # For now, return hybrid mode as we support both
        return jsonify({
            'mode': 'hybrid',
            'methods': {
                'password': True,  # Always available
                'code': True,      # Available if email works
                'link': True,      # Available if email works
                'webauthn': True   # WebAuthn is configured
            },
            'email_required_for': ['code', 'link'],
            'email_configured': smtp_configured,
            'email_mode': email_mode,
            'mailpit_url': 'http://localhost:8026' if email_mode == 'development' else None,
            'recommendations': get_auth_recommendations('hybrid', smtp_configured, email_mode)
        })
        
    except Exception as e:
        logger.error(f"Failed to get auth mode: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

def get_auth_recommendations(auth_mode, smtp_configured, email_mode):
    """Get recommendations based on current setup."""
    recommendations = []
    
    if email_mode == 'development':
        recommendations.append({
            'level': 'info',
            'message': 'Development mode: Check Mailpit at http://localhost:8025 for all emails',
            'action': {
                'label': 'Open Mailpit',
                'url': 'http://localhost:8026'
            }
        })
    elif not smtp_configured:
        recommendations.append({
            'level': 'warning',
            'message': 'No SMTP configured. Passwordless login requires email setup.',
            'action': {
                'label': 'Configure SMTP',
                'url': '/settings/smtp'
            }
        })
    
    if auth_mode == 'hybrid':
        recommendations.append({
            'level': 'success',
            'message': 'Hybrid authentication active: Users can use passwords or email codes'
        })
    
    return recommendations

@config_bp.route('/registration', methods=['GET'])
def get_registration_config():
    """Get registration configuration"""
    try:
        # For now, always allow registration
        # In production, this could be controlled by environment variables or config
        registration_enabled = os.getenv('REGISTRATION_ENABLED', 'true').lower() == 'true'
        
        return jsonify({
            'success': True,
            'enabled': registration_enabled,
            'self_registration': True,
            'admin_approval_required': False,
            'email_verification_required': True
        })
        
    except Exception as e:
        logger.error(f"Error getting registration config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get registration configuration',
            'enabled': True  # Default to enabled on error
        }), 500