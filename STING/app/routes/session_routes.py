"""
Session proxy routes for Kratos authentication
"""

from flask import Blueprint, request, jsonify, make_response
import requests
import logging
import os

logger = logging.getLogger(__name__)

session_bp = Blueprint('session', __name__)

KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://localhost:4433')
KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'http://kratos:4434')

@session_bp.route('/api/session/whoami', methods=['GET'])
def session_whoami():
    """
    Proxy the whoami request to Kratos, forwarding cookies from the browser.
    This allows the backend to validate the session on behalf of the frontend.
    """
    try:
        # Forward all cookies from the browser to Kratos
        cookies = request.cookies.to_dict()
        
        logger.info(f"[SESSION PROXY] Received request with cookies: {list(cookies.keys())}")
        
        # Make the request to Kratos
        response = requests.get(
            f"{KRATOS_PUBLIC_URL}/sessions/whoami",
            cookies=cookies,
            headers={
                'Accept': 'application/json',
                'Cookie': request.headers.get('Cookie', '')  # Forward the raw cookie header
            },
            verify=False  # For development with self-signed certs
        )
        
        logger.info(f"[SESSION PROXY] Kratos response status: {response.status_code}")
        
        # Return the same status and content
        resp = make_response(response.content, response.status_code)
        resp.headers['Content-Type'] = 'application/json'
        
        # Forward any set-cookie headers from Kratos
        for cookie in response.cookies:
            resp.set_cookie(
                cookie.name,
                cookie.value,
                domain=cookie.domain,
                path=cookie.path,
                secure=cookie.secure,
                httponly=cookie.get_nonstandard_attr('HttpOnly', False),
                samesite=cookie.get_nonstandard_attr('SameSite')
            )
        
        return resp
        
    except Exception as e:
        logger.error(f"[SESSION PROXY] Error proxying whoami: {e}")
        return jsonify({'error': 'Failed to validate session'}), 500


@session_bp.route('/api/session/logout', methods=['POST', 'DELETE'])
def session_logout():
    """
    Proxy logout request to Kratos
    """
    try:
        # Get logout flow first
        cookies = request.cookies.to_dict()
        
        # Initialize logout flow
        flow_response = requests.get(
            f"{KRATOS_PUBLIC_URL}/self-service/logout/browser",
            cookies=cookies,
            headers={'Cookie': request.headers.get('Cookie', '')},
            verify=False,
            allow_redirects=False
        )
        
        if flow_response.status_code == 200:
            flow_data = flow_response.json()
            logout_url = flow_data.get('logout_url')
            
            if logout_url:
                # Extract token from logout URL
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(logout_url)
                params = parse_qs(parsed.query)
                token = params.get('token', [None])[0]
                
                if token:
                    # Complete logout
                    logout_response = requests.get(
                        logout_url,
                        verify=False,
                        allow_redirects=False
                    )
                    
                    # Clear the session cookie
                    resp = jsonify({'success': True, 'message': 'Logged out successfully'})
                    resp.set_cookie('ory_kratos_session', '', expires=0, path='/', domain='localhost')
                    return resp
        
        return jsonify({'error': 'Failed to initialize logout'}), 500
        
    except Exception as e:
        logger.error(f"[SESSION PROXY] Error during logout: {e}")
        return jsonify({'error': 'Logout failed'}), 500