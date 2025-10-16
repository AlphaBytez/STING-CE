"""
User management service
Handles user registration, admin promotion, and SSO integration
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.database import db
from app.models.user_models import User, UserRole, UserStatus, UserSession, SystemSetting

logger = logging.getLogger(__name__)

class UserService:
    """Service for user management operations"""
    
    @staticmethod
    def get_or_create_user_from_kratos(kratos_identity: Dict[str, Any]) -> User:
        """
        Get or create a user from Kratos identity
        This is the main entry point for user creation/login
        """
        kratos_id = kratos_identity.get('id')
        traits = kratos_identity.get('traits', {})
        email = traits.get('email')
        
        if not kratos_id or not email:
            raise ValueError("Invalid Kratos identity: missing ID or email")
        
        try:
            # Check if user exists
            user = User.query.filter_by(kratos_id=kratos_id).first()
            
            if user:
                # Update last login
                user.last_login_at = datetime.utcnow()
                # Update email if changed in Kratos
                if user.email != email:
                    user.email = email
                    user.updated_at = datetime.utcnow()
                
                # Sync role from UserSettings (V2 approach) or Kratos traits (fallback)
                # Check UserSettings first since we store role there to avoid Kratos schema conflicts
                from app.models.user_settings import UserSettings
                user_settings = UserSettings.query.filter_by(user_id=kratos_id).first()
                
                if user_settings and user_settings.role:
                    # Use role from UserSettings (V2 database approach)
                    kratos_role = user_settings.role.upper()
                    logger.debug(f"Loaded role '{kratos_role}' from UserSettings for {email}")
                else:
                    # Fallback to Kratos traits (original approach)
                    kratos_role = traits.get('role', 'user').lower()
                    logger.debug(f"Loaded role '{kratos_role}' from Kratos traits for {email}")
                
                # Update user role based on the loaded value  
                if kratos_role == 'admin' and user.role != UserRole.ADMIN:
                    user.role = UserRole.ADMIN
                    user.is_admin = True
                    logger.info(f"Updated user {email} role to ADMIN")
                elif kratos_role == 'super_admin' and user.role != UserRole.SUPER_ADMIN:
                    user.role = UserRole.SUPER_ADMIN
                    user.is_admin = True
                    user.is_super_admin = True
                    logger.info(f"Updated user {email} role to SUPER_ADMIN")
                elif kratos_role == 'user' and user.role != UserRole.USER:
                    user.role = UserRole.USER
                    user.is_admin = False
                    user.is_super_admin = False
                    logger.info(f"Updated user {email} role to USER")
                
                db.session.commit()
                return user
            
            # Create new user
            user = UserService._create_new_user(kratos_id, traits)
            
            # Check if this should be the first admin
            if UserService._should_be_first_admin(user):
                logger.info(f"Promoting first user {email} to admin")
                UserService._promote_first_user_to_admin(user)
            
            db.session.commit()
            return user
        except Exception as e:
            # Rollback on any error
            db.session.rollback()
            logger.error(f"Error creating/updating user: {e}")
            raise
    
    @staticmethod
    def _create_new_user(kratos_id: str, traits: Dict[str, Any]) -> User:
        """Create a new user from Kratos traits"""
        email = traits.get('email')
        name = traits.get('name', {})
        
        # Extract role from UserSettings (V2) or Kratos traits (fallback)
        from app.models.user_settings import UserSettings
        user_settings = UserSettings.query.filter_by(user_id=kratos_id).first()
        
        if user_settings and user_settings.role:
            # Use role from UserSettings (V2 database approach)
            kratos_role = user_settings.role.upper()
            logger.debug(f"Creating user with role '{kratos_role}' from UserSettings")
        else:
            # Fallback to Kratos traits (original approach)
            kratos_role = traits.get('role', 'user').lower()
            logger.debug(f"Creating user with role '{kratos_role}' from Kratos traits")
        
        # Map role to enum
        if kratos_role == 'admin':
            user_role = UserRole.ADMIN
            is_admin = True
        elif kratos_role == 'super_admin':
            user_role = UserRole.SUPER_ADMIN
            is_admin = True
        else:
            user_role = UserRole.USER
            is_admin = False
        
        user = User(
            kratos_id=kratos_id,
            email=email,
            username=traits.get('username'),
            first_name=name.get('first') if isinstance(name, dict) else None,
            last_name=name.get('last') if isinstance(name, dict) else None,
            display_name=traits.get('display_name'),
            organization=traits.get('organization'),
            role=user_role,
            is_admin=is_admin,
            is_super_admin=(kratos_role == 'SUPER_ADMIN'),
            status=UserStatus.ACTIVE,
        )
        
        db.session.add(user)
        logger.info(f"Created new user: {email}")
        return user
    
    @staticmethod
    def _should_be_first_admin(user: User) -> bool:
        """
        Determine if a user should be promoted to admin
        Rules:
        1. If this is the first user ever created
        2. If no admin users exist and this user meets criteria
        """
        # Check if this is the first user
        total_users = User.query.count()
        if total_users <= 1:  # This user was just created
            logger.info("First user detected - will promote to admin")
            return True
        
        # Check if no admins exist
        admin_count = User.query.filter(
            (User.is_admin == True) | (User.is_super_admin == True)
        ).count()
        
        if admin_count == 0:
            logger.warning("No admin users exist - promoting user to admin")
            return True
        
        return False
    
    @staticmethod
    def _promote_first_user_to_admin(user: User):
        """Promote the first user to super admin"""
        user.promote_to_super_admin()
        
        # Set system setting to track that first admin was created
        SystemSetting.set(
            'first_admin_created',
            True,
            'Indicates that the first admin user has been created',
            f'user_{user.id}'
        )
        
        logger.info(f"Promoted first user {user.email} to super admin")
    
    @staticmethod
    def create_admin_user(
        email: str,
        password: str,
        first_name: str = None,
        last_name: str = None,
        is_super_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Create an admin user via Kratos API
        This is for programmatic admin creation
        """
        try:
            # This would typically create the user via Kratos API
            # For now, we'll create a placeholder that would integrate with Kratos
            
            # TODO: Implement Kratos API integration
            # - Create identity via Kratos Admin API
            # - Set password via Kratos Admin API
            # - Return the created identity
            
            logger.info(f"Admin user creation requested for {email}")
            return {
                'success': True,
                'message': 'Admin user creation initiated',
                'email': email,
                'next_steps': 'User will need to complete registration via Kratos flows'
            }
            
        except Exception as e:
            logger.error(f"Failed to create admin user {email}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def promote_user_to_admin(user_id: int, promoted_by_user_id: int) -> bool:
        """Promote an existing user to admin"""
        try:
            user = User.query.get(user_id)
            promoted_by = User.query.get(promoted_by_user_id)
            
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            if not promoted_by or not promoted_by.can_manage_users:
                logger.error(f"User {promoted_by_user_id} cannot promote users")
                return False
            
            user.promote_to_admin()
            db.session.commit()
            
            logger.info(f"User {user.email} promoted to admin by {promoted_by.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote user {user_id}: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_session(user: User, kratos_session_id: str, request_info: Dict[str, Any] = None) -> UserSession:
        """Create a user session record"""
        session = UserSession(
            user_id=user.id,
            kratos_session_id=kratos_session_id,
            ip_address=request_info.get('ip_address') if request_info else None,
            user_agent=request_info.get('user_agent') if request_info else None,
            device_type=request_info.get('device_type') if request_info else None,
        )
        
        db.session.add(session)
        db.session.commit()
        return session
    
    @staticmethod
    def get_user_by_kratos_id(kratos_id: str) -> Optional[User]:
        """Get user by Kratos ID"""
        return User.query.filter_by(kratos_id=kratos_id).first()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_admin_users() -> list[User]:
        """Get all admin users"""
        return User.query.filter(
            (User.is_admin == True) | (User.is_super_admin == True)
        ).all()
    
    @staticmethod
    def is_first_admin_created() -> bool:
        """Check if the first admin has been created"""
        setting = SystemSetting.get_setting('first_admin_created', 'false')
        return setting.lower() == 'true'
    
    @staticmethod
    def get_user_stats() -> Dict[str, int]:
        """Get user statistics"""
        return {
            'total_users': User.query.count(),
            'admin_users': User.query.filter(User.is_admin == True).count(),
            'super_admin_users': User.query.filter(User.is_super_admin == True).count(),
            'active_users': User.query.filter(User.status == UserStatus.ACTIVE.value).count(),
            'pending_users': User.query.filter(User.status == UserStatus.PENDING.value).count(),
        }
    
    @staticmethod
    def prepare_for_sso_migration() -> Dict[str, Any]:
        """
        Prepare the system for future SSO integration
        Returns configuration and migration strategy
        """
        stats = UserService.get_user_stats()
        admins = UserService.get_admin_users()
        
        return {
            'current_state': {
                'user_count': stats['total_users'],
                'admin_count': stats['admin_users'],
                'super_admin_count': stats['super_admin_users'],
                'first_admin_created': UserService.is_first_admin_created(),
            },
            'admin_users': [
                {
                    'id': admin.id,
                    'email': admin.email,
                    'role': admin.role,
                    'is_super_admin': admin.is_super_admin,
                    'created_at': admin.created_at.isoformat() if admin.created_at else None,
                }
                for admin in admins
            ],
            'sso_readiness': {
                'has_admin_users': stats['admin_users'] > 0,
                'user_model_compatible': True,
                'kratos_integration_ready': True,
                'recommendations': [
                    "Ensure at least one super admin exists before SSO migration",
                    "Map SSO groups to STING roles during integration",
                    "Preserve existing admin privileges during migration",
                    "Test admin access before decommissioning Kratos auth",
                ]
            }
        }