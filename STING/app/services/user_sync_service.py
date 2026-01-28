"""
User Synchronization Service
Keeps Kratos and STING databases in sync
"""

import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List
from app.database import db
from app.models.user_models import User, UserRole
import os

logger = logging.getLogger(__name__)


class UserSyncService:
    """Service to synchronize users between Kratos and STING databases"""
    
    def __init__(self):
        self.kratos_admin_url = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
        self.verify_ssl = os.getenv('KRATOS_VERIFY_SSL', 'false').lower() == 'true'
        
    def sync_all_users(self) -> Dict[str, any]:
        """Sync all users between Kratos and STING"""
        logger.info("🔄 Starting full user synchronization...")
        
        results = {
            'synced': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'details': []
        }
        
        try:
            # Get all Kratos identities
            kratos_users = self._get_all_kratos_identities()
            logger.info(f"🔄 Found {len(kratos_users)} users in Kratos")
            
            # Get all STING users
            sting_users = User.query.all()
            sting_emails = {u.email.lower(): u for u in sting_users}
            logger.info(f"🔄 Found {len(sting_users)} users in STING")
            
            # Sync Kratos → STING
            for kratos_user in kratos_users:
                email = kratos_user.get('traits', {}).get('email', '').lower()
                if not email:
                    logger.warning(f"🔄 Skipping Kratos user with no email: {kratos_user.get('id')}")
                    continue
                
                if email in sting_emails:
                    # User exists, update if needed
                    sting_user = sting_emails[email]
                    if self._update_sting_user(sting_user, kratos_user):
                        results['updated'] += 1
                        results['details'].append(f"Updated: {email}")
                else:
                    # Create new user in STING
                    if self._create_sting_user(kratos_user):
                        results['created'] += 1
                        results['details'].append(f"Created: {email}")
                    else:
                        results['errors'] += 1
                        results['details'].append(f"Failed to create: {email}")
                
                results['synced'] += 1
            
            # Optionally sync STING → Kratos for users that only exist in STING
            # This is more complex as it requires creating Kratos identities with credentials
            
            logger.info(f"🔄 Sync complete: {results['synced']} processed, "
                       f"{results['created']} created, {results['updated']} updated, "
                       f"{results['errors']} errors")
            
        except Exception as e:
            logger.error(f"🔄 Sync failed: {e}")
            results['errors'] += 1
            results['details'].append(f"Error: {str(e)}")
        
        return results
    
    def sync_single_user(self, email: str) -> bool:
        """Sync a single user by email"""
        logger.info(f"🔄 Syncing user: {email}")
        
        try:
            # Try to get from Kratos
            kratos_user = self._get_kratos_identity_by_email(email)
            
            if kratos_user:
                # Sync Kratos → STING
                sting_user = User.query.filter_by(email=email).first()
                if sting_user:
                    return self._update_sting_user(sting_user, kratos_user)
                else:
                    return self._create_sting_user(kratos_user)
            else:
                # Check if user exists in STING only
                sting_user = User.query.filter_by(email=email).first()
                if sting_user:
                    logger.warning(f"🔄 User {email} exists in STING but not in Kratos")
                    # Could create in Kratos here if needed
                    return True
                else:
                    logger.warning(f"🔄 User {email} not found in either database")
                    return False
                    
        except Exception as e:
            logger.error(f"🔄 Failed to sync user {email}: {e}")
            return False
    
    def sync_specific_user(self, user_email: str) -> Dict[str, any]:
        """
        Sync a specific user between Kratos and STING
        Wrapper around sync_single_user that returns detailed results for the Profile Sync Worker
        """
        logger.info(f"🔐 Starting specific user sync for: {user_email}")
        
        try:
            success = self.sync_single_user(user_email)
            
            results = {
                'synced': 1 if success else 0,
                'created': 0,  # Would need to track this separately
                'updated': 1 if success else 0,  # Assume update for now
                'errors': 0 if success else 1,
                'details': [f"Sync {'successful' if success else 'failed'} for user: {user_email}"],
                'user_email': user_email
            }
            
            logger.info(f"🔐 Specific user sync result for {user_email}: {'success' if success else 'failed'}")
            return results
            
        except Exception as e:
            logger.error(f"🔐 Specific user sync failed for {user_email}: {e}")
            return {
                'synced': 0,
                'created': 0,
                'updated': 0,
                'errors': 1,
                'details': [f"Error syncing {user_email}: {str(e)}"],
                'user_email': user_email
            }
    
    def _get_all_kratos_identities(self) -> List[Dict]:
        """Get all identities from Kratos"""
        try:
            response = requests.get(
                f"{self.kratos_admin_url}/admin/identities",
                verify=self.verify_ssl,
                timeout=10,
                params={'per_page': 1000}  # Get up to 1000 users
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"🔄 Failed to get Kratos identities: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"🔄 Error fetching Kratos identities: {e}")
            return []
    
    def _get_kratos_identity_by_email(self, email: str) -> Optional[Dict]:
        """Get a single Kratos identity by email"""
        try:
            # Get all identities and filter (Kratos doesn't have email search)
            identities = self._get_all_kratos_identities()
            for identity in identities:
                if identity.get('traits', {}).get('email', '').lower() == email.lower():
                    return identity
            return None
            
        except Exception as e:
            logger.error(f"🔄 Error fetching Kratos identity for {email}: {e}")
            return None
    
    def _create_sting_user(self, kratos_user: Dict) -> bool:
        """Create a STING user from Kratos data"""
        try:
            traits = kratos_user.get('traits', {})
            email = traits.get('email')
            
            if not email:
                return False
            
            # Extract user data
            first_name = traits.get('name', {}).get('first', '')
            last_name = traits.get('name', {}).get('last', '')
            username = email.split('@')[0]
            role = traits.get('role', 'user')
            
            # Create user directly using SQLAlchemy model
            from app.models.user_models import UserRole
            
            # Map role string to enum
            role_enum = UserRole.ADMIN if role in ['admin', 'administrator'] else UserRole.USER
            
            user = User(
                email=email,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role_enum,
                kratos_id=kratos_user.get('id'),
                is_admin=(role_enum == UserRole.ADMIN)
            )
            
            db.session.add(user)
            
            db.session.commit()
            logger.info(f"🔄 Created STING user: {email}")
            return True
            
        except Exception as e:
            logger.error(f"🔄 Failed to create STING user: {e}")
            db.session.rollback()
            return False
    
    def _update_sting_user(self, sting_user: User, kratos_user: Dict) -> bool:
        """Update STING user with Kratos data including authentication methods"""
        try:
            traits = kratos_user.get('traits', {})
            updated = False
            
            # Update fields if changed
            if not sting_user.kratos_id:
                sting_user.kratos_id = kratos_user.get('id')
                updated = True
            
            # Update name if provided
            first_name = traits.get('name', {}).get('first')
            last_name = traits.get('name', {}).get('last')
            
            if first_name and sting_user.first_name != first_name:
                sting_user.first_name = first_name
                updated = True
            
            if last_name and sting_user.last_name != last_name:
                sting_user.last_name = last_name
                updated = True
            
            # Update role if different
            role = traits.get('role', 'user')
            # Convert role string to proper enum
            role_enum = None
            if role.lower() in ['admin', 'administrator']:
                role_enum = UserRole.ADMIN
            elif role.lower() in ['super_admin', 'superadmin', 'super-admin']:
                role_enum = UserRole.SUPER_ADMIN
            else:
                role_enum = UserRole.USER
            
            # Compare using string values to avoid enum name/value mismatch issues
            current_role_str = str(sting_user.role.value) if hasattr(sting_user.role, 'value') else str(sting_user.role)
            new_role_str = str(role_enum.value)
            
            logger.debug(f"🔄 Role comparison: current='{current_role_str}', new='{new_role_str}'")
            
            if current_role_str != new_role_str:
                logger.info(f"🔄 Updating user role from '{current_role_str}' to '{new_role_str}' for {sting_user.email}")
                sting_user.role = role_enum
                updated = True
            
            # ENHANCED: Sync authentication methods from Kratos credentials
            auth_methods_updated = self._sync_authentication_methods(sting_user, kratos_user)
            if auth_methods_updated:
                updated = True
            
            if updated:
                sting_user.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"🔄 Updated STING user: {sting_user.email}")
            
            return updated
            
        except Exception as e:
            logger.error(f"🔄 Failed to update STING user: {e}")
            db.session.rollback()
            return False
    
    def _sync_authentication_methods(self, sting_user: User, kratos_user: Dict) -> bool:
        """
        Sync authentication methods from Kratos and check custom STING credentials
        Returns True if any updates were made
        """
        try:
            # Get full identity with credentials from Kratos
            identity_id = kratos_user.get('id')
            if not identity_id:
                logger.warning(f"🔐 No identity ID found for user {sting_user.email}")
                return False
                
            logger.debug(f"🔐 Syncing auth methods for {sting_user.email} (Kratos ID: {identity_id})")
            
            # Check custom STING passkeys FIRST (takes priority over Kratos WebAuthn)
            custom_passkeys = self._get_sting_passkeys(sting_user.id)
            has_custom_webauthn = len(custom_passkeys) > 0
            
            logger.debug(f"🔐 Custom STING passkeys for {sting_user.email}: {len(custom_passkeys)} active")
            
            # Only check Kratos credentials for TOTP (skip WebAuthn since we use custom)
            detailed_identity = self._get_kratos_identity_with_credentials(identity_id)
            if not detailed_identity:
                logger.warning(f"🔐 Could not fetch Kratos identity for {sting_user.email} - checking custom auth only")
                # Still continue with custom passkey detection
            
            credentials = detailed_identity.get('credentials', {}) if detailed_identity else {}
            updated = False
            
            # SKIP Kratos WebAuthn entirely - we use custom STING WebAuthn
            # Use custom STING passkey detection instead
            has_webauthn = has_custom_webauthn
            
            logger.debug(f"🔐 WebAuthn analysis for {sting_user.email}: "
                        f"custom_passkeys={len(custom_passkeys)}, "
                        f"has_webauthn={has_webauthn} (using custom STING implementation)")
            
            # Enhanced TOTP credential checking
            totp_creds = credentials.get('totp', {})
            totp_identifiers = totp_creds.get('identifiers', [])
            totp_config = totp_creds.get('config', {})
            
            # Check for TOTP URL or secret in config
            has_totp_url = bool(totp_config.get('totp_url')) if totp_config else False
            has_totp_secret = bool(totp_config.get('secret')) if totp_config else False
            has_totp = bool(totp_identifiers) or has_totp_url or has_totp_secret
            
            logger.debug(f"🔐 TOTP analysis for {sting_user.email}: "
                        f"identifiers={len(totp_identifiers)}, "
                        f"has_url={has_totp_url}, "
                        f"has_secret={has_totp_secret}, "
                        f"has_totp={has_totp}")
            
            # Log comprehensive authentication method status
            logger.info(f"🔐 User {sting_user.email} credential sync results - "
                       f"WebAuthn: {has_webauthn} "
                       f"({len(custom_passkeys)} custom passkeys), "
                       f"TOTP: {has_totp}")
            
            # TODO: Add these fields to User model and update them here
            # For now, this serves as important debugging info for the enrollment loop issue
            # if hasattr(sting_user, 'has_webauthn') and sting_user.has_webauthn != has_webauthn:
            #     sting_user.has_webauthn = has_webauthn
            #     updated = True
            # 
            # if hasattr(sting_user, 'has_totp') and sting_user.has_totp != has_totp:
            #     sting_user.has_totp = has_totp  
            #     updated = True
            
            # For debugging: show if sync would have detected credential mismatch
            if has_webauthn or has_totp:
                logger.info(f"✅ User {sting_user.email} has configured authentication methods - "
                           f"sync working correctly (no more enrollment loops expected)")
            else:
                logger.info(f"ℹ️  User {sting_user.email} has no configured auth methods - "
                           f"enrollment flow should be used")
            
            return updated
            
        except Exception as e:
            logger.error(f"🔐 Failed to sync auth methods for {sting_user.email}: {e}")
            import traceback
            logger.debug(f"🔐 Full traceback: {traceback.format_exc()}")
            return False
    
    def _get_kratos_identity_with_credentials(self, identity_id: str) -> Optional[Dict]:
        """Get a single Kratos identity with credentials"""
        try:
            # First, try the corrected API format with multiple parameters
            response = requests.get(
                f"{self.kratos_admin_url}/admin/identities/{identity_id}?include_credential=webauthn&include_credential=totp",
                verify=self.verify_ssl,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"🔐 Successfully fetched identity {identity_id} with combined credentials")
                return response.json()
            else:
                logger.warning(f"🔐 Combined credential fetch failed for {identity_id}: {response.status_code}")
                logger.debug(f"🔐 Response body: {response.text}")
                
                # Fallback: Try fetching credentials individually and merge
                return self._get_identity_with_fallback_credentials(identity_id)
                
        except Exception as e:
            logger.error(f"🔐 Error fetching identity with credentials: {e}")
            # Try fallback approach on any error
            return self._get_identity_with_fallback_credentials(identity_id)
    
    def _get_identity_with_fallback_credentials(self, identity_id: str) -> Optional[Dict]:
        """Fallback method: fetch identity and credentials separately"""
        try:
            logger.info(f"🔐 Using fallback credential fetch for identity {identity_id}")
            
            # Get base identity without credentials
            base_response = requests.get(
                f"{self.kratos_admin_url}/admin/identities/{identity_id}",
                verify=self.verify_ssl,
                timeout=10
            )
            
            if base_response.status_code != 200:
                logger.error(f"🔐 Failed to get base identity {identity_id}: {base_response.status_code}")
                return None
            
            identity = base_response.json()
            
            # Initialize credentials dictionary if not present
            if 'credentials' not in identity:
                identity['credentials'] = {}
            
            # Try to fetch WebAuthn credentials
            try:
                webauthn_response = requests.get(
                    f"{self.kratos_admin_url}/admin/identities/{identity_id}?include_credential=webauthn",
                    verify=self.verify_ssl,
                    timeout=10
                )
                if webauthn_response.status_code == 200:
                    webauthn_data = webauthn_response.json()
                    webauthn_creds = webauthn_data.get('credentials', {}).get('webauthn')
                    if webauthn_creds:
                        identity['credentials']['webauthn'] = webauthn_creds
                        logger.debug(f"🔐 Successfully fetched WebAuthn credentials for {identity_id}")
                else:
                    logger.debug(f"🔐 WebAuthn credential fetch failed: {webauthn_response.status_code}")
            except Exception as e:
                logger.warning(f"🔐 Error fetching WebAuthn credentials: {e}")
            
            # Try to fetch TOTP credentials
            try:
                totp_response = requests.get(
                    f"{self.kratos_admin_url}/admin/identities/{identity_id}?include_credential=totp",
                    verify=self.verify_ssl,
                    timeout=10
                )
                if totp_response.status_code == 200:
                    totp_data = totp_response.json()
                    totp_creds = totp_data.get('credentials', {}).get('totp')
                    if totp_creds:
                        identity['credentials']['totp'] = totp_creds
                        logger.debug(f"🔐 Successfully fetched TOTP credentials for {identity_id}")
                else:
                    logger.debug(f"🔐 TOTP credential fetch failed: {totp_response.status_code}")
            except Exception as e:
                logger.warning(f"🔐 Error fetching TOTP credentials: {e}")
            
            logger.info(f"🔐 Fallback fetch complete for {identity_id} - WebAuthn: {'webauthn' in identity['credentials']}, TOTP: {'totp' in identity['credentials']}")
            return identity
            
        except Exception as e:
            logger.error(f"🔐 Fallback credential fetch failed for {identity_id}: {e}")
            return None
    
    def _get_sting_passkeys(self, user_id: int) -> List[Dict]:
        """
        Get active custom STING passkeys for a user
        Returns list of passkey dictionaries
        """
        try:
            from app.models.passkey_models import Passkey, PasskeyStatus
            
            # Query active passkeys for the user
            passkeys = Passkey.query.filter_by(
                user_id=user_id, 
                status=PasskeyStatus.ACTIVE
            ).all()
            
            # Convert to dict format for consistent handling
            passkey_list = []
            for passkey in passkeys:
                passkey_list.append({
                    'id': passkey.id,
                    'credential_id': passkey.credential_id,
                    'name': passkey.name,
                    'device_type': passkey.device_type,
                    'created_at': passkey.created_at.isoformat() if passkey.created_at else None,
                    'last_used_at': passkey.last_used_at.isoformat() if passkey.last_used_at else None,
                    'usage_count': passkey.usage_count
                })
            
            logger.debug(f"🔐 Found {len(passkey_list)} active STING passkeys for user_id {user_id}")
            return passkey_list
            
        except Exception as e:
            logger.error(f"🔐 Failed to get STING passkeys for user_id {user_id}: {e}")
            return []
    
    def get_sync_status(self) -> Dict:
        """Get current sync status and statistics"""
        try:
            kratos_count = len(self._get_all_kratos_identities())
            sting_count = User.query.count()
            
            # Find unsynced users
            kratos_users = self._get_all_kratos_identities()
            kratos_emails = {u.get('traits', {}).get('email', '').lower() 
                           for u in kratos_users if u.get('traits', {}).get('email')}
            
            sting_users = User.query.all()
            sting_emails = {u.email.lower() for u in sting_users}
            
            only_in_kratos = kratos_emails - sting_emails
            only_in_sting = sting_emails - kratos_emails
            
            return {
                'healthy': len(only_in_kratos) == 0 and len(only_in_sting) == 0,
                'kratos_count': kratos_count,
                'sting_count': sting_count,
                'synced_count': len(kratos_emails & sting_emails),
                'only_in_kratos': list(only_in_kratos),
                'only_in_sting': list(only_in_sting),
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"🔄 Failed to get sync status: {e}")
            return {
                'healthy': False,
                'error': str(e)
            }


# Singleton instance
sync_service = UserSyncService()