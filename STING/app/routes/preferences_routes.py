"""
User and Organization Preferences API Routes
Handles database-backed preference management for navigation, themes, and UI settings
"""

import logging
from flask import Blueprint, jsonify, request, g
from functools import wraps
from app.models.user_settings import UserSettings
from app.models.organization_preferences import OrganizationPreferences, UserPreferenceHistory
from app.utils.decorators import require_auth
from app.extensions import db
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint
preferences_bp = Blueprint('preferences', __name__, url_prefix='/api/preferences')

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not (hasattr(g.user, 'is_admin') and g.user.is_admin):
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# User Preference Routes

@preferences_bp.route('/navigation', methods=['GET'])
@require_auth
def get_user_navigation_preferences():
    """Get user's navigation preferences"""
    try:
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Get user navigation config
        user_config = UserSettings.get_navigation_config(user_id)
        
        # Get organization default if user has none
        if not user_config:
            org_default = OrganizationPreferences.get_navigation_default()
            if org_default:
                user_config = org_default
        
        # Get current version from user settings or default
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        current_version = settings.navigation_version if settings else 4
        
        return jsonify({
            'config': user_config,
            'version': current_version,
            'has_custom_config': UserSettings.get_navigation_config(user_id) is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting navigation preferences: {e}")
        return jsonify({'error': 'Failed to get navigation preferences'}), 500

@preferences_bp.route('/navigation', methods=['PUT'])
@require_auth
def update_user_navigation_preferences():
    """Update user's navigation preferences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        config = data.get('config')
        version = data.get('version', 4)
        
        if not config:
            return jsonify({'error': 'Config is required'}), 400
        
        # Get old config for audit trail
        old_config = UserSettings.get_navigation_config(user_id)
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        old_version = settings.navigation_version if settings else None
        
        # Update navigation config
        success = UserSettings.update_navigation_config(user_id, config, version)
        
        if success:
            # Log the change
            UserPreferenceHistory.log_change(
                user_id=user_id,
                preference_type='navigation',
                old_config=old_config,
                new_config=config,
                old_version=old_version,
                new_version=version,
                changed_by=user_id,
                reason='user_update'
            )
            
            return jsonify({
                'message': 'Navigation preferences updated successfully',
                'config': config,
                'version': version
            }), 200
        else:
            return jsonify({'error': 'Failed to update preferences'}), 500
            
    except Exception as e:
        logger.error(f"Error updating navigation preferences: {e}")
        return jsonify({'error': 'Failed to update navigation preferences'}), 500

@preferences_bp.route('/theme', methods=['GET'])
@require_auth
def get_user_theme_preferences():
    """Get user's theme preferences"""
    try:
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Get user theme preferences
        user_prefs = UserSettings.get_theme_preferences(user_id)
        
        # Get organization default if user has none
        if not user_prefs:
            org_default = OrganizationPreferences.get_theme_default()
            if org_default:
                user_prefs = org_default
        
        return jsonify({
            'preferences': user_prefs,
            'has_custom_preferences': UserSettings.get_theme_preferences(user_id) is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting theme preferences: {e}")
        return jsonify({'error': 'Failed to get theme preferences'}), 500

@preferences_bp.route('/theme', methods=['PUT'])
@require_auth
def update_user_theme_preferences():
    """Update user's theme preferences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        preferences = data.get('preferences')
        
        if not preferences:
            return jsonify({'error': 'Preferences are required'}), 400
        
        # Get old preferences for audit trail
        old_prefs = UserSettings.get_theme_preferences(user_id)
        
        # Update theme preferences
        success = UserSettings.update_theme_preferences(user_id, preferences)
        
        if success:
            # Log the change
            UserPreferenceHistory.log_change(
                user_id=user_id,
                preference_type='theme',
                old_config=old_prefs,
                new_config=preferences,
                changed_by=user_id,
                reason='user_update'
            )
            
            return jsonify({
                'message': 'Theme preferences updated successfully',
                'preferences': preferences
            }), 200
        else:
            return jsonify({'error': 'Failed to update preferences'}), 500
            
    except Exception as e:
        logger.error(f"Error updating theme preferences: {e}")
        return jsonify({'error': 'Failed to update theme preferences'}), 500

@preferences_bp.route('/ui', methods=['GET'])
@require_auth
def get_user_ui_preferences():
    """Get user's UI preferences"""
    try:
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Get user UI preferences
        user_prefs = UserSettings.get_ui_preferences(user_id)
        
        # Get organization default if user has none
        if not user_prefs:
            org_default = OrganizationPreferences.get_ui_default()
            if org_default:
                user_prefs = org_default
        
        return jsonify({
            'preferences': user_prefs,
            'has_custom_preferences': UserSettings.get_ui_preferences(user_id) is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting UI preferences: {e}")
        return jsonify({'error': 'Failed to get UI preferences'}), 500

@preferences_bp.route('/ui', methods=['PUT'])
@require_auth
def update_user_ui_preferences():
    """Update user's UI preferences"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        preferences = data.get('preferences')
        
        if not preferences:
            return jsonify({'error': 'Preferences are required'}), 400
        
        # Get old preferences for audit trail
        old_prefs = UserSettings.get_ui_preferences(user_id)
        
        # Update UI preferences
        success = UserSettings.update_ui_preferences(user_id, preferences)
        
        if success:
            # Log the change
            UserPreferenceHistory.log_change(
                user_id=user_id,
                preference_type='ui',
                old_config=old_prefs,
                new_config=preferences,
                changed_by=user_id,
                reason='user_update'
            )
            
            return jsonify({
                'message': 'UI preferences updated successfully',
                'preferences': preferences
            }), 200
        else:
            return jsonify({'error': 'Failed to update preferences'}), 500
            
    except Exception as e:
        logger.error(f"Error updating UI preferences: {e}")
        return jsonify({'error': 'Failed to update UI preferences'}), 500

@preferences_bp.route('/all', methods=['GET'])
@require_auth
def get_all_user_preferences():
    """Get all user preferences in one call"""
    try:
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Get all preferences from database
        all_prefs = UserSettings.get_all_preferences(user_id)
        
        # Get organization defaults for missing preferences
        if not all_prefs or not all_prefs.get('navigation'):
            org_nav = OrganizationPreferences.get_navigation_default()
            if not all_prefs:
                all_prefs = {}
            if org_nav and not all_prefs.get('navigation'):
                all_prefs['navigation'] = org_nav
                all_prefs['navigation_version'] = 4
        
        if not all_prefs.get('theme'):
            org_theme = OrganizationPreferences.get_theme_default()
            if org_theme:
                all_prefs['theme'] = org_theme
        
        if not all_prefs.get('ui'):
            org_ui = OrganizationPreferences.get_ui_default()
            if org_ui:
                all_prefs['ui'] = org_ui
        
        return jsonify(all_prefs or {}), 200
        
    except Exception as e:
        logger.error(f"Error getting all preferences: {e}")
        return jsonify({'error': 'Failed to get preferences'}), 500

@preferences_bp.route('/migrate-from-localstorage', methods=['POST'])
@require_auth
def migrate_from_localstorage():
    """Migrate user preferences from localStorage to database"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Extract preferences from localStorage data
        navigation = data.get('navigation')
        theme = data.get('theme')
        ui = data.get('ui')
        nav_version = data.get('navigation_version', 4)
        
        # Update all preferences in one transaction
        success = UserSettings.update_all_preferences(
            user_id=user_id,
            navigation=navigation,
            theme=theme,
            ui=ui,
            nav_version=nav_version
        )
        
        if success:
            # Log the migration
            if navigation:
                UserPreferenceHistory.log_change(
                    user_id=user_id,
                    preference_type='navigation',
                    old_config=None,
                    new_config=navigation,
                    old_version=None,
                    new_version=nav_version,
                    changed_by=user_id,
                    reason='localstorage_migration'
                )
            
            if theme:
                UserPreferenceHistory.log_change(
                    user_id=user_id,
                    preference_type='theme',
                    old_config=None,
                    new_config=theme,
                    changed_by=user_id,
                    reason='localstorage_migration'
                )
            
            if ui:
                UserPreferenceHistory.log_change(
                    user_id=user_id,
                    preference_type='ui',
                    old_config=None,
                    new_config=ui,
                    changed_by=user_id,
                    reason='localstorage_migration'
                )
            
            return jsonify({
                'message': 'Preferences migrated successfully',
                'migrated': {
                    'navigation': navigation is not None,
                    'theme': theme is not None,
                    'ui': ui is not None
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to migrate preferences'}), 500
            
    except Exception as e:
        logger.error(f"Error migrating preferences: {e}")
        return jsonify({'error': 'Failed to migrate preferences'}), 500

# Organization/Admin Preference Routes

@preferences_bp.route('/organization', methods=['GET'])
@require_admin
def get_organization_preferences():
    """Get all organization default preferences"""
    try:
        prefs = OrganizationPreferences.get_all_active()
        
        return jsonify({
            'preferences': [pref.to_dict() for pref in prefs]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting organization preferences: {e}")
        return jsonify({'error': 'Failed to get organization preferences'}), 500

@preferences_bp.route('/organization/<preference_type>', methods=['PUT'])
@require_admin
def update_organization_preference(preference_type):
    """Update organization default preference"""
    try:
        if preference_type not in ['navigation', 'theme', 'ui']:
            return jsonify({'error': 'Invalid preference type'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        config = data.get('config')
        version = data.get('version', 1)
        
        if not config:
            return jsonify({'error': 'Config is required'}), 400
        
        # Get admin user ID
        admin_user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        
        # Update organization preference
        pref = OrganizationPreferences.update_preference(
            preference_type=preference_type,
            config=config,
            version=version,
            created_by=admin_user_id
        )
        
        return jsonify({
            'message': f'Organization {preference_type} preference updated successfully',
            'preference': pref.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating organization preference: {e}")
        return jsonify({'error': 'Failed to update organization preference'}), 500

@preferences_bp.route('/push-to-users', methods=['POST'])
@require_admin
def push_preferences_to_users():
    """Push organization preferences to all users (admin operation)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        preference_types = data.get('preference_types', [])
        user_ids = data.get('user_ids')  # Optional: specific users, None = all users
        force_update = data.get('force_update', False)  # Update even if user has custom prefs
        
        if not preference_types:
            return jsonify({'error': 'Preference types required'}), 400
        
        admin_user_id = g.user.kratos_id if hasattr(g.user, 'kratos_id') else str(g.user.id)
        updated_users = 0
        skipped_users = 0
        
        # Get all users or specific users
        if user_ids:
            users_query = UserSettings.query.filter(UserSettings.user_id.in_(user_ids))
        else:
            users_query = UserSettings.query.all()
        
        for user_settings in users_query:
            user_updated = False
            
            for pref_type in preference_types:
                if pref_type not in ['navigation', 'theme', 'ui']:
                    continue
                
                # Get organization default
                org_pref = OrganizationPreferences.get_by_type(pref_type)
                if not org_pref:
                    continue
                
                # Check if user has custom preference and force_update is False
                has_custom = False
                old_config = None
                old_version = None
                
                if pref_type == 'navigation':
                    has_custom = UserSettings.get_navigation_config(user_settings.user_id) is not None
                    old_config = UserSettings.get_navigation_config(user_settings.user_id)
                    old_version = user_settings.navigation_version
                elif pref_type == 'theme':
                    has_custom = UserSettings.get_theme_preferences(user_settings.user_id) is not None
                    old_config = UserSettings.get_theme_preferences(user_settings.user_id)
                elif pref_type == 'ui':
                    has_custom = UserSettings.get_ui_preferences(user_settings.user_id) is not None
                    old_config = UserSettings.get_ui_preferences(user_settings.user_id)
                
                if has_custom and not force_update:
                    skipped_users += 1
                    continue
                
                # Update user preference
                success = False
                if pref_type == 'navigation':
                    success = UserSettings.update_navigation_config(
                        user_settings.user_id, 
                        org_pref.config, 
                        org_pref.version
                    )
                elif pref_type == 'theme':
                    success = UserSettings.update_theme_preferences(
                        user_settings.user_id, 
                        org_pref.config
                    )
                elif pref_type == 'ui':
                    success = UserSettings.update_ui_preferences(
                        user_settings.user_id, 
                        org_pref.config
                    )
                
                if success:
                    user_updated = True
                    
                    # Log the admin push
                    UserPreferenceHistory.log_change(
                        user_id=user_settings.user_id,
                        preference_type=pref_type,
                        old_config=old_config,
                        new_config=org_pref.config,
                        old_version=old_version,
                        new_version=org_pref.version if pref_type == 'navigation' else None,
                        changed_by=admin_user_id,
                        reason='admin_push'
                    )
            
            if user_updated:
                updated_users += 1
        
        return jsonify({
            'message': f'Preferences pushed to users successfully',
            'updated_users': updated_users,
            'skipped_users': skipped_users,
            'preference_types': preference_types
        }), 200
        
    except Exception as e:
        logger.error(f"Error pushing preferences to users: {e}")
        return jsonify({'error': 'Failed to push preferences to users'}), 500

@preferences_bp.route('/history/<user_id>', methods=['GET'])
@require_admin
def get_user_preference_history(user_id):
    """Get user's preference change history (admin only)"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        history = UserPreferenceHistory.get_user_history(user_id, limit)
        
        return jsonify({
            'history': [entry.to_dict() for entry in history]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting preference history: {e}")
        return jsonify({'error': 'Failed to get preference history'}), 500

# Error handlers
@preferences_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Preference not found'}), 404

@preferences_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405