# app/middleware/config_verification.py
from flask import Flask, current_app, jsonify
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import os
from .json_handlers import sanitize_config_for_debug, init_json_provider


logger = logging.getLogger(__name__)

@dataclass
class ConfigVerificationError:
    """Data class to store configuration validation errors"""
    component: str
    setting: str
    expected: Any
    actual: Any
    severity: str  # 'critical' or 'warning'

class ConfigurationVerifier:
    """Verifies configuration consistency while respecting the environment"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.errors: List[ConfigVerificationError] = []
        self.env = app.config.get('APP_ENV', os.getenv('APP_ENV', 'development'))

    def verify_all(self) -> List[ConfigVerificationError]:
        """Run all configuration verifications with environment awareness"""
        self.errors = []
        
        # Base verification methods
        self._verify_cookie_settings()
        self._verify_domain_settings()
        self._verify_security_settings()
        self._verify_webauthn_settings()
        
        return self.errors

    def _verify_cookie_settings(self):
        """Verify cookie settings based on environment"""
        cookie_settings = self.app.config.get('COOKIE_SETTINGS', {})
        base_config = {
            'httponly': True,  # Always true in all environments
        }
        
        # Environment-specific settings
        env_settings = {
            'development': {
                'secure': True,
                'samesite': 'Lax',
                'domain': 'localhost'
            },
            'production': {
                'secure': True,
                'samesite': 'Strict',
                'domain': self.app.config.get('DOMAIN_NAME', 'localhost')
            }
        }
        
        expected_settings = {**base_config, **env_settings.get(self.env, env_settings['development'])}
        
        # Verify settings with appropriate severity
        for setting, expected in expected_settings.items():
            actual = cookie_settings.get(setting)
            # Strip quotes from string values for comparison
            if isinstance(actual, str):
                actual = actual.strip('"\'')
            if actual != expected:
                severity = 'warning' if self.env == 'development' else 'critical'
                self.errors.append(ConfigVerificationError(
                    'Cookie',
                    setting,
                    expected,
                    actual,
                    severity
                ))

    def _verify_domain_settings(self):
        """Verify domain configuration consistency"""
        webauthn_settings = self.app.config.get('WEBAUTHN_SETTINGS', {})
        domain = self.app.config.get('DOMAIN_NAME', 'localhost')
        rp_id = webauthn_settings.get('rp_id')
        
        # Domain verification with environment awareness
        if self.env == 'production':
            if domain == 'localhost':
                self.errors.append(ConfigVerificationError(
                    'Domain',
                    'domain_name',
                    'production domain',
                    domain,
                    'critical'
                ))
        else:
            # In development, localhost is acceptable
            if domain != 'localhost':
                self.errors.append(ConfigVerificationError(
                    'Domain',
                    'domain_name',
                    'localhost',
                    domain,
                    'warning'
                ))

    def _verify_security_settings(self):
        """Verify security settings based on environment"""
        cookie_settings = self.app.config.get('COOKIE_SETTINGS', {})
        
        # Define environment-specific security requirements
        security_requirements = {
            'development': {
                'secure': True,
                'samesite': 'Lax',
                'httponly': True
            },
            'production': {
                'secure': True,
                'samesite': 'Strict',
                'httponly': True
            }
        }
        
        current_requirements = security_requirements.get(self.env, security_requirements['development'])
        
        for setting, expected in current_requirements.items():
            actual = cookie_settings.get(setting)
            if actual != expected:
                severity = 'warning' if self.env == 'development' else 'critical'
                self.errors.append(ConfigVerificationError(
                    'Security',
                    setting,
                    expected,
                    actual,
                    severity
                ))
    def _verify_webauthn_settings(self):
        """Verify WebAuthn-specific configuration"""
        webauthn_settings = self.app.config.get('WEBAUTHN_SETTINGS', {})
        
        # Verify required WebAuthn settings are present
        required_settings = ['rp_id', 'rp_name', 'origins']
        for setting in required_settings:
            if setting not in webauthn_settings:
                self.errors.append(ConfigVerificationError(
                    'WebAuthn',
                    setting,
                    'required setting',
                    'missing',
                    'warning' if self.env == 'development' else 'critical'
                ))

        # Verify origins include both API and frontend domains
        origins = webauthn_settings.get('origins', [])
        if not origins:
            self.errors.append(ConfigVerificationError(
                'WebAuthn',
                'origins',
                'at least one origin',
                'empty list',
                'warning' if self.env == 'development' else 'critical'
            ))

def verify_config(app: Flask) -> None:
        """Middleware function to verify configuration"""
        verifier = ConfigurationVerifier(app)
        errors = verifier.verify_all()
        
        # Log all errors
        for error in errors:
            log_message = (
                f"Configuration error in {error.component} - {error.setting}: "
                f"expected {error.expected}, got {error.actual}"
            )
            if error.severity == 'critical':
                logger.error(log_message)
            else:
                logger.warning(log_message)
        
        # In production, raise exception for critical errors
        if app.config.get('ENV') == 'production':
            critical_errors = [e for e in errors if e.severity == 'critical']
            if critical_errors:
                error_messages = "\n".join([
                    f"- {e.component}.{e.setting}: expected {e.expected}, got {e.actual}"
                    for e in critical_errors
                ])
                raise ValueError(f"Critical configuration errors found:\n{error_messages}")
        else:
            # In development, just log warnings
            if errors:
                logger.warning("Development mode: Configuration warnings found")




def create_debug_routes(app: Flask):
    """Create debug routes for development environment"""
    # Import the debug blueprint
    from app.routes.debug_routes import debug_blueprint

    # Register the debug blueprint
    app.register_blueprint(debug_blueprint)

    @app.route('/debug/configuration')
    def debug_configuration():
        """Route to display current configuration"""
        # Check environment directly from config
        if app.config.get('ENV', 'development').lower() == 'development':
            config_data = {
                'environment': app.config.get('APP_ENV'),
                'cookie_settings': app.config.get('COOKIE_SETTINGS'),
                'domain_settings': {
                    'domain': app.config.get('DOMAIN_NAME'),
                    'webauthn_rp_id': app.config.get('WEBAUTHN_RP_ID')
                },
                'cors_settings': {
                    'origins': app.config.get('CORS_ALLOWED_ORIGINS'),
                    'headers': app.config.get('CORS_ALLOWED_HEADERS'),
                    'methods': app.config.get('CORS_ALLOWED_METHODS')
                }
            }
            safe_config = sanitize_config_for_debug(config_data)
            return jsonify(safe_config)

        return jsonify({
            'error': 'Debug endpoints only available in development environment'
        }), 403

def init_debug_routes(app: Flask):
    """Initialize debug routes and configure JSON handling"""
    
    # Initialize custom JSON provider
    init_json_provider(app)
    
    # Only create debug routes in development
    if app.config.get('APP_ENV') == 'development':
        create_debug_routes(app)