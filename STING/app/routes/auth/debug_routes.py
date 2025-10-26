"""
Debug Routes for Authentication

Debug endpoints for development and troubleshooting authentication flows.
These routes are typically only available in debug mode.
"""

from flask import Blueprint, request, jsonify, session, g, current_app, make_response
import logging
from datetime import datetime, timedelta
import time

from app.models.user_models import User
from app.database import db

logger = logging.getLogger(__name__)

debug_bp = Blueprint('auth_debug', __name__)


@debug_bp.after_request
def after_request(response):
    """Add CORS headers specifically for debug endpoints"""
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@debug_bp.route('/debug/session', methods=['GET'])
def debug_session():
    """Debug endpoint to view current session"""
    # Allow in all environments for debugging this specific issue
    
    # Check Redis sessions too
    redis_sessions = []
    try:
        import redis
        r = redis.from_url(current_app.config.get('SESSION_REDIS'))
        for key in r.keys('sting:*'):
            redis_sessions.append(key.decode())
    except Exception as e:
        redis_sessions = [f'Unable to check Redis: {str(e)}']
    
    return jsonify({
        'flask_session': dict(session),
        'session_id': session.get('_id', 'No session ID'),
        'session_cookie_name': current_app.config.get('SESSION_COOKIE_NAME'),
        'cookies': dict(request.cookies),
        'redis_sessions_count': len(redis_sessions),
        'redis_sessions': redis_sessions[:5],  # Show first 5
        'user': g.user.to_dict() if hasattr(g, 'user') and g.user else None,
        'authenticated': hasattr(g, 'user') and g.user is not None,
        'auth_method': g.auth_method if hasattr(g, 'auth_method') else None,
        'g_attributes': [attr for attr in dir(g) if not attr.startswith('_')]
    })


@debug_bp.route('/debug/simulate-webauthn-complete', methods=['GET', 'POST'])
def debug_simulate_webauthn_complete():
    """Debug endpoint to simulate successful WebAuthn completion for testing"""
    try:
        # Check if we have a pending WebAuthn challenge
        user_id = session.get('webauthn_user_id')
        if not user_id:
            return jsonify({'error': 'No pending WebAuthn challenge'}), 400
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 400
        
        # Clear WebAuthn challenge data
        session.pop('webauthn_challenge_aal2', None)
        session.pop('webauthn_user_id', None)
        session.pop('webauthn_options', None)
        
        # SIMULATE: Establish main authentication session (the fix)
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['auth_method'] = 'enhanced_webauthn'
        session['authenticated_at'] = datetime.utcnow().isoformat()
        session['session_id'] = f"webauthn_{user.id}_{int(time.time())}"
        
        # Set expiration (24 hours from now)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session['expires_at'] = expires_at.isoformat()
        
        # Set AAL2 markers
        session['custom_aal2_verified'] = True
        session['custom_aal2_timestamp'] = datetime.utcnow().isoformat()
        session['custom_aal2_method'] = 'webauthn_biometric'
        
        # Store user in g for immediate access
        g.user = user
        
        logger.info(f"🔐 DEBUG: Simulated WebAuthn completion for user: {user.email}")
        
        return jsonify({
            'verified': True,
            'message': 'WebAuthn completion simulated',
            'user': {
                'id': user.id,
                'email': user.email
            },
            'session_data': {
                'user_id': session.get('user_id'),
                'auth_method': session.get('auth_method'),
                'authenticated_at': session.get('authenticated_at'),
                'expires_at': session.get('expires_at')
            }
        })
        
    except Exception as e:
        logger.error(f"Error simulating WebAuthn complete: {str(e)}")
        return jsonify({'error': 'Failed to simulate authentication'}), 500


@debug_bp.route('/debug/clear-all-sessions', methods=['POST'])
def debug_clear_all_sessions():
    """Debug endpoint to clear all sessions for current user"""
    if not current_app.debug:
        return jsonify({'error': 'Debug mode not enabled'}), 404
    try:
        # Clear Flask session
        session.clear()
        
        # Clear session from database if using server-side sessions
        if hasattr(g, 'user') and g.user:
            # You might have a sessions table to clear
            pass
        
        response = make_response(jsonify({
            'success': True,
            'message': 'All sessions cleared'
        }))
        
        # Clear all possible cookies
        cookie_names = [
            'sting_session', 'session', 'flask_session',
            'ory_kratos_session', 'ory_kratos_session', 'ory_session',
            'csrf_token', 'sting_auth_bridge'
        ]
        
        for cookie_name in cookie_names:
            response.set_cookie(cookie_name, '', max_age=0, path='/')
        
        return response
        
    except Exception as e:
        logger.error(f"Error clearing all sessions: {str(e)}")
        return jsonify({
            'error': 'Failed to clear sessions'
        }), 500


@debug_bp.route('/debug/nuclear-logout', methods=['GET', 'POST'])
def nuclear_logout():
    """Nuclear option - clear everything"""
    if not current_app.debug:
        return jsonify({'error': 'Debug mode not enabled'}), 404
    
    session.clear()
    
    response = make_response('''
        <html>
        <head>
            <script>
                // Clear all localStorage
                localStorage.clear();
                // Clear all sessionStorage
                sessionStorage.clear();
                // Clear IndexedDB (if any)
                if (window.indexedDB) {
                    indexedDB.databases().then(dbs => {
                        dbs.forEach(db => indexedDB.deleteDatabase(db.name));
                    });
                }
                // Redirect to login
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1000);
            </script>
        </head>
        <body>
            <h1>Clearing all data...</h1>
            <p>You will be redirected to login page.</p>
        </body>
        </html>
        ''')
    
    # Clear all cookies
    for cookie in request.cookies:
        response.set_cookie(cookie, '', max_age=0, path='/')
    
    response.headers['Clear-Site-Data'] = '"*"'
    
    return response


@debug_bp.route('/debug/auth-info', methods=['GET'])
def debug_auth_info():
    """Debug endpoint to show comprehensive authentication information"""
    try:
        auth_info = {
            'flask_session': {
                'data': dict(session),
                'id': session.get('_id', 'No session ID'),
                'permanent': session.permanent,
                'new': session.new if hasattr(session, 'new') else None
            },
            'request_info': {
                'cookies': dict(request.cookies),
                'headers': {k: v for k, v in request.headers.items() if 'auth' in k.lower() or 'session' in k.lower()},
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            },
            'g_context': {
                'user': g.user.to_dict() if hasattr(g, 'user') and g.user else None,
                'identity': g.identity if hasattr(g, 'identity') else None,
                'authenticated': hasattr(g, 'user') and g.user is not None,
                'auth_method': g.auth_method if hasattr(g, 'auth_method') else None,
                'all_attributes': [attr for attr in dir(g) if not attr.startswith('_')]
            },
            'app_config': {
                'debug': current_app.debug,
                'session_cookie_name': current_app.config.get('SESSION_COOKIE_NAME'),
                'session_type': current_app.config.get('SESSION_TYPE'),
                'secret_key_set': bool(current_app.config.get('SECRET_KEY')),
                'redis_url': current_app.config.get('SESSION_REDIS_URL', 'Not set')[:50] + '...' if current_app.config.get('SESSION_REDIS_URL') else 'Not set'
            }
        }
        
        # Check Redis sessions if available
        try:
            import redis
            r = redis.from_url(current_app.config.get('SESSION_REDIS'))
            redis_keys = [key.decode() for key in r.keys('sting:*')]
            auth_info['redis_sessions'] = {
                'count': len(redis_keys),
                'keys': redis_keys[:10],  # Show first 10
                'current_session_exists': any('sting:' + str(session.get('_id', '')) in key for key in redis_keys) if session.get('_id') else False
            }
        except Exception as e:
            auth_info['redis_sessions'] = {
                'error': str(e),
                'count': 0
            }
        
        return jsonify(auth_info)
        
    except Exception as e:
        logger.error(f"Error getting debug auth info: {e}")
        return jsonify({
            'error': 'Failed to get debug auth info',
            'exception': str(e)
        }), 500