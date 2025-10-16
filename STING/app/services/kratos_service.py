"""
Kratos Admin API Service
Handles communication with Kratos Admin API for identity management
"""

import logging
import requests
from flask import current_app
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class KratosAdminService:
    """Service for interacting with Kratos Admin API"""
    
    def __init__(self):
        self._admin_url = None
        self._verify_ssl = None
    
    @property
    def admin_url(self):
        if self._admin_url is None:
            # Get Kratos admin URL from config or environment
            self._admin_url = current_app.config.get('KRATOS_ADMIN_URL', 'https://kratos:4434')
        return self._admin_url
    
    @property
    def verify_ssl(self):
        if self._verify_ssl is None:
            # Disable SSL verification for local development
            self._verify_ssl = current_app.config.get('KRATOS_VERIFY_SSL', False)
        return self._verify_ssl
        
    def get_identity(self, identity_id: str) -> Optional[Dict[str, Any]]:
        """Get identity by ID from Kratos"""
        try:
            url = f"{self.admin_url}/admin/identities/{identity_id}"
            response = requests.get(url, verify=self.verify_ssl)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Identity not found: {identity_id}")
                return None
            else:
                logger.error(f"Failed to get identity: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching identity from Kratos: {e}")
            return None
    
    def update_identity_traits(self, identity_id: str, traits: Dict[str, Any]) -> bool:
        """Update identity traits in Kratos"""
        try:
            # First get the current identity to preserve existing data
            current_identity = self.get_identity(identity_id)
            if not current_identity:
                return False
            
            # Merge new traits with existing ones
            current_traits = current_identity.get('traits', {})
            
            # Update profile section
            if 'profile' not in current_traits:
                current_traits['profile'] = {}
            
            # Update each profile field if provided
            profile_updates = {}
            if 'displayName' in traits:
                profile_updates['displayName'] = traits['displayName']
            if 'bio' in traits:
                profile_updates['bio'] = traits['bio']
            if 'location' in traits:
                profile_updates['location'] = traits['location']
            if 'website' in traits:
                profile_updates['website'] = traits['website']
            if 'organization' in traits:
                profile_updates['organization'] = traits['organization']
            if 'profilePicture' in traits:
                profile_updates['profilePicture'] = traits['profilePicture']
            
            current_traits['profile'].update(profile_updates)
            
            # Update name if provided
            if 'firstName' in traits or 'lastName' in traits:
                if 'name' not in current_traits:
                    current_traits['name'] = {}
                if 'firstName' in traits:
                    current_traits['name']['first'] = traits['firstName']
                if 'lastName' in traits:
                    current_traits['name']['last'] = traits['lastName']
            
            # Prepare the update payload
            update_payload = {
                "schema_id": current_identity.get('schema_id', 'default'),
                "state": current_identity.get('state', 'active'),
                "traits": current_traits
            }
            
            # Send update request
            url = f"{self.admin_url}/admin/identities/{identity_id}"
            response = requests.put(
                url, 
                json=update_payload,
                headers={'Content-Type': 'application/json'},
                verify=self.verify_ssl
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated identity traits for {identity_id}")
                return True
            else:
                logger.error(f"Failed to update identity: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating identity traits: {e}")
            return False
    
    def get_identity_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find identity by email address"""
        try:
            # Use the list identities endpoint with email filter
            url = f"{self.admin_url}/admin/identities"
            params = {
                'credentials_identifier': email
            }
            response = requests.get(url, params=params, verify=self.verify_ssl)
            
            if response.status_code == 200:
                identities = response.json()
                # Filter for exact email match
                for identity in identities:
                    if identity.get('traits', {}).get('email') == email:
                        return identity
                return None
            else:
                logger.error(f"Failed to search identities: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for identity by email: {e}")
            return None

# Create a singleton instance
kratos_admin = KratosAdminService()