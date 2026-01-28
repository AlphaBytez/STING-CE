#!/usr/bin/env python3
"""
Security Configuration for Knowledge Service
Manages API keys, permissions, and rate limiting for system operations
"""

import os
from typing import Dict, List, Optional
from datetime import datetime

# System API keys with their permissions and metadata
SYSTEM_API_KEYS = {
    'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0': {
        'name': 'Development/Testing Key',
        'description': 'Primary API key for development and testing (from CLAUDE.md)',
        'permissions': ['system_operations', 'admin', 'honey_jar_management'],
        'rate_limit': None,  # No rate limiting for development
        'created_at': '2025-08-30',
        'environment': 'development'
    },
    'zluwZxtbqbaMVqQ9ubY/iFXxbTPfjFAFGigIubu7A24=': {
        'name': 'Bee Chat Service Key',
        'description': 'API key for Bee Chat service to access honey jars and context',
        'permissions': ['honey_jar_management', 'read_only'],
        'rate_limit': 200,  # 200 requests per minute for service calls
        'created_at': '2025-09-25',
        'environment': 'production'
    }
}

# Add custom system API key from environment if provided
if custom_key := os.getenv('KNOWLEDGE_SYSTEM_API_KEY'):
    SYSTEM_API_KEYS[custom_key] = {
        'name': 'Custom System Key',
        'description': 'Custom system API key from environment variable',
        'permissions': ['system_operations', 'honey_jar_management'],
        'rate_limit': 100,  # 100 requests per minute for custom keys
        'created_at': datetime.now().isoformat(),
        'environment': os.getenv('ENVIRONMENT', 'production')
    }

# Additional API keys for specific services (future expansion)
if backup_key := os.getenv('KNOWLEDGE_BACKUP_API_KEY'):
    SYSTEM_API_KEYS[backup_key] = {
        'name': 'Backup Service Key',
        'description': 'API key for automated backup operations',
        'permissions': ['system_operations', 'read_only'],
        'rate_limit': 50,  # 50 requests per minute
        'created_at': datetime.now().isoformat(),
        'environment': 'backup'
    }

# Permission definitions
PERMISSION_DEFINITIONS = {
    'system_operations': 'Full system-level operations including honey jar CRUD',
    'admin': 'Administrative access to all honey jars and operations',
    'honey_jar_management': 'Create, update, delete honey jars and documents',
    'read_only': 'Read access to honey jars and documents',
    'upload_only': 'Upload documents to existing honey jars'
}

# Rate limiting configuration (requests per minute)
DEFAULT_RATE_LIMITS = {
    'system_operations': None,  # No limit for system operations
    'admin': 1000,  # 1000 requests per minute for admin operations
    'honey_jar_management': 500,  # 500 requests per minute
    'read_only': 200,  # 200 requests per minute for read operations
    'upload_only': 100  # 100 requests per minute for uploads
}

def get_api_key_info(api_key: str) -> Optional[Dict]:
    """
    Get information about an API key
    
    Args:
        api_key: The API key to look up
        
    Returns:
        API key information dictionary or None if not found
    """
    return SYSTEM_API_KEYS.get(api_key)

def is_valid_api_key(api_key: str) -> bool:
    """
    Check if an API key is valid
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    return api_key in SYSTEM_API_KEYS

def get_api_key_permissions(api_key: str) -> List[str]:
    """
    Get permissions for an API key
    
    Args:
        api_key: The API key
        
    Returns:
        List of permissions or empty list if key not found
    """
    key_info = SYSTEM_API_KEYS.get(api_key, {})
    return key_info.get('permissions', [])

def get_api_key_rate_limit(api_key: str) -> Optional[int]:
    """
    Get rate limit for an API key
    
    Args:
        api_key: The API key
        
    Returns:
        Rate limit (requests per minute) or None for no limit
    """
    key_info = SYSTEM_API_KEYS.get(api_key, {})
    return key_info.get('rate_limit')

def has_permission(api_key: str, required_permission: str) -> bool:
    """
    Check if API key has a specific permission
    
    Args:
        api_key: The API key
        required_permission: The permission to check
        
    Returns:
        True if API key has the permission, False otherwise
    """
    permissions = get_api_key_permissions(api_key)
    return required_permission in permissions or 'admin' in permissions

# Security audit configuration
SECURITY_CONFIG = {
    'log_all_api_key_requests': True,
    'log_failed_auth_attempts': True,
    'mask_api_keys_in_logs': True,  # Only show last 8 characters
    'rate_limiting_enabled': True,
    'suspicious_activity_threshold': 10,  # Failed attempts before flagging
    'api_key_rotation_reminder_days': 90  # Remind to rotate keys after 90 days
}

def mask_api_key(api_key: str) -> str:
    """
    Mask API key for logging (security best practice)
    
    Args:
        api_key: The API key to mask
        
    Returns:
        Masked API key showing only last 8 characters
    """
    if len(api_key) <= 8:
        return '*' * len(api_key)
    return '*' * (len(api_key) - 8) + api_key[-8:]