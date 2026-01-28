#!/usr/bin/env python3
"""
Security checks for installation - passwordless system
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def cleanup_legacy_password_files():
    """Clean up legacy password files from previous password-based installations"""
    
    # Legacy password file locations from old installations
    legacy_locations = [
        Path.home() / '.sting-ce' / 'admin_password.txt',
        Path('/opt/sting-ce/admin_password.txt'),
        Path('/opt/sting/admin_password.txt'),  # Legacy location
        Path('/.sting-ce/admin_password.txt'),  # Container location
    ]
    
    # Clean up any legacy password files
    cleaned_files = []
    for location in legacy_locations:
        if location.exists():
            try:
                location.unlink()
                cleaned_files.append(str(location))
                logger.info(f"Cleaned up legacy password file: {location}")
            except Exception as e:
                logger.debug(f"Could not remove {location}: {e}")
    
    if cleaned_files:
        logger.info("="*60)
        logger.info("✅ Legacy password files cleaned up")
        logger.info("="*60)
        logger.info("STING now uses passwordless authentication exclusively.")
        logger.info("Login with your email to receive a magic link.")
        logger.info("="*60)
        
        return True  # Legacy files cleaned
    
    return False  # No legacy files found

def ensure_passwordless_setup():
    """Ensure the system is configured for passwordless authentication"""
    
    # Clean up any legacy password files
    cleanup_legacy_password_files()
    
    # Log passwordless status
    logger.info("🔐 Passwordless authentication is active")
    logger.info("Default admin: admin@sting.local")
    
    return True  # Always passwordless now

if __name__ == "__main__":
    # Test the security check
    logging.basicConfig(level=logging.INFO)
    check_existing_credentials()