"""
Knowledge Service Proxy Routes
Proxies requests to the knowledge service with proper authentication
"""

from flask import Blueprint, request, jsonify, g
import requests
import logging
import os
from functools import wraps
from app.utils.decorators import require_auth
from app.middleware.api_key_middleware import api_key_optional
from app.utils.decorators import require_auth_or_api_key

knowledge_proxy_bp = Blueprint('knowledge_proxy', __name__)
logger = logging.getLogger(__name__)

# Knowledge service URL
KNOWLEDGE_SERVICE_URL = os.getenv('KNOWLEDGE_SERVICE_URL', 'http://sting-ce-knowledge:8090')

def proxy_request(path, method='GET', **kwargs):
    """
    Proxy a request to the knowledge service with authentication
    """
    try:
        # Check if using API key authentication
        if hasattr(g, 'api_key') and g.api_key:
            # Use API key for authentication
            session_token = f"api-key-{g.api_key.user_id}"
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
        elif hasattr(g, 'user') and g.user:
            # User is authenticated via session

            user = g.user
            user_id = user.id
            user_email = user.email

            # HYBRID AUTH: Get session token from Flask session first, then Kratos fallback
            from flask import session

            # Priority 1: Flask session for enhanced WebAuthn
            if session.get('auth_method') == 'enhanced_webauthn' and session.get('session_id'):
                session_token = f"flask-webauthn-{session.get('session_id')}"
            # Priority 2: Kratos session cookie fallback
            elif request.cookies.get('ory_kratos_session'):
                session_token = request.cookies.get('ory_kratos_session')
            # Priority 3: Generate session token from user ID
            else:
                session_token = f"flask-session-{user.id}"
        else:
            # No authentication - public access
            # We'll use the service API key to access knowledge service
            # but indicate this is a public request
            session_token = "public-access"
            user_id = "public"
            user_email = "public@sting.local"
        
        # Build the full URL
        url = f"{KNOWLEDGE_SERVICE_URL}/{path}"
        
        # Set up headers with authentication - try service API key first, then Bearer token
        headers = kwargs.get('headers', {})

        # Always use service API key for knowledge service (more reliable than session tokens)
        service_api_key = os.getenv('STING_SERVICE_API_KEY')
        if service_api_key:
            headers['X-API-Key'] = service_api_key
            logger.info(f"Using service API key for knowledge service authentication: {service_api_key[:10]}...")
        else:
            logger.warning("No service API key found - knowledge service access may fail")
            headers['Authorization'] = f"Bearer {session_token}"

        headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        # Forward the request
        logger.info(f"Proxying {method} request to {url}")
        logger.info(f"Headers being sent: {headers}")

        # Add timeout if not specified
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        # Make the request based on method
        if method == 'GET':
            # For GET requests, don't pass json parameter
            kwargs.pop('json', None)
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
        logger.info(f"Knowledge service response: {response.status_code}")
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            logger.error(f"Knowledge service returned {response.status_code}: {response.text}")
            logger.error(f"Request headers were: {headers}")
            try:
                return jsonify(response.json()), response.status_code
            except:
                # If response is not JSON, return a generic error
                return jsonify({'error': f'Knowledge service error: {response.text}'}), response.status_code
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proxying request to knowledge service: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503
    except Exception as e:
        logger.error(f"Unexpected error in proxy: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Proxy endpoints for honey jars
@knowledge_proxy_bp.route('/honey-jars', methods=['GET'])
def list_honey_jars():
    """List all honey jars - public endpoint that proxies to knowledge service"""
    # This endpoint is public but the knowledge service will filter results
    # based on the authentication status passed through
    page = request.args.get('page', 1)
    page_size = request.args.get('page_size', 20)

    # Call proxy_request which will use service API key to authenticate
    # with knowledge service
    return proxy_request(f'honey-jars?page={page}&page_size={page_size}')

@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_honey_jar(honey_jar_id):
    """Get a specific honey jar"""
    return proxy_request(f'honey-jars/{honey_jar_id}')

@knowledge_proxy_bp.route('/honey-jars', methods=['POST'])
@require_auth_or_api_key(['admin', 'write'])
def create_honey_jar():
    """Create a new honey jar"""
    return proxy_request('honey-jars', method='POST', json=request.get_json())

@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>', methods=['PUT'])
@require_auth_or_api_key(['admin', 'write'])
def update_honey_jar(honey_jar_id):
    """Update a honey jar"""
    return proxy_request(f'honey-jars/{honey_jar_id}', method='PUT', json=request.get_json())

@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>', methods=['DELETE'])
@require_auth
def delete_honey_jar(honey_jar_id):
    """Delete a honey jar"""
    return proxy_request(f'honey-jars/{honey_jar_id}', method='DELETE')

# Document endpoints
@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>/documents', methods=['GET'])
@require_auth
def list_documents(honey_jar_id):
    """List documents in a honey jar using direct database access"""
    try:
        from app.services.honey_jar_service import get_honey_jar_service
        from app.utils.database import get_db_session
        from flask import jsonify

        logger.info(f"📋 Fetching documents for honey jar: {honey_jar_id}")

        # Use database-direct approach to bypass broken knowledge service API
        honey_jar_service = get_honey_jar_service()

        with get_db_session() as db:
            documents = honey_jar_service.get_documents(honey_jar_id, db)

        logger.info(f"✅ Retrieved {len(documents)} documents for honey jar {honey_jar_id}")
        return jsonify({
            "success": True,
            "data": documents,
            "count": len(documents)
        })

    except Exception as e:
        logger.error(f"❌ Error fetching documents for honey jar {honey_jar_id}: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({
            "success": False,
            "error": f"Failed to fetch documents: {str(e)}",
            "data": []
        }), 500

@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>/documents', methods=['POST'])
@require_auth
def upload_documents(honey_jar_id):
    """Upload documents to a honey jar"""
    # For file uploads, we need special handling
    try:
        logger.info(f"Upload request received for honey jar {honey_jar_id}")
        logger.info(f"User: {g.user.email if g.user else 'Unknown'}")
        
        files = request.files.getlist('files')
        metadata = request.form.get('metadata', '{}')
        
        logger.info(f"Number of files: {len(files)}")
        for file in files:
            logger.info(f"File: {file.filename}, Size: {file.content_length if hasattr(file, 'content_length') else 'Unknown'}")
        
        # Prepare files for forwarding
        files_data = []
        for file in files:
            files_data.append(('files', (file.filename, file.stream, file.content_type)))
        
        # Make the request
        url = f"{KNOWLEDGE_SERVICE_URL}/honey-jars/{honey_jar_id}/documents"
        
        # Get auth token using same hybrid logic
        user = g.user
        from flask import session
        
        # HYBRID AUTH: Same logic as proxy_request function
        if session.get('auth_method') == 'enhanced_webauthn' and session.get('session_id'):
            session_token = f"flask-webauthn-{session.get('session_id')}"
        elif request.cookies.get('ory_kratos_session'):
            session_token = request.cookies.get('ory_kratos_session')
        else:
            session_token = f"flask-session-{user.id}"
        
        headers = {'Authorization': f"Bearer {session_token}"}
        data = {'metadata': metadata}
        
        response = requests.post(url, files=files_data, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            logger.error(f"Knowledge service upload failed: {response.status_code} - {response.text}")
            try:
                error_data = response.json()
                return jsonify(error_data), response.status_code
            except:
                # If response is not JSON, return a generic error
                return jsonify({
                    'error': 'Failed to upload documents',
                    'detail': f'Knowledge service returned status {response.status_code}'
                }), response.status_code
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({
            'error': 'Knowledge service unavailable',
            'detail': 'Unable to connect to the knowledge service. Please try again later.'
        }), 503
    except requests.exceptions.Timeout as e:
        logger.error(f"Knowledge service timeout: {e}")
        return jsonify({
            'error': 'Request timeout',
            'detail': 'The upload request timed out. Please try again with smaller files.'
        }), 504
    except Exception as e:
        logger.error(f"Error uploading documents: {e}", exc_info=True)
        return jsonify({'error': 'Failed to upload documents', 'detail': str(e)}), 500

# Document download endpoint
@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>/documents/<document_id>/download', methods=['GET'])
@require_auth
def download_document(honey_jar_id, document_id):
    """Download a specific document from a honey jar"""
    try:
        from app.services.honey_jar_service import get_honey_jar_service
        from app.utils.database import get_db_session
        from flask import send_file
        import os

        logger.info(f"📥 Download request for document {document_id} in honey jar {honey_jar_id}")

        honey_jar_service = get_honey_jar_service()

        with get_db_session() as db:
            # Get document info
            document = honey_jar_service.get_document(honey_jar_id, document_id, db)

            if not document:
                return jsonify({'error': 'Document not found'}), 404

            # Get file path
            file_path = document.get('file_path')
            if not file_path or not os.path.exists(file_path):
                logger.error(f"❌ File not found at path: {file_path}")
                return jsonify({'error': 'File not found on server'}), 404

            # Send file
            return send_file(
                file_path,
                as_attachment=True,
                download_name=document.get('filename', 'document')
            )
    except Exception as e:
        logger.error(f"❌ Error downloading document: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({'error': 'Failed to download document'}), 500

# Document preview endpoint
@knowledge_proxy_bp.route('/honey-jars/<honey_jar_id>/documents/<document_id>/preview', methods=['GET'])
@require_auth
def preview_document(honey_jar_id, document_id):
    """Preview a document (text/PDF content only)"""
    try:
        from app.services.honey_jar_service import get_honey_jar_service
        from app.utils.database import get_db_session
        import mimetypes

        logger.info(f"👁 Preview request for document {document_id} in honey jar {honey_jar_id}")

        honey_jar_service = get_honey_jar_service()

        with get_db_session() as db:
            # Get document content (first 10KB for preview)
            content = honey_jar_service.get_document_preview(honey_jar_id, document_id, db)

            if content is None:
                return jsonify({'error': 'Document not found or cannot be previewed'}), 404

            return jsonify({
                'success': True,
                'content': content,
                'document_id': document_id
            })
    except Exception as e:
        logger.error(f"❌ Error previewing document: {str(e)}")
        return jsonify({'error': 'Failed to preview document'}), 500

# Search endpoint
@knowledge_proxy_bp.route('/search', methods=['POST'])
@require_auth
def search():
    """Search across honey jars"""
    return proxy_request('search', method='POST', json=request.get_json())

# Bee context endpoint
@knowledge_proxy_bp.route('/bee/context', methods=['POST'])
@require_auth
def bee_context():
    """Get context for bee chatbot"""
    return proxy_request('bee/context', method='POST', json=request.get_json())


# Honey Jar semantic search endpoint (for Nectar Worker)
@knowledge_proxy_bp.route('/jars/<jar_id>/search', methods=['GET'])
@api_key_optional()
def search_honey_jar(jar_id):
    """
    Search a specific Honey Jar for relevant documents
    Used by Nectar Worker for bot context retrieval
    Supports both API key and session authentication
    """
    try:
        # Get search parameters
        query = request.args.get('query', '')
        limit = request.args.get('limit', 5, type=int)
        is_public = request.args.get('is_public', 'false').lower() == 'true'
        bot_owner_id = request.args.get('bot_owner_id')

        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400

        # Limit the number of results
        limit = min(limit, 20)  # Max 20 results

        # Proxy search request to knowledge service
        search_data = {
            'query': query,
            'honey_jar_ids': [jar_id],
            'limit': limit,
            'is_public': is_public,
            'bot_owner_id': bot_owner_id
        }

        logger.info(f"Searching Honey Jar {jar_id} with query: {query[:50]}...")

        # Use proxy_request to forward to knowledge service
        return proxy_request('search', method='POST', json=search_data)

    except Exception as e:
        logger.error(f"Error searching Honey Jar {jar_id}: {e}")
        return jsonify({'error': 'Failed to search Honey Jar'}), 500