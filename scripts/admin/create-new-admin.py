#!/usr/bin/env python3
"""Create a new admin user with a known password"""
import requests
import secrets
import string
import sys
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KRATOS_ADMIN_URL = os.getenv("KRATOS_ADMIN_URL", "http://sting-ce-kratos:4434")

def generate_password():
    """Generate a secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(16))

def get_kratos_user_id(email):
    """Get Kratos user ID by email"""
    try:
        response = requests.get(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            params={'credentials_identifier': email},
            verify=False,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            identities = response.json()
            if identities:
                return identities[0]['id']
        return None
    except Exception as e:
        print(f"Error getting Kratos user ID: {e}")
        return None

def sync_sting_database(email, kratos_id):
    """Sync user with STING database"""
    try:
        # Use STING API to create/update user record
        sync_response = requests.post(
            "http://sting-ce-app:5050/api/admin/sync-user",
            json={
                'email': email,
                'kratos_id': kratos_id,
                'role': 'admin'
            },
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'
            },
            timeout=10
        )
        
        return sync_response.status_code in [200, 201]
    except Exception as e:
        print(f"STING database sync error: {e}")
        return False

def create_admin_user(email, password=None, passwordless=True):
    """Create a new admin user - PASSWORDLESS BY DEFAULT"""
    print(f"Creating admin user: {email}")
    
    # Base identity data
    identity_data = {
        "schema_id": "default",
        "state": "active",
        "traits": {
            "email": email,
            "name": {
                "first": "Admin",
                "last": "User"
            },
            "role": "admin",
            "force_password_change": False
        }
    }
    
    # Add credentials based on mode - PASSWORDLESS IS DEFAULT
    if passwordless:
        print("🔐 Creating admin account (email authentication enabled)")
        print("🚀 STING is fully passwordless - no passwords stored!")
        # Don't add any credentials - Kratos will enable available methods based on configuration
    else:
        # Legacy password mode (discouraged)
        if not password:
            password = generate_password()
        print(f"⚠️  Creating LEGACY password-based admin (not recommended)")
        print(f"💡 Consider using passwordless mode instead!")
        identity_data["credentials"] = {
            "password": {
                "config": {
                    "password": password
                }
            }
        }
    
    try:
        response = requests.post(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            json=identity_data,
            verify=False
        )
        
        if response.status_code == 201:
            user_data = response.json()
            kratos_id = user_data.get('id')
            print("✅ Admin user created successfully in Kratos!")
            
            # Sync with STING database
            if kratos_id:
                print("🔗 Syncing with STING database...")
                if sync_sting_database(email, kratos_id):
                    print("✅ STING database sync completed!")
                else:
                    print("⚠️ STING database sync failed (user may still work)")
            
            print(f"\nEmail: {email}")
            if passwordless:
                print("🔐 Passwordless account - email verification required")
                print("\nFirst login steps:")
                print("1. Go to: https://localhost:8443/login")
                print("2. Enter your email address")
                print("3. Click the magic link sent to your email")
                print("4. You'll be redirected to set up additional security")
            else:
                print(f"Password: {password}")
                print("\nNext steps:")
                print("1. Login at: https://localhost:8443/login")
            
            print("\n🔒 IMPORTANT: Admin Security Setup Required")
            print("After email verification, you'll set up:")
            print("  • TOTP authenticator app (required for admins)")
            print("  • Passkey/biometric authentication (optional but recommended)")
            print("Admin accounts require enhanced security for dashboard access.")
            print("\n⚠️  Dashboard access will be blocked until security setup is complete.")
            print("💡 This ensures maximum security and provides recovery options.")
            return True
        elif response.status_code == 409:
            print("⚠️ User already exists in Kratos - checking STING database sync...")
            
            # Get existing Kratos user
            kratos_id = get_kratos_user_id(email)
            if kratos_id:
                print(f"🔍 Found Kratos user ID: {kratos_id}")
                # Try to sync with STING database
                if sync_sting_database(email, kratos_id):
                    print("✅ Database synchronization completed!")
                    print("🔗 User now synchronized between Kratos and STING databases")
                    return True
                else:
                    print("❌ Failed to synchronize databases")
                    return False
            else:
                print("❌ Could not retrieve Kratos user information")
                return False
        else:
            print(f"❌ Failed to create user: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create a new admin user - PASSWORDLESS BY DEFAULT')
    parser.add_argument('--email', default='admin@sting.local', help='Admin email')
    parser.add_argument('--password', help='LEGACY: Admin password (only used with --use-password)')
    parser.add_argument('--use-password', action='store_true', help='LEGACY: Create password-based admin (not recommended)')
    parser.add_argument('--passwordless', action='store_true', default=True, help='Create passwordless admin (DEFAULT)')
    
    args = parser.parse_args()
    
    # Override passwordless if user explicitly requested password mode
    if args.use_password:
        args.passwordless = False
    
    success = create_admin_user(args.email, args.password, args.passwordless)
    sys.exit(0 if success else 1)