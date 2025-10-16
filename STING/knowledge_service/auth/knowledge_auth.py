#!/usr/bin/env python3
"""
Knowledge Authentication - Integration with STING's Kratos Auth
Handles user authentication and authorization for Knowledge Service
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import json

logger = logging.getLogger(__name__)

class KnowledgeAuth:
    """Authentication and authorization for Knowledge Service"""
    
    def __init__(self):
        self.kratos_public_url = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
        self.kratos_admin_url = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
        self.security = HTTPBearer(auto_error=False)
        
    async def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Get current authenticated user from Kratos session
        
        Args:
            credentials: Optional bearer token
            request: Optional request object to get cookies
            
        Returns:
            User information dictionary
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            # For development/testing, allow bypass with mock user
            if not credentials and os.getenv('KNOWLEDGE_DEV_MODE', 'false').lower() == 'true':
                return {
                    "id": os.getenv('KNOWLEDGE_DEV_USER_ID', 'dev-user'),
                    "email": os.getenv('KNOWLEDGE_DEV_USER_EMAIL', 'dev@sting.local'),
                    "role": os.getenv('KNOWLEDGE_DEV_USER_ROLE', 'admin'),
                    "name": {
                        "first": os.getenv('KNOWLEDGE_DEV_USER_FIRST_NAME', 'Dev'),
                        "last": os.getenv('KNOWLEDGE_DEV_USER_LAST_NAME', 'User')
                    }
                }
            
            # Try to get session token from either Bearer header or cookies
            session_token = None
            
            if credentials:
                session_token = credentials.credentials
            elif request and hasattr(request, 'cookies'):
                # Try to get session from cookies if no Bearer token
                session_token = request.cookies.get('ory_kratos_session') or \
                              request.cookies.get('ory_kratos_session')
            
            if not session_token:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Verify session with Kratos
            user_info = await self.verify_session(session_token)
            if not user_info:
                raise HTTPException(status_code=401, detail="Invalid authentication")
            
            return user_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=500, detail="Authentication service error")
    
    async def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify session token with Kratos
        
        Args:
            session_token: Session token to verify
            
        Returns:
            User information if valid, None otherwise
        """
        try:
            async with httpx.AsyncClient(verify=False) as client:
                # Try with X-Session-Token header first (for API mode sessions)
                response = await client.get(
                    f"{self.kratos_public_url}/sessions/whoami",
                    headers={"X-Session-Token": session_token},
                    timeout=10.0
                )
                
                # If header method fails, try as cookie (for browser mode sessions)
                if response.status_code != 200:
                    # Try with the configured session cookie name
                    response = await client.get(
                        f"{self.kratos_public_url}/sessions/whoami",
                        cookies={"ory_kratos_session": session_token},
                        timeout=10.0
                    )
                
                if response.status_code == 200:
                    session_data = response.json()
                    identity = session_data.get("identity", {})
                    traits = identity.get("traits", {})
                    
                    return {
                        "id": identity.get("id"),
                        "email": traits.get("email"),
                        "role": traits.get("role", "user"),
                        "name": traits.get("name", {}),
                        "session_id": session_data.get("id")
                    }
                else:
                    logger.warning(f"Kratos session verification failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to verify session with Kratos: {e}")
            return None
    
    async def can_access_honey_jar(
        self,
        user: Dict[str, Any],
        honey_jar: Dict[str, Any]
    ) -> bool:
        """
        Check if user can access a specific Honey Jar
        
        Args:
            user: User information
            honey_jar: Honey Jar information
            
        Returns:
            True if user has access, False otherwise
        """
        try:
            permissions = honey_jar.get("permissions", {})
            user_email = user.get("email", "")
            user_role = user.get("role", "user")
            
            # Public honey jars are accessible to all authenticated users
            if honey_jar.get("type") == "public":
                return True
            
            # Owner access
            if honey_jar.get("owner") == user_email:
                return True
            
            # Admin access
            if user_role == "admin":
                return True
            
            # Public read access (legacy support)
            if permissions.get("public_read", False):
                return True
            
            # Role-based access
            allowed_roles = permissions.get("allowed_roles", [])
            if user_role in allowed_roles:
                return True
            
            # User-specific access
            allowed_users = permissions.get("allowed_users", [])
            if user_email in allowed_users:
                return True
            
            # Team-based access (if implemented)
            user_teams = user.get("teams", [])
            allowed_teams = permissions.get("allowed_teams", [])
            if any(team in allowed_teams for team in user_teams):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check Honey Jar access: {e}")
            return False
    
    async def can_edit_honey_jar(
        self,
        user: Dict[str, Any],
        honey_jar: Dict[str, Any]
    ) -> bool:
        """
        Check if user can edit a specific Honey Jar
        
        Args:
            user: User information
            honey_jar: Honey Jar information
            
        Returns:
            True if user can edit, False otherwise
        """
        try:
            permissions = honey_jar.get("permissions", {})
            user_email = user.get("email", "")
            user_role = user.get("role", "user")
            
            # Owner access
            if honey_jar.get("owner") == user_email:
                return True
            
            # Admin access
            if user_role == "admin":
                return True
            
            # Public write access (rare but possible)
            if permissions.get("public_write", False):
                return True
            
            # Role-based edit access
            edit_roles = permissions.get("edit_roles", [])
            if user_role in edit_roles:
                return True
            
            # User-specific edit access
            edit_users = permissions.get("edit_users", [])
            if user_email in edit_users:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check Honey Jar edit access: {e}")
            return False
    
    async def can_create_honey_jar(self, user: Dict[str, Any]) -> bool:
        """
        Check if user can create new Honey Pots
        
        Args:
            user: User information
            
        Returns:
            True if user can create Honey Pots, False otherwise
        """
        try:
            user_role = user.get("role", "user")
            
            # Admin can always create
            if user_role == "admin":
                return True
            
            # Check configured creation roles
            creation_roles = os.getenv('KNOWLEDGE_CREATION_ROLES', 'admin,support,moderator,editor').split(',')
            if user_role in creation_roles:
                return True
            
            # Check if user has explicit creation permission
            user_permissions = user.get("permissions", {})
            if user_permissions.get("can_create_honey_jars", False):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check Honey Jar creation access: {e}")
            return False
    
    async def can_delete_honey_jar(
        self,
        user: Dict[str, Any],
        honey_jar: Dict[str, Any]
    ) -> bool:
        """
        Check if user can delete a specific Honey Jar
        
        Args:
            user: User information
            honey_jar: Honey Jar information
            
        Returns:
            True if user can delete, False otherwise
        """
        try:
            user_email = user.get("email", "")
            user_role = user.get("role", "user")
            
            # Owner can delete (with confirmation)
            if honey_jar.get("owner") == user_email:
                return True
            
            # Admin can delete
            if user_role == "admin":
                return True
            
            # Explicit delete permission
            permissions = honey_jar.get("permissions", {})
            delete_users = permissions.get("delete_users", [])
            if user_email in delete_users:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check Honey Jar delete access: {e}")
            return False
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """
        Get all roles for a user from Kratos
        
        Args:
            user_id: User ID
            
        Returns:
            List of user roles
        """
        try:
            # This would query Kratos for user roles
            # For now, return basic role mapping
            return ["user"]  # Default role
            
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return ["user"]
    
    async def get_user_teams(self, user_id: str) -> List[str]:
        """
        Get teams/groups for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of team names user belongs to
        """
        try:
            # This would query the team/group system
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get user teams: {e}")
            return []
    
    def get_permission_context(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get permission context for logging and auditing
        
        Args:
            user: User information
            
        Returns:
            Permission context dictionary
        """
        return {
            "user_id": user.get("id"),
            "user_email": user.get("email"),
            "user_role": user.get("role", "user"),
            "session_id": user.get("session_id"),
            "timestamp": "utcnow().isoformat()"
        }
    
    async def log_access_attempt(
        self,
        user: Dict[str, Any],
        resource: str,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log access attempts for security auditing
        
        Args:
            user: User information
            resource: Resource being accessed
            action: Action being attempted
            success: Whether the attempt was successful
            details: Additional details
        """
        try:
            log_entry = {
                "timestamp": "utcnow().isoformat()",
                "user_id": user.get("id"),
                "user_email": user.get("email"),
                "resource": resource,
                "action": action,
                "success": success,
                "details": details or {}
            }
            
            # In a production system, this would write to a security log
            logger.info(f"Access attempt: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify API key against STING database and return user context
        
        Args:
            api_key: API key to verify
            
        Returns:
            User information if valid, None otherwise
        """
        try:
            # First check against known system API keys for backward compatibility
            if api_key == 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0':
                logger.info("Development API key authenticated successfully")
                return {
                    "id": "system",
                    "email": "system@sting.local",
                    "role": "admin",
                    "name": {"first": "System", "last": "Operations"},
                    "auth_type": "api_key",
                    "permissions": ["system_operations", "admin"]
                }
            
            # Check for custom system API key from environment
            custom_key = os.getenv('KNOWLEDGE_SYSTEM_API_KEY')
            if custom_key and api_key == custom_key:
                logger.info("Custom system API key authenticated successfully")
                return {
                    "id": "custom_system",
                    "email": "custom_system@sting.local", 
                    "role": "admin",
                    "auth_type": "api_key",
                    "permissions": ["system_operations"]
                }
            
            # NEW: Check STING database for user-created API keys
            try:
                import httpx
                import hashlib
                
                # Call Flask app to verify API key (centralized validation)
                async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                    response = await client.get(
                        f"https://app:5050/api/keys/verify",
                        headers={"X-API-Key": api_key}
                    )
                    
                    if response.status_code == 200:
                        key_data = response.json()
                        logger.info(f"User API key authenticated: {key_data.get('name')}")
                        
                        return {
                            "id": key_data.get('user_id', 'api_user'),
                            "email": key_data.get('user_email', 'api@sting.local'),
                            "role": "admin" if "admin" in key_data.get('scopes', []) else "user",
                            "name": {
                                "first": key_data.get('name', 'API'),
                                "last": "User"
                            },
                            "auth_type": "user_api_key",
                            "permissions": key_data.get('scopes', []),
                            "api_key_name": key_data.get('name')
                        }
                        
            except Exception as db_error:
                logger.warning(f"Failed to verify API key with STING database: {db_error}")
            
            # Invalid API key
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            return None
            
        except Exception as e:
            logger.error(f"API key verification error: {e}")
            return None

# Global instance for dependency injection
knowledge_auth = KnowledgeAuth()