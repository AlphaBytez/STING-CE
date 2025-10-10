"""Kratos Admin API utilities for managing identities"""
import os
import requests
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Kratos admin API configuration
# Admin API runs on HTTPS in this setup
KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')

# Disable SSL warnings for self-signed certificates in development
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_identity_by_email(email):
    """
    Get identity from Kratos by email address
    
    Args:
        email: Email address to search for
        
    Returns:
        Identity object if found, None otherwise
    """
    try:
        # Search for identity by email trait
        url = urljoin(KRATOS_ADMIN_URL, '/admin/identities')
        
        # Note: Kratos doesn't have a direct email search, so we need to list and filter
        # In production, you might want to implement pagination for large user bases
        response = requests.get(
            url,
            params={'page_size': 1000},  # Adjust based on your needs
            verify=False  # For self-signed certs in dev
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to list identities: {response.status_code} - {response.text}")
            return None
            
        identities = response.json()
        
        # Filter by email
        for identity in identities:
            traits = identity.get('traits', {})
            if traits.get('email', '').lower() == email.lower():
                return identity
                
        return None
        
    except Exception as e:
        logger.error(f"Error getting identity by email: {e}")
        return None


def get_identity_by_id(identity_id):
    """
    Get identity from Kratos by ID
    
    Args:
        identity_id: Identity ID
        
    Returns:
        Identity object if found, None otherwise
    """
    try:
        url = urljoin(KRATOS_ADMIN_URL, f'/admin/identities/{identity_id}')
        
        response = requests.get(
            url,
            verify=False  # For self-signed certs in dev
        )
        
        if response.status_code == 404:
            return None
        elif response.status_code != 200:
            logger.error(f"Failed to get identity: {response.status_code} - {response.text}")
            return None
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error getting identity by ID: {e}")
        return None


def list_identity_sessions(identity_id):
    """
    List all sessions for an identity
    
    Args:
        identity_id: Identity ID
        
    Returns:
        List of sessions
    """
    try:
        url = urljoin(KRATOS_ADMIN_URL, f'/admin/identities/{identity_id}/sessions')
        
        response = requests.get(
            url,
            verify=False  # For self-signed certs in dev
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to list sessions: {response.status_code} - {response.text}")
            return []
            
        return response.json()
        
    except Exception as e:
        logger.error(f"Error listing identity sessions: {e}")
        return []


def delete_identity_sessions(identity_id):
    """
    Delete all sessions for an identity (logout everywhere)
    
    Args:
        identity_id: Identity ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        url = urljoin(KRATOS_ADMIN_URL, f'/admin/identities/{identity_id}/sessions')
        
        response = requests.delete(
            url,
            verify=False  # For self-signed certs in dev
        )
        
        if response.status_code != 204:
            logger.error(f"Failed to delete sessions: {response.status_code} - {response.text}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error deleting identity sessions: {e}")
        return False


def get_session_by_id(session_id):
    """
    Get session details using the Admin API
    This is the recommended way for backend services to validate sessions
    
    Args:
        session_id: The session ID (extracted from cookie value)
        
    Returns:
        Session object with identity if valid, None otherwise
    """
    try:
        # Admin API endpoint for session validation
        url = urljoin(KRATOS_ADMIN_URL, f'/admin/sessions/{session_id}')
        
        logger.info(f"Validating session via Admin API: {url}")
        
        response = requests.get(
            url,
            verify=False,  # For self-signed certs in dev
            timeout=5
        )
        
        if response.status_code == 200:
            session_data = response.json()
            logger.info(f"Session valid - Identity ID: {session_data.get('identity', {}).get('id')}")
            return session_data
        elif response.status_code == 404:
            logger.warning(f"Session not found: {session_id}")
            return None
        elif response.status_code == 401:
            logger.warning(f"Session invalid or expired: {session_id}")
            return None
        else:
            logger.error(f"Unexpected response from Admin API: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout validating session via Admin API")
        return None
    except Exception as e:
        logger.error(f"Error validating session via Admin API: {e}", exc_info=True)
        return None


def extract_session_id_from_cookie(cookie_value):
    """
    Extract the session ID from a Kratos session cookie value
    
    Kratos session cookies are in the format: "MTczNTg0NjUyOHxEdi1CQkFFQ180SUFBUkFCRUFBQVJfLUNBQUVHYzNSeWFXNW5EQThBRFhObGMzTnBiMjVmZEc5clpXNEdjM1J5YVc1bkRDSUFJRFl5WkRKaU1UUmhMVEZqWmpBdE5HWmlaQzA0WW1aaUxXRTRPVGN6TldGaE1qZGlOMnw4U0o3Nk1aaDFQa2R2UGFpWE5acVBGdE8ydGRLOE9fNHJHdGRHQ3RFcUJ3PQ=="
    The actual session ID is embedded within this base64 encoded value
    
    Args:
        cookie_value: The raw cookie value
        
    Returns:
        The session ID or the cookie value itself if extraction fails
    """
    try:
        # For now, we'll use the cookie value as-is
        # Kratos Admin API should accept the full cookie value as session ID
        return cookie_value.strip()
    except Exception as e:
        logger.error(f"Error extracting session ID from cookie: {e}")
        return cookie_value

def update_identity_password(identity_id, new_password):
    """
    Update the password for an identity
    
    Args:
        identity_id: Identity ID
        new_password: New password
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the current identity first
        url = urljoin(KRATOS_ADMIN_URL, f'/admin/identities/{identity_id}')
        response = requests.get(url, verify=False)
        
        if response.status_code != 200:
            logger.error(f"Failed to get identity: {response.status_code}")
            return False
            
        identity = response.json()
        
        # Update with new password
        update_data = {
            "schema_id": identity.get("schema_id", "default"),
            "state": "active",
            "traits": identity.get("traits", {}),
            "credentials": {
                "password": {
                    "config": {
                        "password": new_password
                    }
                }
            }
        }
        
        response = requests.put(
            url,
            json=update_data,
            verify=False
        )
        
        if response.status_code in [200, 204]:
            logger.info(f"Successfully updated password for identity {identity_id}")
            return True
        else:
            logger.error(f"Failed to update password: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating identity password: {e}")
        return False

def update_identity_traits(email, trait_updates):
    """
    Update specific traits for an identity
    
    Args:
        email: Email address of the identity
        trait_updates: Dictionary of traits to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First get the identity
        identity = get_identity_by_email(email)
        if not identity:
            logger.error(f"Identity not found for email: {email}")
            return False
            
        identity_id = identity["id"]
        
        # Get current traits and update them
        current_traits = identity.get("traits", {})
        current_traits.update(trait_updates)
        
        # Update the identity
        url = urljoin(KRATOS_ADMIN_URL, f"/admin/identities/{identity_id}")
        
        update_data = {
            "schema_id": identity.get("schema_id"),
            "state": identity.get("state"),
            "traits": current_traits
        }
        
        response = requests.put(
            url,
            json=update_data,
            verify=False  # For self-signed certs in dev
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to update identity traits: {response.status_code} - {response.text}")
            return False
            
        logger.info(f"Successfully updated traits for {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating identity traits: {e}")
        return False

