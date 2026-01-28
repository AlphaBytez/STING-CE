#!/usr/bin/env python3
"""
Admin Password Reset Tool
Allows system administrators to reset the admin password from the command line
"""

import os
import sys
import secrets
import string
import requests
import json
from pathlib import Path

def generate_secure_password(length=16):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def reset_admin_password():
    """Reset the admin password directly in Kratos"""
    print("🔐 STING Admin Password Reset Tool")
    print("=" * 50)
    
    # Get Kratos admin URL from environment or use default
    kratos_admin_url = os.getenv('KRATOS_ADMIN_URL', 'https://localhost:4434')
    
    # Check if we want to generate a new password or use a provided one
    if len(sys.argv) > 1 and sys.argv[1] != '--generate':
        new_password = sys.argv[1]
        print(f"Using provided password")
    else:
        new_password = generate_secure_password()
        print(f"Generated new secure password")
    
    try:
        # First, find the admin identity
        print("\n📋 Finding admin identity...")
        response = requests.get(
            f"{kratos_admin_url}/identities",
            params={"credentials_identifier": "admin@sting.local"},
            verify=False  # For self-signed certificates
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to find admin identity: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        identities = response.json()
        if not identities:
            print("❌ Admin user not found")
            return False
        
        admin_id = identities[0]['id']
        print(f"✅ Found admin identity: {admin_id}")
        
        # Update the password
        print("\n🔄 Updating password...")
        update_data = {
            "schemas": ["default"],
            "state": "active",
            "traits": {
                "email": "admin@sting.local",
                "role": "admin",
                "force_password_change": False
            },
            "credentials": {
                "password": {
                    "config": {
                        "password": new_password
                    }
                }
            }
        }
        
        response = requests.put(
            f"{kratos_admin_url}/identities/{admin_id}",
            json=update_data,
            verify=False
        )
        
        if response.status_code in [200, 204]:
            print("✅ Password updated successfully!")
            
            # Save the new password to file
            password_file = Path.home() / '.sting-ce' / 'admin_password.txt'
            password_file.parent.mkdir(parents=True, exist_ok=True)
            password_file.write_text(new_password)
            
            # Also save to project directory for reference
            project_password_file = Path('/Users/captain-wolf/Documents/GitHub/STING-CE/STING/admin_password.txt')
            if project_password_file.parent.exists():
                project_password_file.write_text(new_password)
            
            print(f"\n✅ Admin password has been reset!")
            print(f"📝 New credentials:")
            print(f"   Email: admin@sting.local")
            print(f"   Password: {new_password}")
            print(f"\n💾 Password saved to: {password_file}")
            
            # Clear any force_password_change flag
            print("\n🔓 Clearing password change requirement...")
            # This would normally update the UserSettings in the app database
            
            return True
        else:
            print(f"❌ Failed to update password: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Kratos. Make sure the service is running.")
        print(f"   Tried to connect to: {kratos_admin_url}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main entry point"""
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Usage: python reset_admin_password.py [password|--generate]")
        print("  password    - Set a specific password")
        print("  --generate  - Generate a secure random password (default)")
        print("\nExample:")
        print("  python reset_admin_password.py MyNewPassword123!")
        print("  python reset_admin_password.py --generate")
        sys.exit(0)
    
    success = reset_admin_password()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()