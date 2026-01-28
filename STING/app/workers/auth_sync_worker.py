"""
Auth Sync Worker Service
Background worker that maintains authentication credential synchronization between Kratos and STING
Enables reliable AAL2 enforcement by ensuring STING database reflects Kratos credential state
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import requests
import redis
from app.database import db
from app.models.user_models import User
from app.models.passkey_models import Passkey
from app import create_app

logger = logging.getLogger(__name__)


class AuthSyncWorker:
    """Background worker for Kratos ↔ STING credential synchronization"""
    
    def __init__(self):
        self.app = None
        self.running = False
        self.thread = None
        self.sync_interval = int(os.getenv('AUTH_SYNC_INTERVAL_MINUTES', '2'))  # Fast sync for AAL2
        self.last_sync = None
        self.redis_client = None
        self.kratos_admin_url = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'users_synced': 0,
            'credential_updates': 0,
            'errors': []
        }
    
    def start(self):
        """Start the auth sync worker"""
        if self.running:
            logger.warning("🔐 Auth sync worker already running")
            return
        
        logger.info("🔐 Starting auth sync worker...")
        self.running = True
        
        # Create Flask app context for database access
        if not self.app:
            self.app = create_app()
        
        # Initialize Redis for AAL2 caching
        try:
            self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))
            self.redis_client.ping()
            logger.info("🔐 Connected to Redis for AAL2 caching")
        except Exception as e:
            logger.error(f"🔐 Redis connection failed: {e}")
            self.redis_client = None
        
        # Start worker thread
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"🔐 Auth sync worker started (interval: {self.sync_interval} minutes)")
    
    def stop(self):
        """Stop the auth sync worker"""
        logger.info("🔐 Stopping auth sync worker...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("🔐 Auth sync worker stopped")
    
    def _worker_loop(self):
        """Main worker loop"""
        with self.app.app_context():
            while self.running:
                try:
                    start_time = time.time()
                    logger.info("🔐 Starting credential synchronization cycle...")
                    
                    # Perform sync
                    sync_result = self._sync_credentials()
                    
                    # Update stats
                    self.sync_stats['total_syncs'] += 1
                    if sync_result['success']:
                        self.sync_stats['successful_syncs'] += 1
                        self.sync_stats['users_synced'] += sync_result.get('users_processed', 0)
                        self.sync_stats['credential_updates'] += sync_result.get('updates', 0)
                    else:
                        self.sync_stats['failed_syncs'] += 1
                    
                    self.last_sync = datetime.utcnow()
                    
                    elapsed = time.time() - start_time
                    logger.info(f"🔐 Sync cycle completed in {elapsed:.2f}s - {sync_result.get('updates', 0)} updates")
                    
                except Exception as e:
                    logger.error(f"🔐 Sync cycle error: {e}")
                    self.sync_stats['failed_syncs'] += 1
                    self.sync_stats['errors'].append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': str(e)
                    })
                
                # Sleep until next sync
                time.sleep(self.sync_interval * 60)
    
    def _sync_credentials(self) -> Dict[str, Any]:
        """Synchronize credentials from Kratos to STING database"""
        try:
            # Get all STING users that need credential sync
            sting_users = User.query.filter(User.kratos_id.isnot(None)).all()
            
            updates = 0
            users_processed = 0
            
            for sting_user in sting_users:
                try:
                    # Get Kratos identity data
                    kratos_identity = self._get_kratos_identity(sting_user.kratos_id)
                    if not kratos_identity:
                        continue
                    
                    # Sync credential status
                    user_updates = self._sync_user_credentials(sting_user, kratos_identity)
                    updates += user_updates
                    users_processed += 1
                    
                    # Cache AAL2 capability for fast enforcement
                    self._cache_aal2_capability(sting_user, kratos_identity)
                    
                except Exception as user_error:
                    logger.error(f"🔐 Error syncing user {sting_user.email}: {user_error}")
                    continue
            
            return {
                'success': True,
                'users_processed': users_processed,
                'updates': updates
            }
            
        except Exception as e:
            logger.error(f"🔐 Credential sync error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_kratos_identity(self, kratos_id: str) -> Optional[Dict]:
        """Get identity data from Kratos Admin API"""
        try:
            response = requests.get(
                f"{self.kratos_admin_url}/admin/identities/{kratos_id}",
                verify=False,
                headers={"Accept": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"🔐 Kratos identity {kratos_id} not found: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"🔐 Error fetching Kratos identity {kratos_id}: {e}")
            return None
    
    def _sync_user_credentials(self, sting_user: User, kratos_identity: Dict) -> int:
        """Sync specific user's credentials from Kratos to STING"""
        updates = 0
        credentials = kratos_identity.get('credentials', {})
        
        try:
            # Sync TOTP status
            kratos_has_totp = bool(credentials.get('totp'))
            if sting_user.totp_enabled != kratos_has_totp:
                sting_user.totp_enabled = kratos_has_totp
                updates += 1
                logger.info(f"🔐 Updated TOTP status for {sting_user.email}: {kratos_has_totp}")
            
            # Sync WebAuthn status  
            webauthn_creds = credentials.get('webauthn', {})
            kratos_webauthn_count = len(webauthn_creds.get('credentials', [])) if webauthn_creds else 0
            
            # Update user's WebAuthn credential count
            if hasattr(sting_user, 'webauthn_credential_count'):
                if sting_user.webauthn_credential_count != kratos_webauthn_count:
                    sting_user.webauthn_credential_count = kratos_webauthn_count
                    updates += 1
                    logger.info(f"🔐 Updated WebAuthn count for {sting_user.email}: {kratos_webauthn_count}")
            
            # Update user metadata with AAL2 capability
            metadata = sting_user.metadata or {}
            old_aal2_capable = metadata.get('aal2_capable', False)
            
            # User is AAL2 capable if they have TOTP OR any passkeys (Kratos or STING Enhanced)
            sting_passkey_count = Passkey.query.filter_by(user_id=sting_user.id, status='ACTIVE').count()
            new_aal2_capable = kratos_has_totp or kratos_webauthn_count > 0 or sting_passkey_count > 0
            
            if old_aal2_capable != new_aal2_capable:
                metadata['aal2_capable'] = new_aal2_capable
                metadata['aal2_methods'] = {
                    'totp': kratos_has_totp,
                    'kratos_webauthn': kratos_webauthn_count > 0,
                    'sting_enhanced_webauthn': sting_passkey_count > 0
                }
                metadata['last_credential_sync'] = datetime.utcnow().isoformat()
                sting_user.metadata = metadata
                updates += 1
                logger.info(f"🔐 Updated AAL2 capability for {sting_user.email}: {new_aal2_capable}")
            
            if updates > 0:
                db.session.commit()
            
            return updates
            
        except Exception as e:
            logger.error(f"🔐 Error syncing credentials for {sting_user.email}: {e}")
            db.session.rollback()
            return 0
    
    def _cache_aal2_capability(self, sting_user: User, kratos_identity: Dict):
        """Cache AAL2 capability in Redis for fast enforcement checks"""
        if not self.redis_client:
            return
        
        try:
            # Determine AAL2 capability
            credentials = kratos_identity.get('credentials', {})
            has_totp = bool(credentials.get('totp'))
            
            webauthn_creds = credentials.get('webauthn', {})
            kratos_webauthn_count = len(webauthn_creds.get('credentials', [])) if webauthn_creds else 0
            
            sting_passkey_count = Passkey.query.filter_by(user_id=sting_user.id, status='ACTIVE').count()
            
            aal2_capable = has_totp or kratos_webauthn_count > 0 or sting_passkey_count > 0
            
            # Cache for 5 minutes (fast AAL2 checks)
            cache_key = f"aal2_capable:{sting_user.kratos_id}"
            cache_data = {
                'aal2_capable': aal2_capable,
                'methods': {
                    'totp': has_totp,
                    'kratos_webauthn': kratos_webauthn_count > 0,
                    'sting_enhanced_webauthn': sting_passkey_count > 0
                },
                'last_updated': datetime.utcnow().isoformat()
            }
            
            self.redis_client.setex(cache_key, 300, str(cache_data))  # 5-minute TTL
            
        except Exception as e:
            logger.error(f"🔐 Error caching AAL2 capability for {sting_user.email}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            **self.sync_stats,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'running': self.running,
            'sync_interval_minutes': self.sync_interval
        }


# Worker entry point
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    worker = AuthSyncWorker()
    
    try:
        worker.start()
        logger.info("🔐 Auth sync worker started successfully")
        
        # Keep main thread alive
        while worker.running:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("🔐 Received shutdown signal")
    finally:
        worker.stop()
        logger.info("🔐 Auth sync worker shutdown complete")