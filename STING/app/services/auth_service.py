"""
Authentication Service for STING

Handles user login flows, first user promotion, password change enforcement,
and emergency recovery systems.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.database import db
from app.models.user_models import User, UserRole, SystemSetting

logger = logging.getLogger(__name__)

class AuthenticationService:
    """Service class for handling authentication logic"""
    
    @staticmethod
    def handle_user_login(kratos_id: str, kratos_traits: dict) -> Tuple[User, Dict]:
        """
        Handle user login with all security checks and first-user promotion
        
        Returns:
            tuple: (user_object, auth_info_dict)
            auth_info_dict contains:
            - requires_password_change: bool
            - is_first_user: bool
            - recovery_codes: list (only if first user)
            - should_setup_passkey: bool
        """
        try:
            # Get or create user
            user = User.query.filter_by(kratos_id=kratos_id).first()
            
            if not user:
                # Create new user
                user = AuthenticationService._create_new_user(kratos_id, kratos_traits)
            else:
                # Update existing user from Kratos
                user.update_from_kratos(kratos_traits)
            
            # Update last login
            user.last_login_at = datetime.utcnow()
            
            # Check for first user promotion
            auth_info = AuthenticationService._check_first_user_promotion(user)
            
            # Check password change requirements
            auth_info['requires_password_change'] = user.requires_password_change
            
            # Determine if passkey setup is needed
            auth_info['should_setup_passkey'] = AuthenticationService._should_setup_passkey(user)
            
            db.session.commit()
            
            logger.info(f"User login processed: {user.email} (role: {user.effective_role})")
            
            return user, auth_info
            
        except Exception as e:
            logger.error(f"Error handling user login: {e}")
            db.session.rollback()
            raise
    
    @staticmethod
    def _create_new_user(kratos_id: str, kratos_traits: dict) -> User:
        """Create a new user from Kratos traits"""
        user = User(
            kratos_id=kratos_id,
            email=kratos_traits.get('email'),
            first_name=kratos_traits.get('name', {}).get('first'),
            last_name=kratos_traits.get('name', {}).get('last'),
            username=kratos_traits.get('username'),
            role=UserRole.USER
        )
        
        db.session.add(user)
        db.session.flush()  # Get the ID
        
        logger.info(f"Created new user: {user.email}")
        return user
    
    @staticmethod
    def _check_first_user_promotion(user: User) -> Dict:
        """Check if user should be promoted to first super admin"""
        auth_info = {
            'is_first_user': False,
            'recovery_codes': None,
            'first_user_setup_required': False
        }
        
        # Check if this should be the first super admin
        if user.check_and_promote_first_user():
            auth_info['is_first_user'] = True
            auth_info['first_user_setup_required'] = True
            
            # Generate recovery codes (they're already generated in the method)
            # but we need to get them for display
            recovery_codes = user.generate_emergency_recovery_codes()
            auth_info['recovery_codes'] = recovery_codes
            
            logger.warning(f"First super admin created: {user.email}")
            
            # Log this critical security event
            AuthenticationService._log_security_event(
                'FIRST_SUPER_ADMIN_CREATED',
                f'First super admin user created: {user.email}',
                user.email
            )
        
        return auth_info
    
    @staticmethod
    def _should_setup_passkey(user: User) -> bool:
        """Determine if user should set up passkey authentication"""
        # For super admins and admins, always recommend passkey
        if user.is_admin or user.is_super_admin:
            return True
        
        # For first users, require passkey
        if user.is_first_user:
            return True
        
        # Check if user had passkeys before (migration scenario)
        # This would require checking Kratos for existing WebAuthn credentials
        # For now, we'll be conservative and recommend setup for important users
        
        # Could add other logic here (e.g., after certain time period)
        return False
    
    @staticmethod
    def check_passkey_preservation(user: User) -> Dict:
        """Check if user's passkey data is preserved after migration"""
        # Import here to avoid circular imports
        from app.utils.kratos_session import get_configured_auth_methods
        
        try:
            # Get configured authentication methods from Kratos
            configured_methods = get_configured_auth_methods(user.kratos_id)
            has_passkeys = configured_methods.get('webauthn', False)
            
            return {
                'has_passkeys': has_passkeys,
                'passkey_count': 1 if has_passkeys else 0,  # At least one if any exist
                'needs_reregistration': not has_passkeys,
                'migration_detected': user.is_first_user and user.password_changed_at is None
            }
        except Exception as e:
            logger.error(f"Error checking passkey preservation for user {user.email}: {e}")
            # Return conservative fallback
            return {
                'has_passkeys': False,
                'passkey_count': 0,
                'needs_reregistration': True,
                'migration_detected': user.is_first_user and user.password_changed_at is None
            }
    
    @staticmethod
    def verify_emergency_recovery(email: str, recovery_code: str, new_password: str) -> Tuple[bool, str]:
        """
        Verify emergency recovery code and reset access
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            user = User.query.filter_by(email=email).first()
            
            if not user:
                return False, "User not found"
            
            if not user.is_super_admin:
                return False, "Emergency recovery only available for super administrators"
            
            # Verify recovery code
            if not user.verify_recovery_code(recovery_code):
                AuthenticationService._log_security_event(
                    'RECOVERY_CODE_FAILED',
                    f'Invalid recovery code attempt for: {email}',
                    email
                )
                return False, "Invalid or already used recovery code"
            
            # Reset password in Kratos (this would need to be implemented)
            # For now, we'll mark that password change is required
            user.force_password_change()
            
            db.session.commit()
            
            AuthenticationService._log_security_event(
                'EMERGENCY_RECOVERY_SUCCESS',
                f'Emergency recovery successful for: {email}',
                email
            )
            
            return True, "Emergency recovery successful. Please log in and change your password."
            
        except Exception as e:
            logger.error(f"Error in emergency recovery: {e}")
            return False, "Emergency recovery failed due to system error"
    
    @staticmethod
    def complete_forced_password_change(user: User) -> bool:
        """Mark password change as completed for a user"""
        try:
            user.complete_password_change()
            db.session.commit()
            
            AuthenticationService._log_security_event(
                'PASSWORD_CHANGE_COMPLETED',
                f'Forced password change completed for: {user.email}',
                user.email
            )
            
            return True
        except Exception as e:
            logger.error(f"Error completing password change: {e}")
            return False
    
    @staticmethod
    def get_first_user_setup_info(user: User) -> Optional[Dict]:
        """Get setup information for first user"""
        if not user.is_first_user or not user.requires_password_change:
            return None
        
        return {
            'is_first_user': True,
            'requires_password_change': True,
            'has_recovery_codes': bool(user.emergency_recovery_codes),
            'recovery_codes_count': len(user.emergency_recovery_codes.get('codes', [])) if user.emergency_recovery_codes else 0,
            'email': user.email,
            'setup_steps': [
                'Change your temporary password',
                'Set up passkey authentication',
                'Save your emergency recovery codes',
                'Verify your recovery email'
            ]
        }
    
    @staticmethod
    def _log_security_event(event_type: str, description: str, user_email: str = None):
        """Log security-related events"""
        try:
            # Create audit log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'description': description,
                'user_email': user_email,
                'source': 'authentication_service'
            }
            
            # Log to file
            logger.warning(f"SECURITY_EVENT: {event_type} - {description}")
            
            # Could also store in database or send to external audit system
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    @staticmethod
    def check_user_access_permissions(user: User) -> Dict:
        """Check what access permissions a user has"""
        return {
            'can_access_dashboard': True,
            'can_manage_users': user.can_manage_users,
            'can_manage_llm': user.can_manage_llm,
            'can_access_bee_settings': True,  # Everyone can view
            'can_modify_bee_settings': user.can_manage_llm,
            'requires_password_change': user.requires_password_change,
            'role': user.effective_role,
            'is_first_user': user.is_first_user
        }