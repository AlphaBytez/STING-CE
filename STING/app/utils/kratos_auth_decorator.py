"""
Kratos-aware authentication decorator
Validates authentication directly against Kratos without requiring Flask session
"""

import logging
import requests
from flask import request, jsonify, g
from functools import wraps

logger = logging.getLogger(__name__)

def require_kratos_session(f):
    """Decorator that validates Kratos session directly"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Kratos session cookie
        session_cookie = (
            request.cookies.get('ory_kratos_session') or 
            request.cookies.get('ory_session') or
            request.cookies.get('kratos_session')
        )
        
        if not session_cookie:
            logger.warning(f"No Kratos session cookie found for {request.path}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'No valid session found'
            }), 401
        
        try:
            # Validate session with Kratos directly (use service name from container)
            kratos_url = 'https://kratos:4433'
            response = requests.get(
                f'{kratos_url}/sessions/whoami',
                headers={
                    'Accept': 'application/json',
                    'Cookie': f'ory_kratos_session={session_cookie}'
                },
                timeout=5,
                verify=False  # Disable SSL verification for self-signed certs
            )
            
            if response.status_code != 200:
                logger.warning(f"Kratos session validation failed: {response.status_code}")
                return jsonify({
                    'error': 'Invalid session',
                    'message': 'Session validation failed'
                }), 401
            
            session_data = response.json()
            identity = session_data.get('identity')
            
            if not identity:
                logger.warning("No identity found in Kratos session")
                return jsonify({
                    'error': 'Invalid session',
                    'message': 'No identity found'
                }), 401
            
            # Store identity in g for use in the endpoint
            g.kratos_identity = identity
            g.user_email = identity.get('traits', {}).get('email')
            g.user_role = identity.get('traits', {}).get('role', 'user')
            
            logger.debug(f"Kratos session validated for {g.user_email}")
            
            return f(*args, **kwargs)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating Kratos session: {e}")
            return jsonify({
                'error': 'Authentication error',
                'message': 'Session validation failed'
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in Kratos auth decorator: {e}")
            return jsonify({
                'error': 'Authentication error', 
                'message': 'Internal authentication error'
            }), 500
    
    return decorated_function