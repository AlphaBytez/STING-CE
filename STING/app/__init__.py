# Standard library imports
import datetime
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess

# Third-party imports
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_session import Session
import redis
try:
    from OpenSSL import SSL
    import certbot.main
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False
    SSL = None
# SuperTokens imports removed - using Kratos
import requests
# Ory Kratos Admin API URL
KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'http://kratos:4434')
import os
from flask import request, g, abort
from functools import wraps
# SuperTokens WebAuthn imports removed - using Kratos
from .middleware import verify_config, init_debug_routes
from .middleware.json_handlers import ConfigJSONProvider

# Local application imports
from app.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    config_dict
)

# from app.routes.auth import auth_blueprint  # SuperTokens auth deprecated
from app.routes.llm_routes import llm_bp
from app.routes.user_routes import user_bp
# from app.routes.webauthn_routes import webauthn_bp  # ARCHIVED - using Kratos WebAuthn
# from app.routes.auth_routes import auth_bp  # Legacy - REMOVED: replaced by modular auth routes
from app.routes.auth.kratos_session_routes import kratos_session_bp
from app.routes.auth.password_routes import password_bp as auth_password_bp
from app.routes.auth.aal_routes import aal_bp as auth_aal_bp
from app.routes.auth.debug_routes import debug_bp as auth_debug_bp
from app.routes.auth.misc_routes import misc_bp as auth_misc_bp
from app.routes.admin_recovery_routes import admin_recovery_bp
from app.routes.admin_setup_routes import admin_setup_bp
from app.routes.admin_registration_routes import admin_registration_bp
from app.routes.admin_routes import admin_bp
from app.routes.pii_routes import pii_bp
from app.routes.config_routes import config_bp
from app.routes.aal_routes import aal_bp as original_aal_bp
from app.routes.enhanced_webauthn_routes import enhanced_webauthn_bp
from app.routes.nectar_bot_routes import nectar_bot_bp
from app.routes.kratos_webhooks import kratos_webhooks_bp
# from app.routes.file_routes import file_bp  # Import moved to create_app to avoid early initialization
from app.database import init_db, db
from sqlalchemy import text
from app.middleware.config_verification import verify_config, create_debug_routes


# SuperTokens handler functions removed - using Kratos    

def get_or_create_certificates(domain: str) -> tuple[str, str]:
    """Get or create SSL certificates."""
    # Use a local directory for certificates in development
    if os.getenv('FLASK_ENV') == 'development' or domain == 'localhost':
        cert_dir = Path.home() / '.sting' / 'certs'
    else:
        cert_dir = Path('/app/certs')
    cert_path = cert_dir / 'server.crt'
    key_path = cert_dir / 'server.key'
    
    # For development, create self-signed certificates if they don't exist
    if domain == 'localhost':
        cert_dir.mkdir(parents=True, exist_ok=True)
        if not (cert_path.exists() and key_path.exists()):
            cmd = [
                'openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-nodes',
                '-out', str(cert_path), '-keyout', str(key_path),
                '-days', '365', '-subj', f'/CN={domain}'
            ]
            subprocess.run(cmd, check=True)
    
    if not (cert_path.exists() and key_path.exists()):
        raise FileNotFoundError(f"SSL certificates not found: {cert_path}, {key_path}")
    
    return str(cert_path), str(key_path)

def create_app(config=None):
    # Configure Flask to serve React build files
    frontend_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    static_folder = os.path.join(frontend_build_path, 'static')
    
    flask_app = Flask(__name__, 
                     static_folder=static_folder,
                     static_url_path='/static')
    # Decorator to protect routes using Kratos session via Admin HTTP API
    def require_kratos_session(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
            if not cookie:
                abort(401)
            # Validate session via Kratos Admin API
            resp = requests.get(
                f"{KRATOS_ADMIN_URL}/sessions/whoami",
                cookies={'ory_kratos_session': cookie}
            )
            if resp.status_code != 200:
                abort(401)
            data = resp.json().get('session', {})
            g.identity = data.get('identity', {})
            return fn(*args, **kwargs)
        return wrapper
    flask_app.json_provider_class = ConfigJSONProvider
    
    logger = flask_app.logger
    logger.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app_env = os.getenv('APP_ENV', 'development').lower()
    config_class = config or config_dict.get(app_env, DevelopmentConfig)
    flask_app.config.from_object(config_class)
    
    # Set maximum file upload size (100MB)
    flask_app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
    
    try:
        domain = os.getenv('DOMAIN_NAME', 'localhost')
        cert_path, key_path = get_or_create_certificates(domain)
        
        if SSL_AVAILABLE and SSL:
            ssl_context = SSL.Context(SSL.TLSv1_2_METHOD)
            ssl_context.use_certificate_file(cert_path)
            ssl_context.use_privatekey_file(key_path)
        else:
            # Fallback for development without pyOpenSSL
            ssl_context = 'adhoc' if domain == 'localhost' else None
        
        database_url = os.environ.get('DATABASE_URL')
        print(f"DEBUG: DATABASE_URL = {database_url}")
        config_update = {
            'SSL_CERT_PATH': cert_path,
            'SSL_KEY_PATH': key_path,
            'SQLALCHEMY_DATABASE_URI': database_url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        }
        
        # Only set pool options for PostgreSQL databases
        if database_url and not database_url.startswith('sqlite'):
            config_update.update({
                'SQLALCHEMY_POOL_SIZE': 10,
                'SQLALCHEMY_MAX_OVERFLOW': 20,
            })
        
        # Get WebAuthn RP ID from environment
        webauthn_rp_id = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
        
        # Build origins list based on RP ID
        webauthn_origins = [
            f'https://{webauthn_rp_id}:8443',
            f'https://{webauthn_rp_id}:5050',
            f'http://{webauthn_rp_id}:8443',
            f'http://{webauthn_rp_id}:5050',
            f'https://{webauthn_rp_id}:4433'
        ]
        
        # Always include localhost for local development
        if webauthn_rp_id != 'localhost':
            webauthn_origins.extend([
                'https://localhost:8443',
                'https://localhost:5050',
                'http://localhost:8443',
                'http://localhost:5050',
                'https://localhost:4433'
            ])
        
        logger.info(f"WebAuthn RP ID: {webauthn_rp_id}")
        logger.info(f"WebAuthn Origins: {webauthn_origins}")
        
        # PURE KRATOS: Redis sessions no longer needed (stateless Flask backend)
        # import redis  
        # redis_client = redis.from_url('redis://redis:6379/0')
        
        # Get optimal cookie configuration based on environment
        from app.utils.environment import get_optimal_cookie_config, log_environment_info
        cookie_config = get_optimal_cookie_config()
        
        # Log environment information for debugging
        log_environment_info()
        
        # PURE KRATOS SESSIONS: Simplified configuration (no Redis sessions needed)
        config_update.update({
            'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', os.urandom(32)),
            'WEBAUTHN_RP_ID': webauthn_rp_id,
            'WEBAUTHN_RP_NAME': os.environ.get('WEBAUTHN_RP_NAME', 'STING App'),
            'WEBAUTHN_RP_ORIGINS': webauthn_origins,
            # Use environment-specific cookie configuration (for Kratos cookies only)
            **cookie_config
        })
        
        flask_app.config.update(config_update)
        
        # Initialize Pure Kratos Authentication Middleware for identity management
        from app.middleware.kratos_auth_middleware import KratosAuthMiddleware
        KratosAuthMiddleware(flask_app)

        # TEMPORARILY DISABLED: Session storage causing serialization errors in v1
        # Will re-enable after isolating the bytes object source
        #
        # flask_app.config.update({
        #     'SESSION_TYPE': 'null',  # Disable session storage temporarily
        # })

        # Skip Flask-Session initialization to avoid serialization conflicts

        logger.info("🔐 Kratos authentication initialized (sessions temporarily disabled)")
        
    except Exception as e:
        logger.error(f"Error during app initialization: {str(e)}")
        raise

    # Initialize Supertokens FIRST
    # init(
    #     app_info=InputAppInfo(
    #         app_name="STING",
    #         api_domain="https://localhost:5050",
    #         website_domain="https://localhost:8443",
    #         api_base_path="/api/auth",
    #         website_base_path="/auth"
    #     ),
    #         api_key=os.getenv('ST_API_KEY')
    #     ),
    #     framework='flask',
    #     recipe_list=[
    #         session.init(
    #             cookie_domain=flask_app.config['COOKIE_SETTINGS']['domain'],
    #             cookie_secure=flask_app.config['COOKIE_SETTINGS']['secure'],
    #             cookie_same_site=flask_app.config['COOKIE_SETTINGS']['samesite'].lower(),
    #             get_token_transfer_method=lambda _, __, ___: "cookie"
    #         ),
    #         passwordless.init(
    #             contact_config=ContactEmailOnlyConfig(),
    #             flow_type="USER_INPUT_CODE_AND_MAGIC_LINK",
    #             override=passwordless.InputOverrideConfig(
    #                 functions=lambda original_implementation: {
    #                     "signInUpPOST": custom_sign_in_up_handler
    #                 }
    #             )
    #         )
    #     ]
    # )
    
    # SuperTokens initialization removed - using Kratos for authentication
    
    # DISABLED: Legacy auth middleware - replaced by KratosAuthMiddleware for v1 release
    # from app.middleware.auth_middleware import load_user_from_session, check_aal2_for_api_only
    # from app.middleware.aal_middleware import get_current_aal_status

    # DISABLED: Legacy before_request middleware - replaced by KratosAuthMiddleware for v1 release
    # @flask_app.before_request
    # def before_request():
    #     """Load user from session and validate AAL requirements before each request"""
    #     try:
    #         # Handle OPTIONS requests (CORS preflight) without authentication
    #         if request.method == 'OPTIONS':
    #             logger.debug(f"Handling OPTIONS request for: {request.path}")
    #             return None
    #
    #         # Skip auth for certain paths
    #         skip_auth_paths = [
    #             '/health',
    #             '/api/files/upload-temp',  # Allow Bee chat uploads
    #             '/api/beeacon/public/',   # Allow public Beeacon monitoring endpoints
    #             '/api/dashboard/public/',  # Allow public dashboard metrics
    #             '/api/dashboard/metrics',  # Allow dashboard metrics (temporary)
    #             '/api/storage/usage',      # Allow storage usage (temporary)
    #             '/api/auth/settings',     # Allow settings flow for enrollment passkey setup
    #             '/api/auth/webauthn-totp-setup',  # Allow flexible auth for TOTP setup
    #             '/api/auth/sync-kratos-session',  # Allow flexible auth for session sync
    #             '/api/auth/security-gate',  # Allow security gate status check for dashboard guard
    #             '/api/auth/me',             # Allow session info endpoint
    #             '/api/auth/aal-status',     # Allow AAL status check during auth sync
    #             '/api/totp/verify-totp',    # Allow TOTP verification for AAL2 step-up
    #             '/api/totp/',               # Allow ALL TOTP endpoints (setup, enrollment, verification)
    #             '/api/totp-enrollment/',    # Allow TOTP enrollment (chicken-and-egg fix)
    #             '/api/webauthn/',           # Allow ALL WebAuthn endpoints (setup, enrollment, verification)
    #             '/api/webauthn-enrollment/', # Allow WebAuthn enrollment (chicken-and-egg fix)
    #             '/api/biometric/',          # Allow biometric/passkey setup endpoints
    #             # CRITICAL: Enrollment and settings setup paths must bypass AAL2
    #             '/api/settings/',           # Allow settings access for enrollment
    #             '/api/user/profile',        # Allow profile access during enrollment
    #             '/api/security-gate',       # Allow security gate status checks
    #             '/api/enhanced-webauthn/authentication/complete',  # Allow WebAuthn for AAL2 step-up
    #             '/api/webauthn/native/',  # Allow WebAuthn native endpoints during enrollment
    #             '/api/webauthn/register/',  # Allow WebAuthn standard endpoints during enrollment
    #             '/.ory/',
    #             '/static/',
    #             '/favicon.ico',
    #             '/logout'
    #         ]
    #
    #         if any(request.path.startswith(path) for path in skip_auth_paths):
    #             logger.debug(f"Skipping auth middleware for: {request.path}")
    #             return None
    #
    #         # Load user session data for all paths (including /api/auth/me)
    #         load_user_from_session()
    #
    #         # SELECTIVE AAL2: Only enforce AAL2 for sensitive operations, not basic dashboard access
    #         # This allows users to access dashboard after simple email authentication
    #
    #         # PASSKEY-FIRST SECURITY MODEL: Simple "confirm it's you" approach
    #
    #         # Paths that require reauthentication (passkey preferred, TOTP fallback, 30-min cache)
    #         reauthentication_paths = [
    #             '/api/admin',           # Admin functions - confirm identity
    #             '/api/audit',           # Audit logs - confirm identity
    #             '/api/reports/',        # All report operations - confirm identity
    #             '/api/pii',             # PII configuration - confirm identity
    #             '/api/system',          # System configuration - confirm identity
    #             '/api/config',          # Configuration changes - confirm identity
    #             '/api/backup',          # Backup operations - confirm identity
    #             '/api/chat/sensitive',  # Sensitive chat operations - confirm identity
    #             '/api/keys',            # API key management - confirm identity
    #         ]
    #
    #         # Paths that REQUIRE traditional AAL2 (TOTP only) - critical account operations
    #         critical_paths = [
    #             '/api/user/delete',     # User management - requires TOTP
    #             '/api/user/create',     # User creation - requires TOTP
    #             '/api/webauthn/passkey/remove',  # Passkey removal - requires TOTP
    #             '/api/webauthn/passkey/delete',  # Passkey deletion - requires TOTP
    #         ]
    #
    #         # PASSKEY-FIRST CHECK: Most sensitive operations use passkey/TOTP reauthentication
    #         if any(request.path.startswith(path) for path in reauthentication_paths):
    #             # Use existing AAL2 system but with extended cache (30 min) and passkey preference
    #             api_aal2_response = check_aal2_for_api_only()
    #             if api_aal2_response:
    #                 return api_aal2_response
    #
    #         # CRITICAL OPERATIONS CHECK: For account changes, still enforce strict AAL2
    #         elif any(request.path.startswith(path) for path in critical_paths):
    #             api_aal2_response = check_aal2_for_api_only()
    #             if api_aal2_response:
    #                 return api_aal2_response
    #
    #         # SELECTIVE ADMIN AAL2: Let admins complete basic dashboard access with AAL1
    #         # Only enforce AAL2 for admin-specific operations, not basic API calls
    #         admin_only_paths = [
    #             '/api/admin',           # Admin panel functions
    #             '/api/user/delete',     # User management
    #             '/api/user/create',     # User creation
    #             '/api/system',          # System configuration
    #             '/api/pii',             # PII configuration
    #             '/api/audit'            # Audit logs
    #         ]
    #
    #         try:
    #             aal_status = get_current_aal_status()
    #             if aal_status and aal_status['role'] == 'admin':
    #                 # SIMPLIFIED 2FA: Disable admin-specific AAL2 enforcement
    #                 # Trust basic authentication for clean user experience
    #                 # if any(request.path.startswith(path) for path in admin_only_paths):
    #                 #     api_aal2_response = check_aal2_for_api_only()
    #                 #     if api_aal2_response:
    #                 #         logger.info(f"Admin AAL2 required for {aal_status['email']} accessing admin function: {request.path}")
    #                 #         return api_aal2_response
    #                 pass  # Simplified: no additional checks for admins
    #         except Exception as e:
    #             logger.warning(f"Error checking admin AAL2 requirement: {e}")
    #             # Continue without blocking if there's an error
    #
    #         # Basic protected routes (no AAL2 required) - just need basic authentication
    #         # TEMPORARILY DISABLED: AAL2 enforcement causing catch-22 with settings access
    #         # protected_paths = ['/api/knowledge', '/api/honey', '/api/user', '/api/reports']
    #         #
    #         # if any(request.path.startswith(path) for path in protected_paths):
    #         if False:  # Disable AAL2 enforcement temporarily
    #             aal_status = get_current_aal_status()
    #
    #             if not aal_status:
    #                 logger.warning(f"No AAL status found for protected path: {request.path}")
    #                 # For API requests, return JSON error
    #                 if request.path.startswith('/api/'):
    #                     return jsonify({"error": "Authentication required", "code": "NO_SESSION"}), 401
    #                 # For web requests, handled by frontend routing
    #                 return None
    #
    #             validation = aal_status['validation']
    #             user_role = aal_status['role']
    #
    #             if not validation['valid']:
    #                 logger.warning(f"AAL validation failed for {aal_status['email']} ({user_role}): {validation['reason']}")
    #
    #                 # For API requests, return AAL error with step-up info
    #                 if request.path.startswith('/api/'):
    #                     return jsonify({
    #                         "error": "Insufficient authentication level",
    #                         "code": "INSUFFICIENT_AAL",
    #                         "details": {
    #                             "current_aal": validation['current_aal'],
    #                             "required_aal": validation['required_aal'],
    #                             "missing_methods": validation['missing_methods'],
    #                             "reason": validation['reason'],
    #                             "redirect_url": "/dashboard/settings/security"
    #                         }
    #                     }), 403
    #
    #                 # For web requests, allow frontend to handle redirect
    #                 return None
    #
    #             logger.debug(f"AAL validation passed for {aal_status['email']} ({user_role}) on {request.path}")
    #
    #     except Exception as e:
    #         logger.error(f"Error in before_request middleware: {e}", exc_info=True)
    
    # Add security headers to prevent caching
    from app.utils.security_headers import add_security_headers
    
    @flask_app.after_request
    def after_request(response):
        """Add security headers to all responses"""
        # Only add no-cache headers to authenticated routes
        if request.path.startswith('/api/') and request.path != '/api/auth/login':
            response = add_security_headers(response)
        return response

    # Configure CORS - support both localhost and custom domains
    allowed_origins = [
        'https://localhost:8443',
        'http://localhost:8443',
        'https://localhost:4433',
        'http://localhost:4433',
        'https://sting.local:8443',
        'http://sting.local:8443',
        'https://sting.local:4433',
        'http://sting.local:4433'
    ]
    
    # Add custom hostname from config if present
    custom_domain = os.getenv('STING_HOSTNAME') or os.getenv('HOSTNAME')
    if custom_domain and custom_domain not in ['localhost', 'sting.local']:
        allowed_origins.extend([
            f'https://{custom_domain}:8443',
            f'http://{custom_domain}:8443',
            f'https://{custom_domain}:4433',
            f'http://{custom_domain}:4433'
        ])
        logger.info(f"Added custom hostname to CORS: {custom_domain}")
    
    # Also allow any IP address for local network access
    # This allows access like https://192.168.1.100:8443
    CORS(flask_app,
        origins=allowed_origins + ['https://*:8443', 'http://*:8443'],
        allow_headers=[
            "Content-Type", "Authorization", "X-Requested-With"
        ],
        expose_headers=["Content-Type", "X-Total-Count"],
        methods=["OPTIONS", "GET", "POST", "PUT", "DELETE"],
        supports_credentials=True,
        vary_header=True,
        send_wildcard=False,
        always_send=True
    )

    if app_env == 'development':
        create_debug_routes(flask_app)
        try:
            verify_config(flask_app)
        except Exception as e:
            logger.warning(f"Configuration warnings in development: {str(e)}")
    else:
        verify_config(flask_app)

    # Initialize database
    init_db(flask_app)
    
    # Register blueprints AFTER Supertokens init
    try:
        # flask_app.register_blueprint(auth_blueprint, url_prefix='/api/auth')  # SuperTokens auth deprecated
        # logger.info("Auth blueprint registered successfully")
        
        flask_app.register_blueprint(llm_bp)
        logger.info("LLM management blueprint registered successfully")
        
        flask_app.register_blueprint(user_bp)
        logger.info("User management blueprint registered successfully")
        print("DEBUG: After user blueprint registration", flush=True)
        
        # ARCHIVED: Custom WebAuthn - now using Kratos WebAuthn
        # logger.info("DEBUG: About to register WebAuthn blueprint")
        # print("DEBUG: About to register WebAuthn blueprint", flush=True)
        # try:
        #     logger.info("Attempting to register WebAuthn blueprint...")
        #     print(f"DEBUG: webauthn_bp = {webauthn_bp}", flush=True)
        #     # Already imported at the top
        #     flask_app.register_blueprint(webauthn_bp, url_prefix='/api/webauthn')
        #     logger.info("WebAuthn blueprint registered successfully")
        #     print("DEBUG: WebAuthn blueprint registered successfully", flush=True)
        # except Exception as e:
        #     logger.error(f"Could not register WebAuthn blueprint: {e}", exc_info=True)
        #     print(f"DEBUG: WebAuthn registration failed: {e}", flush=True)
        
        # Register modular auth blueprints (pure Kratos structure)
        flask_app.register_blueprint(kratos_session_bp, url_prefix='/api/auth')
        logger.info("Pure Kratos session blueprint registered successfully")
        
        flask_app.register_blueprint(auth_password_bp, url_prefix='/api/auth')
        logger.info("Auth password blueprint registered successfully")
        
        flask_app.register_blueprint(auth_aal_bp, url_prefix='/api/auth')
        logger.info("Auth AAL blueprint registered successfully")
        
        flask_app.register_blueprint(auth_debug_bp, url_prefix='/api/auth')
        logger.info("Auth debug blueprint registered successfully")
        
        flask_app.register_blueprint(auth_misc_bp, url_prefix='/api/auth')
        logger.info("Auth misc blueprint registered successfully")
        
        # Session establishment endpoint for coordinated auth
        from app.routes.auth_session_establish import auth_session_bp
        flask_app.register_blueprint(auth_session_bp, url_prefix='/api/auth/session')
        logger.info("Session establishment blueprint registered successfully")

        # Legacy auth blueprint (being phased out)
        # flask_app.register_blueprint(auth_bp, url_prefix='/api/auth')
        # logger.info("Legacy auth blueprint registered successfully")
        
        # HYBRID: Custom WebAuthn API routes (for AAL2 elevation with Kratos native)
        from app.routes.webauthn_api_routes import webauthn_api_bp
        flask_app.register_blueprint(webauthn_api_bp, url_prefix='/api/webauthn')
        logger.info("WebAuthn API blueprint registered successfully")
        
        # DEPRECATED: Native WebAuthn routes (replaced by Kratos native)
        # try:
        #     from app.routes.webauthn_native_routes import webauthn_native_bp
        #     flask_app.register_blueprint(webauthn_native_bp)
        #     logger.info("Native WebAuthn blueprint registered successfully")
        # except ImportError as e:
        #     logger.warning(f"Could not import native WebAuthn routes (webauthn library may not be installed): {e}")
        
        # Register test auth bypass routes (DEVELOPMENT ONLY)
        if os.getenv('ENABLE_TEST_AUTH', 'false').lower() == 'true':
            try:
                from app.routes.test_auth_bypass import test_auth_bp
                flask_app.register_blueprint(test_auth_bp)
                logger.warning("⚠️  TEST AUTH BYPASS ENABLED - DEVELOPMENT ONLY!")
            except ImportError as e:
                logger.warning(f"Could not import test auth bypass routes: {e}")
        
        # Register AAL (Authentication Assurance Level) routes - Original Implementation
        # Note: Some AAL functionality is also in the new auth_aal_bp above
        flask_app.register_blueprint(original_aal_bp, name='original_aal')
        logger.info("AAL blueprint (original) registered successfully")
        
        # Register Custom AAL2 routes for biometric step-up authentication
        from app.routes.aal2_routes import aal2_bp
        flask_app.register_blueprint(aal2_bp)
        logger.info("Custom AAL2 blueprint registered successfully")
        
        # Register Enhanced WebAuthn routes for hybrid AAL2 authentication
        # DEPRECATED: Enhanced WebAuthn (replaced by Kratos native)
        # flask_app.register_blueprint(enhanced_webauthn_bp, url_prefix='/api/enhanced-webauthn')
        logger.info("Enhanced WebAuthn blueprint registered successfully")
        
        # Register Admin Invitation routes for secure admin-to-admin invitations
        from app.routes.admin_invitation_routes import admin_invitation_bp
        flask_app.register_blueprint(admin_invitation_bp)
        logger.info("Admin invitation blueprint registered successfully")
        
        # Register admin setup routes (passwordless admin registration)
        flask_app.register_blueprint(admin_setup_bp, url_prefix='/api/auth')
        logger.info("Admin setup blueprint registered successfully")
        
        # Register admin recovery routes
        flask_app.register_blueprint(admin_recovery_bp, url_prefix='/api/admin/recovery')
        logger.info("Admin recovery blueprint registered successfully")
        
        # Register admin registration routes (improved admin onboarding)
        flask_app.register_blueprint(admin_registration_bp)
        logger.info("Admin registration blueprint registered successfully")
        
        # Register admin management routes
        flask_app.register_blueprint(admin_bp)
        logger.info("Admin management blueprint registered successfully")

        # Register Kratos webhooks
        flask_app.register_blueprint(kratos_webhooks_bp, url_prefix='/api/kratos/webhooks')
        logger.info("Kratos webhooks blueprint registered successfully")

        # Register PII configuration routes
        flask_app.register_blueprint(pii_bp, url_prefix='/api/pii')
        logger.info("PII configuration blueprint registered successfully")
        
        # Register bootstrap routes for creating default honey jars
        try:
            from app.routes.bootstrap_routes import bootstrap_bp
            flask_app.register_blueprint(bootstrap_bp, url_prefix='/api/bootstrap')
            logger.info("Bootstrap routes blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Bootstrap blueprint registration failed: {e}")
            logger.info("Bootstrap features will be unavailable")
        
        from app.routes.session_routes import session_bp
        flask_app.register_blueprint(session_bp)
        logger.info("Session proxy blueprint registered successfully")
        
        # Register chatbot (Bee) routes
        try:
            from app.routes.chatbot_routes import chatbot_bp
            flask_app.register_blueprint(chatbot_bp)
            logger.info("Chatbot (Bee) blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Chatbot blueprint registration failed: {e}")
            logger.info("Chatbot features will be unavailable")
        
        # Register external AI proxy routes
        try:
            from app.routes.external_ai_proxy import external_ai_proxy_bp
            flask_app.register_blueprint(external_ai_proxy_bp)
            logger.info("External AI proxy blueprint registered successfully")
        except Exception as e:
            logger.warning(f"External AI proxy blueprint registration failed: {e}")
            logger.info("External AI proxy features will be unavailable")
        
        # Register knowledge proxy routes
        try:
            from app.routes.knowledge_proxy import knowledge_proxy_bp
            flask_app.register_blueprint(knowledge_proxy_bp, url_prefix='/api/knowledge')
            logger.info("Knowledge proxy blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Knowledge proxy blueprint registration failed: {e}")
            logger.info("Knowledge/honey jar features will be unavailable")

        # Register messaging proxy routes
        try:
            from app.routes.messaging_proxy import messaging_proxy_bp
            flask_app.register_blueprint(messaging_proxy_bp, url_prefix='/api/messaging')
            logger.info("Messaging proxy blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Messaging proxy blueprint registration failed: {e}")
            logger.info("Messaging/chat features will be unavailable")

        # Import file_bp locally to avoid early Vault initialization
        try:
            from app.routes.file_routes import file_bp
            flask_app.register_blueprint(file_bp)
            logger.info("File management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"File management blueprint registration failed: {e}")
            logger.info("File management features will be unavailable")
        
        # Register report management blueprint
        try:
            from app.routes.report_routes import report_bp
            flask_app.register_blueprint(report_bp)
            logger.info("Report management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Report management blueprint registration failed: {e}")
            logger.info("Report management features will be unavailable")
        
        # Register metrics blueprint
        try:
            from app.routes.metrics_routes import metrics_bp
            flask_app.register_blueprint(metrics_bp)
            logger.info("Metrics blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Metrics blueprint registration failed: {e}")
        
        # Register system blueprint
        try:
            from app.routes.system_routes import system_bp
            flask_app.register_blueprint(system_bp, url_prefix='/api')
            logger.info("System blueprint registered successfully")
        except Exception as e:
            logger.warning(f"System blueprint registration failed: {e}")
            logger.info("Metrics features will be unavailable")
        
        # Register TOTP routes blueprint
        try:
            from app.routes.totp_routes import totp_bp
            flask_app.register_blueprint(totp_bp, url_prefix='/api/totp')
            logger.info("TOTP routes blueprint registered successfully")
        except Exception as e:
            logger.warning(f"TOTP blueprint registration failed: {e}")
            logger.info("TOTP features will be unavailable")
        
        # Register TOTP enrollment routes (simplified enrollment API)
        try:
            from app.routes.totp_enrollment_routes import totp_enrollment_bp
            flask_app.register_blueprint(totp_enrollment_bp, url_prefix='/api/totp-enrollment')
            logger.info("TOTP enrollment routes registered successfully")
        except Exception as e:
            logger.warning(f"TOTP enrollment blueprint registration failed: {e}")
            logger.info("TOTP enrollment features will be unavailable")
        
        # Register WebAuthn enrollment routes (simplified enrollment API)
        try:
            from app.routes.webauthn_enrollment_routes import webauthn_enrollment_bp
            # DEPRECATED: Custom WebAuthn enrollment (replaced by Kratos native)
            # flask_app.register_blueprint(webauthn_enrollment_bp, url_prefix='/api/webauthn-enrollment')
            logger.info("WebAuthn enrollment routes registered successfully")
        except Exception as e:
            logger.warning(f"WebAuthn enrollment blueprint registration failed: {e}")
            logger.info("WebAuthn enrollment features will be unavailable")
        
        # Register debug authentication routes (development/testing)
        try:
            from app.routes.debug_auth_routes import debug_auth_bp
            flask_app.register_blueprint(debug_auth_bp, url_prefix='/api/debug-auth')
            logger.info("Debug authentication routes registered successfully")
        except Exception as e:
            logger.warning(f"Debug auth blueprint registration failed: {e}")
            logger.info("Debug authentication features will be unavailable")

        # Register biometric authentication routes
        try:
            from app.routes.biometric_routes import biometric_bp
            flask_app.register_blueprint(biometric_bp)
            logger.info("🔒 Biometric authentication blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Biometric blueprint registration failed: {e}")
            logger.info("Biometric AAL2 features will be unavailable")
        
        # Register Beeacon monitoring routes
        try:
            from app.routes.beeacon_routes import beeacon
            flask_app.register_blueprint(beeacon)
            logger.info("Beeacon monitoring blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Beeacon blueprint registration failed: {e}")
            logger.info("Beeacon monitoring features will be unavailable")
        
        # Register dashboard metrics routes
        try:
            from app.routes.dashboard_routes import dashboard
            flask_app.register_blueprint(dashboard)
            logger.info("Dashboard metrics blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Dashboard blueprint registration failed: {e}")
            logger.info("Dashboard metrics features will be unavailable")
        
        # Register API key management routes
        try:
            from app.routes.api_key_routes import api_key_bp
            flask_app.register_blueprint(api_key_bp)
            logger.info("API key management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"API key blueprint registration failed: {e}")

        # Register recovery codes routes
        try:
            from app.routes.recovery_routes import recovery_bp
            flask_app.register_blueprint(recovery_bp)
            logger.info("Recovery codes blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Recovery codes blueprint registration failed: {e}")

        # Register config routes
        try:
            flask_app.register_blueprint(config_bp)
            logger.info("Config blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Config blueprint registration failed: {e}")
            logger.info("API key management features will be unavailable")
        
        # Register user sync routes
        try:
            from app.routes.sync_routes import sync_bp
            flask_app.register_blueprint(sync_bp)
            logger.info("🔄 User sync blueprint registered successfully")
        except Exception as e:
            logger.warning(f"User sync blueprint registration failed: {e}")
            logger.info("User sync features will be unavailable")
        
        # Register Nectar Bot management routes
        try:
            flask_app.register_blueprint(nectar_bot_bp)
            logger.info("🤖 Nectar Bot management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Nectar Bot blueprint registration failed: {e}")
            logger.info("Nectar Bot management features will be unavailable")
        
        # Register stub routes for legacy endpoints (clean console errors)
        try:
            from app.routes.stub_routes import stub_bp
            flask_app.register_blueprint(stub_bp)
            logger.info("🧹 Legacy endpoint stubs registered successfully")
        except Exception as e:
            logger.warning(f"Stub routes registration failed: {e}")
            logger.info("Some legacy endpoints may return 404 errors")
        
        # Register Demo Data management routes
        try:
            from app.routes.demo_routes import demo_bp
            flask_app.register_blueprint(demo_bp)
            logger.info("🎭 Demo data management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Demo data blueprint registration failed: {e}")
            logger.info("Demo data management features will be unavailable")
        
        # Register Storage management routes
        try:
            from app.routes.storage_routes import storage_bp
            flask_app.register_blueprint(storage_bp)
            logger.info("💾 Storage management blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Storage blueprint registration failed: {e}")
            logger.info("Storage management features will be unavailable")
        
        # Register MVP dashboard routes
        try:
            from app.routes.mvp_routes import mvp_bp
            flask_app.register_blueprint(mvp_bp)
            logger.info("🚀 MVP dashboard blueprint registered successfully")
        except Exception as e:
            logger.warning(f"MVP blueprint registration failed: {e}")
            logger.info("MVP features will be unavailable")
        
        # Register Email notification routes
        try:
            from app.routes.email_routes import email_bp
            flask_app.register_blueprint(email_bp)
            logger.info("📧 Email notification blueprint registered successfully")
        except Exception as e:
            logger.warning(f"Email blueprint registration failed: {e}")
            logger.info("Email notification features will be unavailable")

        # Basket Storage Management Routes
        try:
            from app.routes.basket_routes import basket_bp
            flask_app.register_blueprint(basket_bp)
            logger.info("🧺 Basket routes registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register basket routes: {str(e)}")
            logger.info("Basket storage management features will be unavailable")
        
        # User and Organization Preferences Routes
        try:
            from app.routes.support_routes import support_bp
            flask_app.register_blueprint(support_bp)
            logger.info("🐝 Support ticket management blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register support routes: {str(e)}")
            logger.info("Bee-powered support system will be unavailable")
        
        try:
            from app.routes.preferences_routes import preferences_bp
            flask_app.register_blueprint(preferences_bp)
            logger.info("⚙️ Preferences management blueprint registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to register preferences routes: {str(e)}")
            logger.info("Database-backed preferences features will be unavailable")
    except Exception as e:
        logger.error(f"Failed to register blueprints: {str(e)}")
        raise

    @flask_app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Not found"}), 404

    @flask_app.errorhandler(405)
    def method_not_allowed_error(error):
        return jsonify({"error": "Method not allowed"}), 405
    
    @flask_app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            "error": "File too large", 
            "detail": "The uploaded file exceeds the maximum allowed size of 100MB"
        }), 413

    @flask_app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    @flask_app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200

    @flask_app.route('/api/health/chatbot', methods=['GET'])
    def chatbot_health_check():
        """
        Proxy health check to chatbot service for initialization status
        Used by frontend to determine intelligent timeouts for chat requests
        """
        import requests
        chatbot_url = os.getenv('CHATBOT_SERVICE_URL', 'http://chatbot:9001')
        try:
            response = requests.get(f"{chatbot_url}/health", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return jsonify({
                    'status': 'healthy',
                    'service_initialized': data.get('service_initialized', False),
                    'model_loaded': data.get('model_loaded', False),
                    'chatbot_service': 'available'
                }), 200
            else:
                return jsonify({
                    'status': 'unhealthy',
                    'service_initialized': False,
                    'chatbot_service': 'error'
                }), 503
        except Exception as e:
            logger.warning(f"Chatbot health check failed: {e}")
            return jsonify({
                'status': 'unavailable',
                'service_initialized': False,
                'chatbot_service': 'unavailable',
                'error': str(e)
            }), 503

    @flask_app.route('/test', methods=['GET'])
    def test():
        return jsonify({"message": "Test route working"})

    @flask_app.route('/')
    def root():
        return jsonify({"message": "Root endpoint working"})

    # Add catch-all route for React app
    @flask_app.route('/', defaults={'path': ''})
    @flask_app.route('/<path:path>')
    def serve_react_app(path):
        """
        Serve React app for all non-API routes
        This enables client-side routing to work properly
        """
        # List of path prefixes that should return API responses, not the React app
        api_prefixes = [
            'api/',
            'health',
            'test',
            '.ory/',
            'static/',
            'favicon.ico'
        ]
        
        # If it's an API route, let Flask handle it normally
        if any(path.startswith(prefix) for prefix in api_prefixes):
            flask_app.logger.debug(f"API route detected: {path}")
            return flask_app.send_static_file('404.html'), 404
        
        # For all other routes, serve the React app's index.html
        try:
            # Try to serve from the React build directory
            react_build_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
            index_path = os.path.join(react_build_path, 'index.html')
            
            if os.path.exists(index_path):
                flask_app.logger.debug(f"Serving React app for route: /{path}")
                return flask_app.send_file(index_path)
            else:
                flask_app.logger.error(f"React build not found at: {react_build_path}")
                return jsonify({
                    "error": "Frontend not built", 
                    "message": "Run 'npm run build' in the frontend directory"
                }), 500
                
        except Exception as e:
            flask_app.logger.error(f"Error serving React app: {e}")
            return jsonify({"error": "Internal server error"}), 500

    # Apply force password change middleware v2 after blueprints are registered
    # This version uses database instead of Kratos traits to avoid schema validation issues
    from app.middleware.force_password_change_v2 import apply_force_password_change_middleware_v2
    apply_force_password_change_middleware_v2(flask_app)
    
    # TOTP enforcement is now handled by the unified enforce_2fa() middleware above
    # Removed duplicate TOTPEnforcementMiddleware to avoid conflicts

    with flask_app.app_context():
        # Import all models to ensure tables are created
        try:
            from app.models.report_models import Report, ReportTemplate, ReportQueue
            logger.info("Report models imported successfully")
        except Exception as e:
            logger.warning(f"Failed to import report models: {e}")
        
        # Import user settings model for v2 password change flow
        try:
            from app.models.user_settings import UserSettings
            logger.info("UserSettings model imported successfully")
        except Exception as e:
            logger.warning(f"Failed to import UserSettings model: {e}")

        # Import recovery codes model for tiered authentication
        try:
            from app.models.recovery_code_models import RecoveryCode
            logger.info("RecoveryCode model imported successfully")
        except Exception as e:
            logger.warning(f"Failed to import RecoveryCode model: {e}")

        # Import audit log model for security tracking
        try:
            from app.models.audit_log_models import AuditLog
            logger.info("AuditLog model imported successfully")
        except Exception as e:
            logger.warning(f"Failed to import AuditLog model: {e}")
        
        db.create_all()
        
        # FIX: Ensure database permissions are correct after fresh install
        # This prevents recurring 500 errors from permission issues
        try:
            db.engine.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user"))
            db.engine.execute(text("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user"))
            logger.info("🔧 Database permissions verified and fixed if needed")
        except Exception as e:
            logger.warning(f"🔧 Database permission check failed (may be normal): {e}")
        
        # Initialize default admin user on startup using v2 (database-based) approach
        try:
            from app.utils.default_admin_setup_v2 import ensure_admin_exists
            from app.utils.demo_users_setup import initialize_demo_users
            from app.utils.startup_banner import display_startup_banner
            from app.utils.session_validator import SessionValidator
            from app.utils.startup_checks import run_startup_checks
            from threading import Thread
            
            # TEMPORARILY DISABLED: Admin setup is corrupting credentials on every app restart
            # This causes login issues whenever frontend is updated
            # def init_admin():
            #     with flask_app.app_context():
            #         try:
            #             # Run startup checks first to fix any issues
            #             run_startup_checks()
            #             
            #             # Use V2 admin setup (database-based) - consolidated approach
            #             admin_created = ensure_admin_exists()
            #             if admin_created:
            #                 logger.info("V2 admin initialization completed successfully")
            #             else:
            #                 logger.info("V2 admin initialization skipped (admin already exists)")
            #             # Also initialize demo users for better first-time experience
            #             try:
            #                 initialize_demo_users()
            #             except Exception as e:
            #                 logger.warning(f"Failed to initialize demo users: {e}")
            #             # Initialize report templates
            #             try:
            #                 from app.utils.init_report_templates import create_default_templates
            #                 template_count = create_default_templates()
            #                 logger.info(f"Initialized {template_count} default report templates")
            #             except Exception as e:
            #                 logger.warning(f"Failed to initialize report templates: {e}")
            #             # Display banner after admin initialization
            #             display_startup_banner()
            #             
            #         except Exception as e:
            #             logger.error(f"Failed during admin initialization: {e}")
            #             # Still display banner even if admin setup fails
            #             try:
            #                 display_startup_banner()
            #             except Exception as banner_e:
            #                 logger.error(f"Failed to display banner: {banner_e}")
 
            # thread = Thread(target=init_admin)
            # thread.daemon = True
            # thread.start()
            
            # Initialize report templates
            try:
                from app.utils.init_report_templates import create_default_templates
                template_count = create_default_templates()
                logger.info(f"Initialized {template_count} default report templates")
            except Exception as e:
                logger.warning(f"Failed to initialize report templates: {e}")
            
            # Still show banner even with admin init disabled
            try:
                display_startup_banner()
            except Exception as e:
                logger.error(f"Failed to display banner: {e}")
            
            # Validate existing sessions on startup
            try:
                redis_client = flask_app.config.get('SESSION_REDIS')
                if redis_client:
                    validator = SessionValidator(redis_client)
                    stats = validator.validate_sessions_on_startup()
                    logging.info(f"Session validation on startup: {stats}")
            except Exception as e:
                logging.warning(f"Session validation skipped: {e}")
            
        except Exception as e:
            logging.error(f"Failed to initialize default admin: {e}")

    # Initialize Profile Sync Worker for Kratos-STING user synchronization
    try:
        from app.workers.profile_sync_worker import init_profile_worker
        init_profile_worker(flask_app)
        logger.info("🔄 Profile sync worker initialized successfully")
    except Exception as e:
        logger.warning(f"Profile sync worker initialization failed: {e}")
        logger.info("Profile sync features will be unavailable")

    return flask_app