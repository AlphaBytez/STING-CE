import os
import requests
import logging

logger = logging.getLogger(__name__)

# Public URL of the Kratos API (sessions, identity)
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://localhost:4433')

def whoami(session_credential: str, is_token: bool = False):
    """
    Call Kratos /sessions/whoami to retrieve the authenticated identity.
    Returns JSON on success or None otherwise.
    """
    if not session_credential:
        logger.warning("No session credential provided to whoami")
        return None
    try:
        # Use token in header or cookie based on type
        if is_token:
            headers = {'Authorization': f'Bearer {session_credential}'}
            cookies = {}
            logger.info(f"Calling Kratos whoami with Bearer token")
        else:
            headers = {}
            # Use the standard Kratos session cookie name
            cookies = {
                'ory_kratos_session': session_credential
            }
            logger.info(f"Calling Kratos whoami with session cookie: ory_kratos_session")
            
        logger.info(f"Calling Kratos whoami at {KRATOS_PUBLIC_URL}/sessions/whoami")
        logger.info(f"Request cookies: {list(cookies.keys())}")
        
        # Add timeout to prevent hanging
        resp = requests.get(
            f"{KRATOS_PUBLIC_URL}/sessions/whoami", 
            cookies=cookies, 
            headers=headers, 
            verify=False,
            timeout=5
        )
        
        logger.info(f"Kratos whoami response status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            identity = data.get('identity', {})
            logger.info(f"Kratos whoami success - identity ID: {identity.get('id')}, email: {identity.get('traits', {}).get('email')}")
            return data
        elif resp.status_code == 401:
            logger.warning(f"Kratos session invalid or expired (401)")
            try:
                error_data = resp.json()
                logger.warning(f"Kratos error: {error_data}")
            except:
                logger.warning(f"Kratos error response: {resp.text}")
        elif resp.status_code == 403:
            # CRITICAL FIX: Return AAL2 error data instead of None
            logger.warning(f"Kratos session requires AAL2 (403)")
            try:
                error_data = resp.json()
                logger.error(f"Response: {error_data}")
                
                # Check if this is specifically an AAL2 error
                if (error_data.get('error', {}).get('id') == 'session_aal2_required' or 
                    'aal2' in str(error_data).lower()):
                    logger.info("Detected AAL2 error - returning error data for middleware")
                    return error_data  # Return the error data instead of None
                else:
                    logger.warning(f"403 error but not AAL2-related: {error_data}")
            except:
                logger.error(f"Response text: {resp.text}")
        else:
            logger.error(f"Kratos whoami returned unexpected status: {resp.status_code}")
            try:
                logger.error(f"Response: {resp.json()}")
            except:
                logger.error(f"Response text: {resp.text}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling Kratos whoami at {KRATOS_PUBLIC_URL}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error calling Kratos: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling Kratos whoami: {e}", exc_info=True)
        return None
    return None


def logout(session_credential: str):
    """
    Call Kratos logout endpoint to invalidate the session.
    Note: Kratos v1.3.1 may not support this endpoint properly.
    """
    if not session_credential:
        logger.warning("No session credential provided to logout")
        return False
    
    try:
        # Kratos expects the logout flow to be initiated first
        # For now, we'll just log the attempt since v1.3.1 doesn't support it well
        logger.info(f"Attempting Kratos logout (may not be supported in v1.3.1)")
        
        # Try to revoke the session
        cookies = {
            'ory_kratos_session': session_credential
        }
        
        # Attempt to get logout flow (may not work in v1.3.1)
        resp = requests.get(
            f"{KRATOS_PUBLIC_URL}/self-service/logout/browser",
            cookies=cookies,
            verify=False,
            timeout=5,
            allow_redirects=False
        )
        
        if resp.status_code in [200, 302, 303]:
            logger.info("Kratos logout flow initiated")
            return True
        else:
            logger.warning(f"Kratos logout returned status: {resp.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error during Kratos logout: {e}")
        return False