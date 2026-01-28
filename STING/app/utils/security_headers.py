"""Security headers middleware for preventing caching of authenticated content"""
from flask import make_response
from functools import wraps

def add_security_headers(response):
    """Add security headers to prevent caching"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def no_cache(f):
    """Decorator to add no-cache headers to a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        return add_security_headers(response)
    return decorated_function