# app/utils/audit_logger.py
"""
Audit logging utilities for STING application.
Provides convenient functions for logging security and authentication events.
"""

from flask import request, g, session
from app.models.audit_log_models import AuditLog, AuditEventType, AuditSeverity
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class AuditLogger:
    """Centralized audit logging functionality"""

    @staticmethod
    def get_current_user():
        """Get current user from Flask context"""
        return getattr(g, 'user', None)

    @staticmethod
    def get_current_request():
        """Get current request object"""
        try:
            return request
        except RuntimeError:
            # Outside request context
            return None

    @classmethod
    def log_authentication_success(cls, user, auth_method, tier=None, details=None):
        """Log successful authentication event"""
        return AuditLog.log_auth_success(
            user=user,
            auth_method=auth_method,
            tier=tier,
            request=cls.get_current_request(),
            details=details
        )

    @classmethod
    def log_authentication_failure(cls, email, auth_method, reason, details=None):
        """Log failed authentication attempt"""
        return AuditLog.log_auth_failure(
            email=email,
            auth_method=auth_method,
            reason=reason,
            request=cls.get_current_request(),
            details=details
        )

    @classmethod
    def log_tiered_auth_event(cls, operation, tier, success=True, user=None, details=None):
        """Log tiered authentication event"""
        user = user or cls.get_current_user()
        if not user:
            logger.warning("Cannot log tiered auth event: no user context")
            return None

        if success:
            message = f"Tiered auth success (Tier {tier}) for {operation} by {user.email}"
            event_type = AuditEventType.TIERED_AUTH_SUCCESS
            severity = AuditSeverity.MEDIUM
        else:
            message = f"Tiered auth failed (Tier {tier}) for {operation} by {user.email}"
            event_type = AuditEventType.TIERED_AUTH_FAILED
            severity = AuditSeverity.HIGH

        return AuditLog.log_event(
            event_type=event_type,
            message=message,
            user=user,
            request=cls.get_current_request(),
            severity=severity.value,
            auth_tier=tier,
            action=operation,
            success=success,
            details=details
        )

    @classmethod
    def log_api_key_event(cls, action, api_key_name=None, scopes=None, success=True, error=None):
        """Log API key related events"""
        user = cls.get_current_user()
        if not user:
            logger.warning("Cannot log API key event: no user context")
            return None

        if action == 'create':
            event_type = AuditEventType.API_KEY_CREATED
            message = f"API key '{api_key_name}' created by {user.email}"
        elif action == 'delete':
            event_type = AuditEventType.API_KEY_DELETED
            message = f"API key '{api_key_name}' deleted by {user.email}"
        else:
            event_type = AuditEventType.API_KEY_USED
            message = f"API key '{api_key_name}' used by {user.email}"

        details = {
            'action': action,
            'api_key_name': api_key_name,
            'scopes': scopes
        }

        if error:
            details['error'] = error

        return AuditLog.log_event(
            event_type=event_type,
            message=message,
            user=user,
            request=cls.get_current_request(),
            severity=AuditSeverity.HIGH.value,
            resource=f"api_key:{api_key_name}" if api_key_name else "api_key",
            action=action,
            success=success,
            error_message=error,
            details=details
        )

    @classmethod
    def log_recovery_code_event(cls, action, count=None, success=True, error=None):
        """Log recovery code events"""
        user = cls.get_current_user()
        if not user:
            logger.warning("Cannot log recovery code event: no user context")
            return None

        if action == 'generate':
            event_type = AuditEventType.RECOVERY_CODES_GENERATED
            message = f"Generated {count} recovery codes for {user.email}"
        elif action == 'use':
            event_type = AuditEventType.RECOVERY_CODE_USED
            message = f"Recovery code used by {user.email}"
        elif action == 'revoke':
            event_type = AuditEventType.RECOVERY_CODES_REVOKED
            message = f"Recovery codes revoked for {user.email}"
        else:
            return None

        details = {'action': action}
        if count:
            details['count'] = count
        if error:
            details['error'] = error

        return AuditLog.log_event(
            event_type=event_type,
            message=message,
            user=user,
            request=cls.get_current_request(),
            severity=AuditSeverity.HIGH.value,
            action=action,
            success=success,
            error_message=error,
            details=details
        )

    @classmethod
    def log_passkey_event(cls, action, success=True, error=None, details=None):
        """Log passkey/WebAuthn events"""
        user = cls.get_current_user()
        if not user:
            logger.warning("Cannot log passkey event: no user context")
            return None

        event_mapping = {
            'register': AuditEventType.PASSKEY_REGISTERED,
            'authenticate': AuditEventType.PASSKEY_AUTH_SUCCESS if success else AuditEventType.PASSKEY_AUTH_FAILED,
            'delete': AuditEventType.PASSKEY_DELETED
        }

        event_type = event_mapping.get(action)
        if not event_type:
            logger.warning(f"Unknown passkey action: {action}")
            return None

        if success:
            message = f"Passkey {action} successful for {user.email}"
        else:
            message = f"Passkey {action} failed for {user.email}"
            if error:
                message += f": {error}"

        event_details = {'action': action}
        if details:
            event_details.update(details)
        if error:
            event_details['error'] = error

        return AuditLog.log_event(
            event_type=event_type,
            message=message,
            user=user,
            request=cls.get_current_request(),
            severity=AuditSeverity.HIGH.value,
            auth_method='webauthn',
            action=action,
            success=success,
            error_message=error,
            details=event_details
        )

    @classmethod
    def log_security_event(cls, description, severity=AuditSeverity.HIGH, user=None, details=None):
        """Log general security events"""
        user = user or cls.get_current_user()

        return AuditLog.log_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            message=description,
            user=user,
            request=cls.get_current_request(),
            severity=severity.value,
            details=details
        )

def audit_auth_decorator(auth_method, tier=None):
    """
    Decorator to automatically audit authentication events.

    Usage:
        @audit_auth_decorator('totp', tier=2)
        def my_protected_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = AuditLogger.get_current_user()
            operation = func.__name__

            try:
                # Log the authentication challenge
                AuditLogger.log_tiered_auth_event(
                    operation=operation,
                    tier=tier,
                    success=True,
                    user=user,
                    details={
                        'function': func.__name__,
                        'auth_method': auth_method,
                        'tier': tier
                    }
                )

                # Execute the function
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                # Log the failure
                AuditLogger.log_tiered_auth_event(
                    operation=operation,
                    tier=tier,
                    success=False,
                    user=user,
                    details={
                        'function': func.__name__,
                        'auth_method': auth_method,
                        'tier': tier,
                        'error': str(e)
                    }
                )
                raise

        return wrapper
    return decorator

def audit_action(action, resource=None, severity=AuditSeverity.MEDIUM):
    """
    Decorator to audit general actions.

    Usage:
        @audit_action('document_upload', resource='honey_jar', severity=AuditSeverity.HIGH)
        def upload_document():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = AuditLogger.get_current_user()

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Log successful action
                AuditLog.log_event(
                    event_type=AuditEventType.SENSITIVE_DATA_ACCESS,
                    message=f"{action} performed by {user.email if user else 'anonymous'}",
                    user=user,
                    request=AuditLogger.get_current_request(),
                    severity=severity.value,
                    resource=resource,
                    action=action,
                    success=True,
                    details={
                        'function': func.__name__,
                        'action': action,
                        'resource': resource
                    }
                )

                return result

            except Exception as e:
                # Log failed action
                AuditLog.log_event(
                    event_type=AuditEventType.SENSITIVE_DATA_ACCESS,
                    message=f"{action} failed for {user.email if user else 'anonymous'}: {str(e)}",
                    user=user,
                    request=AuditLogger.get_current_request(),
                    severity=AuditSeverity.HIGH.value,
                    resource=resource,
                    action=action,
                    success=False,
                    error_message=str(e),
                    details={
                        'function': func.__name__,
                        'action': action,
                        'resource': resource,
                        'error': str(e)
                    }
                )
                raise

        return wrapper
    return decorator