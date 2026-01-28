"""
Startup checks and fixes to ensure system stability
"""
import logging
import requests
import os
import time
from datetime import datetime, timedelta
from .default_admin_setup_v2 import DEFAULT_ADMIN_EMAIL, KRATOS_ADMIN_URL

logger = logging.getLogger(__name__)

def fix_admin_force_password_change():
    """Ensure admin account has proper password change setup"""
    try:
        # Wait for Kratos to be ready
        time.sleep(5)
        
        # Get all identities
        response = requests.get(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            verify=False
        )
        
        if response.status_code == 200:
            identities = response.json()
            
            # Find admin identity
            for identity in identities:
                if identity.get('traits', {}).get('email') == DEFAULT_ADMIN_EMAIL:
                    admin_id = identity['id']
                    traits = identity.get('traits', {})
                    
                    # Check if this is a fresh admin account (created within last hour)
                    created_at = identity.get('created_at', '')
                    if created_at:
                        from datetime import datetime
                        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        time_since_creation = datetime.now(created_time.tzinfo) - created_time
                        
                        # If created within last hour and has force_password_change
                        if time_since_creation.total_seconds() < 3600 and traits.get('force_password_change', False):
                            logger.info("New admin account detected with force_password_change - allowing grace period")
                            
                            # Add grace period marker
                            traits['password_change_grace_period'] = True
                            traits['grace_period_expires'] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
                            
                            # Temporarily disable force_password_change
                            traits['force_password_change'] = False
                            
                            update_data = {
                                "schema_id": identity['schema_id'],
                                "state": identity['state'],
                                "traits": traits
                            }
                            
                            update_response = requests.put(
                                f"{KRATOS_ADMIN_URL}/admin/identities/{admin_id}",
                                json=update_data,
                                verify=False
                            )
                            
                            if update_response.status_code == 200:
                                logger.info("✅ Applied 24-hour grace period for admin password change")
                                logger.warning("⚠️  Admin must change password within 24 hours!")
                            else:
                                logger.error(f"Failed to update admin: {update_response.status_code}")
                    else:
                        # For existing accounts, just log the status
                        if traits.get('force_password_change', False):
                            logger.warning("Admin has force_password_change=True - user must change password")
                        else:
                            logger.info("Admin account password requirements satisfied")
                    break
                    
    except Exception as e:
        logger.error(f"Error checking admin password requirements: {e}")

def clear_stale_sessions():
    """Clear any stale sessions on startup to prevent CSRF issues"""
    try:
        # This is optional - only if you want to force all users to re-login after restart
        # Uncomment the following lines to enable:
        
        # logger.info("Clearing all sessions on startup...")
        # response = requests.get(
        #     f"{KRATOS_ADMIN_URL}/admin/identities",
        #     verify=False
        # )
        # 
        # if response.status_code == 200:
        #     identities = response.json()
        #     for identity in identities:
        #         requests.delete(
        #             f"{KRATOS_ADMIN_URL}/admin/identities/{identity['id']}/sessions",
        #             verify=False
        #         )
        #     logger.info("All sessions cleared")
        
        pass  # Currently disabled to preserve sessions across restarts
        
    except Exception as e:
        logger.error(f"Error clearing sessions: {e}")

def run_startup_checks():
    """Run all startup checks and fixes"""
    logger.info("Running startup checks...")
    
    # TEMPORARILY DISABLED: This is corrupting admin credentials
    # # Fix admin force_password_change if needed
    # fix_admin_force_password_change()
    
    # Clear stale sessions if needed
    clear_stale_sessions()
    
    logger.info("Startup checks completed")