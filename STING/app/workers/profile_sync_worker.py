"""
Profile Sync Worker Service
Background worker that maintains user profile synchronization between Kratos and STING
Similar architecture to the report worker service
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
import os
# import schedule - using time.sleep instead for simplicity
from app.services.user_sync_service import sync_service
from app.database import db
from app import create_app

logger = logging.getLogger(__name__)


class ProfileSyncWorker:
    """Background worker for profile synchronization"""
    
    def __init__(self):
        self.app = None
        self.running = False
        self.thread = None
        self.sync_interval = int(os.getenv('PROFILE_SYNC_INTERVAL_MINUTES', '5'))
        self.last_sync = None
        self.sync_stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'users_synced': 0,
            'errors': []
        }
    
    def start(self):
        """Start the profile sync worker"""
        if self.running:
            logger.warning("🔄 Profile sync worker already running")
            return
        
        logger.info("🔄 Starting profile sync worker...")
        self.running = True
        
        # Create Flask app context for database access
        if not self.app:
            self.app = create_app()
        
        # Start worker thread
        self.thread = threading.Thread(target=self._run_worker, daemon=True)
        self.thread.start()
        
        logger.info(f"🔄 Profile sync worker started (sync every {self.sync_interval} minutes)")
    
    def stop(self):
        """Stop the profile sync worker"""
        logger.info("🔄 Stopping profile sync worker...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🔄 Profile sync worker stopped")
    
    def _run_worker(self):
        """Main worker loop"""
        with self.app.app_context():
            # Perform initial sync
            self._perform_sync()
            
            # Main loop with timed intervals
            last_sync = datetime.utcnow()
            
            while self.running:
                try:
                    current_time = datetime.utcnow()
                    time_since_sync = (current_time - last_sync).total_seconds()
                    
                    # Check if it's time for next sync (convert minutes to seconds)
                    if time_since_sync >= (self.sync_interval * 60):
                        self._perform_sync()
                        last_sync = current_time
                    
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"🔄 Worker error: {e}")
                    self.sync_stats['errors'].append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': str(e)
                    })
                    time.sleep(10)  # Wait before retrying
    
    def _perform_sync(self):
        """Perform profile synchronization"""
        try:
            logger.info("🔄 Starting profile synchronization...")
            self.sync_stats['total_syncs'] += 1
            
            # Get sync status first
            status = sync_service.get_sync_status()
            
            if not status.get('healthy', False):
                logger.info(f"🔄 Profiles out of sync - {len(status.get('only_in_kratos', []))} in Kratos only, "
                          f"{len(status.get('only_in_sting', []))} in STING only")
                
                # Perform sync
                results = sync_service.sync_all_users()
                
                self.sync_stats['successful_syncs'] += 1
                self.sync_stats['users_synced'] += results.get('synced', 0)
                
                logger.info(f"🔄 Sync completed: {results.get('created', 0)} created, "
                          f"{results.get('updated', 0)} updated, {results.get('errors', 0)} errors")
            else:
                logger.info("🔄 Profiles already in sync")
                self.sync_stats['successful_syncs'] += 1
            
            self.last_sync = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"🔄 Sync failed: {e}")
            self.sync_stats['failed_syncs'] += 1
            self.sync_stats['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            })
            # Keep only last 10 errors
            if len(self.sync_stats['errors']) > 10:
                self.sync_stats['errors'] = self.sync_stats['errors'][-10:]
    
    def get_status(self):
        """Get worker status"""
        return {
            'running': self.running,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'next_sync': (datetime.utcnow() + timedelta(minutes=self.sync_interval)).isoformat() if self.running else None,
            'sync_interval_minutes': self.sync_interval,
            'stats': self.sync_stats
        }
    
    def trigger_sync(self):
        """Manually trigger a sync"""
        if not self.running:
            logger.warning("🔄 Worker not running, starting for manual sync...")
            self.start()
        
        logger.info("🔄 Manual sync triggered")
        threading.Thread(target=lambda: self._perform_sync_with_context(), daemon=True).start()
        return True
    
    def trigger_auth_sync(self, user_email: str = None):
        """
        Trigger sync specifically after authentication event
        Optimized for session synchronization after WebAuthn/passkey authentication
        """
        if not self.running:
            logger.warning("🔄 Worker not running, starting for auth sync...")
            self.start()
        
        logger.info(f"🔐 Authentication sync triggered for user: {user_email or 'all'}")
        threading.Thread(target=lambda: self._perform_auth_sync_with_context(user_email), daemon=True).start()
        return True
    
    def _perform_sync_with_context(self):
        """Perform sync with app context (for manual triggers)"""
        with self.app.app_context():
            self._perform_sync()
    
    def _perform_auth_sync_with_context(self, user_email: str = None):
        """
        Perform authentication-specific sync with app context
        Prioritizes session synchronization and provides faster feedback
        """
        with self.app.app_context():
            try:
                logger.info(f"🔐 Starting authentication sync for user: {user_email or 'all'}")
                
                # Perform focused sync for authentication events
                if user_email:
                    # User-specific sync for faster response
                    results = sync_service.sync_specific_user(user_email)
                else:
                    # Full sync fallback
                    results = sync_service.sync_all_users()
                
                logger.info(f"🔐 Authentication sync completed: {results}")
                
                # Update stats
                self.sync_stats['total_syncs'] += 1
                self.sync_stats['successful_syncs'] += 1
                self.sync_stats['users_synced'] += results.get('synced', 0)
                self.last_sync = datetime.utcnow()
                
                return results
                
            except Exception as e:
                logger.error(f"🔐 Authentication sync failed: {e}")
                self.sync_stats['failed_syncs'] += 1
                self.sync_stats['errors'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e),
                    'type': 'auth_sync'
                })
                return None


# Global worker instance
profile_worker = ProfileSyncWorker()


def init_profile_worker(app=None):
    """Initialize and start the profile sync worker"""
    global profile_worker
    
    if app:
        profile_worker.app = app
    
    # Check if worker should be enabled
    if os.getenv('PROFILE_SYNC_ENABLED', 'true').lower() == 'true':
        profile_worker.start()
        logger.info("🔄 Profile sync worker initialized and started")
    else:
        logger.info("🔄 Profile sync worker is disabled")
    
    return profile_worker


def main():
    """Main entry point for running as a module"""
    import signal
    import sys
    
    def signal_handler(signum, frame):
        logger.info("🔄 Profile sync worker received shutdown signal")
        profile_worker.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🔄 Starting profile sync worker in standalone mode...")
    
    # Initialize and start the worker
    worker = init_profile_worker()
    
    if worker.running:
        logger.info("🔄 Profile sync worker is running. Press Ctrl+C to stop.")
        try:
            # Keep the main thread alive
            while worker.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🔄 Received keyboard interrupt")
        finally:
            worker.stop()
    else:
        logger.error("🔄 Failed to start profile sync worker")
        sys.exit(1)


if __name__ == "__main__":
    main()