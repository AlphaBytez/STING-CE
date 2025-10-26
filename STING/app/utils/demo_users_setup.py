"""
Demo Users Setup - Creates demo users on system initialization
Similar to how the admin user is created
"""

import logging
import requests
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'http://kratos:4434')

# Demo users to create
DEMO_USERS = [
    {
        'email': 'demo@example.com',
        'password': 'DemoPassword123!',
        'first_name': 'Demo',
        'last_name': 'User',
        'description': 'General demo user'
    },
    {
        'email': 'testuser@example.com',
        'password': 'TestPassword123!',
        'first_name': 'Test',
        'last_name': 'User',
        'description': 'Test user for development'
    }
]

def get_demo_marker_path():
    """Get path for demo users initialization marker"""
    install_dir = os.getenv('STING_INSTALL_DIR', '/Users/captain-wolf/.sting-ce')
    if os.path.exists(install_dir):
        base_path = Path(install_dir)
    else:
        base_path = Path('/.sting-ce')
    
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path / '.demo_users_initialized'

def is_demo_initialized():
    """Check if demo users have already been initialized"""
    return get_demo_marker_path().exists()

def mark_demo_initialized():
    """Mark that demo users have been initialized"""
    try:
        with open(get_demo_marker_path(), 'w') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
        return True
    except Exception as e:
        logger.error(f"Error creating demo initialized marker: {e}")
        return False

def check_user_exists(email):
    """Check if a user already exists"""
    try:
        response = requests.get(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            params={'credentials_identifier': email},
            verify=False
        )
        
        if response.status_code == 200:
            identities = response.json()
            return len(identities) > 0
        else:
            logger.error(f"Failed to check user {email}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        return False

def create_demo_user(user_info):
    """Create a demo user in Kratos"""
    try:
        identity_data = {
            "schema_id": "default",
            "state": "active",
            "traits": {
                "email": user_info['email'],
                "name": {
                    "first": user_info['first_name'],
                    "last": user_info['last_name']
                },
                "role": "user"  # Regular user, not admin
            },
            "credentials": {
                "password": {
                    "config": {
                        "password": user_info['password']
                    }
                }
            }
        }
        
        response = requests.post(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            json=identity_data,
            verify=False
        )
        
        if response.status_code == 201:
            logger.info(f"Successfully created demo user: {user_info['email']}")
            return True
        else:
            logger.error(f"Failed to create demo user {user_info['email']}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating demo user: {e}")
        return False

def initialize_demo_users():
    """
    Initialize demo users if they don't exist
    This should be called during application startup
    """
    try:
        # Skip if already initialized (unless forced)
        if is_demo_initialized() and not os.getenv('FORCE_DEMO_USERS', '').lower() == 'true':
            logger.info("Demo users already initialized, skipping creation")
            return True
        
        # Wait a bit for Kratos to be ready
        time.sleep(5)
        
        created_count = 0
        for user in DEMO_USERS:
            if not check_user_exists(user['email']):
                logger.info(f"Creating demo user: {user['email']}")
                if create_demo_user(user):
                    created_count += 1
                else:
                    logger.error(f"Failed to create demo user: {user['email']}")
            else:
                logger.info(f"Demo user already exists: {user['email']}")
        
        # Mark as initialized
        mark_demo_initialized()
        
        if created_count > 0:
            # Create notice
            notice = f"""
================================================================================
📧 DEMO USERS CREATED
================================================================================
The following demo users are available for testing:

"""
            for user in DEMO_USERS:
                notice += f"  • {user['email']} / {user['password']} - {user['description']}\n"
            
            notice += """
🔗 Login at: https://localhost:8443/login
================================================================================
"""
            logger.info(notice)
            print(notice)  # Also print to stdout for visibility
        
        return True
            
    except Exception as e:
        logger.error(f"Error initializing demo users: {e}")
        return False