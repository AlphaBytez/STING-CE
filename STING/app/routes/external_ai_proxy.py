"""
External AI service proxy routes
Forwards requests to the external-ai service container
"""

from flask import Blueprint, request, jsonify, g
import requests
import logging
import os
import json
from datetime import datetime
from app.utils.decorators import require_auth_or_api_key
from app.services.request_classifier import classify_request, format_classification_message
from app.services.report_service import get_report_service

external_ai_proxy_bp = Blueprint('external_ai_proxy', __name__)
logger = logging.getLogger(__name__)

# External AI service URL
EXTERNAL_AI_SERVICE_URL = os.getenv('EXTERNAL_AI_SERVICE_URL', 'http://external-ai:8091')

@external_ai_proxy_bp.route('/api/external-ai/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@require_auth_or_api_key(['admin', 'write', 'read'])
def proxy_external_ai(path):
    """
    Proxy all requests to the external AI service
    With intelligent request classification for Bee chat
    """
    try:
        # INTERCEPT: Classify Bee chat requests before proxying
        if path == 'bee/chat' and request.method == 'POST':
            try:
                data = request.get_json()
                if data and 'message' in data:
                    message = data.get('message')

                    # Get user context
                    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else 'unknown'

                    # Classify the request
                    classification, metadata = classify_request(
                        prompt=message,
                        user_request=message,
                        max_chat_tokens=2000
                    )

                    logger.info(
                        f"📊 Request classification for {user_id}: "
                        f"{metadata['total_estimated_tokens']} tokens → {classification}"
                    )

                    if metadata.get('reasoning'):
                        logger.debug(f"Classification reasoning: {', '.join(metadata['reasoning'][:3])}")

                    # If classified as REPORT, route to report generation
                    if classification == "report":
                        logger.info(f"🔀 Routing to report generation ({metadata['total_estimated_tokens']} tokens)")

                        report_service = get_report_service()
                        report_result = report_service.create_bee_service_report(
                            user_id=user_id,
                            user_message=message,
                            conversation_id=data.get('conversation_id'),
                            honey_jar_id=data.get('honey_jar_id'),
                            context={}
                        )

                        if not report_result['success']:
                            logger.error(f"Report creation failed: {report_result.get('error')}")
                            # Fall through to normal chat if report creation fails
                        else:
                            # Return report response
                            bee_response = format_classification_message(classification, metadata)
                            bee_response += f"\n\n**Report ID:** #{report_result['report_id']}"

                            if report_result.get('queue_position'):
                                bee_response += f"\n**Queue Position:** #{report_result['queue_position']}"

                            if report_result.get('estimated_completion'):
                                bee_response += f"\n**Estimated Completion:** {report_result['estimated_completion']}"

                            return jsonify({
                                'response': bee_response,
                                'conversation_id': data.get('conversation_id'),
                                'report_generated': True,
                                'report_metadata': {
                                    'report_id': report_result['report_id'],
                                    'classification': classification,
                                    'token_count': metadata['total_estimated_tokens'],
                                    'reasoning': metadata.get('reasoning', [])[:3],
                                    'word_count_requested': metadata.get('word_count_requested'),
                                    'queue_position': report_result.get('queue_position'),
                                    'estimated_completion': report_result.get('estimated_completion')
                                },
                                'metadata': metadata,
                                'timestamp': datetime.now().isoformat()
                            }), 200
                    else:
                        logger.info(f"💬 Processing as chat ({metadata['total_estimated_tokens']} tokens)")
                        # Fall through to normal proxying

            except Exception as classification_error:
                logger.warning(f"Classification failed: {classification_error}, proceeding with chat")
                # Fall through to normal proxying

        # Build the target URL
        target_url = f"{EXTERNAL_AI_SERVICE_URL}/{path}"
        
        # Get request headers and remove hop-by-hop headers
        headers = {key: value for key, value in request.headers if key.lower() not in [
            'host', 'connection', 'keep-alive', 'proxy-authenticate', 
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]}
        
        # Add authentication if available
        if hasattr(g, 'session_token'):
            headers['Authorization'] = f'Bearer {g.session_token}'
        elif hasattr(g, 'user') and g.user:
            headers['X-User-Id'] = str(g.user.id)
            headers['X-User-Email'] = g.user.email
            headers['X-User-Role'] = g.user.role
        
        # Forward the request
        logger.debug(f"Proxying {request.method} request to {target_url}")
        
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            allow_redirects=False,
            timeout=90  # Increased for AI inference (models can take 30-60s)
        )
        
        # Create response with same status code and headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = {k: v for k, v in response.headers.items() if k.lower() not in excluded_headers}
        
        return response.content, response.status_code, headers
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout proxying request to external AI service: {path}")
        return jsonify({'error': 'External AI service timeout'}), 504
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error proxying to external AI service: {path}")
        return jsonify({'error': 'External AI service unavailable'}), 503
        
    except Exception as e:
        logger.error(f"Error proxying to external AI service: {e}")
        return jsonify({'error': 'Internal proxy error'}), 500