#!/usr/bin/env python3
"""
Create a regular user account in STING.

This script creates non-admin users who can:
- Access honey jars they're assigned to
- Use the Bee Chat interface
- View documents within their permission scope

Usage:
    msting create user user@example.com
    msting create user --email=user@example.com --name="John Doe"
"""
import requests
import sys
import urllib3
import os
import argparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default to localhost (for running from host), can be overridden with env var
KRATOS_ADMIN_URL = os.getenv("KRATOS_ADMIN_URL", "https://localhost:4434")
STING_API_URL = os.getenv("STING_API_URL", "https://localhost:5050")


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


def sync_sting_database(email, kratos_id, role='user'):
    """Sync user with STING database"""
    try:
        sync_response = requests.post(
            f"{STING_API_URL}/api/admin/sync-user",
            json={
                'email': email,
                'kratos_id': kratos_id,
                'role': role
            },
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'
            },
            timeout=10,
            verify=False
        )
        
        return sync_response.status_code in [200, 201]
    except Exception as e:
        print(f"STING database sync error: {e}")
        return False


def create_user(email, first_name="User", last_name="", role="user"):
    """
    Create a new regular user - PASSWORDLESS BY DEFAULT.
    
    Args:
        email: User's email address
        first_name: User's first name (default: "User")
        last_name: User's last name (optional)
        role: User role - 'user', 'viewer', 'editor' (default: 'user')
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"👤 Creating user account: {email}")
    print(f"   Role: {role}")
    
    # Build identity data for Kratos
    identity_data = {
        "schema_id": "default",
        "state": "active",
        "traits": {
            "email": email,
            "name": {
                "first": first_name,
                "last": last_name
            },
            "role": role,
            "force_password_change": False
        }
    }
    
    # All users are passwordless - they authenticate via email/passkey
    print("🔐 Creating passwordless account (email verification required)")
    
    try:
        response = requests.post(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            json=identity_data,
            verify=False,
            timeout=15
        )
        
        if response.status_code == 201:
            user_data = response.json()
            kratos_id = user_data.get('id')
            print("✅ User created successfully in Kratos!")
            
            # Sync with STING database
            if kratos_id:
                print("🔗 Syncing with STING database...")
                if sync_sting_database(email, kratos_id, role):
                    print("✅ STING database sync completed!")
                else:
                    print("⚠️ STING database sync failed (user may still work)")
            
            print(f"\n{'='*50}")
            print(f"✅ USER CREATED SUCCESSFULLY")
            print(f"{'='*50}")
            print(f"📧 Email: {email}")
            print(f"👤 Name: {first_name} {last_name}".strip())
            print(f"🔑 Role: {role}")
            print(f"🔐 Authentication: Passwordless (email/passkey)")
            print(f"{'='*50}")
            print("\n📝 First login steps:")
            print("1. Go to: https://<HOSTNAME>:8443/login")
            print("2. Enter the email address")
            print("3. Click the verification link sent to email")
            print("4. User will be prompted to set up passkey authentication")
            print("\n💡 TIP: Users can also be assigned to honey jars in the admin UI")
            return True
            
        elif response.status_code == 409:
            print("⚠️ User already exists in Kratos - attempting database sync...")
            
            # Get existing Kratos user
            kratos_id = get_kratos_user_id(email)
            if kratos_id:
                print(f"🔍 Found existing Kratos user ID: {kratos_id}")
                # Try to sync with STING database
                if sync_sting_database(email, kratos_id, role):
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
            print(f"❌ Failed to create user: HTTP {response.status_code}")
            try:
                error_data = response.json()
                if 'error' in error_data:
                    print(f"   Error: {error_data['error'].get('message', 'Unknown error')}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is Kratos running?")
        print("   Try: msting status")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out - Kratos may be slow or unresponsive")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def list_users():
    """List all users in the system"""
    try:
        response = requests.get(
            f"{KRATOS_ADMIN_URL}/admin/identities",
            verify=False,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            identities = response.json()
            print(f"\n{'='*60}")
            print(f"📋 STING USERS ({len(identities)} total)")
            print(f"{'='*60}")
            
            for identity in identities:
                traits = identity.get('traits', {})
                email = traits.get('email', 'N/A')
                name = traits.get('name', {})
                full_name = f"{name.get('first', '')} {name.get('last', '')}".strip() or 'N/A'
                role = traits.get('role', 'user')
                state = identity.get('state', 'unknown')
                
                role_emoji = '👑' if role == 'admin' else '👤'
                state_emoji = '✅' if state == 'active' else '⚠️'
                
                print(f"{state_emoji} {role_emoji} {email}")
                print(f"      Name: {full_name} | Role: {role} | State: {state}")
                print()
            
            return True
        else:
            print(f"❌ Failed to list users: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Create a regular user account in STING',
        epilog='''
Examples:
  msting create user user@example.com
  msting create user --email=user@example.com --name="John Doe"
  msting create user --email=test@company.com --role=editor
        '''
    )
    
    parser.add_argument('email', nargs='?', help='User email address')
    parser.add_argument('--email', dest='email_flag', help='User email address (alternative)')
    parser.add_argument('--name', help='Full name (e.g., "John Doe")')
    parser.add_argument('--first-name', dest='first_name', help='First name')
    parser.add_argument('--last-name', dest='last_name', help='Last name')
    parser.add_argument('--role', choices=['user', 'moderator'], 
                        default='user', help='User role (default: user). For admin, use: msting create admin')
    parser.add_argument('--list', action='store_true', help='List all users')
    
    args = parser.parse_args()
    
    # Handle --list command
    if args.list:
        success = list_users()
        sys.exit(0 if success else 1)
    
    # Get email from positional or flag
    email = args.email or args.email_flag
    
    if not email:
        print("❌ Error: Email address is required")
        print("\nUsage:")
        print("  msting create user user@example.com")
        print("  msting create user --email=user@example.com")
        print("\nFor more options: msting create user --help")
        sys.exit(1)
    
    # Parse name
    first_name = args.first_name or "User"
    last_name = args.last_name or "Account"  # Default to "Account" to meet minLength requirement
    
    if args.name:
        parts = args.name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else "Account"  # Default last name if not provided
    
    # Create the user
    success = create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=args.role
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
