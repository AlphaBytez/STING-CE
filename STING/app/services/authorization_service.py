#!/usr/bin/env python3
"""
Authorization Service - Custom AAL Business Rules
Purpose: Implement STING's business logic for authentication assurance levels
Context: Bridge the gap between Kratos AAL and our requirements for biometric auth

Key Concepts:
- Kratos AAL1: Single factor (email + passkey without UV)
- Kratos AAL2: Two factors (email + password + TOTP, or email + TOTP)
- Our AAL2: Includes biometric passkeys (UV flag = true) which Kratos treats as AAL1
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from flask import session, g, request
from typing import Dict, Optional, Tuple, List
from app.utils.environment import get_database_url

logger = logging.getLogger(__name__)

class AuthorizationService:
    """Service for managing STING's custom authorization rules"""
    
    def __init__(self):
        self.db_url = get_database_url()
        self.engine = create_engine(self.db_url) if self.db_url else None
    
    def get_effective_aal(self, kratos_session: Dict, identity_id: str) -> str:
        """
        Calculate the effective AAL combining Kratos AAL + our biometric detection
        
        Returns:
        - 'aal1': Standard single factor
        - 'aal2': Enhanced security (TOTP or biometric)
        """
        try:
            # Start with what Kratos says
            kratos_aal = kratos_session.get('authenticator_assurance_level', 'aal1')
            
            # If Kratos already says AAL2, we respect that
            if kratos_aal == 'aal2':
                logger.info(f"🔒 User {identity_id} has Kratos AAL2 (TOTP verified)")
                return 'aal2'
            
            # Check if user authenticated with biometric in current session
            session_id = kratos_session.get('id')
            if self.has_biometric_auth(identity_id, session_id):
                logger.info(f"🔒 User {identity_id} upgraded to AAL2 via biometric authentication")
                return 'aal2'
            
            # Default to AAL1
            logger.info(f"🔒 User {identity_id} remains at AAL1")
            return 'aal1'
            
        except Exception as e:
            logger.error(f"Error calculating effective AAL for {identity_id}: {e}")
            return 'aal1'  # Fail safe
    
    def has_biometric_auth(self, identity_id: str, session_id: Optional[str] = None) -> bool:
        """Check if user has authenticated with biometric verification in current session"""
        if not self.engine or not identity_id:
            return False
        
        try:
            with self.engine.connect() as conn:
                # Look for biometric auth in current session (last 1 hour for safety)
                query = text("""
                    SELECT COUNT(*) > 0 as has_biometric
                    FROM biometric_authentications 
                    WHERE identity_id = :identity_id
                      AND user_verified = true
                      AND auth_time > NOW() - INTERVAL '1 hour'
                """)
                
                params = {'identity_id': identity_id}
                
                # If we have a specific session, check it
                if session_id:
                    query = text("""
                        SELECT COUNT(*) > 0 as has_biometric
                        FROM biometric_authentications 
                        WHERE identity_id = :identity_id
                          AND session_id = :session_id
                          AND user_verified = true
                    """)
                    params['session_id'] = session_id
                
                result = conn.execute(query, params)
                has_biometric = result.scalar()
                
                logger.debug(f"Biometric check for {identity_id} (session: {session_id}): {has_biometric}")
                return bool(has_biometric)
                
        except Exception as e:
            logger.error(f"Error checking biometric auth for {identity_id}: {e}")
            return False
    
    def record_biometric_auth(self, identity_id: str, credential_id: str, 
                            session_id: str, user_verified: bool = True,
                            authenticator_type: str = 'platform') -> bool:
        """Record a biometric authentication event"""
        if not self.engine:
            return False
        
        try:
            with self.engine.connect() as conn:
                # Insert biometric authentication record
                query = text("""
                    INSERT INTO biometric_authentications 
                    (identity_id, credential_id, session_id, user_verified, 
                     authenticator_type, user_agent, ip_address, auth_time)
                    VALUES (:identity_id, :credential_id, :session_id, :user_verified,
                            :authenticator_type, :user_agent, :ip_address, NOW())
                    ON CONFLICT (session_id, identity_id) 
                    DO UPDATE SET 
                        user_verified = :user_verified,
                        auth_time = NOW(),
                        credential_id = :credential_id
                """)
                
                params = {
                    'identity_id': identity_id,
                    'credential_id': credential_id,
                    'session_id': session_id,
                    'user_verified': user_verified,
                    'authenticator_type': authenticator_type,
                    'user_agent': request.headers.get('User-Agent', '')[:500] if request else '',
                    'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', 
                                                    request.environ.get('REMOTE_ADDR', '')) if request else None
                }
                
                conn.execute(query, params)
                conn.commit()
                
                logger.info(f"🔒 Recorded biometric auth for {identity_id} (UV: {user_verified})")
                return True
                
        except Exception as e:
            logger.error(f"Error recording biometric auth for {identity_id}: {e}")
            return False
    
    def record_credential_metadata(self, credential_id: str, identity_id: str,
                                 credential_name: str = None, is_biometric: bool = False,
                                 authenticator_type: str = 'platform') -> bool:
        """Record metadata about a credential for UI display"""
        if not self.engine:
            return False
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO credential_metadata 
                    (credential_id, identity_id, credential_name, is_biometric, 
                     authenticator_type, last_used)
                    VALUES (:credential_id, :identity_id, :credential_name, :is_biometric,
                            :authenticator_type, NOW())
                    ON CONFLICT (credential_id) 
                    DO UPDATE SET 
                        last_used = NOW(),
                        is_biometric = :is_biometric,
                        credential_name = :credential_name,
                        updated_at = NOW()
                """)
                
                params = {
                    'credential_id': credential_id,
                    'identity_id': identity_id,
                    'credential_name': credential_name or f'Passkey ({authenticator_type})',
                    'is_biometric': is_biometric,
                    'authenticator_type': authenticator_type
                }
                
                conn.execute(query, params)
                conn.commit()
                
                logger.info(f"🔒 Recorded credential metadata for {credential_id} (biometric: {is_biometric})")
                return True
                
        except Exception as e:
            logger.error(f"Error recording credential metadata: {e}")
            return False
    
    def get_user_credentials(self, identity_id: str) -> Dict[str, List]:
        """Get user's credentials separated by biometric capability"""
        if not self.engine:
            return {'biometric': [], 'standard': []}
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT credential_id, credential_name, is_biometric, 
                           authenticator_type, last_used
                    FROM credential_metadata 
                    WHERE identity_id = :identity_id
                    ORDER BY last_used DESC, created_at DESC
                """)
                
                result = conn.execute(query, {'identity_id': identity_id})
                credentials = result.fetchall()
                
                biometric_creds = []
                standard_creds = []
                
                for cred in credentials:
                    cred_data = {
                        'credential_id': cred.credential_id,
                        'name': cred.credential_name,
                        'type': cred.authenticator_type,
                        'last_used': cred.last_used.isoformat() if cred.last_used else None
                    }
                    
                    if cred.is_biometric:
                        biometric_creds.append(cred_data)
                    else:
                        standard_creds.append(cred_data)
                
                return {
                    'biometric': biometric_creds,
                    'standard': standard_creds
                }
                
        except Exception as e:
            logger.error(f"Error getting user credentials for {identity_id}: {e}")
            return {'biometric': [], 'standard': []}
    
    def can_access_sensitive_data(self, identity_id: str, kratos_session: Dict) -> Tuple[bool, str]:
        """
        Check if user can access sensitive data (reports, admin features, etc.)
        
        Returns:
        - (True/False, reason)
        """
        effective_aal = self.get_effective_aal(kratos_session, identity_id)
        
        if effective_aal == 'aal2':
            return True, "AAL2 verified via TOTP or biometric authentication"
        
        return False, "AAL2 required - please use TOTP or biometric authentication"
    
    def cleanup_old_biometric_records(self, days: int = 30) -> int:
        """Clean up old biometric authentication records"""
        if not self.engine:
            return 0
        
        try:
            with self.engine.connect() as conn:
                query = text("""
                    DELETE FROM biometric_authentications 
                    WHERE auth_time < NOW() - INTERVAL '%s days'
                """ % days)
                
                result = conn.execute(query)
                conn.commit()
                
                deleted_count = result.rowcount
                logger.info(f"🧹 Cleaned up {deleted_count} old biometric authentication records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up biometric records: {e}")
            return 0

# Global instance
authorization_service = AuthorizationService()

# Convenience functions for Flask integration
def get_effective_aal(identity_id: str = None, kratos_session: Dict = None) -> str:
    """Get effective AAL for current user"""
    if not identity_id and hasattr(g, 'user') and g.user:
        identity_id = g.user.id
    
    if not kratos_session and hasattr(g, 'kratos_session'):
        kratos_session = g.kratos_session
    
    if not identity_id or not kratos_session:
        return 'aal1'
    
    return authorization_service.get_effective_aal(kratos_session, identity_id)

def requires_aal2(identity_id: str = None, kratos_session: Dict = None) -> bool:
    """Check if user meets AAL2 requirements"""
    effective_aal = get_effective_aal(identity_id, kratos_session)
    return effective_aal == 'aal2'

def record_biometric_login(identity_id: str, credential_id: str, session_id: str, 
                         user_verified: bool = True, authenticator_type: str = 'platform') -> bool:
    """Record biometric authentication event"""
    return authorization_service.record_biometric_auth(
        identity_id, credential_id, session_id, user_verified, authenticator_type
    )