"""
File Management Routes for STING-CE
Handles file upload, download, and management endpoints.
"""

import os
import logging
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from io import BytesIO
from typing import Optional

from app.services.file_service import FileService, ProfileFileService, FileServiceError
from app.utils.kratos_client import whoami
from app.utils.decorators import require_auth, require_auth_method, require_dual_factor
from app.utils.audit_logger import AuditLogger
from app.models.audit_log_models import AuditSeverity

logger = logging.getLogger(__name__)

# Create blueprint
file_bp = Blueprint('files', __name__, url_prefix='/api/files')

# Initialize services lazily
file_service = None
profile_service = None

def get_file_service():
    """Get file service instance, initializing if needed."""
    global file_service
    if file_service is None:
        try:
            file_service = FileService()
        except Exception as e:
            logger.error(f"Failed to initialize FileService: {e}")
            raise FileServiceError(f"File service unavailable: {str(e)}")
    return file_service

def get_profile_service():
    """Get profile service instance, initializing if needed."""
    global profile_service
    if profile_service is None:
        try:
            profile_service = ProfileFileService()
        except Exception as e:
            logger.error(f"Failed to initialize ProfileFileService: {e}")
            raise FileServiceError(f"Profile service unavailable: {str(e)}")
    return profile_service

# Configuration
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB default

def get_current_user() -> Optional[str]:
    """Get current user ID from Flask or Kratos session (hybrid auth support)."""
    from flask import g, session
    
    # PRIORITY 1: Check Flask session first (for WebAuthn/Touch ID auth)
    if hasattr(g, 'user') and g.user:
        return g.user.kratos_id or str(g.user.id)
    
    # PRIORITY 2: Try Flask session directly if g.user not set
    if session.get('user_id') and session.get('auth_method') == 'enhanced_webauthn':
        try:
            from app.models.user_models import User
            user = User.query.get(session.get('user_id'))
            if user:
                return user.kratos_id or str(user.id)
        except Exception as e:
            logger.error(f"Error loading user from Flask session in get_current_user: {e}")
    
    # PRIORITY 3: Fall back to Kratos session
    session_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
    if not session_cookie:
        return None
    
    identity = whoami(session_cookie)
    if not identity:
        return None
    
    return identity.get('identity', {}).get('id')

@file_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    """Handle file too large errors."""
    return jsonify({
        'success': False,
        'error': 'File too large',
        'max_size': MAX_CONTENT_LENGTH
    }), 413

@file_bp.route('/upload', methods=['POST'])
@require_auth_method(['webauthn', 'totp', 'email'])  # Tier 2: Basic file operations
def upload_file():
    """
    Upload a file.
    
    Form data:
    - file: File to upload
    - file_type: File type category (optional)
    - metadata: JSON metadata (optional)
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get file type and metadata
        file_type = request.form.get('file_type', 'user_document')
        metadata_str = request.form.get('metadata', '{}')
        
        try:
            import json
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}
        
        # Read file data
        file_data = file.read()
        filename = secure_filename(file.filename)
        
        # Upload file
        result = get_file_service().upload_file(file_data, filename, file_type, user_id, metadata)

        if result['success']:
            # Audit log the successful file upload
            from flask import g
            if hasattr(g, 'user') and g.user:
                AuditLogger.log_security_event(
                    description=f"File '{filename}' uploaded successfully by {g.user.email}",
                    severity=AuditSeverity.MEDIUM,
                    user=g.user,
                    details={
                        'filename': filename,
                        'file_type': file_type,
                        'file_size': len(file_data),
                        'file_id': result.get('file_id')
                    }
                )

            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in file upload: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@file_bp.route('/<file_id>', methods=['GET'])
@require_auth
def download_file(file_id: str):
    """Download a file by ID."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Download file
        file_data = get_file_service().download_file(file_id, user_id)
        if not file_data:
            return jsonify({'error': 'File not found or access denied'}), 404
        
        # Create file-like object
        file_obj = BytesIO(file_data['data'])
        
        return send_file(
            file_obj,
            as_attachment=True,
            download_name=file_data['filename'],
            mimetype=file_data.get('mime_type', 'application/octet-stream')
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/<file_id>/metadata', methods=['GET'])
@require_auth
def get_file_metadata(file_id: str):
    """Get file metadata."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        metadata = get_file_service().get_file_metadata(file_id, user_id)
        if not metadata:
            return jsonify({'error': 'File not found or access denied'}), 404
        
        return jsonify({'success': True, 'data': metadata})
        
    except Exception as e:
        logger.error(f"Error getting metadata for file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/<file_id>', methods=['DELETE'])
@require_auth_method(['webauthn', 'totp'])  # Tier 3: Sensitive file deletion
def delete_file(file_id: str):
    """Delete a file."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        success = get_file_service().delete_file(file_id, user_id)
        if success:
            # Audit log the successful file deletion
            from flask import g
            if hasattr(g, 'user') and g.user:
                AuditLogger.log_security_event(
                    description=f"File '{file_id}' deleted by {g.user.email}",
                    severity=AuditSeverity.HIGH,
                    user=g.user,
                    details={
                        'file_id': file_id,
                        'action': 'delete_file'
                    }
                )

            return jsonify({'success': True, 'message': 'File deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'File not found or access denied'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/', methods=['GET'])
@require_auth
def list_files():
    """
    List user's files.
    
    Query parameters:
    - file_type: Filter by file type
    - limit: Maximum number of files (default: 50)
    - offset: Offset for pagination (default: 0)
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get query parameters
        file_type = request.args.get('file_type')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        offset = int(request.args.get('offset', 0))
        
        files = get_file_service().list_user_files(user_id, file_type, limit, offset)
        
        return jsonify({
            'success': True,
            'data': files,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'count': len(files)
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/<file_id>/share', methods=['POST'])
@require_auth
def share_file(file_id: str):
    """
    Share a file with another user.
    
    JSON body:
    - user_id: Target user ID
    - permission_type: Permission type ('read', 'write', 'delete')
    - expires_at: Optional expiration timestamp
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        target_user_id = data.get('user_id')
        permission_type = data.get('permission_type', 'read')
        expires_at_str = data.get('expires_at')
        
        if not target_user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        # Parse expiration date if provided
        expires_at = None
        if expires_at_str:
            from datetime import datetime
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid expires_at format'}), 400
        
        success = get_file_service().share_file(file_id, user_id, target_user_id, permission_type, expires_at)
        
        if success:
            return jsonify({'success': True, 'message': 'File shared successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to share file'}), 400
            
    except Exception as e:
        logger.error(f"Error sharing file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/<file_id>/revoke', methods=['POST'])
@require_auth
def revoke_file_access(file_id: str):
    """
    Revoke file access from a user.
    
    JSON body:
    - user_id: Target user ID
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        target_user_id = data.get('user_id')
        if not target_user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        success = get_file_service().revoke_file_access(file_id, user_id, target_user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Access revoked successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to revoke access'}), 400
            
    except Exception as e:
        logger.error(f"Error revoking access to file {file_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Profile-specific routes
@file_bp.route('/profile/picture', methods=['POST'])
@require_auth
def upload_profile_picture():
    """Upload a profile picture."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file data
        file_data = file.read()
        filename = secure_filename(file.filename)
        
        # Upload profile picture
        result = get_profile_service().upload_profile_picture(file_data, filename, user_id)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error uploading profile picture: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/profile/picture', methods=['GET'])
@require_auth
def get_profile_picture():
    """Get user's profile picture."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        file_data = get_profile_service().get_profile_picture(user_id)
        if not file_data:
            return jsonify({'error': 'No profile picture found'}), 404
        
        # Create file-like object
        file_obj = BytesIO(file_data['data'])
        
        return send_file(
            file_obj,
            mimetype=file_data.get('mime_type', 'image/jpeg'),
            as_attachment=False
        )
        
    except Exception as e:
        logger.error(f"Error getting profile picture: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/bee/upload-temp', methods=['POST'])
@require_auth
def bee_upload_temp():
    """
    Upload a temporary file for Bee Chat analysis.
    Files are stored temporarily (48 hours) and encrypted with user's key.
    
    Form data:
    - file: File to upload
    - session_id: Chat session ID (optional)
    - analysis_type: Type of analysis requested (optional)
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get optional parameters
        session_id = request.form.get('session_id', 'default')
        analysis_type = request.form.get('analysis_type', 'general')
        
        # Create metadata for temporary file
        metadata = {
            'session_id': session_id,
            'analysis_type': analysis_type,
            'uploaded_for': 'bee_chat',
            'retention_hours': 48,
            'auto_delete': True
        }
        
        # Read file data
        file_data = file.read()
        filename = secure_filename(file.filename)
        
        # Upload as temporary file
        result = get_file_service().upload_file(file_data, filename, 'temporary', user_id, metadata)
        
        if result['success']:
            # Extract text content for immediate analysis
            try:
                file_content = get_file_service().extract_text_content(result['file_id'], user_id)
                result['extracted_text'] = file_content.get('text', '')
                result['extraction_success'] = file_content.get('success', False)
            except Exception as e:
                logger.warning(f"Failed to extract text from uploaded file: {e}")
                result['extracted_text'] = ''
                result['extraction_success'] = False
            
            # Add Bee Chat specific response fields
            result.update({
                'upload_type': 'temporary',
                'retention_hours': 48,
                'available_until': result.get('expires_at'),
                'ready_for_analysis': True,
                'analysis_instructions': f"File '{filename}' has been uploaded and is ready for analysis."
            })
            
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error in Bee Chat temp upload: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process file upload'
        }), 500

@file_bp.route('/bee/sessions/<session_id>/files', methods=['GET'])
@require_auth
def list_bee_session_files(session_id: str):
    """List temporary files for a specific Bee Chat session."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get files for this session
        files = get_file_service().list_user_files(
            user_id, 
            file_type='temporary',
            session_id=session_id
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'files': files,
            'count': len(files)
        })
        
    except Exception as e:
        logger.error(f"Error listing Bee session files: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/profile/picture', methods=['PUT'])
@require_auth
def update_profile_picture():
    """Update profile picture."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file data
        file_data = file.read()
        filename = secure_filename(file.filename)
        
        # Update profile picture
        result = get_profile_service().update_profile_picture(file_data, filename, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error updating profile picture: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Honey Reserve Management Endpoints
@file_bp.route('/honey-reserve/usage', methods=['GET'])
@require_auth
def get_honey_reserve_usage():
    """Get current Honey Reserve usage for the user."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        usage_data = get_file_service().get_honey_reserve_usage(user_id)
        
        return jsonify({
            'success': True,
            'data': usage_data
        })
        
    except Exception as e:
        logger.error(f"Error getting Honey Reserve usage: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/honey-reserve/quota', methods=['GET'])
@require_auth
def get_honey_reserve_quota():
    """Get user's Honey Reserve quota information."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        quota_info = get_file_service().get_user_quota(user_id)
        
        return jsonify({
            'success': True,
            'data': quota_info
        })
        
    except Exception as e:
        logger.error(f"Error getting Honey Reserve quota: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/honey-reserve/cleanup', methods=['POST'])
@require_auth
def cleanup_honey_reserve():
    """Manually cleanup expired temporary files for the user."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        cleanup_result = get_file_service().cleanup_expired_files(user_id)
        
        return jsonify({
            'success': True,
            'data': cleanup_result
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up Honey Reserve: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/honey-reserve/files', methods=['DELETE'])
@require_dual_factor(['webauthn', 'totp'], ['email'])  # Tier 4: Critical bulk deletion
def bulk_delete_files():
    """
    Bulk delete files from Honey Reserve.
    
    JSON body:
    - file_ids: List of file IDs to delete
    """
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data or 'file_ids' not in data:
            return jsonify({'error': 'file_ids array required'}), 400
        
        file_ids = data['file_ids']
        if not isinstance(file_ids, list):
            return jsonify({'error': 'file_ids must be an array'}), 400
        
        delete_results = get_file_service().bulk_delete_files(file_ids, user_id)
        
        return jsonify({
            'success': True,
            'data': delete_results
        })
        
    except Exception as e:
        logger.error(f"Error bulk deleting files: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/honey-reserve/storage-breakdown', methods=['GET'])
@require_auth
def get_storage_breakdown():
    """Get detailed storage breakdown by category."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        breakdown = get_file_service().get_storage_breakdown(user_id)
        
        return jsonify({
            'success': True,
            'data': breakdown
        })
        
    except Exception as e:
        logger.error(f"Error getting storage breakdown: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Encryption Management Endpoints
@file_bp.route('/encryption/status', methods=['GET'])
@require_auth
def get_encryption_status():
    """Get encryption service status and statistics."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        from app.services.honey_reserve_encryption import get_encryption_service
        encryption_service = get_encryption_service()
        
        # Get cache statistics
        cache_stats = encryption_service.get_cache_stats()
        
        # Check if encryption is enabled
        honey_reserve_encryption_enabled = os.environ.get('HONEY_RESERVE_ENCRYPT_AT_REST', 'true').lower() == 'true'
        
        return jsonify({
            'success': True,
            'data': {
                'encryption_enabled': honey_reserve_encryption_enabled,
                'algorithm': 'AES-256-GCM',
                'key_derivation': 'HKDF-SHA256',
                'cache_stats': cache_stats,
                'supported_file_types': [
                    'temporary', 'honey_jar_document', 'user_document',
                    'profile_picture', 'report', 'export'
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting encryption status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@file_bp.route('/encryption/rotate-key', methods=['POST'])
@require_auth
def rotate_encryption_key():
    """Rotate user's encryption key (clears cache to force re-derivation)."""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        from app.services.honey_reserve_encryption import get_encryption_service
        encryption_service = get_encryption_service()
        
        success = encryption_service.rotate_user_key(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Encryption key rotated successfully',
                'user_id': user_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to rotate encryption key'
            }), 500
        
    except Exception as e:
        logger.error(f"Error rotating encryption key: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@file_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for file service."""
    try:
        # Test Vault connectivity
        vault_healthy = get_file_service().vault_client.vault_manager.client.sys.is_initialized()
        
        # Test encryption service
        encryption_healthy = True
        encryption_stats = None
        try:
            from app.services.honey_reserve_encryption import get_encryption_service
            encryption_service = get_encryption_service()
            encryption_stats = encryption_service.get_cache_stats()
        except Exception as e:
            logger.warning(f"Encryption service check failed: {e}")
            encryption_healthy = False
        
        overall_healthy = vault_healthy and encryption_healthy
        
        response_data = {
            'status': 'healthy' if overall_healthy else 'degraded',
            'vault_connected': vault_healthy,
            'encryption_service': encryption_healthy,
            'timestamp': os.path.getmtime(__file__)
        }
        
        if encryption_stats:
            response_data['encryption_stats'] = encryption_stats
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500