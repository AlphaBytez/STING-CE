from flask import Blueprint, request, jsonify, g, session
from flask_cors import CORS
from app.models.api_key_models import ApiKey, ApiKeyUsage
from app.utils.decorators import require_auth_or_api_key, require_aal2_or_api_key, require_auth_method, require_dual_factor
from app.utils.audit_logger import AuditLogger
from app.middleware.api_key_middleware import api_key_required, validate_api_key_format
from app import db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
api_key_bp = Blueprint('api_keys', __name__, url_prefix='/api/keys')
CORS(api_key_bp, supports_credentials=True)

@api_key_bp.route('/auth-check', methods=['GET'])
@require_auth_method(['webauthn', 'totp'])  # Pre-check authentication requirements
def check_api_key_auth():
    """
    Pre-check if user can create/manage API keys
    This endpoint has the same auth requirements as API key operations
    but doesn't actually do anything - just validates authentication
    """
    return jsonify({
        'auth_status': 'authorized',
        'message': 'User can create/manage API keys',
        'methods_verified': getattr(g, 'verified_methods', [])
    })

@api_key_bp.route('', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])  # AAL1 sufficient - viewing existing keys is low risk
def list_api_keys():
    """List all API keys for the current user"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
            user_email = g.user.email
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')
            user_email = session.get('user_email')

        if not user_id or not user_email:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Query API keys for the current user
        query = ApiKey.query.filter_by(user_id=user_id)
        
        # Apply filters
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        if active_only:
            query = query.filter_by(is_active=True)
        
        # Order by creation date (newest first)
        query = query.order_by(ApiKey.created_at.desc())
        
        # Paginate
        api_keys = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'api_keys': [key.to_dict() for key in api_keys.items],
            'pagination': {
                'page': page,
                'pages': api_keys.pages,
                'per_page': per_page,
                'total': api_keys.total,
                'has_next': api_keys.has_next,
                'has_prev': api_keys.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        return jsonify({'error': 'Failed to list API keys'}), 500

@api_key_bp.route('', methods=['POST'])
@require_aal2_or_api_key(['admin', 'write'])  # AAL2 required for session auth, or API key with proper scopes
def create_api_key():
    """Create a new API key"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
            user_email = g.user.email
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')
            user_email = session.get('user_email')

        if not user_id or not user_email:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({
                'error': 'API key name is required',
                'type': 'validation_error'
            }), 400

        if len(name) > 255:
            return jsonify({
                'error': 'API key name must be less than 255 characters',
                'type': 'validation_error'
            }), 400

        # Additional name validation
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            return jsonify({
                'error': 'API key name contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and periods.',
                'type': 'validation_error'
            }), 400
        
        # Check if name already exists for this user
        existing = ApiKey.query.filter_by(user_id=user_id, name=name).first()
        if existing:
            return jsonify({'error': 'An API key with this name already exists'}), 400
        
        # Validate scopes
        scopes = data.get('scopes', ['read'])
        valid_scopes = ['read', 'write', 'admin']
        if not isinstance(scopes, list) or not all(scope in valid_scopes for scope in scopes):
            return jsonify({
                'error': 'Invalid scopes',
                'valid_scopes': valid_scopes
            }), 400
        
        # Validate permissions
        permissions = data.get('permissions', {})
        if permissions and not isinstance(permissions, dict):
            return jsonify({'error': 'Permissions must be a dictionary'}), 400
        
        # Validate expiration
        expires_in_days = data.get('expires_in_days')
        if expires_in_days is not None:
            if not isinstance(expires_in_days, (int, float)) or expires_in_days <= 0:
                return jsonify({'error': 'expires_in_days must be a positive number'}), 400
            if expires_in_days > 365:
                return jsonify({'error': 'Maximum expiration is 365 days'}), 400
        
        # Check user's current API key count (limit to 10 per user)
        current_count = ApiKey.query.filter_by(user_id=user_id, is_active=True).count()
        if current_count >= 10:
            return jsonify({
                'error': 'Maximum API key limit reached',
                'message': 'You can have at most 10 active API keys. Please delete unused keys first.'
            }), 400
        
        # Create the API key
        api_key, secret = ApiKey.generate_key(
            user_id=user_id,
            user_email=user_email,
            name=name,
            scopes=scopes,
            permissions=permissions,
            expires_in_days=expires_in_days,
            description=data.get('description', '').strip() or None
        )
        
        # Set rate limit if provided
        rate_limit = data.get('rate_limit_per_minute', 60)
        if isinstance(rate_limit, int) and 1 <= rate_limit <= 1000:
            api_key.rate_limit_per_minute = rate_limit
        
        # Save to database
        db.session.add(api_key)
        db.session.commit()
        
        logger.info(f"Created API key '{name}' for user {user_email}")

        # Audit log the API key creation
        AuditLogger.log_api_key_event(
            action='create',
            api_key_name=name,
            scopes=scopes,
            success=True
        )

        # Return the API key details (including the secret - this is the only time it's returned)
        response_data = api_key.to_dict()
        response_data['secret'] = secret  # Only returned once at creation
        response_data['warning'] = 'Store this secret key safely. It will not be shown again.'

        return jsonify(response_data), 201
        
    except ValueError as e:
        # Handle validation errors specifically
        logger.warning(f"Validation error creating API key: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Validation error',
            'message': str(e),
            'type': 'validation_error'
        }), 400
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Unexpected error creating API key: {str(e)}", exc_info=True)
        db.session.rollback()

        # Provide a more detailed error message while being secure
        error_message = "Failed to create API key"
        if "database" in str(e).lower():
            error_message = "Database error while creating API key"
        elif "connection" in str(e).lower():
            error_message = "Connection error while creating API key"

        return jsonify({
            'error': error_message,
            'message': 'Please try again or contact support if the problem persists',
            'type': 'server_error'
        }), 500

@api_key_bp.route('/<key_id>', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_api_key(key_id):
    """Get details of a specific API key"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Find the API key
        api_key = ApiKey.query.filter_by(key_id=key_id, user_id=user_id).first()
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Get recent usage statistics
        recent_usage = ApiKeyUsage.query.filter(
            ApiKeyUsage.api_key_id == api_key.id,
            ApiKeyUsage.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        response_data = api_key.to_dict()
        response_data['recent_usage_30_days'] = recent_usage
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting API key: {str(e)}")
        return jsonify({'error': 'Failed to get API key'}), 500

@api_key_bp.route('/<key_id>', methods=['PUT'])
@require_auth_method(['webauthn', 'totp'])  # Requires WebAuthn OR TOTP authentication method
def update_api_key(key_id):
    """Update an API key (name, scopes, permissions, etc.)"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Find the API key
        api_key = ApiKey.query.filter_by(key_id=key_id, user_id=user_id).first()
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        # Update allowed fields
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'error': 'Name cannot be empty'}), 400
            
            # Check for name conflicts
            existing = ApiKey.query.filter(
                ApiKey.user_id == user_id,
                ApiKey.name == name,
                ApiKey.id != api_key.id
            ).first()
            if existing:
                return jsonify({'error': 'An API key with this name already exists'}), 400
            
            api_key.name = name
        
        if 'description' in data:
            api_key.description = data['description'].strip() or None
        
        if 'scopes' in data:
            scopes = data['scopes']
            valid_scopes = ['read', 'write', 'admin']
            if not isinstance(scopes, list) or not all(scope in valid_scopes for scope in scopes):
                return jsonify({
                    'error': 'Invalid scopes',
                    'valid_scopes': valid_scopes
                }), 400
            api_key.scopes = scopes
        
        if 'permissions' in data:
            permissions = data['permissions']
            if not isinstance(permissions, dict):
                return jsonify({'error': 'Permissions must be a dictionary'}), 400
            api_key.permissions = permissions
        
        if 'is_active' in data:
            api_key.is_active = bool(data['is_active'])
        
        if 'rate_limit_per_minute' in data:
            rate_limit = data['rate_limit_per_minute']
            if isinstance(rate_limit, int) and 1 <= rate_limit <= 1000:
                api_key.rate_limit_per_minute = rate_limit
            else:
                return jsonify({'error': 'Rate limit must be between 1 and 1000'}), 400
        
        db.session.commit()
        logger.info(f"Updated API key '{api_key.name}' for user {api_key.user_email}")
        
        return jsonify(api_key.to_dict())
        
    except Exception as e:
        logger.error(f"Error updating API key: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update API key'}), 500

@api_key_bp.route('/<key_id>', methods=['DELETE'])
@require_dual_factor(['webauthn', 'totp'], ['email'])  # Tier 3: Primary method + email confirmation
def delete_api_key(key_id):
    """Delete an API key"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Find the API key
        api_key = ApiKey.query.filter_by(key_id=key_id, user_id=user_id).first()
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Soft delete by deactivating (keep for audit trail)
        api_key_name = api_key.name
        api_key.is_active = False
        db.session.commit()

        logger.info(f"Deleted API key '{api_key_name}' for user {api_key.user_email}")

        # Audit log the API key deletion
        AuditLogger.log_api_key_event(
            action='delete',
            api_key_name=api_key_name,
            success=True
        )

        return jsonify({
            'message': 'API key deleted successfully',
            'key_id': key_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete API key'}), 500

@api_key_bp.route('/<key_id>/usage', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_api_key_usage(key_id):
    """Get usage statistics for an API key"""
    try:
        # Get user info from either Flask session or API key
        if hasattr(g, 'api_user') and g.api_user:
            # API key authentication
            user_id = g.api_key.user_id
        elif hasattr(g, 'user') and g.user:
            # Session authentication via g.user (set by auth middleware)
            user_id = g.user.kratos_id  # Use Kratos ID for consistency
        else:
            # Fallback to session variables (legacy)
            user_id = session.get('identity_id')

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Find the API key
        api_key = ApiKey.query.filter_by(key_id=key_id, user_id=user_id).first()
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Get query parameters
        days = request.args.get('days', 7, type=int)
        if days > 90:
            days = 90  # Limit to 90 days
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        # Get usage logs
        since_date = datetime.utcnow() - timedelta(days=days)
        
        usage_query = ApiKeyUsage.query.filter(
            ApiKeyUsage.api_key_id == api_key.id,
            ApiKeyUsage.timestamp >= since_date
        ).order_by(ApiKeyUsage.timestamp.desc())
        
        usage_logs = usage_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Calculate statistics
        total_requests = usage_query.count()
        successful_requests = usage_query.filter(ApiKeyUsage.status_code < 400).count()
        error_rate = ((total_requests - successful_requests) / total_requests * 100) if total_requests > 0 else 0
        
        # Group by day for chart data
        from sqlalchemy import func
        daily_usage = db.session.query(
            func.date(ApiKeyUsage.timestamp).label('date'),
            func.count(ApiKeyUsage.id).label('requests')
        ).filter(
            ApiKeyUsage.api_key_id == api_key.id,
            ApiKeyUsage.timestamp >= since_date
        ).group_by(func.date(ApiKeyUsage.timestamp)).all()
        
        return jsonify({
            'statistics': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'error_rate': round(error_rate, 2),
                'period_days': days
            },
            'daily_usage': [
                {
                    'date': day.date.isoformat(),
                    'requests': day.requests
                } for day in daily_usage
            ],
            'recent_logs': [log.to_dict() for log in usage_logs.items],
            'pagination': {
                'page': page,
                'pages': usage_logs.pages,
                'per_page': per_page,
                'total': usage_logs.total,
                'has_next': usage_logs.has_next,
                'has_prev': usage_logs.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting API key usage: {str(e)}")
        return jsonify({'error': 'Failed to get usage statistics'}), 500

@api_key_bp.route('/validate', methods=['POST'])
@api_key_required(scopes=['read'])
def validate_api_key():
    """Validate an API key (for testing purposes)"""
    try:
        api_key = g.api_key
        
        return jsonify({
            'valid': True,
            'key_id': api_key.key_id,
            'name': api_key.name,
            'scopes': api_key.scopes,
            'permissions': api_key.permissions,
            'user_email': api_key.user_email,
            'expires_at': api_key.expires_at.isoformat() if api_key.expires_at else None,
            'rate_limit_per_minute': api_key.rate_limit_per_minute,
            'message': 'API key is valid and active'
        })
        
    except Exception as e:
        logger.error(f"Error validating API key: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500

@api_key_bp.route('/verify', methods=['GET'])
def verify_api_key():
    """Verify API key for other services (cross-service authentication)"""
    try:
        # Get API key from X-API-Key header (for other services to call)
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'Missing X-API-Key header'}), 401
        
        # Verify the API key using the model
        api_key_obj = ApiKey.verify_key(api_key)
        if not api_key_obj:
            return jsonify({'error': 'Invalid or expired API key'}), 401
        
        # Return key information for other services
        return jsonify({
            'valid': True,
            'user_id': api_key_obj.user_id,
            'user_email': api_key_obj.user_email,
            'name': api_key_obj.name,
            'scopes': api_key_obj.scopes,
            'permissions': api_key_obj.permissions,
            'is_admin': 'admin' in api_key_obj.scopes
        })
        
    except Exception as e:
        logger.error(f'Error verifying API key for service: {str(e)}')
        return jsonify({'error': 'Server error'}), 500
