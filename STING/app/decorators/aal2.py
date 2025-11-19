"""
Custom AAL2 (Authentication Assurance Level 2) Decorator System

This system provides custom AAL2 enforcement for sensitive operations:
- Tracks passkey enrollment status in STING database
- Manages AAL2 verification sessions in Redis
- Provides step-up authentication for biometric verification
- Separates from Kratos AAL2 to avoid configuration complexity

Architecture:
- Kratos: Handles primary authentication (email codes) = AAL1
- Custom: Handles biometric step-up verification = Custom AAL2
- Redis: Stores AAL2 session markers with TTL
"""

import logging
import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from flask import request, jsonify, g, current_app, session
from app.models.user_models import User
from app.utils.kratos_client import whoami

logger = logging.getLogger(__name__)

class CustomAAL2Manager:
    """Manages custom AAL2 verification and session tracking"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.aal2_prefix = "sting:custom_aal2:"
        self.aal2_duration = 30 * 60  # 30 minutes in seconds (extended for better UX)
        self.biometric_duration = 30 * 60  # 30 minutes in seconds for biometric verification
        
    def _get_redis_client(self):
        """Get Redis client for AAL2 session storage"""
        try:
            # Use the same Redis instance as the rest of STING
            return redis.from_url('redis://redis:6379/0')
        except Exception as e:
            logger.error(f"Failed to connect to Redis for AAL2: {e}")
            return None
    
    def check_passkey_enrollment(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user has passkey enrolled in BOTH STING and Kratos databases

        Args:
            user_id: STING user ID (integer) OR Kratos ID (UUID string)

        Returns:
            Dict with enrollment status and metadata
        """
        try:
            # Check user's passkey enrollment status in database
            # Handle both STING user ID (int) and Kratos ID (UUID string)
            if isinstance(user_id, str):
                # Kratos ID (UUID) - query by kratos_id
                user = User.query.filter_by(kratos_id=user_id).first()
            else:
                # STING user ID (int) - query by id
                user = User.query.get(user_id)
            if not user:
                return {
                    'enrolled': False,
                    'reason': 'User not found',
                    'enrollment_url': '/dashboard/settings/security'
                }
            
            # 1. Check STING database for enhanced WebAuthn (biometrics)
            sting_has_passkey = getattr(user, 'has_webauthn_credentials', False)
            sting_has_passkey = sting_has_passkey or (user.metadata and 
                                                    isinstance(user.metadata, dict) and 
                                                    user.metadata.get('webauthn_enrolled', False))
            
            # Also check the passkeys table
            try:
                from app.models.passkey_models import Passkey
                sting_passkey_count = Passkey.count_user_passkeys(user.id)
                sting_has_passkey = sting_has_passkey or (sting_passkey_count > 0)
            except Exception as e:
                logger.warning(f"Failed to check STING passkeys table: {e}")
            
            # 2. Check Kratos for WebAuthn credentials
            kratos_has_passkey = False
            kratos_has_totp = False
            
            if user.kratos_id:
                try:
                    import requests
                    import os
                    kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'https://kratos:4434')
                    response = requests.get(
                        f"{kratos_admin_url}/admin/identities/{user.kratos_id}",
                        verify=False,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        identity_data = response.json()
                        credentials = identity_data.get('credentials', {})
                        
                        # DEBUG: Log the actual credential structure
                        logger.info(f"🔍 DEBUG - Full Kratos credentials structure for {user.email}: {credentials}")
                        
                        # Check for WebAuthn credentials in Kratos - try multiple possible paths
                        kratos_has_passkey = False
                        if 'webauthn' in credentials:
                            webauthn_data = credentials.get('webauthn', {})
                            logger.info(f"🔍 DEBUG - WebAuthn data structure: {webauthn_data}")
                            
                            # Try different possible paths for credentials
                            webauthn_creds = []
                            
                            # Path 1: credentials.webauthn.config.credentials[] (current attempt)
                            if 'config' in webauthn_data and 'credentials' in webauthn_data['config']:
                                webauthn_creds = webauthn_data['config']['credentials']
                                logger.info(f"🔍 DEBUG - Found credentials via config.credentials: {len(webauthn_creds)} items")
                            
                            # Path 2: credentials.webauthn.identifiers[] (common Kratos pattern)
                            elif 'identifiers' in webauthn_data:
                                webauthn_creds = webauthn_data['identifiers']
                                logger.info(f"🔍 DEBUG - Found credentials via identifiers: {len(webauthn_creds)} items")
                            
                            # Path 3: credentials.webauthn directly has credential data
                            elif 'credential_id' in webauthn_data or 'public_key' in webauthn_data:
                                webauthn_creds = [webauthn_data]  # Single credential object
                                logger.info(f"🔍 DEBUG - Found single credential object directly")
                            
                            # Path 4: Check if webauthn_data itself is non-empty (any valid config)
                            elif webauthn_data:
                                # If webauthn section exists and has any data, assume credential exists
                                webauthn_creds = [True]  # Placeholder to indicate presence
                                logger.info(f"🔍 DEBUG - WebAuthn section exists with data, assuming credential present")
                            
                            kratos_has_passkey = len(webauthn_creds) > 0
                        
                        # Also check for TOTP (valid for AAL2)
                        kratos_has_totp = 'totp' in credentials and bool(credentials.get('totp', {}).get('config', {}))
                        
                        logger.info(f"✅ Kratos credentials final result for {user.email}: passkey={kratos_has_passkey}, totp={kratos_has_totp}")
                except Exception as e:
                    logger.warning(f"Failed to check Kratos credentials for user {user_id}: {e}")
            
            # 3. Combine results - user is enrolled if they have EITHER type OR TOTP
            total_enrolled = sting_has_passkey or kratos_has_passkey or kratos_has_totp
            
            enrollment_details = []
            if sting_has_passkey:
                enrollment_details.append("Enhanced WebAuthn/Touch ID")
            if kratos_has_passkey:
                enrollment_details.append("Kratos Passkey")
            if kratos_has_totp:
                enrollment_details.append("TOTP Authenticator")
            
            reason = f"Enrolled: {', '.join(enrollment_details)}" if total_enrolled else "No authentication methods enrolled"
            
            return {
                'enrolled': total_enrolled,
                'user_id': user_id,
                'email': user.email,
                'enrollment_url': '/dashboard/settings/security',
                'reason': reason,
                'details': {
                    'sting_webauthn': sting_has_passkey,
                    'kratos_passkey': kratos_has_passkey,
                    'kratos_totp': kratos_has_totp
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking passkey enrollment for user {user_id}: {e}")
            return {
                'enrolled': False,
                'reason': f'Database error: {str(e)}',
                'enrollment_url': '/dashboard/settings/security'
            }
    
    def set_aal2_verified(self, user_id: int, verification_method: str = 'webauthn') -> bool:
        """
        Mark user as AAL2 verified for the session duration
        
        Args:
            user_id: STING user ID
            verification_method: Method used for verification (webauthn, totp, etc.)
            
        Returns:
            bool: True if successfully stored
        """
        if not self.redis_client:
            logger.error("Redis not available for AAL2 session storage")
            return False
            
        try:
            key = f"{self.aal2_prefix}{user_id}"
            verification_data = {
                'user_id': user_id,
                'method': verification_method,
                'verified_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(seconds=self.aal2_duration)).isoformat()
            }
            
            # Store with TTL
            self.redis_client.setex(
                key, 
                self.aal2_duration, 
                json.dumps(verification_data)
            )
            
            logger.info(f"✅ Custom AAL2 verified for user {user_id} using {verification_method}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting AAL2 verification for user {user_id}: {e}")
            return False
    
    def check_aal2_verified(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user has current AAL2 verification
        
        Args:
            user_id: STING user ID
            
        Returns:
            Dict with verification status and details
        """
        if not self.redis_client:
            return {
                'verified': False,
                'reason': 'Redis not available'
            }
            
        try:
            key = f"{self.aal2_prefix}{user_id}"
            data = self.redis_client.get(key)
            
            if not data:
                return {
                    'verified': False,
                    'reason': 'No AAL2 verification found'
                }
            
            verification_data = json.loads(data.decode('utf-8'))
            
            # Check if still valid (Redis TTL should handle this, but double-check)
            expires_at = datetime.fromisoformat(verification_data['expires_at'])
            if datetime.utcnow() > expires_at:
                # Clean up expired entry
                self.redis_client.delete(key)
                return {
                    'verified': False,
                    'reason': 'AAL2 verification expired'
                }
            
            return {
                'verified': True,
                'method': verification_data['method'],
                'verified_at': verification_data['verified_at'],
                'expires_at': verification_data['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Error checking AAL2 verification for user {user_id}: {e}")
            return {
                'verified': False,
                'reason': f'Check failed: {str(e)}'
            }

    def check_biometric_verified(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user has recent biometric verification using existing biometric service

        Args:
            user_id: STING user ID

        Returns:
            Dict with biometric verification status and details
        """
        try:
            from app.services.authorization_service import authorization_service

            # Check if user has biometric auth in the last 30 minutes
            has_biometric = authorization_service.has_biometric_auth(
                user_id=user_id,
                within_minutes=30  # 30 minute window for biometric verification
            )

            if has_biometric:
                logger.info(f"✅ User {user_id} has recent biometric verification")
                return {
                    'verified': True,
                    'method': 'biometric',
                    'source': 'authorization_service',
                    'expires_in_minutes': 30
                }
            else:
                return {
                    'verified': False,
                    'reason': 'No recent biometric verification found',
                    'required_action': 'biometric_prompt'
                }

        except Exception as e:
            logger.error(f"Error checking biometric verification for user {user_id}: {e}")
            return {
                'verified': False,
                'reason': f'Biometric check failed: {str(e)}',
                'fallback_to_aal2': True
            }

    def require_aal2_for_credential_modification(self, user_id: int, operation: str = "credential modification") -> Optional[Dict[str, Any]]:
        """
        Check if AAL2 verification is required for credential modification.

        CRITICAL CHICKEN-AND-EGG HANDLING:
        - If user has 0 credentials → Allow without AAL2 (first-time setup)
        - If user has ≥1 credentials → Require AAL2 verification

        This prevents the impossible scenario where a user needs to verify with a credential
        to add their first credential.

        Args:
            user_id: STING user ID
            operation: Description of the operation being performed

        Returns:
            None if operation is allowed, Dict with error details if blocked
        """
        try:
            # Check if user has any existing credentials
            enrollment_status = self.check_passkey_enrollment(user_id)
            has_credentials = enrollment_status['enrolled']

            logger.info(f"🔐 Credential modification check for user {user_id}: has_credentials={has_credentials}, operation={operation}")

            # CHICKEN-AND-EGG EXCEPTION: Allow first credential without AAL2
            if not has_credentials:
                logger.info(f"✅ First credential setup - allowing {operation} without AAL2 for user {user_id}")
                return None  # Allow operation

            # User has existing credentials - require AAL2 verification
            aal2_status = self.check_aal2_verified(user_id)

            if aal2_status['verified']:
                logger.info(f"✅ AAL2 verified - allowing {operation} for user {user_id}")
                return None  # Allow operation

            # AAL2 not verified - block the operation
            logger.warning(f"❌ AAL2 verification required for {operation} (user {user_id} has existing credentials)")

            # Provide step-up URL for frontend to redirect user to AAL2 verification
            return {
                'error': 'AAL2_VERIFICATION_REQUIRED',
                'message': 'For security, please verify with your existing passkey or TOTP before modifying credentials',
                'code': 'AAL2_REQUIRED',
                'step_up_url': '/security-upgrade',  # Frontend route for AAL2 step-up
                'return_to': None,  # Frontend should store current location before redirecting
                'details': {
                    'reason': 'User has existing credentials - AAL2 verification required for modifications',
                    'action_required': 'Verify with existing passkey/TOTP',
                    'has_existing_credentials': True,
                    'enrollment_details': enrollment_status.get('details', {}),
                    'operation_blocked': operation
                },
                'aal2_status': {
                    'verified': False,
                    'reason': aal2_status.get('reason', 'Not verified')
                }
            }

        except Exception as e:
            logger.error(f"Error checking AAL2 requirement for credential modification: {e}")
            # Fail closed - require AAL2 on error
            return {
                'error': 'SECURITY_CHECK_FAILED',
                'message': 'Unable to verify security status. Please try again.',
                'code': 'SYSTEM_ERROR',
                'details': str(e)
            }


# Global AAL2 manager instance
aal2_manager = CustomAAL2Manager()


def require_custom_aal2(f):
    """
    Decorator to enforce custom AAL2 verification for sensitive operations
    
    This decorator:
    1. Ensures user is authenticated via Kratos (AAL1)
    2. Checks if user has passkey enrolled
    3. Verifies recent AAL2 biometric authentication
    4. Returns appropriate error responses for frontend handling
    
    Usage:
        @app.route('/api/sensitive-data')
        @require_custom_aal2
        def get_sensitive_data():
            return jsonify({"data": "secret stuff"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 1. Ensure user is authenticated (should be handled by auth middleware)
            if not hasattr(g, 'user') or not g.user:
                return jsonify({
                    'error': 'AUTHENTICATION_REQUIRED',
                    'message': 'You must be logged in to access this resource',
                    'code': 'NOT_AUTHENTICATED'
                }), 401
            
            user_id = g.user.id
            user_email = g.user.email
            
            logger.info(f"🔐 Custom AAL2 check for {user_email} (ID: {user_id}) on {request.endpoint}")
            
            # 2. Check if user has passkey enrolled
            enrollment_status = aal2_manager.check_passkey_enrollment(user_id)
            
            if not enrollment_status['enrolled']:
                logger.warning(f"User {user_email} attempted AAL2 operation without passkey enrollment")
                return jsonify({
                    'error': 'PASSKEY_ENROLLMENT_REQUIRED',
                    'message': 'This operation requires biometric authentication. Please set up a passkey first.',
                    'code': 'MISSING_PASSKEY',
                    'enrollment_url': enrollment_status['enrollment_url'],
                    'reason': enrollment_status['reason']
                }), 403
            
            # 3. Check if user has recent AAL2 verification
            aal2_status = aal2_manager.check_aal2_verified(user_id)
            
            if not aal2_status['verified']:
                logger.warning(f"User {user_email} needs AAL2 step-up for sensitive operation")
                return jsonify({
                    'error': 'AAL2_VERIFICATION_REQUIRED',
                    'message': 'This operation requires biometric verification. Please authenticate with your passkey.',
                    'code': 'STEP_UP_REQUIRED',
                    'reason': aal2_status['reason'],
                    'action': 'biometric_challenge'
                }), 403
            
            # 4. All AAL2 requirements satisfied - allow access
            logger.info(f"✅ Custom AAL2 verification passed for {user_email}")
            
            # Store AAL2 info in g for the request
            g.aal2_verified = True
            g.aal2_method = aal2_status['method']
            g.aal2_verified_at = aal2_status['verified_at']
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in custom AAL2 decorator: {str(e)}")
            return jsonify({
                'error': 'AAL2_CHECK_FAILED',
                'message': 'Unable to verify security level. Please try again.',
                'code': 'SYSTEM_ERROR'
            }), 500
    
    return decorated_function


def require_biometric_or_aal2(f):
    """
    Flexible decorator for biometric-first security with AAL2 fallback

    This decorator implements the new security model:
    1. Checks for recent biometric verification first (30 minute cache)
    2. Falls back to traditional AAL2 check if no biometric
    3. Allows TOTP as ultimate fallback
    4. Reduces Flask AAL2 management burden

    Usage:
        @app.route('/api/sensitive-operation')
        @require_biometric_or_aal2
        def sensitive_operation():
            return jsonify({"data": "protected content"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 1. Ensure user is authenticated (should be handled by auth middleware)
            if not hasattr(g, 'user') or not g.user:
                return jsonify({
                    'error': 'AUTHENTICATION_REQUIRED',
                    'message': 'You must be logged in to access this resource',
                    'code': 'NOT_AUTHENTICATED'
                }), 401

            user_id = g.user.id
            user_email = g.user.email

            logger.info(f"🔐 Biometric-first security check for {user_email} (ID: {user_id}) on {request.endpoint}")

            # 2. Check for recent biometric verification first (30 minutes)
            biometric_status = aal2_manager.check_biometric_verified(user_id)

            if biometric_status['verified']:
                logger.info(f"✅ Biometric verification passed for {user_email} - allowing access")

                # Store biometric info in g for the request
                g.biometric_verified = True
                g.verification_method = 'biometric'
                g.verification_source = biometric_status.get('source', 'authorization_service')

                return f(*args, **kwargs)

            # 3. Biometric not available, check for enrollment
            enrollment_status = aal2_manager.check_passkey_enrollment(user_id)

            if not enrollment_status['enrolled']:
                logger.warning(f"User {user_email} attempted protected operation without any 2FA enrollment")
                return jsonify({
                    'error': 'TWO_FACTOR_ENROLLMENT_REQUIRED',
                    'message': 'This operation requires two-factor authentication. Please set up TOTP or a passkey first.',
                    'code': 'MISSING_2FA',
                    'enrollment_url': enrollment_status['enrollment_url'],
                    'reason': enrollment_status['reason']
                }), 403

            # 4. Fall back to traditional AAL2 check (TOTP)
            aal2_status = aal2_manager.check_aal2_verified(user_id)

            if aal2_status['verified']:
                logger.info(f"✅ AAL2 verification passed for {user_email} - allowing access")

                # Store AAL2 info in g for the request
                g.aal2_verified = True
                g.verification_method = 'aal2'
                g.aal2_method = aal2_status['method']
                g.aal2_verified_at = aal2_status['verified_at']

                return f(*args, **kwargs)

            # 5. Neither biometric nor AAL2 verification available
            logger.warning(f"User {user_email} needs step-up authentication for protected operation")
            return jsonify({
                'error': 'STEP_UP_AUTHENTICATION_REQUIRED',
                'message': 'This operation requires additional verification. Use biometric authentication or enter your TOTP code.',
                'code': 'STEP_UP_REQUIRED',
                'options': {
                    'biometric_available': True,  # Can prompt for biometric
                    'totp_available': True,       # Can fall back to TOTP AAL2
                    'preferred_method': 'biometric'
                },
                'biometric_reason': biometric_status.get('reason'),
                'aal2_reason': aal2_status.get('reason')
            }), 403

        except Exception as e:
            logger.error(f"Error in biometric-first security decorator: {str(e)}")
            return jsonify({
                'error': 'SECURITY_CHECK_FAILED',
                'message': 'Unable to verify security level. Please try again.',
                'code': 'SYSTEM_ERROR'
            }), 500

    return decorated_function


def get_aal2_status(user_id: int) -> Dict[str, Any]:
    """
    Get comprehensive AAL2 status for a user

    Args:
        user_id: STING user ID

    Returns:
        Dict with enrollment and verification status
    """
    enrollment = aal2_manager.check_passkey_enrollment(user_id)
    # Always check AAL2 verification regardless of passkey enrollment (TOTP is also valid AAL2)
    verification = aal2_manager.check_aal2_verified(user_id)

    # Extract TOTP enrollment from enrollment details
    totp_enrolled = enrollment.get('details', {}).get('kratos_totp', False)

    return {
        'user_id': user_id,
        'passkey_enrolled': enrollment['enrolled'],
        'totp_enrolled': totp_enrolled,  # Add TOTP enrollment status
        'enrollment_url': enrollment.get('enrollment_url'),
        'aal2_verified': verification['verified'],
        'verification_method': verification.get('method'),
        'verified_at': verification.get('verified_at'),
        'expires_at': verification.get('expires_at'),
        'needs_enrollment': not enrollment['enrolled'],
        'needs_verification': enrollment['enrolled'] and not verification['verified']
    }


def verify_aal2_challenge(user_id: int, verification_method: str = 'webauthn') -> bool:
    """
    Mark AAL2 challenge as completed for a user
    
    This should be called after successful WebAuthn verification
    
    Args:
        user_id: STING user ID
        verification_method: Method used for verification
        
    Returns:
        bool: True if successfully verified
    """
    return aal2_manager.set_aal2_verified(user_id, verification_method)