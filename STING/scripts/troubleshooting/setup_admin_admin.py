#!/usr/bin/env python3
"""
STING Admin-Admin Setup Script

Creates a limited "admin" user that can only promote other users but cannot:
- Access LLM settings (requires super_admin)
- Perform destructive operations
- Modify system configuration

This provides a secure way to delegate user management without full system access.

The created admin will be prompted to:
1. Change their temporary password on first login
2. Set up passkey authentication
3. Only have access to user promotion features

Usage:
    python setup_admin_admin.py [--email EMAIL]
"""

import os
import sys
import argparse
import secrets
import string
import requests
import json
import urllib3
from datetime import datetime

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def log(message):
    print(f"{GREEN}[ADMIN SETUP]{NC} {message}")

def warning(message):
    print(f"{YELLOW}[WARNING]{NC} {message}")

def error(message):
    print(f"{RED}[ERROR]{NC} {message}")

def info(message):
    print(f"{BLUE}[INFO]{NC} {message}")

def generate_temp_password(length=16):
    """Generate a secure temporary password"""
    # Use a mix of letters, numbers, and safe symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def create_kratos_identity(email, password, kratos_admin_url="https://localhost:4434"):
    """Create a Kratos identity via the Admin API"""
    try:
        # Create identity payload with password credentials
        identity_payload = {
            "schema_id": "default",
            "traits": {
                "email": email,
                "name": {
                    "first": "Admin",
                    "last": "User"
                }
            },
            "credentials": {
                "password": {
                    "config": {
                        "password": password
                    }
                }
            }
        }
        
        # Create the identity
        response = requests.post(
            f"{kratos_admin_url}/admin/identities",
            json=identity_payload,
            headers={"Content-Type": "application/json"},
            verify=False
        )
        
        if response.status_code != 201:
            print(f"❌ Failed to create Kratos identity: {response.text}")
            return None
        
        identity = response.json()
        identity_id = identity["id"]
        log(f"Created Kratos identity: {identity_id}")
        return identity_id
        
    except requests.exceptions.ConnectionError:
        error(f"Could not connect to Kratos Admin API at {kratos_admin_url}")
        error("Make sure Kratos is running and accessible")
        return None
    except Exception as e:
        error(f"Error creating Kratos identity: {e}")
        return None

def create_limited_admin(email, password):
    """Create a limited admin user in STING database"""
    try:
        from app import create_app
        from app.database import db
        from app.models.user_models import User, UserRole, UserStatus, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            # Check if admin already exists
            existing_admin = User.query.filter_by(email=email).first()
            if existing_admin:
                warning(f"User {email} already exists")
                if existing_admin.role == UserRole.ADMIN:
                    log("User is already an admin")
                    return True
                else:
                    # Promote existing user
                    existing_admin.role = UserRole.ADMIN
                    existing_admin.is_admin = True
                    existing_admin.is_super_admin = False  # Explicitly NOT super admin
                    existing_admin.updated_at = datetime.utcnow()
                    db.session.commit()
                    log(f"Promoted existing user {email} to limited admin")
                    return True
            
            # Create new limited admin user (this will be created when they first log in)
            # For now, just log that the Kratos identity is ready
            log(f"Limited admin Kratos identity ready for: {email}")
            log("User will be automatically created as limited admin on first login")
            
            # Set a flag that this admin should be auto-promoted
            SystemSetting.set(
                f'auto_promote_admin_{email.replace("@", "_").replace(".", "_")}',
                True,
                f'Auto-promote {email} to limited admin on first login',
                f'admin_setup_{datetime.utcnow().isoformat()}'
            )
            
            db.session.commit()
            return True
            
    except Exception as e:
        error(f"Error setting up limited admin: {e}")
        return False

def create_admin_admin_user(email, password):
    """Complete admin-admin user creation process"""
    log(f"🔐 Creating limited admin user: {email}")
    print("=" * 60)
    
    # Step 1: Create Kratos identity
    log("1. Creating Kratos identity with password...")
    identity_id = create_kratos_identity(email, password)
    
    if not identity_id:
        error("Failed to create Kratos identity. Cannot continue.")
        return False
    
    # Step 2: Set up auto-promotion
    log("2. Configuring auto-promotion to limited admin...")
    if not create_limited_admin(email, password):
        error("Failed to configure limited admin auto-promotion")
        return False
    
    # Step 3: Display instructions
    print("\n" + "=" * 60)
    log("✅ Limited admin user setup completed!")
    print()
    info("ADMIN USER DETAILS:")
    print(f"   📧 Email: {email}")
    print(f"   🔑 Temporary Password: {password}")
    print(f"   🆔 Kratos ID: {identity_id}")
    print()
    info("SECURITY FEATURES:")
    print("   • Limited to user promotion only")
    print("   • Cannot access LLM settings")
    print("   • Cannot perform destructive operations")
    print("   • Must set up passkey on first login")
    print("   • Must change temporary password")
    print()
    info("FIRST LOGIN PROCESS:")
    print("   1. Go to: https://localhost:8443/login")
    print("   2. Use the temporary password above")
    print("   3. System will prompt to change password")
    print("   4. Set up passkey authentication")
    print("   5. Admin can then promote other users")
    print()
    warning("IMPORTANT SECURITY NOTES:")
    print("   ⚠️  Change the temporary password immediately")
    print("   ⚠️  Set up passkey for secure authentication")
    print("   ⚠️  This admin CANNOT access system configuration")
    print("   ⚠️  Only super_admin can access LLM settings")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Create limited STING admin user')
    parser.add_argument('--email', help='Admin user email address')
    parser.add_argument('--kratos-url', default='https://localhost:4434',
                       help='Kratos Admin API URL (default: https://localhost:4434)')
    
    args = parser.parse_args()
    
    print("🐝 STING Limited Admin Setup")
    print("=" * 40)
    print()
    print("This creates an admin user with LIMITED privileges:")
    print("• Can promote/demote other users")
    print("• Cannot access LLM/system settings")
    print("• Ideal for user management delegation")
    print()
    
    # Get email
    email = args.email
    if not email:
        email = input("Enter admin email address: ").strip()
        if not email or '@' not in email:
            error("Valid email address required")
            return 1
    
    # Check if services are running
    log("Checking STING services...")
    try:
        response = requests.get(f"{args.kratos_url}/admin/health/ready", verify=False, timeout=5)
        if response.status_code != 200:
            error("Kratos service is not ready")
            return 1
    except:
        error("Cannot connect to Kratos service")
        error("Make sure STING services are running with: docker compose up -d")
        return 1
    
    # Generate secure temporary password
    temp_password = generate_temp_password()
    
    # Create the limited admin user
    success = create_admin_admin_user(email, temp_password)
    
    if success:
        log("🎉 Setup completed successfully!")
        return 0
    else:
        error("Setup failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())