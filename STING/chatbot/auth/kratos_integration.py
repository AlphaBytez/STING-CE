import httpx
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class KratosAuth:
    """
    Integration with Ory Kratos for authentication
    Supports passkey/WebAuthn authentication
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.public_url = config.get('kratos_public_url', 'https://kratos:4433')
        self.admin_url = config.get('kratos_admin_url', 'https://kratos:4434')
        
        # Create HTTP client with custom settings
        self.client = httpx.AsyncClient(
            verify=False,  # For self-signed certificates in dev
            timeout=httpx.Timeout(30.0)
        )
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize Kratos connection"""
        try:
            # Test connection to Kratos
            response = await self.client.get(f"{self.admin_url}/admin/health/ready")
            if response.status_code == 200:
                self._initialized = True
                logger.info("Kratos authentication initialized successfully")
            else:
                logger.error(f"Kratos health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to initialize Kratos: {str(e)}")
            self._initialized = False
    
    async def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and get user info"""
        if not session_token:
            return None

        try:
            # Call Kratos whoami endpoint
            # Kratos expects the session token as a Cookie, not as a Bearer token
            response = await self.client.get(
                f"{self.public_url}/sessions/whoami",
                headers={
                    "Cookie": f"ory_kratos_session={session_token}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract user information
                identity = data.get('identity', {})
                traits = identity.get('traits', {})
                
                user_info = {
                    'id': identity.get('id'),
                    'email': traits.get('email'),
                    'username': traits.get('username', traits.get('email', '').split('@')[0]),
                    'role': self._get_user_role(identity),
                    'verified': identity.get('verifiable_addresses', [{}])[0].get('verified', False),
                    'session_id': data.get('id'),
                    'authenticated_at': data.get('authenticated_at'),
                    'expires_at': data.get('expires_at'),
                    'identity': identity
                }
                
                logger.info(f"Session verified for user {user_info['id']}")
                return user_info
            
            elif response.status_code == 401:
                logger.debug("Invalid or expired session token")
                return None
            else:
                logger.error(f"Kratos session verification failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error verifying session: {str(e)}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by ID (requires admin access)"""
        try:
            response = await self.client.get(
                f"{self.admin_url}/admin/identities/{user_id}"
            )
            
            if response.status_code == 200:
                identity = response.json()
                traits = identity.get('traits', {})
                
                return {
                    'id': identity.get('id'),
                    'email': traits.get('email'),
                    'username': traits.get('username', traits.get('email', '').split('@')[0]),
                    'role': self._get_user_role(identity),
                    'verified': identity.get('verifiable_addresses', [{}])[0].get('verified', False),
                    'created_at': identity.get('created_at'),
                    'updated_at': identity.get('updated_at')
                }
            else:
                logger.error(f"Failed to get user {user_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
    
    async def check_passkey_support(self, user_id: str) -> bool:
        """Check if user has passkey/WebAuthn credentials"""
        try:
            user_info = await self.get_user_by_id(user_id)
            if not user_info:
                return False
            
            # Check for WebAuthn credentials in identity
            identity = user_info.get('identity', {})
            credentials = identity.get('credentials', {})
            
            # Check if user has webauthn credentials
            if 'webauthn' in credentials:
                webauthn_creds = credentials['webauthn']
                if webauthn_creds and webauthn_creds.get('identifiers'):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking passkey support: {str(e)}")
            return False
    
    async def initiate_passkey_login(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Initiate passkey login flow"""
        try:
            # Create a login flow
            response = await self.client.get(
                f"{self.public_url}/self-service/login/api"
            )
            
            if response.status_code == 200:
                flow = response.json()
                
                return {
                    'flow_id': flow.get('id'),
                    'ui': flow.get('ui'),
                    'expires_at': flow.get('expires_at'),
                    'type': 'passkey',
                    'public_url': f"{self.public_url}/self-service/login/flows?id={flow.get('id')}"
                }
            else:
                logger.error(f"Failed to initiate passkey login: {response.status_code}")
                return {'error': 'Failed to initiate login'}
                
        except Exception as e:
            logger.error(f"Error initiating passkey login: {str(e)}")
            return {'error': str(e)}
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        try:
            response = await self.client.get(
                f"{self.admin_url}/admin/identities/{user_id}/sessions"
            )
            
            if response.status_code == 200:
                sessions = response.json()
                
                return [{
                    'id': session.get('id'),
                    'authenticated_at': session.get('authenticated_at'),
                    'expires_at': session.get('expires_at'),
                    'active': session.get('active', False),
                    'authentication_methods': session.get('authentication_methods', [])
                } for session in sessions]
            else:
                logger.error(f"Failed to get user sessions: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a specific session"""
        try:
            response = await self.client.delete(
                f"{self.admin_url}/admin/sessions/{session_id}"
            )
            
            if response.status_code in [204, 200]:
                logger.info(f"Session {session_id} revoked successfully")
                return True
            else:
                logger.error(f"Failed to revoke session: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking session: {str(e)}")
            return False
    
    def _get_user_role(self, identity: Dict[str, Any]) -> str:
        """Extract user role from identity"""
        traits = identity.get('traits', {})
        
        # Check for role in traits
        role = traits.get('role', 'end_user')
        
        # Check for admin email patterns
        email = traits.get('email', '')
        if email.endswith('@admin.sting.local') or email in self.config.get('admin_emails', []):
            role = 'admin'
        elif email.endswith('@support.sting.local'):
            role = 'support'
        
        return role
    
    async def is_healthy(self) -> bool:
        """Health check for Kratos auth"""
        try:
            response = await self.client.get(
                f"{self.admin_url}/admin/health/ready",
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()