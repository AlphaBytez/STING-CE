#!/usr/bin/env python3
"""
Installation ID management for STING
Helps distinguish between fresh installs and upgrades
"""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def get_installation_paths():
    """Get consistent paths for installation files"""
    # Try to use the install directory if available
    install_dir = os.getenv('STING_INSTALL_DIR')
    
    if install_dir and os.path.exists(install_dir):
        base_path = Path(install_dir)
    else:
        # Use platform-appropriate default
        if os.path.exists('/opt/sting-ce'):
            # Linux/WSL installation
            base_path = Path('/opt/sting-ce')
        else:
            # Fallback to home directory
            base_path = Path.home() / '.sting-ce'
    
    base_path.mkdir(parents=True, exist_ok=True)
    return {
        'installation_id': base_path / '.installation_id',
        'installation_date': base_path / '.installation_date'
    }

def get_or_create_installation_id():
    """Get existing installation ID or create a new one"""
    paths = get_installation_paths()
    
    # Check if we have an existing installation ID
    if paths['installation_id'].exists():
        try:
            with open(paths['installation_id'], 'r') as f:
                install_id = f.read().strip()
                if install_id:
                    return install_id, False  # ID, is_new
        except Exception as e:
            logger.error(f"Error reading installation ID: {e}")
    
    # Create new installation ID
    install_id = str(uuid.uuid4())
    try:
        with open(paths['installation_id'], 'w') as f:
            f.write(install_id)
        os.chmod(paths['installation_id'], 0o600)
        
        # Also record installation date
        with open(paths['installation_date'], 'w') as f:
            f.write(datetime.utcnow().isoformat())
        os.chmod(paths['installation_date'], 0o600)
        
        logger.info(f"Created new installation ID: {install_id}")
        return install_id, True  # ID, is_new
    except Exception as e:
        logger.error(f"Error creating installation ID: {e}")
        return None, False

def is_fresh_installation():
    """Check if this is a fresh installation"""
    paths = get_installation_paths()
    
    # If no installation ID exists, it's fresh
    if not paths['installation_id'].exists():
        return True
    
    # Check if the installation ID was just created (within last 5 minutes)
    if paths['installation_date'].exists():
        try:
            with open(paths['installation_date'], 'r') as f:
                install_date_str = f.read().strip()
                install_date = datetime.fromisoformat(install_date_str)
                time_since_install = (datetime.utcnow() - install_date).total_seconds()
                
                # Consider it fresh if installed within last 5 minutes
                if time_since_install < 300:
                    return True
        except Exception as e:
            logger.error(f"Error checking installation date: {e}")
    
    return False

def mark_installation_complete():
    """Mark that the installation has been completed"""
    paths = get_installation_paths()
    
    # Update the installation date to mark completion
    # This prevents considering it "fresh" after initial setup
    try:
        # Set date to past to indicate completion
        completion_marker = paths['installation_date'].with_suffix('.completed')
        with open(completion_marker, 'w') as f:
            f.write(datetime.utcnow().isoformat())
        logger.info("Installation marked as complete")
    except Exception as e:
        logger.error(f"Error marking installation complete: {e}")

if __name__ == "__main__":
    # Test the installation ID system
    logging.basicConfig(level=logging.INFO)
    
    install_id, is_new = get_or_create_installation_id()
    print(f"Installation ID: {install_id}")
    print(f"Is new installation: {is_new}")
    print(f"Is fresh installation: {is_fresh_installation()}")