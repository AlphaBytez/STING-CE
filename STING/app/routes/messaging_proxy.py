"""
Messaging Service Proxy Routes
Proxies requests to the messaging service with proper authentication
"""

from flask import Blueprint, request, jsonify, g
import requests
import logging
import os
from app.utils.decorators import require_auth

messaging_proxy_bp = Blueprint('messaging_proxy', __name__)
logger = logging.getLogger(__name__)

# Messaging service URL
MESSAGING_SERVICE_URL = os.getenv('MESSAGING_SERVICE_URL', 'http://sting-ce-messaging:8889')

def proxy_messaging_request(path, method='GET', **kwargs):
    """
    Proxy a request to the messaging service with authentication
    """
    try:
        # Get user context for messaging service
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401

        user = g.user

        # Build the full URL
        url = f"{MESSAGING_SERVICE_URL}/{path}"

        # Set up headers with user context
        headers = kwargs.get('headers', {})
        headers.update({
            'Content-Type': 'application/json',
            'X-User-ID': str(user.id),
            'X-User-Email': user.email,
            'X-User-Role': getattr(user, 'role', 'user')
        })
        kwargs['headers'] = headers

        # Add timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30

        # Forward the request
        logger.info(f"Proxying {method} request to {url}")

        # Make the request based on method
        if method == 'GET':
            response = requests.get(url, **kwargs)
        elif method == 'POST':
            response = requests.post(url, **kwargs)
        elif method == 'PUT':
            response = requests.put(url, **kwargs)
        elif method == 'DELETE':
            response = requests.delete(url, **kwargs)
        else:
            return jsonify({'error': 'Unsupported method'}), 405

        # Return the response
        logger.info(f"Messaging service response: {response.status_code}")
        if response.status_code < 300:
            try:
                return jsonify(response.json()), response.status_code
            except:
                return jsonify({'result': response.text}), response.status_code
        else:
            logger.error(f"Messaging service returned {response.status_code}: {response.text}")
            try:
                return jsonify(response.json()), response.status_code
            except:
                return jsonify({'error': f'Messaging service error: {response.text}'}), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying request to messaging service: {e}")
        return jsonify({'error': 'Failed to connect to messaging service'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in messaging proxy: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Chat conversation endpoints
@messaging_proxy_bp.route('/chat/conversations/<conversation_id>/messages', methods=['GET'])
@require_auth
def get_conversation_messages(conversation_id):
    """Get messages in a conversation"""
    limit = request.args.get('limit', 100)
    offset = request.args.get('offset', 0)
    return proxy_messaging_request(f'chat/conversations/{conversation_id}/messages?limit={limit}&offset={offset}')

@messaging_proxy_bp.route('/chat/conversations/<conversation_id>/messages', methods=['POST'])
@require_auth
def save_conversation_message(conversation_id):
    """Save a message to a conversation"""
    return proxy_messaging_request(f'chat/conversations/{conversation_id}/messages', method='POST', json=request.get_json())

@messaging_proxy_bp.route('/chat/conversations', methods=['GET'])
@require_auth
def list_conversations():
    """List user's conversations"""
    return proxy_messaging_request('chat/conversations')

@messaging_proxy_bp.route('/chat/conversations', methods=['POST'])
@require_auth
def create_conversation():
    """Create a new conversation"""
    return proxy_messaging_request('chat/conversations', method='POST', json=request.get_json())

# Health endpoint (public)
@messaging_proxy_bp.route('/health', methods=['GET'])
def messaging_health():
    """Check messaging service health"""
    try:
        response = requests.get(f"{MESSAGING_SERVICE_URL}/health", timeout=5)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': 'Messaging service unavailable'}), 503