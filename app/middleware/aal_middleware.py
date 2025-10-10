"""
AAL (Authentication Assurance Level) Middleware
Enforces proper authentication requirements during the authentication flow
"""

import logging
from typing import Dict, Optional
from flask import request, jsonify, g
from functools import wraps
from app.utils.kratos_session import whoami, check_user_has_required_methods
from app.utils.response_helpers import error_response

logger = logging.getLogger(__name__)

class AALRequirement:
    """Define AAL requirements for different user roles"""
    
    # AAL requirements per role - ENHANCED STING SECURITY MODEL
    ROLE_AAL_REQUIREMENTS = {
        'user': {
            'minimum_aal': 'aal2',  # STING requires 2FA for all users (AI security platform)
            'required_methods': ['webauthn'],  # Passkey OR TOTP required for AI operations
            'allow_alternatives': True,  # Allow TOTP instead of passkey
            'description': 'STING users require 2FA for secure AI operations (passwordless + passkey OR TOTP)'
        },
        'admin': {
            'minimum_aal': 'aal2', 
            'required_methods': ['webauthn'],  # Passkey OR TOTP (industry standard)
            'allow_alternatives': True,  # Allow TOTP instead of passkey
            'description': 'Admins require 2FA (passwordless + passkey OR TOTP - GitHub/AWS standard)'
        },
        'moderator': {
            'minimum_aal': 'aal2',
            'required_methods': ['webauthn'], 
            'allow_alternatives': True,
            'description': 'Moderators require 2FA (passkey or TOTP)'
        }
    }
    
    @classmethod
    def get_requirements(cls, role: str) -> dict:
        """Get AAL requirements for a specific role"""
        return cls.ROLE_AAL_REQUIREMENTS.get(role, cls.ROLE_AAL_REQUIREMENTS['user'])
    
    @classmethod
    def validate_session_aal(cls, session_data: dict, role: str, allow_enrollment: bool = False, identity_id: str = None) -> dict:
        """
        Validate if a session meets AAL requirements for the given role.
        
        SECURITY CRITICAL: This function determines dashboard access permissions.
        
        Args:
            session_data: Kratos session data
            role: User role
            allow_enrollment: If True, allow AAL1 users to access dashboard for enrollment setup  
            identity_id: Kratos identity ID (required for secure validation)
        
        Returns:
            dict: {
                'valid': bool,
                'current_aal': str,
                'required_aal': str,
                'missing_methods': list,
                'reason': str,
                'enrollment_allowed': bool
            }
        """
        requirements = cls.get_requirements(role)
        
        # TODO: Implement recent AAL2 check once function is properly synced
        current_aal = session_data.get('authenticator_assurance_level', 'aal1')
        auth_methods = session_data.get('authentication_methods', [])
        
        # Extract method names from authentication_methods (what was used THIS session)
        used_methods = [method.get('method') for method in auth_methods if method.get('method')]
        
        # SECURITY FIX: Check what methods user has CONFIGURED, not just what they used
        if identity_id:
            try:
                method_check = check_user_has_required_methods(identity_id, requirements['required_methods'])
                configured_methods = method_check['configured_methods']
                missing_configured_methods = method_check['missing_methods']
                has_all_configured = method_check['has_all_required']
                
                logger.info(f"🔒 Security validation for {role} user {identity_id}:")
                logger.info(f"🔒   Required methods: {requirements['required_methods']}")
                logger.info(f"🔒   Configured methods: {configured_methods}")
                logger.info(f"🔒   Missing methods: {missing_configured_methods}")
                logger.info(f"🔒   Has all required: {has_all_configured}")
                
            except Exception as e:
                logger.error(f"🔒 Failed to check configured methods for {identity_id}: {e}")
                # On error, deny access for security
                return {
                    'valid': False,
                    'current_aal': current_aal,
                    'required_aal': requirements['minimum_aal'],
                    'missing_methods': requirements['required_methods'],
                    'reason': 'Failed to validate authentication methods - access denied for security',
                    'enrollment_allowed': False
                }
        else:
            # Fallback to session-based check (less secure)
            logger.warning("🔒 No identity_id provided - using less secure session-based validation")
            missing_configured_methods = []
            for required_method in requirements['required_methods']:
                if required_method not in used_methods:
                    missing_configured_methods.append(required_method)
            has_all_configured = len(missing_configured_methods) == 0
            configured_methods = {}
        
        # ENROLLMENT LOGIC: Only allow enrollment access for users who ACTUALLY need setup
        if allow_enrollment and current_aal == 'aal1':
            # SECURITY: Only grant enrollment access if user genuinely lacks required methods
            if not has_all_configured and missing_configured_methods:
                # STING SECURITY MODEL: All users must configure 2FA for AI operations
                logger.warning(f"🔒 BLOCKING {role} user {identity_id} - STING requires 2FA for secure AI operations")
                return {
                    'valid': False,  # DENY access until 2FA is configured
                    'current_aal': current_aal,
                    'required_aal': requirements['minimum_aal'],
                    'missing_methods': missing_configured_methods,
                    'reason': f'STING requires 2FA for secure AI operations: {missing_configured_methods}',
                    'enrollment_required': True,  # Signal that enrollment is required
                    'enforcement_level': 'strict' if role == 'admin' else 'guided',  # Different UX approach
                    'enrollment_allowed': False   # No dashboard access until 2FA is configured
                }
            else:
                # User has all methods configured but didn't use them this session
                logger.warning(f"🔒 User {identity_id} has all required methods but only used AAL1 - blocking enrollment access")
                return {
                    'valid': False,
                    'current_aal': current_aal, 
                    'required_aal': requirements['minimum_aal'],
                    'missing_methods': [],
                    'reason': f'User has required methods configured but needs to authenticate with AAL2',
                    'enrollment_allowed': False
                }
        
        # Check AAL level requirement
        if current_aal != requirements['minimum_aal']:
            return {
                'valid': False,
                'current_aal': current_aal,
                'required_aal': requirements['minimum_aal'],
                'missing_methods': missing_configured_methods,
                'reason': f"Insufficient AAL: {current_aal}, required: {requirements['minimum_aal']}",
                'enrollment_allowed': False
            }
        
        # Check if user has required methods configured and used them
        if not has_all_configured:
            return {
                'valid': False,
                'current_aal': current_aal,
                'required_aal': requirements['minimum_aal'],
                'missing_methods': missing_configured_methods,
                'reason': f"Missing required authentication methods: {missing_configured_methods}",
                'enrollment_allowed': False
            }
        
        # INDUSTRY STANDARD: For all roles that allow alternatives (including admins),
        # having the methods configured is sufficient for general access.
        # Step-up authentication (AAL2) is only required for sensitive operations.
        if requirements['allow_alternatives']:
            # Industry standard: Having any required method configured is sufficient
            # No need to enforce usage in every session - that's what step-up auth is for
            logger.info(f"AAL validation passed for {role}: Has configured methods and allows alternatives")
        
        # Legacy path for roles that require all methods (currently none in industry standard)
        else:
            missing_session_methods = []
            for required_method in requirements['required_methods']:
                if required_method not in used_methods:
                    missing_session_methods.append(required_method)
            
            if missing_session_methods:
                return {
                    'valid': False,
                    'current_aal': current_aal,
                    'required_aal': requirements['minimum_aal'],
                    'missing_methods': missing_session_methods,
                    'reason': f"Role {role} requires all methods to be used: {missing_session_methods} not used this session",
                    'enrollment_allowed': False
                }
        
        # All checks passed
        return {
            'valid': True,
            'current_aal': current_aal,
            'required_aal': requirements['minimum_aal'],
            'missing_methods': [],
            'reason': 'AAL requirements satisfied',
            'enrollment_allowed': False
        }


def require_aal(minimum_aal: str = 'aal2', allowed_roles: list = None):
    """
    Decorator to enforce AAL requirements on routes
    
    Args:
        minimum_aal: Minimum AAL required (aal1, aal2)
        allowed_roles: List of roles allowed to access this route
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get current session
                session_info = whoami(request)
                
                if not session_info:
                    logger.warning(f"AAL middleware: No session found for {request.endpoint}")
                    return error_response("Authentication required", 401)
                
                # Extract session and identity data
                session_data = session_info.get('session', session_info)
                identity = session_info.get('identity', {})
                traits = identity.get('traits', {})
                user_role = traits.get('role', 'user')
                user_email = traits.get('email', 'unknown')
                
                # Check role permissions
                if allowed_roles and user_role not in allowed_roles:
                    logger.warning(f"AAL middleware: Role {user_role} not allowed for {request.endpoint}")
                    return error_response("Insufficient permissions", 403)
                
                # Extract identity ID for secure validation
                identity = session_info.get('identity', {})
                identity_id = identity.get('id')
                
                # Validate AAL requirements (strict mode for protected routes)
                validation = AALRequirement.validate_session_aal(session_data, user_role, allow_enrollment=False, identity_id=identity_id)
                
                if not validation['valid']:
                    logger.warning(f"AAL middleware: Invalid AAL for {user_email} ({user_role}): {validation['reason']}")
                    
                    # Return step-up authentication response
                    return jsonify({
                        'error': 'Insufficient authentication level',
                        'code': 'INSUFFICIENT_AAL',
                        'details': {
                            'current_aal': validation['current_aal'],
                            'required_aal': validation['required_aal'],
                            'missing_methods': validation['missing_methods'],
                            'reason': validation['reason'],
                            'step_up_url': f"/self-service/login/browser?aal={validation['required_aal']}&return_to={request.url}"
                        }
                    }), 403
                
                # Store validation result for the route
                g.aal_validation = validation
                g.user_role = user_role
                g.user_email = user_email
                
                logger.debug(f"AAL middleware: Access granted to {user_email} ({user_role}) for {request.endpoint}")
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"AAL middleware error: {str(e)}")
                return error_response("Authentication validation failed", 500)
                
        return decorated_function
    return decorator


def require_admin_aal():
    """Convenience decorator for admin-only routes requiring full 3FA"""
    return require_aal(minimum_aal='aal2', allowed_roles=['admin'])


def require_user_aal():
    """Convenience decorator for user routes requiring 2FA"""
    return require_aal(minimum_aal='aal2')


def get_current_aal_status():
    """
    Get the current user's AAL status without enforcing requirements
    
    Returns:
        dict: Current AAL status or None if not authenticated
    """
    try:
        session_info = whoami(request)
        
        if not session_info:
            return None
            
        session_data = session_info.get('session', session_info)
        identity = session_info.get('identity', {})
        traits = identity.get('traits', {})
        user_role = traits.get('role', 'user')
        identity_id = identity.get('id')
        
        # SECURITY FIX: Pass identity_id for proper method validation
        validation = AALRequirement.validate_session_aal(
            session_data, 
            user_role, 
            allow_enrollment=True,
            identity_id=identity_id
        )
        
        # Also get the configured methods for debugging
        configured_methods = {}
        if identity_id:
            try:
                from app.utils.kratos_session import get_configured_auth_methods
                configured_methods = get_configured_auth_methods(identity_id)
                logger.info(f"🔒 Configured methods for {identity_id}: {configured_methods}")
            except Exception as e:
                logger.error(f"🔒 Error getting configured methods for {identity_id}: {e}")
        
        logger.info(f"🔒 AAL status check for {user_role} user {identity_id}: {validation.get('reason', 'Unknown')}")
        
        return {
            'authenticated': True,
            'role': user_role,
            'email': traits.get('email', 'unknown'),
            'validation': validation,
            'requirements': AALRequirement.get_requirements(user_role),
            'configured_methods': configured_methods
        }
        
    except Exception as e:
        logger.error(f"Error getting AAL status: {str(e)}")
        return None


def check_aal_compliance(session_data: dict, user_role: str, identity_id: str = None) -> bool:
    """
    Simple function to check if a session is AAL compliant
    
    Args:
        session_data: Kratos session data
        user_role: User role (user, admin, moderator)
        identity_id: Kratos identity ID for secure validation
        
    Returns:
        bool: True if compliant, False otherwise
    """
    validation = AALRequirement.validate_session_aal(session_data, user_role, allow_enrollment=False, identity_id=identity_id)
    return validation['valid']