"""
Default admin setup v2 — database-based admin initialization.
Provides constants and ensure_admin_exists() for startup admin creation.

Note: The actual admin setup via this module is DISABLED in __init__.py
(it was corrupting credentials on every app restart). These constants
are still imported by startup_checks.py.
"""
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@sting-ce.local')
KRATOS_ADMIN_URL = os.environ.get('KRATOS_ADMIN_URL', 'https://kratos:4434')


def ensure_admin_exists():
    """Check if default admin exists, create if not.
    
    Currently disabled at the call site in __init__.py to prevent
    credential corruption on restarts. Kept as a stub for future use.
    """
    logger.info("Admin setup v2: skipped (managed via installation wizard)")
    return False
