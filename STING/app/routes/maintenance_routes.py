"""
Admin Maintenance Routes
API endpoints for managing system maintenance windows.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone, timedelta
import logging

from app.utils.decorators import require_auth_or_api_key
from app.middleware.maintenance_middleware import (
    get_maintenance_state,
    enable_maintenance,
    disable_maintenance,
    clear_maintenance_cache
)
from app.models.user_models import SystemSetting

logger = logging.getLogger(__name__)

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/api/admin/maintenance')


@maintenance_bp.route('/status', methods=['GET'])
def get_maintenance_status():
    """
    Get current maintenance status.
    Public endpoint - anyone can check if system is in maintenance.
    """
    state = get_maintenance_state()
    
    if not state or not state.get('enabled'):
        return jsonify({
            'maintenance_mode': False,
            'status': 'operational'
        })
    
    response = {
        'maintenance_mode': True,
        'status': 'maintenance',
        'message': state.get('message', 'System maintenance in progress'),
        'allow_admins': state.get('allow_admins', True)
    }
    
    # Include timing info if available
    if state.get('start_time'):
        response['start_time'] = state['start_time']
    if state.get('end_time'):
        response['end_time'] = state['end_time']
    
    return jsonify(response)


@maintenance_bp.route('', methods=['GET'])
@require_auth_or_api_key(['admin'])
def get_maintenance_details():
    """
    Get detailed maintenance status (admin only).
    Includes audit info like who enabled maintenance.
    """
    state = get_maintenance_state()
    
    # Also get maintenance history from database
    history = SystemSetting.get('maintenance_history', [])
    
    # Get any scheduled maintenance
    scheduled = SystemSetting.get('scheduled_maintenance', [])
    
    return jsonify({
        'current_state': state or {'enabled': False},
        'history': history[-10:] if history else [],  # Last 10 entries
        'scheduled': scheduled
    })


@maintenance_bp.route('', methods=['POST'])
@require_auth_or_api_key(['admin'])
def enable_maintenance_mode():
    """
    Enable maintenance mode.
    
    Request body:
    {
        "message": "System maintenance in progress",
        "start_time": "2026-01-20T02:00:00Z",  // Optional - for scheduled start
        "end_time": "2026-01-20T04:00:00Z",    // Optional - for auto-end
        "allow_admins": true,                   // Default: true
        "duration_minutes": 120                 // Alternative to end_time
    }
    """
    data = request.get_json() or {}
    
    # Get current user for audit
    user = getattr(g, 'user', None)
    updated_by = user.email if user else 'api_key'
    
    # Parse parameters
    message = data.get('message', 'System maintenance in progress. Please try again later.')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    allow_admins = data.get('allow_admins', True)
    
    # Handle duration_minutes as alternative to end_time
    if not end_time and data.get('duration_minutes'):
        start = datetime.now(timezone.utc)
        if start_time:
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = start + timedelta(minutes=int(data['duration_minutes']))
        end_time = end.isoformat()
    
    # Enable maintenance
    success = enable_maintenance(
        message=message,
        start_time=start_time,
        end_time=end_time,
        allow_admins=allow_admins,
        updated_by=updated_by
    )
    
    if not success:
        return jsonify({
            'error': 'Failed to enable maintenance mode',
            'message': 'Could not update maintenance state'
        }), 500
    
    # Log to audit history
    _log_maintenance_event('enabled', updated_by, {
        'message': message,
        'start_time': start_time,
        'end_time': end_time,
        'allow_admins': allow_admins
    })
    
    logger.info(f"Maintenance mode ENABLED by {updated_by}")
    
    return jsonify({
        'success': True,
        'message': 'Maintenance mode enabled',
        'maintenance_mode': True,
        'details': {
            'message': message,
            'start_time': start_time,
            'end_time': end_time,
            'allow_admins': allow_admins,
            'enabled_by': updated_by
        }
    })


@maintenance_bp.route('', methods=['DELETE'])
@require_auth_or_api_key(['admin'])
def disable_maintenance_mode():
    """
    Disable maintenance mode immediately.
    """
    # Get current user for audit
    user = getattr(g, 'user', None)
    updated_by = user.email if user else 'api_key'
    
    # Get current state for logging
    current_state = get_maintenance_state()
    
    # Disable maintenance
    success = disable_maintenance(updated_by=updated_by)
    
    if not success:
        return jsonify({
            'error': 'Failed to disable maintenance mode',
            'message': 'Could not update maintenance state'
        }), 500
    
    # Log to audit history
    _log_maintenance_event('disabled', updated_by, {
        'previous_state': current_state
    })
    
    logger.info(f"Maintenance mode DISABLED by {updated_by}")
    
    return jsonify({
        'success': True,
        'message': 'Maintenance mode disabled',
        'maintenance_mode': False,
        'disabled_by': updated_by
    })


@maintenance_bp.route('/schedule', methods=['POST'])
@require_auth_or_api_key(['admin'])
def schedule_maintenance():
    """
    Schedule a future maintenance window.
    
    Request body:
    {
        "start_time": "2026-01-25T02:00:00Z",
        "end_time": "2026-01-25T04:00:00Z",
        "message": "Scheduled maintenance",
        "notify_users": true
    }
    """
    data = request.get_json() or {}
    
    if not data.get('start_time') or not data.get('end_time'):
        return jsonify({
            'error': 'Missing required fields',
            'message': 'start_time and end_time are required'
        }), 400
    
    # Validate times are in the future
    try:
        start = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if start < now:
            return jsonify({
                'error': 'Invalid start_time',
                'message': 'start_time must be in the future'
            }), 400
        
        if end <= start:
            return jsonify({
                'error': 'Invalid end_time',
                'message': 'end_time must be after start_time'
            }), 400
            
    except ValueError as e:
        return jsonify({
            'error': 'Invalid datetime format',
            'message': str(e)
        }), 400
    
    # Get current user
    user = getattr(g, 'user', None)
    scheduled_by = user.email if user else 'api_key'
    
    # Get existing scheduled maintenance
    scheduled = SystemSetting.get('scheduled_maintenance', [])
    
    # Add new scheduled window
    window = {
        'id': f"maint_{int(datetime.now(timezone.utc).timestamp())}",
        'start_time': data['start_time'],
        'end_time': data['end_time'],
        'message': data.get('message', 'Scheduled system maintenance'),
        'notify_users': data.get('notify_users', True),
        'scheduled_by': scheduled_by,
        'scheduled_at': datetime.now(timezone.utc).isoformat()
    }
    
    scheduled.append(window)
    SystemSetting.set('scheduled_maintenance', scheduled, updated_by=scheduled_by)
    
    logger.info(f"Maintenance scheduled by {scheduled_by}: {data['start_time']} to {data['end_time']}")
    
    return jsonify({
        'success': True,
        'message': 'Maintenance window scheduled',
        'window': window
    })


@maintenance_bp.route('/schedule/<window_id>', methods=['DELETE'])
@require_auth_or_api_key(['admin'])
def cancel_scheduled_maintenance(window_id):
    """
    Cancel a scheduled maintenance window.
    """
    user = getattr(g, 'user', None)
    cancelled_by = user.email if user else 'api_key'
    
    scheduled = SystemSetting.get('scheduled_maintenance', [])
    
    # Find and remove the window
    original_count = len(scheduled)
    scheduled = [w for w in scheduled if w.get('id') != window_id]
    
    if len(scheduled) == original_count:
        return jsonify({
            'error': 'Not found',
            'message': f'Scheduled maintenance window {window_id} not found'
        }), 404
    
    SystemSetting.set('scheduled_maintenance', scheduled, updated_by=cancelled_by)
    
    logger.info(f"Scheduled maintenance {window_id} cancelled by {cancelled_by}")
    
    return jsonify({
        'success': True,
        'message': 'Scheduled maintenance cancelled'
    })


@maintenance_bp.route('/history', methods=['GET'])
@require_auth_or_api_key(['admin'])
def get_maintenance_history():
    """
    Get maintenance event history.
    """
    history = SystemSetting.get('maintenance_history', [])
    
    # Support pagination
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    total = len(history)
    # History is stored newest-first
    paginated = history[offset:offset + limit]
    
    return jsonify({
        'history': paginated,
        'total': total,
        'limit': limit,
        'offset': offset
    })


def _log_maintenance_event(event_type: str, user: str, details: dict):
    """
    Log a maintenance event to the audit history.
    """
    try:
        history = SystemSetting.get('maintenance_history', [])
        
        event = {
            'type': event_type,
            'user': user,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': details
        }
        
        # Prepend to history (newest first)
        history.insert(0, event)
        
        # Keep only last 100 events
        if len(history) > 100:
            history = history[:100]
        
        SystemSetting.set('maintenance_history', history)
        
    except Exception as e:
        logger.error(f"Failed to log maintenance event: {e}")


# Also expose a public status endpoint on system routes
def register_public_status_route(system_bp):
    """
    Register a public maintenance status endpoint on the system blueprint.
    Call this from system_routes.py
    """
    @system_bp.route('/maintenance/status', methods=['GET'])
    def public_maintenance_status():
        """Public maintenance status check"""
        state = get_maintenance_state()
        
        if not state or not state.get('enabled'):
            return jsonify({
                'maintenance_mode': False,
                'status': 'operational'
            })
        
        return jsonify({
            'maintenance_mode': True,
            'status': 'maintenance',
            'message': state.get('message', 'System maintenance in progress'),
            'estimated_end': state.get('end_time')
        })
