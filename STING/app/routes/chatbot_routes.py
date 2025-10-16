"""
Chatbot (Bee) routes for STING application
Proxy requests to the chatbot service
"""

from flask import Blueprint, request, jsonify, g
from app.utils.decorators import require_auth_or_api_key
import requests
import logging
import os
import json

chatbot_bp = Blueprint('chatbot', __name__)
logger = logging.getLogger(__name__)

# Chatbot service URL
CHATBOT_SERVICE_URL = os.getenv('CHATBOT_SERVICE_URL', 'http://chatbot:8888')
EXTERNAL_AI_SERVICE_URL = os.getenv('EXTERNAL_AI_SERVICE_URL', 'http://external-ai:8091')

@chatbot_bp.route('/api/bee/chat', methods=['POST'])
@require_auth_or_api_key(['admin', 'write', 'read'])
def chat_with_bee():
    """
    Chat endpoint for Bee assistant
    Requires authentication (session or API key)
    """
    try:
        
        # Get request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        context = data.get('context', {})
        
        # Add user information to context (handle both session and API key auth)
        if hasattr(g, 'api_key') and g.api_key:
            # API key authentication
            logger.info(f"🔑 API Key Debug: Using API key {g.api_key.name} with user_id: {g.api_key.user_id}")
            context['user_id'] = str(g.api_key.user_id)
            context['user_email'] = str(g.api_key.user_email) 
            context['user_role'] = 'admin' if 'admin' in g.api_key.scopes else 'user'
            context['auth_type'] = 'api_key'
        elif hasattr(g, 'user') and g.user:
            # Session authentication
            context['user_id'] = str(g.user.id)
            context['user_email'] = g.user.email
            context['user_role'] = str(g.user.role)
            context['auth_type'] = 'session'
        else:
            # Fallback for API-only usage
            context['user_id'] = data.get('user_id', 'api_user')
            context['user_email'] = 'api@sting.local'
            context['user_role'] = 'user'
            context['auth_type'] = 'fallback'
        
        # Prepare request for chatbot service
        # If authenticated via API key or session, bypass Bee's auth check
        chat_request = {
            'message': message,
            'conversation_id': conversation_id,
            'context': context,
            'user_id': context['user_id'],
            'require_auth': False  # Auth already validated by Flask decorator
        }
        
        # Try external AI service first (modern stack)
        try:
            # Determine user identifier for logging
            user_identifier = context.get('user_email', context.get('user_id', 'unknown'))
            logger.info(f"Sending chat request to external AI service for user {user_identifier}")
            
            # Get session token if available
            auth_headers = {}
            if hasattr(g, 'session_token'):
                auth_headers['Authorization'] = f'Bearer {g.session_token}'
            
            response = requests.post(
                f"{EXTERNAL_AI_SERVICE_URL}/bee/chat",
                json=chat_request,
                headers=auth_headers,
                timeout=30
            )

            if response.status_code == 200:
                # Parse JSON with lenient mode to handle escape sequences from LLM responses (e.g., <think> tags)
                response_data = json.loads(response.text, strict=False)
                return jsonify(response_data)
            else:
                logger.warning(f"External AI service returned {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"External AI service unavailable: {e}")
        
        # Fallback to direct chatbot service
        try:
            logger.info("Falling back to direct chatbot service")
            
            response = requests.post(
                f"{CHATBOT_SERVICE_URL}/chat",
                json=chat_request,
                timeout=30
            )
            
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                logger.error(f"Chatbot service returned {response.status_code}: {response.text}")
                return jsonify({
                    'error': 'Chat service temporarily unavailable',
                    'details': response.text
                }), response.status_code
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Chatbot service error: {e}")
            return jsonify({
                'error': 'Chat service connection failed',
                'details': str(e)
            }), 503
            
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@chatbot_bp.route('/api/bee/conversations', methods=['GET'])
def get_conversations():
    """
    Get user's conversation history
    """
    try:
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Forward request to chatbot service
        response = requests.get(
            f"{CHATBOT_SERVICE_URL}/conversations/{g.user.id}",
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch conversations'}), response.status_code
            
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@chatbot_bp.route('/api/bee/health', methods=['GET'])
def chatbot_health():
    """
    Check chatbot service health
    """
    try:
        # Check external AI service
        external_ai_healthy = False
        try:
            response = requests.get(f"{EXTERNAL_AI_SERVICE_URL}/health", timeout=5)
            external_ai_healthy = response.status_code == 200
        except:
            pass
        
        # Check direct chatbot service
        chatbot_healthy = False
        try:
            response = requests.get(f"{CHATBOT_SERVICE_URL}/health", timeout=5)
            chatbot_healthy = response.status_code == 200
        except:
            pass
        
        return jsonify({
            'status': 'healthy' if (external_ai_healthy or chatbot_healthy) else 'unhealthy',
            'services': {
                'external_ai': external_ai_healthy,
                'chatbot': chatbot_healthy
            }
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500