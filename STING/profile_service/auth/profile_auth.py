"""
Profile Authentication - Kratos integration for profile service.
"""

import os
import logging
import requests
from typing import Optional, Dict, Any, List
from functools import wraps
from flask import request, g, jsonify

logger = logging.getLogger(__name__)

class ProfileAuth:
    """Authentication handler for profile service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.kratos_public_url = config.get('KRATOS_PUBLIC_URL', 'https://localhost:4433')
        self.kratos_admin_url = config.get('KRATOS_ADMIN_URL', 'http://kratos:4434')
    
    def get_current_user(self, session_cookie: str = None) -> Optional[Dict[str, Any]]:
        """
        Get current user from Kratos session.
        
        Args:
            session_cookie: Session cookie value
            
        Returns:
            User identity or None
        """
        if not session_cookie:
            session_cookie = request.cookies.get('ory_kratos_session') or request.cookies.get('ory_kratos_session')
        
        if not session_cookie:
            return None
        
        try:
            # Validate session with Kratos
            response = requests.get(
                f"{self.kratos_public_url}/sessions/whoami",
                cookies={'ory_kratos_session': session_cookie},
                verify=False,  # For development with self-signed certs
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                identity = data.get('identity', {})
                
                return {
                    'id': identity.get('id'),
                    'email': identity.get('traits', {}).get('email'),
                    'traits': identity.get('traits', {}),
                    'session_id': data.get('id'),
                    'active': data.get('active', False)
                }
            else:
                logger.warning(f"Kratos session validation failed: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error validating Kratos session: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in session validation: {e}")
            return None
    
    def require_auth(self, f):
        """
        Decorator to require authentication for endpoints.
        
        Args:
            f: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = self.get_current_user()
            
            if not user:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            
            if not user.get('active', False):
                return jsonify({
                    'error': 'Session inactive',
                    'code': 'SESSION_INACTIVE'
                }), 401
            
            # Store user in Flask's g object for use in the request
            g.current_user = user
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_self_or_admin(self, f):
        """
        Decorator to require user to be accessing their own profile or be an admin.
        
        Args:
            f: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            
            if not user:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            
            # Get user_id from URL parameters or request data
            target_user_id = kwargs.get('user_id') or request.view_args.get('user_id')
            
            if not target_user_id:
                # If no specific user_id, assume current user
                target_user_id = user['id']
                kwargs['user_id'] = target_user_id
            
            # Check if user is accessing their own profile
            if user['id'] == target_user_id:
                return f(*args, **kwargs)
            
            # Check if user is admin (based on traits or role)
            user_traits = user.get('traits', {})
            user_role = user_traits.get('role', 'user')
            
            if user_role in ['admin', 'superuser']:
                return f(*args, **kwargs)
            
            return jsonify({
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }), 403
        
        return decorated_function
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """
        Get user permissions from Kratos traits.
        
        Args:
            user_id: User ID
            
        Returns:
            List of permissions
        """
        try:
            # Get user identity from Kratos admin API
            response = requests.get(
                f"{self.kratos_admin_url}/admin/identities/{user_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                identity = response.json()
                traits = identity.get('traits', {})
                
                # Extract permissions from traits
                permissions = traits.get('permissions', [])
                role = traits.get('role', 'user')
                
                # Add role-based permissions
                if role == 'admin':
                    permissions.extend(['admin:read', 'admin:write', 'admin:delete'])
                elif role == 'moderator':
                    permissions.extend(['moderate:read', 'moderate:write'])
                
                return list(set(permissions))  # Remove duplicates
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return []
    
    def update_user_traits(self, user_id: str, traits: Dict[str, Any]) -> bool:
        """
        Update user traits in Kratos.
        
        Args:
            user_id: User ID
            traits: Traits to update
            
        Returns:
            True if successful
        """
        try:
            # Get current identity
            response = requests.get(
                f"{self.kratos_admin_url}/admin/identities/{user_id}",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get identity {user_id}")
                return False
            
            identity = response.json()
            current_traits = identity.get('traits', {})
            
            # Merge traits
            updated_traits = {**current_traits, **traits}
            
            # Update identity
            update_response = requests.put(
                f"{self.kratos_admin_url}/admin/identities/{user_id}",
                json={
                    'schema_id': identity.get('schema_id', 'default'),
                    'traits': updated_traits,
                    'state': identity.get('state', 'active')
                },
                timeout=10
            )
            
            if update_response.status_code == 200:
                logger.info(f"Updated traits for user {user_id}")
                return True
            else:
                logger.error(f"Failed to update traits: {update_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating user traits: {e}")
            return False