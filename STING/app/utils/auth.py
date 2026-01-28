"""
Auth utilities module - provides centralized auth decorators.

This module re-exports auth decorators from their implementation files
to provide a single import point for routes.
"""

# Import from the actual implementations
from app.utils.flexible_auth import require_auth_flexible
from app.middleware.kratos_auth_middleware import require_admin, require_auth

# Re-export for convenience
__all__ = [
    'require_auth_flexible',
    'require_admin',
    'require_auth',
]
