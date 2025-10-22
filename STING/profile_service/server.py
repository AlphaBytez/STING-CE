#!/usr/bin/env python3
"""
STING-CE Profile Service
Handles user profile management, file uploads, and profile data.
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.profile_api import profile_bp
from core.profile_manager import ProfileManager
from auth.profile_auth import ProfileAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configuration
    app.config.update({
        'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', os.urandom(32)),
        'DATABASE_URL': os.environ.get('DATABASE_URL'),
        'VAULT_ADDR': os.environ.get('VAULT_ADDR', 'http://vault:8200'),
        'VAULT_TOKEN': os.environ.get('VAULT_TOKEN', 'root'),
        'KRATOS_PUBLIC_URL': os.environ.get('KRATOS_PUBLIC_URL', 'https://localhost:4433'),
        'KRATOS_ADMIN_URL': os.environ.get('KRATOS_ADMIN_URL', 'http://kratos:4434'),
        'PROFILE_SERVICE_PORT': int(os.environ.get('PROFILE_SERVICE_PORT', 8092)),
        'MAX_CONTENT_LENGTH': 50 * 1024 * 1024,  # 50MB max file size
    })
    
    # CORS configuration
    CORS(app, 
         origins=['https://localhost:8443', 'https://localhost:5050'],
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    
    # Initialize services
    profile_manager = ProfileManager(app.config)
    profile_auth = ProfileAuth(app.config)
    
    # Store in app context
    app.profile_manager = profile_manager
    app.profile_auth = profile_auth
    
    # Register blueprints
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        try:
            # Test database connectivity
            db_healthy = profile_manager.health_check()
            
            # For now, assume vault is healthy if we can reach this point
            # The service doesn't actually use Vault based on the ProfileFileService implementation
            vault_healthy = True
            
            status = 'healthy' if db_healthy else 'degraded'
            
            return jsonify({
                'status': status,
                'database': 'healthy' if db_healthy else 'unhealthy',
                'vault': 'healthy' if vault_healthy else 'unhealthy',
                'service': 'profile-service',
                'version': '1.0.0'
            }), 200 if status == 'healthy' else 503
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'service': 'profile-service'
            }), 503
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint."""
        return jsonify({
            'service': 'STING-CE Profile Service',
            'version': '1.0.0',
            'status': 'running'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({'error': 'File too large'}), 413
    
    return app

def main():
    """Main entry point."""
    app = create_app()
    
    port = app.config['PROFILE_SERVICE_PORT']
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting STING-CE Profile Service on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    if os.environ.get('FLASK_ENV') == 'production':
        # Use Gunicorn in production
        import gunicorn.app.base
        
        class GunicornApp(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                for key, value in self.options.items():
                    self.cfg.set(key, value)
            
            def load(self):
                return self.application
        
        options = {
            'bind': f'0.0.0.0:{port}',
            'workers': 2,
            'timeout': 120,
            'keepalive': 2,
            'max_requests': 1000,
            'max_requests_jitter': 100,
        }
        
        GunicornApp(app, options).run()
    else:
        # Development server
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )

if __name__ == '__main__':
    main()