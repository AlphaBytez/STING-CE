"""
Profile API - REST endpoints for profile management.
"""

import logging
from flask import Blueprint, request, jsonify, send_file, current_app, g
from werkzeug.utils import secure_filename
from io import BytesIO

logger = logging.getLogger(__name__)

# Create blueprint
profile_bp = Blueprint('profile', __name__)

def get_profile_manager():
    """Get profile manager from app context."""
    return current_app.profile_manager

def get_profile_auth():
    """Get profile auth from app context."""
    return current_app.profile_auth

@profile_bp.route('/', methods=['GET'])
def get_current_user_profile():
    """Get current user's profile."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    manager = get_profile_manager()
    profile = manager.get_profile(user['id'])
    
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    return jsonify({
        'success': True,
        'profile': profile
    })

@profile_bp.route('/', methods=['POST'])
def create_current_user_profile():
    """Create current user's profile."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    manager = get_profile_manager()
    result = manager.create_profile(user['id'], data)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@profile_bp.route('/', methods=['PUT'])
def update_current_user_profile():
    """Update current user's profile."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON data required'}), 400
    
    manager = get_profile_manager()
    result = manager.update_profile(user['id'], data)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@profile_bp.route('/<user_id>', methods=['GET'])
def get_user_profile(user_id: str):
    """Get user profile by ID."""
    auth = get_profile_auth()
    
    # Require authentication
    current_user = auth.get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    manager = get_profile_manager()
    profile = manager.get_profile(user_id)
    
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    # Check if user can view this profile
    can_view_private = (current_user['id'] == user_id or 
                       current_user.get('traits', {}).get('role') in ['admin', 'moderator'])
    
    if not can_view_private:
        # Return public profile only
        public_fields = [
            'id', 'user_id', 'display_name', 'first_name', 'last_name', 
            'full_name', 'bio', 'location', 'website', 'profile_picture_file_id',
            'profile_completion', 'created_at'
        ]
        profile = {k: v for k, v in profile.items() if k in public_fields}
    
    return jsonify({
        'success': True,
        'profile': profile
    })

@profile_bp.route('/picture', methods=['POST'])
def upload_profile_picture():
    """Upload profile picture for current user."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Read file data
    file_data = file.read()
    filename = secure_filename(file.filename)
    
    manager = get_profile_manager()
    result = manager.upload_profile_picture(user['id'], file_data, filename)
    
    if result['success']:
        return jsonify(result), 201
    else:
        return jsonify(result), 400

@profile_bp.route('/picture', methods=['GET'])
def get_current_user_profile_picture():
    """Get current user's profile picture."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    manager = get_profile_manager()
    file_data = manager.get_profile_picture(user['id'])
    
    if not file_data:
        return jsonify({'error': 'No profile picture found'}), 404
    
    # Create file-like object
    file_obj = BytesIO(file_data['data'])
    
    return send_file(
        file_obj,
        mimetype=file_data.get('mime_type', 'image/jpeg'),
        as_attachment=False
    )

@profile_bp.route('/<user_id>/picture', methods=['GET'])
def get_user_profile_picture(user_id: str):
    """Get user's profile picture by ID."""
    auth = get_profile_auth()
    
    # Require authentication
    current_user = auth.get_current_user()
    if not current_user:
        return jsonify({'error': 'Authentication required'}), 401
    
    manager = get_profile_manager()
    
    # Check if profile exists and is accessible
    profile = manager.get_profile(user_id)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    file_data = manager.get_profile_picture(user_id)
    if not file_data:
        return jsonify({'error': 'No profile picture found'}), 404
    
    # Create file-like object
    file_obj = BytesIO(file_data['data'])
    
    return send_file(
        file_obj,
        mimetype=file_data.get('mime_type', 'image/jpeg'),
        as_attachment=False
    )

@profile_bp.route('/search', methods=['GET'])
def search_profiles():
    """Search profiles."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Search query required'}), 400
    
    limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 results
    
    manager = get_profile_manager()
    profiles = manager.search_profiles(query, limit)
    
    return jsonify({
        'success': True,
        'profiles': profiles,
        'query': query,
        'count': len(profiles)
    })

@profile_bp.route('/', methods=['DELETE'])
def delete_current_user_profile():
    """Delete current user's profile."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    manager = get_profile_manager()
    result = manager.delete_profile(user['id'])
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

@profile_bp.route('/stats', methods=['GET'])
def get_profile_stats():
    """Get profile statistics (admin only)."""
    auth = get_profile_auth()
    
    # Require authentication
    user = auth.get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Check admin role
    user_role = user.get('traits', {}).get('role', 'user')
    if user_role not in ['admin', 'superuser']:
        return jsonify({'error': 'Admin access required'}), 403
    
    # TODO: Implement profile statistics
    # This would include total profiles, completion rates, etc.
    
    return jsonify({
        'success': True,
        'stats': {
            'total_profiles': 0,
            'complete_profiles': 0,
            'partial_profiles': 0,
            'incomplete_profiles': 0
        }
    })

# Error handlers
@profile_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404

@profile_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@profile_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large errors."""
    return jsonify({'error': 'File too large'}), 413