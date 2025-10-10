#!/usr/bin/env python3
"""
STING Admin User Creation Script

This script creates an admin user programmatically using Kratos and STING's user management system.
Run this after installation to set up the first admin user with a temporary password.

Usage:
    python create_admin.py [--email EMAIL] [--password PASSWORD] [--temp-password]
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

def generate_temp_password(length=12):
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits
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
            verify=False  # Skip SSL verification for self-signed certificates
        )
        
        if response.status_code != 201:
            print(f"❌ Failed to create Kratos identity: {response.text}")
            return None
        
        identity = response.json()
        identity_id = identity["id"]
        print(f"✅ Created Kratos identity with password: {identity_id}")
        return identity_id
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to Kratos Admin API at {kratos_admin_url}")
        print("   Make sure Kratos is running and accessible")
        return None
    except Exception as e:
        print(f"❌ Error creating Kratos identity: {e}")
        return None

def promote_user_to_admin(email):
    """Promote the user to admin in STING database"""
    try:
        # Import here to avoid issues if script is run outside Flask context
        from app import create_app
        from app.database import db
        from app.models.user_models import User, UserRole, SystemSetting
        
        app = create_app()
        
        with app.app_context():
            # Find the user by email
            user = User.query.filter_by(email=email).first()
            
            if not user:
                print(f"❌ User {email} not found in STING database")
                print("   The user may need to complete their first login to be created in STING")
                return False
            
            # Promote to super admin
            user.promote_to_super_admin()
            
            # Mark as first admin if none exists
            if not SystemSetting.get('first_admin_created', False):
                SystemSetting.set(
                    'first_admin_created',
                    True,
                    'First admin user created programmatically',
                    f'admin_script_{datetime.utcnow().isoformat()}'
                )
            
            db.session.commit()
            print(f"✅ Promoted {email} to super admin")
            return True
            
    except Exception as e:
        print(f"❌ Error promoting user in STING: {e}")
        return False

def create_admin_user(email, password, temp_password=False):
    """Complete admin user creation process"""
    print(f"🐝 Creating STING admin user: {email}")
    print("=" * 50)
    
    # Step 1: Create Kratos identity
    print("1. Creating Kratos identity...")
    identity_id = create_kratos_identity(email, password)
    
    if not identity_id:
        print("❌ Failed to create Kratos identity. Cannot continue.")
        return False
    
    # Step 2: Instructions for user creation in STING
    print("\n2. Admin user setup instructions:")
    print(f"   • Kratos identity created: {identity_id}")
    print(f"   • Email: {email}")
    print(f"   • Password: {'[TEMPORARY]' if temp_password else '[AS PROVIDED]'}")
    print("\n   To complete setup:")
    print("   a) User must log in once to create STING profile")
    print("   b) Run this script again to promote to admin")
    print("   c) Or user will be auto-promoted if they're the first user")
    
    if temp_password:
        print(f"\n   ⚠️  TEMPORARY PASSWORD: {password}")
        print("      User MUST change this password on first login!")
    
    # Step 3: Try to promote if user exists
    print("\n3. Checking for existing STING user...")
    if promote_user_to_admin(email):
        print("✅ User promoted to admin successfully!")
    else:
        print("ℹ️  User not found in STING database yet.")
        print("   They will be auto-promoted when they first log in.")
    
    print("\n🎉 Admin user creation process completed!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Create STING admin user')
    parser.add_argument('--email', help='Admin user email address')
    parser.add_argument('--password', help='Admin user password')
    parser.add_argument('--temp-password', action='store_true', 
                       help='Generate a temporary password that must be changed')
    parser.add_argument('--kratos-url', default='https://localhost:4434',
                       help='Kratos Admin API URL (default: https://localhost:4434)')
    
    args = parser.parse_args()
    
    # Get email
    email = args.email
    if not email:
        email = input("Enter admin email address: ").strip()
        if not email or '@' not in email:
            print("❌ Valid email address required")
            return 1
    
    # Get password
    password = args.password
    temp_password = args.temp_password
    
    if temp_password:
        password = generate_temp_password()
        print(f"🔐 Generated temporary password: {password}")
    elif not password:
        import getpass
        password = getpass.getpass("Enter admin password: ").strip()
        if not password:
            print("❌ Password required")
            return 1
        
        confirm = getpass.getpass("Confirm password: ").strip()
        if password != confirm:
            print("❌ Passwords do not match")
            return 1
    
    # Create the admin user
    success = create_admin_user(email, password, temp_password)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())