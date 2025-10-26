"""
Authentication Dependencies for Knowledge Service
Provides flexible authentication that accepts both Bearer tokens and cookies
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .knowledge_auth import knowledge_auth

logger = logging.getLogger(__name__)

async def get_current_user_flexible(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any]:
    """
    Get current authenticated user from either Bearer token or cookies
    
    Args:
        request: The FastAPI request object
        credentials: Optional bearer token from Authorization header
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Check for API key authentication first (highest priority for system operations)
        api_key = request.headers.get('X-API-Key')
        if api_key:
            user_info = await knowledge_auth.verify_api_key(api_key)
            if user_info:
                logger.info(f"Authenticated via API key: {user_info.get('email')}")
                return user_info
        
        # Then try to get session from cookies (this is more reliable for browser requests)
        # Check for both Flask session cookie and Kratos session cookie
        session_token = request.cookies.get('ory_kratos_session') or \
                      request.cookies.get('ory_session_sting_ce') or \
                      request.cookies.get('sting_session')
        
        if session_token:
            logger.info(f"Found session token in cookies: {session_token[:20]}...")
            # Verify session with Kratos
            user_info = await knowledge_auth.verify_session(session_token)
            if user_info:
                logger.info(f"Successfully authenticated user via cookie: {user_info.get('email')}")
                return user_info
        
        # Then check if we have a Bearer token (fallback for API requests)
        if credentials and credentials.credentials:
            # The bearer token might be a Kratos session token
            logger.info(f"Found Bearer token: {credentials.credentials[:20]}...")
            user_info = await knowledge_auth.verify_session(credentials.credentials)
            if user_info:
                logger.info(f"Successfully authenticated user via Bearer token: {user_info.get('email')}")
                return user_info
        
        # Fall back to the original Bearer token authentication (which includes dev mode check)
        return await knowledge_auth.get_current_user(credentials, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication service error")