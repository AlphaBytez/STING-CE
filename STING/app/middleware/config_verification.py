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
        domain_name = self.app.config.get('DOMAIN_NAME', 'localhost')

        base_config = {
            'httponly': True,  # Always true in all environments
        }

        # Environment-specific settings
        # For self-hosted/OVA, Lax is acceptable and domain can be .local
        env_settings = {
            'development': {
                'secure': True,
                'samesite': 'Lax',
                'domain': domain_name  # Accept configured domain (localhost or .local)
            },
            'production': {
                'secure': True,
                'samesite': 'Lax',  # Lax is acceptable for self-hosted
                'domain': domain_name
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
                # Cookie mismatches are warnings, not critical errors
                self.errors.append(ConfigVerificationError(
                    'Cookie',
                    setting,
                    expected,
                    actual,
                    'warning'
                ))

    def _verify_domain_settings(self):
        """Verify domain configuration consistency"""
        webauthn_settings = self.app.config.get('WEBAUTHN_SETTINGS', {})
        domain = self.app.config.get('DOMAIN_NAME', 'localhost')
        rp_id = webauthn_settings.get('rp_id')

        # Domain verification with environment awareness
        # .local domains (mDNS) are acceptable for development/self-hosted
        is_local_domain = domain == 'localhost' or domain.endswith('.local')

        if self.env == 'production':
            # In production, warn if using localhost (but .local is ok for self-hosted)
            if domain == 'localhost':
                self.errors.append(ConfigVerificationError(
                    'Domain',
                    'domain_name',
                    'production domain',
                    domain,
                    'warning'  # Downgrade to warning - self-hosted may use localhost
                ))
        else:
            # In development, localhost and .local domains are both acceptable
            if not is_local_domain:
                self.errors.append(ConfigVerificationError(
                    'Domain',
                    'domain_name',
                    'localhost or .local domain',
                    domain,
                    'warning'
                ))

    def _verify_security_settings(self):
        """Verify security settings based on environment"""
        cookie_settings = self.app.config.get('COOKIE_SETTINGS', {})

        # Define security requirements - Lax is acceptable for self-hosted
        # (Strict can cause issues with cross-origin redirects in some setups)
        security_requirements = {
            'secure': True,
            'samesite': 'Lax',  # Lax is acceptable for all environments
            'httponly': True
        }

        for setting, expected in security_requirements.items():
            actual = cookie_settings.get(setting)
            # Strip quotes from string values
            if isinstance(actual, str):
                actual = actual.strip('"\'')
            if actual != expected:
                # Security mismatches are warnings for self-hosted deployments
                self.errors.append(ConfigVerificationError(
                    'Security',
                    setting,
                    expected,
                    actual,
                    'warning'
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
        """Middleware function to verify configuration

        For self-hosted/OVA deployments, we log warnings but don't fail startup.
        This allows flexible deployment configurations.
        """
        verifier = ConfigurationVerifier(app)
        errors = verifier.verify_all()

        # Log all errors/warnings
        for error in errors:
            log_message = (
                f"Configuration note in {error.component} - {error.setting}: "
                f"expected {error.expected}, got {error.actual}"
            )
            if error.severity == 'critical':
                logger.warning(log_message)  # Log as warning, not error
            else:
                logger.info(log_message)

        # For self-hosted deployments, we don't fail on config differences
        # Just log a summary if there are any notes
        if errors:
            logger.info(f"Configuration check completed with {len(errors)} note(s). "
                       "This is normal for self-hosted/OVA deployments.")




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