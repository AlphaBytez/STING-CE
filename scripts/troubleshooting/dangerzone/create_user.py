#!/usr/bin/env python3
"""
STING Regular User Creation Script

This script creates a regular user programmatically using Kratos and STING's user management system.
Creates email-only users that can login with email codes (AAL1) and optionally set up 2FA later.

Usage:
    python create_user.py [--email EMAIL] [--first-name FIRST] [--last-name LAST]
"""

import os
import sys
import argparse
import requests
import json
import urllib3
from datetime import datetime

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_user_in_kratos(email, first_name="User", last_name="Account"):
    """
    Create a regular user in Kratos with email-only authentication (AAL1)
    This prevents AAL2 traps while allowing optional 2FA setup later
    """
    
    KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'https://localhost:4434')
    
    # User identity payload - same pattern as admin but role: 'user'
    identity_payload = {
        "schema_id": "default",
        "traits": {
            "email": email,
            "name": {
                "first": first_name,
                "last": last_name
            },
            "role": "user"  # Regular user, not admin
        },
        "credentials": {
            "code": {
                "config": {
                    "identifiers": [email]
                }
            }
        }
    }
    
    try:
        print(f"🔐 Creating regular user: {email}")
        print(f"📧 Email-only authentication enabled (passwordless)")
        
        # Create identity in Kratos
        response = requests.post(
            f'{KRATOS_ADMIN_URL}/admin/identities',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json=identity_payload,
            verify=False
        )
        
        if response.status_code == 201:
            user_data = response.json()
            print(f"✅ User created successfully in Kratos!")
            print(f"📧 Email: {email}")
            print(f"🆔 User ID: {user_data['id']}")
            print(f"🔐 Authentication: Email codes only (AAL1)")
            print()
            print(f"🎯 Next steps for user:")
            print(f"1. User can login at: https://localhost:8443/login")
            print(f"2. Enter email: {email}")
            print(f"3. Check email for login code")
            print(f"4. Optional: Set up 2FA in Settings after login")
            print()
            print(f"✅ User ready for email-based login!")
            return True
            
        elif response.status_code == 409:
            print(f"⚠️  User {email} already exists in Kratos")
            return True
            
        else:
            print(f"❌ Failed to create user: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error creating user: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Create a regular STING user with email authentication'
    )
    parser.add_argument('email', help='User email address')
    parser.add_argument('--first-name', default='User', help='First name (default: User)')
    parser.add_argument('--last-name', default='Account', help='Last name (default: Account)')
    
    args = parser.parse_args()
    
    print("🐝 STING User Creation Script")
    print("=" * 40)
    print(f"Creating regular user: {args.email}")
    print(f"Name: {args.first_name} {args.last_name}")
    print()
    
    success = create_user_in_kratos(args.email, args.first_name, args.last_name)
    
    if success:
        print("🎉 User creation completed successfully!")
        sys.exit(0)
    else:
        print("❌ User creation failed")
        sys.exit(1)

if __name__ == '__main__':
    main()