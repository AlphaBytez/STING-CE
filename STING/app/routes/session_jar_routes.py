"""
Session Jar Routes
Proxy routes for session jar operations — temporary honey jars for chat file uploads.
Files flow through the existing knowledge service PII + vectorization pipeline.
"""

from flask import Blueprint, request, jsonify, g
import requests
import logging
import os
import json

from app.utils.decorators import require_auth

session_jar_bp = Blueprint('session_jar', __name__)
logger = logging.getLogger(__name__)

KNOWLEDGE_SERVICE_URL = os.getenv('KNOWLEDGE_SERVICE_URL', 'http://sting-ce-knowledge:8090')
SESSION_JAR_MAX_SIZE_BYTES = int(os.getenv('SESSION_JAR_MAX_SIZE_BYTES', str(50 * 1024 * 1024)))
SESSION_JAR_MAX_FILES = int(os.getenv('SESSION_JAR_MAX_FILES', '20'))
SESSION_JAR_ALLOWED_TYPES = os.getenv('SESSION_JAR_ALLOWED_TYPES', 'text/plain,text/markdown,text/html,application/pdf,application/json,application/vnd.openxmlformats-officedocument.wordprocessingml.document').split(',')


def _get_auth_headers():
    """Build authentication headers for knowledge service requests."""
    headers = {}
    service_api_key = os.getenv('STING_SERVICE_API_KEY')
    if service_api_key:
        headers['X-API-Key'] = service_api_key
    else:
        from flask import session
        if hasattr(g, 'user') and g.user:
            if session.get('auth_method') == 'enhanced_webauthn' and session.get('session_id'):
                headers['Authorization'] = f"Bearer flask-webauthn-{session.get('session_id')}"
            elif request.cookies.get('ory_kratos_session'):
                headers['Authorization'] = f"Bearer {request.cookies.get('ory_kratos_session')}"
            else:
                headers['Authorization'] = f"Bearer flask-session-{g.user.id}"
    return headers


def _get_user_email():
    """Get current user's email."""
    if hasattr(g, 'user') and g.user:
        return g.user.email
    return 'anonymous'


@session_jar_bp.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """
    Upload a file to a session jar. Creates the session jar on first upload.
    Expects multipart form data with 'file' and 'conversation_id'.
    """
    conversation_id = request.form.get('conversation_id')
    if not conversation_id:
        return jsonify({'error': 'conversation_id is required'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    if file.content_type and file.content_type not in SESSION_JAR_ALLOWED_TYPES:
        return jsonify({
            'error': f'File type not allowed: {file.content_type}',
            'allowed_types': SESSION_JAR_ALLOWED_TYPES
        }), 415

    headers = _get_auth_headers()
    user_email = _get_user_email()

    try:
        # Step 1: Get or create session jar
        get_resp = requests.get(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/by-conversation/{conversation_id}",
            headers={**headers, 'Content-Type': 'application/json'},
            timeout=10
        )

        if get_resp.status_code == 200:
            session_jar = get_resp.json()
            jar_id = session_jar['id']

            # Check file count limit
            doc_count = session_jar.get('stats', {}).get('document_count', 0)
            if doc_count >= SESSION_JAR_MAX_FILES:
                return jsonify({
                    'error': f'Session jar file limit reached ({SESSION_JAR_MAX_FILES} files)',
                    'current_count': doc_count
                }), 413
        else:
            # Create new session jar
            create_resp = requests.post(
                f"{KNOWLEDGE_SERVICE_URL}/session-jars",
                headers={**headers, 'Content-Type': 'application/json'},
                json={
                    'conversation_id': conversation_id,
                    'max_size_bytes': SESSION_JAR_MAX_SIZE_BYTES
                },
                timeout=10
            )
            if create_resp.status_code not in (200, 201):
                logger.error(f"Failed to create session jar: {create_resp.text}")
                return jsonify({'error': 'Failed to create session jar'}), 500
            session_jar = create_resp.json()
            jar_id = session_jar['id']

        # Step 2: Upload file to the session jar via knowledge service
        upload_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
        upload_resp = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/honey-jars/{jar_id}/documents/upload",
            headers=upload_headers,
            files={'file': (file.filename, file.stream, file.content_type)},
            data={'tags': json.dumps(['session-upload', 'chat-context'])},
            timeout=120
        )

        if upload_resp.status_code not in (200, 201):
            logger.error(f"Failed to upload file to session jar: {upload_resp.text}")
            error_detail = 'File upload failed'
            if upload_resp.status_code == 413:
                error_detail = 'Session jar size limit exceeded'
            return jsonify({'error': error_detail}), upload_resp.status_code

        upload_result = upload_resp.json()

        return jsonify({
            'success': True,
            'session_jar_id': jar_id,
            'conversation_id': conversation_id,
            'document': upload_result,
            'message': f'File "{file.filename}" uploaded and processing started'
        }), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503
    except Exception as e:
        logger.error(f"Session jar upload error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@session_jar_bp.route('/<conversation_id>', methods=['GET'])
@require_auth
def get_session_jar(conversation_id):
    """Get session jar status and file list for a conversation."""
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    try:
        resp = requests.get(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/by-conversation/{conversation_id}",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 404:
            return jsonify({'exists': False, 'conversation_id': conversation_id}), 200

        if resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch session jar'}), resp.status_code

        data = resp.json()
        data['exists'] = True
        return jsonify(data), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503


@session_jar_bp.route('/<conversation_id>/status', methods=['GET'])
@require_auth
def get_session_jar_status(conversation_id):
    """Get processing status of files in a session jar."""
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    try:
        resp = requests.get(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/by-conversation/{conversation_id}",
            headers=headers,
            timeout=10
        )

        if resp.status_code == 404:
            return jsonify({'exists': False, 'processing_complete': True}), 200

        if resp.status_code != 200:
            return jsonify({'error': 'Failed to fetch session jar'}), resp.status_code

        data = resp.json()
        documents = data.get('documents', [])

        processing = [d for d in documents if d.get('status') in ('pending', 'processing')]
        completed = [d for d in documents if d.get('status') == 'completed']
        failed = [d for d in documents if d.get('status') == 'failed']

        return jsonify({
            'exists': True,
            'session_jar_id': data.get('id'),
            'processing_complete': len(processing) == 0,
            'total_files': len(documents),
            'completed': len(completed),
            'processing': len(processing),
            'failed': len(failed),
            'documents': documents
        }), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503


@session_jar_bp.route('/<conversation_id>/promote', methods=['POST'])
@require_auth
def promote_session_jar(conversation_id):
    """Promote a session jar to a permanent honey jar with optional AI summary."""
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    body = request.get_json(silent=True) or {}
    jar_name = body.get('name')
    jar_description = body.get('description')

    try:
        # Get session jar ID
        get_resp = requests.get(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/by-conversation/{conversation_id}",
            headers=headers,
            timeout=10
        )
        if get_resp.status_code != 200:
            return jsonify({'error': 'No session jar found for this conversation'}), 404

        jar_id = get_resp.json()['id']

        # Generate AI conversation summary if enabled
        summary_document = None
        ai_summary_enabled = os.getenv('SESSION_JAR_AI_SUMMARY', 'true').lower() == 'true'
        if ai_summary_enabled and body.get('generate_summary', True):
            try:
                external_ai_url = os.getenv('EXTERNAL_AI_URL', 'http://external-ai:8091')
                summary_resp = requests.post(
                    f"{external_ai_url}/bee/summarize-conversation",
                    json={'conversation_id': conversation_id, 'user_id': g.user.id if hasattr(g, 'user') and g.user else 'unknown'},
                    timeout=60
                )
                if summary_resp.status_code == 200:
                    summary_document = summary_resp.json().get('summary', '')
                    logger.info(f"✅ Generated AI summary for session jar promotion")
                else:
                    logger.warning(f"AI summary generation returned {summary_resp.status_code}")
            except Exception as e:
                logger.warning(f"AI summary generation failed (non-blocking): {e}")

        # Promote the jar
        promote_resp = requests.post(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/{jar_id}/promote",
            headers=headers,
            json={
                'name': jar_name or f"Promoted: {conversation_id[:8]}",
                'description': jar_description or 'Promoted from chat session',
                'summary_document': summary_document
            },
            timeout=30
        )

        if promote_resp.status_code != 200:
            return jsonify({'error': 'Failed to promote session jar'}), promote_resp.status_code

        return jsonify(promote_resp.json()), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503


@session_jar_bp.route('/<conversation_id>', methods=['DELETE'])
@require_auth
def delete_session_jar(conversation_id):
    """Delete a session jar and all its data."""
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    try:
        resp = requests.delete(
            f"{KNOWLEDGE_SERVICE_URL}/session-jars/by-conversation/{conversation_id}",
            headers=headers,
            timeout=15
        )

        if resp.status_code == 200:
            return jsonify(resp.json()), 200
        else:
            return jsonify({'error': 'Failed to delete session jar'}), resp.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge service connection error: {e}")
        return jsonify({'error': 'Failed to connect to knowledge service'}), 503
