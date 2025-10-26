from functools import wraps
from flask import request, jsonify, g
from app.models.api_key_models import ApiKey, ApiKeyUsage
import time
import re

def api_key_required(scopes=None, permissions=None):
    """
    Decorator for API endpoints that require API key authentication
    
    Args:
        scopes (list): Required scopes (e.g., ['read', 'write'])
        permissions (dict): Required permissions (e.g., {'honey_jars': ['read', 'write']})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Get API key from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'error': 'Missing Authorization header',
                    'message': 'API key required. Use: Authorization: Bearer sk_...'
                }), 401
            
            # Extract API key from Bearer token format
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    'error': 'Invalid Authorization header format',
                    'message': 'Use: Authorization: Bearer sk_...'
                }), 401
            
            api_key_secret = auth_header.replace('Bearer ', '')
            
            # Verify the API key
            api_key = ApiKey.verify_key(api_key_secret)
            if not api_key:
                # Log failed attempt
                ApiKeyUsage.log_usage(
                    api_key=None,
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=401,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    error_message='Invalid or expired API key'
                )
                
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'API key is invalid, expired, or inactive'
                }), 401
            
            # Check required scopes
            if scopes:
                missing_scopes = []
                for scope in scopes:
                    if not api_key.has_scope(scope):
                        missing_scopes.append(scope)
                
                if missing_scopes:
                    # Log insufficient permissions
                    response_time = int((time.time() - start_time) * 1000)
                    ApiKeyUsage.log_usage(
                        api_key=api_key,
                        endpoint=request.endpoint or request.path,
                        method=request.method,
                        status_code=403,
                        response_time_ms=response_time,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        error_message=f'Missing required scopes: {missing_scopes}'
                    )
                    
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'API key missing required scopes: {missing_scopes}',
                        'required_scopes': scopes,
                        'current_scopes': api_key.scopes
                    }), 403
            
            # Check required permissions
            if permissions:
                missing_permissions = []
                for resource, actions in permissions.items():
                    for action in actions:
                        if not api_key.has_permission(resource, action):
                            missing_permissions.append(f'{resource}:{action}')
                
                if missing_permissions:
                    # Log insufficient permissions
                    response_time = int((time.time() - start_time) * 1000)
                    ApiKeyUsage.log_usage(
                        api_key=api_key,
                        endpoint=request.endpoint or request.path,
                        method=request.method,
                        status_code=403,
                        response_time_ms=response_time,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        error_message=f'Missing required permissions: {missing_permissions}'
                    )
                    
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'API key missing required permissions: {missing_permissions}',
                        'required_permissions': permissions,
                        'current_permissions': api_key.permissions
                    }), 403
            
            # Store API key in request context
            g.api_key = api_key
            g.current_user_id = api_key.user_id
            g.current_user_email = api_key.user_email
            
            try:
                # Execute the decorated function
                result = f(*args, **kwargs)
                
                # Log successful usage
                response_time = int((time.time() - start_time) * 1000)
                ApiKeyUsage.log_usage(
                    api_key=api_key,
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=200,
                    response_time_ms=response_time,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                return result
                
            except Exception as e:
                # Log error
                response_time = int((time.time() - start_time) * 1000)
                ApiKeyUsage.log_usage(
                    api_key=api_key,
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=500,
                    response_time_ms=response_time,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    error_message=str(e)
                )
                
                raise
        
        return decorated_function
    return decorator

def api_key_optional():
    """
    Decorator for endpoints that can use either session auth or API key auth
    Sets g.api_key if an API key is provided and valid
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for API key in Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer sk_'):
                api_key_secret = auth_header.replace('Bearer ', '')
                api_key = ApiKey.verify_key(api_key_secret)
                
                if api_key:
                    # Store API key in request context
                    g.api_key = api_key
                    g.current_user_id = api_key.user_id
                    g.current_user_email = api_key.user_email
                    g.auth_method = 'api_key'
                else:
                    g.auth_method = 'invalid_api_key'
            else:
                g.auth_method = 'session'
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def rate_limit_check(api_key, endpoint=None):
    """
    Check if API key has exceeded rate limit
    Returns (is_allowed, remaining_requests, reset_time)
    """
    import time
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Simple in-memory rate limiting (for production, use Redis)
    # This is a basic implementation - in production you'd want Redis with sliding window
    current_minute = int(time.time() // 60)
    
    # Get usage in current minute window
    recent_usage = ApiKeyUsage.query.filter(
        ApiKeyUsage.api_key_id == api_key.id,
        ApiKeyUsage.timestamp >= datetime.utcnow() - timedelta(minutes=1)
    ).count()
    
    rate_limit = api_key.rate_limit_per_minute
    remaining = max(0, rate_limit - recent_usage)
    is_allowed = recent_usage < rate_limit
    reset_time = (current_minute + 1) * 60  # Next minute
    
    return is_allowed, remaining, reset_time

def validate_api_key_format(api_key):
    """Validate API key format"""
    if not api_key:
        return False, "API key is required"
    
    if not isinstance(api_key, str):
        return False, "API key must be a string"
    
    if not api_key.startswith('sk_'):
        return False, "API key must start with 'sk_'"
    
    if len(api_key) < 20:
        return False, "API key is too short"
    
    # Check for valid characters (base64url safe characters)
    if not re.match(r'^sk_[A-Za-z0-9_-]+$', api_key):
        return False, "API key contains invalid characters"
    
    return True, "Valid format"