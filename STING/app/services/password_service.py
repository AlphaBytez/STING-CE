"""
Password Service for STING

Handles password validation, verification, and change operations
through Kratos integration.
"""

import logging
from typing import Dict, Tuple, Optional
import requests
import os

from app.database import db
from app.models.user_models import User
from app.utils.kratos_client import whoami
from app.utils.kratos_admin import (
    get_identity_by_email, 
    get_identity_by_id, 
    KRATOS_ADMIN_URL
)

logger = logging.getLogger(__name__)

# Get Kratos URLs from config
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')


class PasswordService:
    """Service for managing password operations"""
    
    @staticmethod
    def validate_password_requirements(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets security requirements.
        
        Args:
            password: The password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if len(password) < 8:
                return False, 'Password must be at least 8 characters long'
            
            # Check for basic password complexity
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
            
            if not (has_upper and has_lower and has_digit and has_special):
                return False, 'Password must contain uppercase and lowercase letters, numbers, and special characters'
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating password requirements: {e}")
            return False, f'Password validation failed: {str(e)}'
    
    @staticmethod
    def verify_current_password(user: User, password: str) -> Tuple[bool, Optional[str]]:
        """
        Verify the user's current password using Kratos.
        
        Args:
            user: The user object
            password: The password to verify
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # First create a login flow - use browser flow for consistency
            flow_response = requests.get(
                f"{KRATOS_PUBLIC_URL}/self-service/login/browser",
                headers={'Accept': 'application/json'},
                verify=False
            )
            
            if flow_response.status_code != 200:
                logger.error(f"Failed to create login flow: {flow_response.status_code} - {flow_response.text}")
                return False, 'Failed to verify password'
                
            flow = flow_response.json()
            flow_id = flow.get('id')
            
            if not flow_id:
                logger.error("No flow ID in response")
                return False, 'Failed to verify password'
            
            # Submit credentials to the flow
            login_response = requests.post(
                f"{KRATOS_PUBLIC_URL}/self-service/login?flow={flow_id}",
                json={
                    'identifier': user.email,
                    'password': password,
                    'method': 'password'
                },
                verify=False
            )
            
            if login_response.status_code != 200:
                # Check if it's a 400 error which usually means wrong password
                if login_response.status_code == 400:
                    response_data = login_response.json()
                    # Check for password error in the response
                    if 'ui' in response_data and 'messages' in response_data['ui']:
                        for msg in response_data['ui']['messages']:
                            if msg.get('type') == 'error':
                                return False, 'Current password is incorrect'
                return False, 'Current password is incorrect'
            
            return True, None
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False, 'Failed to verify current password'
    
    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Change user's password through Kratos.
        
        Args:
            user: The user object
            current_password: The user's current password
            new_password: The new password to set
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate new password
            is_valid, validation_error = PasswordService.validate_password_requirements(new_password)
            if not is_valid:
                return False, validation_error
            
            # Verify current password
            is_current_valid, verify_error = PasswordService.verify_current_password(user, current_password)
            if not is_current_valid:
                return False, verify_error
            
            # Update password via Kratos Admin API
            identity_id = user.kratos_id if hasattr(user, 'kratos_id') else None
            if not identity_id:
                # Get identity ID from Kratos
                identity = get_identity_by_email(user.email)
                if not identity:
                    return False, 'User identity not found'
                identity_id = identity['id']
            
            # Get the full identity object
            full_identity = get_identity_by_id(identity_id)
            if not full_identity:
                return False, 'Failed to get user identity'
            
            # Prepare update data with all required fields
            # IMPORTANT: Clear force_password_change in the same update to avoid session issues
            updated_traits = full_identity.get('traits', {}).copy()
            if updated_traits.get('force_password_change', False):
                logger.info("Clearing force_password_change flag during password update")
                updated_traits['force_password_change'] = False
            
            update_data = {
                'schema_id': full_identity.get('schema_id', 'default'),
                'state': full_identity.get('state', 'active'),
                'traits': updated_traits,
                'credentials': {
                    'password': {
                        'config': {
                            'password': new_password
                        }
                    }
                }
            }
            
            # Update password using PUT
            update_response = requests.put(
                f"{KRATOS_ADMIN_URL}/admin/identities/{identity_id}",
                json=update_data,
                verify=False
            )
            
            if update_response.status_code != 200:
                logger.error(f"Failed to update password: Status {update_response.status_code}, Response: {update_response.text}")
                error_data = {}
                try:
                    error_data = update_response.json()
                except:
                    pass
                
                # Provide more specific error messages
                if update_response.status_code == 400:
                    error_msg = error_data.get('error', {}).get('message', 'Invalid password format or requirements not met')
                    return False, error_msg
                elif update_response.status_code == 404:
                    return False, 'User identity not found'
                else:
                    return False, 'Failed to update password'
            
            logger.info("Password and force_password_change flag updated successfully")
            
            # Update UserSettings to clear force_password_change flag
            try:
                from app.models.user_settings import UserSettings
                if UserSettings.mark_password_changed(identity_id):
                    logger.info("UserSettings updated - force_password_change cleared")
                    
                    # Force commit to ensure database is updated before response
                    db.session.commit()
                    logger.info("Database transaction committed")
                    
                    # If this is the admin user, also mark in filesystem
                    if user.email == 'admin@sting.local':
                        try:
                            # V2 approach: UserSettings database record is already updated above
                            # No need for additional marker files in V2 system
                            logger.info("Admin password change recorded in UserSettings (V2 system)")
                        except Exception as e:
                            logger.error(f"Error with V2 password change marking: {e}")
            except Exception as e:
                logger.error(f"Error updating UserSettings: {e}")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False, f'Password change failed: {str(e)}'
    
    @staticmethod
    def verify_password_for_session(email: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Verify password for session-based operations.
        
        Args:
            email: User's email address
            password: Password to verify
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Create a login flow - use browser flow for consistency
            flow_response = requests.get(
                f"{KRATOS_PUBLIC_URL}/self-service/login/browser",
                headers={'Accept': 'application/json'},
                verify=False
            )
            
            if flow_response.status_code != 200:
                return False, "Failed to create login flow"
            
            flow = flow_response.json()
            flow_id = flow.get('id')
            
            if not flow_id:
                return False, "Failed to create login flow"
            
            # Submit credentials
            login_response = requests.post(
                f"{KRATOS_PUBLIC_URL}/self-service/login?flow={flow_id}",
                json={
                    'identifier': email,
                    'password': password,
                    'method': 'password'
                },
                verify=False
            )
            
            if login_response.status_code == 200:
                return True, None
            else:
                return False, 'Invalid password'
                
        except Exception as e:
            logger.error(f"Error verifying password with Kratos: {e}")
            return False, 'Failed to verify password'
    
    @staticmethod
    def check_admin_password_notice() -> Dict:
        """
        Check if admin password notice should be shown.
        
        Returns:
            Dict with notice information
        """
        try:
            from pathlib import Path
            
            # Check if password file exists - use mounted install directory
            password_file = Path('/.sting-ce/admin_password.txt')
            
            if not password_file.exists():
                return {
                    'show_notice': False,
                    'message': 'Admin password has been changed'
                }
                
            # Read the password
            with open(password_file, 'r') as f:
                admin_password = f.read().strip()
                
            if not admin_password:
                return {
                    'show_notice': False,
                    'message': 'Admin password file is empty'
                }
                
            # Check if admin user still has force_password_change flag
            identity = get_identity_by_email('admin@sting.local')
            
            if identity and not identity.get('traits', {}).get('force_password_change', False):
                # Password has been changed, remove the file
                password_file.unlink()
                return {
                    'show_notice': False,
                    'message': 'Admin password has been changed'
                }
                
            return {
                'show_notice': True,
                'admin_email': 'admin@sting.local',
                'admin_password': admin_password,
                'message': 'Default admin credentials - MUST be changed on first login!'
            }
            
        except Exception as e:
            logger.error(f"Error checking admin notice: {e}")
            return {
                'show_notice': False,
                'error': 'Failed to get admin notice'
            }
    
    @staticmethod
    def check_force_password_change(email: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user needs to change password.
        
        Args:
            email: User's email address
            
        Returns:
            Tuple of (needs_change, error_message)
        """
        try:
            # Check if the user exists and needs password change
            identity = get_identity_by_email(email)
            if not identity:
                return False, 'User not found'
            
            # Check UserSettings for force_password_change flag
            from app.models.user_settings import UserSettings
            settings = UserSettings.get_by_kratos_id(identity['id'])
            
            if not settings or not settings.force_password_change:
                return False, None
                
            return True, None
            
        except Exception as e:
            logger.error(f"Error checking force password change: {e}")
            return False, f'Check failed: {str(e)}'