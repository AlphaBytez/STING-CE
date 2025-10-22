"""
Enhanced AAL2 check for biometric WebAuthn authentication.

This module implements custom logic to determine if WebAuthn authentication 
qualifies for AAL2 based on authenticator characteristics, specifically 
detecting biometric authentications that Kratos treats as AAL1.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def check_webauthn_aal2_eligibility(session_data: Dict[str, Any]) -> bool:
    """
    Custom logic to determine if WebAuthn authentication qualifies for AAL2
    based on authenticator characteristics
    
    Args:
        session_data: Session data from Kratos or enhanced WebAuthn
        
    Returns:
        bool: True if WebAuthn authentication should qualify for AAL2
    """
    logger.debug("Checking WebAuthn AAL2 eligibility for session: %s", session_data.get('id', 'unknown'))
    
    # Check if user used WebAuthn with user verification
    authentication_methods = session_data.get('authentication_methods', [])
    webauthn_methods = [m for m in authentication_methods if m.get('method') == 'webauthn']
    
    for method in webauthn_methods:
        # Check for UV flag or biometric indicators
        if method.get('user_verified') or method.get('biometric_used'):
            logger.info("WebAuthn AAL2 qualified: User verification detected")
            return True
    
    # Check for enhanced WebAuthn session marker
    if session_data.get('auth_method') == 'enhanced_webauthn':
        # Enhanced WebAuthn sessions often involve biometric verification
        if session_data.get('custom_aal2_verified'):
            logger.info("WebAuthn AAL2 qualified: Custom AAL2 verification flag set")
            return True
        
        # Check for biometric session markers
        if session_data.get('biometric_verified') or session_data.get('user_verification_performed'):
            logger.info("WebAuthn AAL2 qualified: Biometric verification detected in enhanced session")
            return True
    
    # Check device characteristics from identity credentials
    identity = session_data.get('identity', {})
    credentials = identity.get('credentials', {})
    
    if 'webauthn' in credentials:
        webauthn_creds = credentials['webauthn'].get('credentials', [])
        
        for cred in webauthn_creds:
            # Platform authenticators (built-in) often support biometrics
            if cred.get('authenticator_attachment') == 'platform':
                logger.info("WebAuthn AAL2 qualified: Platform authenticator detected")
                return True
            
            # Check for specific biometric authenticator types
            authenticator_metadata = cred.get('authenticator_metadata', {})
            if authenticator_metadata.get('biometric_capable'):
                logger.info("WebAuthn AAL2 qualified: Biometric-capable authenticator")
                return True
            
            # Check for user verification capability
            if authenticator_metadata.get('user_verification', '').lower() in ['internal', 'required']:
                logger.info("WebAuthn AAL2 qualified: User verification capable authenticator")
                return True
    
    logger.debug("WebAuthn AAL2 not qualified: No biometric indicators found")
    return False

def get_effective_aal(kratos_session: Dict[str, Any], flask_session: Optional[Dict[str, Any]] = None) -> str:
    """
    Determine effective AAL level considering custom WebAuthn AAL2 logic
    
    Args:
        kratos_session: Session data from Kratos
        flask_session: Optional Flask session data for enhanced context
        
    Returns:
        str: 'aal1' or 'aal2' based on effective authentication level
    """
    logger.debug("Determining effective AAL for session: %s", kratos_session.get('id', 'unknown'))
    
    # Get base AAL from Kratos
    base_aal = kratos_session.get('authenticator_assurance_level', 'aal1')
    logger.debug("Base AAL from Kratos: %s", base_aal)
    
    # If already AAL2, return as-is
    if base_aal == 'aal2':
        logger.debug("Base AAL is already aal2, returning aal2")
        return 'aal2'
    
    # Check Flask session for enhanced WebAuthn indicators
    if flask_session:
        # Enhanced WebAuthn sessions can override AAL
        if flask_session.get('auth_method') == 'enhanced_webauthn':
            if flask_session.get('custom_aal2_verified'):
                logger.info("Effective AAL upgraded to aal2: Enhanced WebAuthn with custom verification")
                return 'aal2'
        
        # Check for biometric session flags
        if flask_session.get('biometric_verified') or flask_session.get('user_verification_performed'):
            logger.info("Effective AAL upgraded to aal2: Biometric verification detected in Flask session")
            return 'aal2'
    
    # Check if WebAuthn qualifies for AAL2
    if check_webauthn_aal2_eligibility(kratos_session):
        logger.info("Effective AAL upgraded to aal2: WebAuthn qualifies for AAL2")
        return 'aal2'
    
    logger.debug("Effective AAL remains: %s", base_aal)
    return base_aal

def should_bypass_aal_requirement(session_data: Dict[str, Any], required_aal: str = 'aal2') -> bool:
    """
    Determine if AAL requirement should be bypassed based on enhanced authentication
    
    Args:
        session_data: Combined session data from various sources
        required_aal: The AAL level being required
        
    Returns:
        bool: True if AAL requirement should be bypassed
    """
    if required_aal != 'aal2':
        # Only handle AAL2 bypass logic
        return False
    
    # Check for enhanced WebAuthn with biometric verification
    if session_data.get('auth_method') == 'enhanced_webauthn':
        if session_data.get('custom_aal2_verified') or session_data.get('biometric_verified'):
            logger.info("AAL2 requirement bypass approved: Enhanced WebAuthn with biometric verification")
            return True
    
    # Check effective AAL
    effective_aal = get_effective_aal(session_data, session_data)
    if effective_aal == 'aal2':
        logger.info("AAL2 requirement bypass approved: Effective AAL is aal2")
        return True
    
    logger.debug("AAL2 requirement bypass denied: Insufficient authentication level")
    return False