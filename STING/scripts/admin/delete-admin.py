#!/usr/bin/env python3
"""
Delete admin user from Kratos
"""

import sys
import os
import argparse
import requests
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Kratos configuration - use env var or default to HTTPS
KRATOS_ADMIN_URL = os.getenv("KRATOS_ADMIN_URL", "https://kratos:4434")

def delete_admin(email, force=False):
    """Delete admin user from Kratos"""

    print(f"🔍 Searching for admin user: {email}")

    try:
        # Find the admin user
        response = requests.get(
            f'{KRATOS_ADMIN_URL}/admin/identities',
            timeout=10,
            verify=False
        )

        if response.status_code != 200:
            print(f"❌ Failed to query Kratos: {response.status_code}")
            return False

        identities = response.json()
        admin_id = None

        for identity in identities:
            if identity.get('traits', {}).get('email') == email:
                admin_id = identity.get('id')
                break

        if not admin_id:
            print(f"❌ Admin user not found: {email}")
            return False

        # Confirm deletion unless --force or non-interactive
        if not force:
            # Check if running interactively (stdin is a tty)
            if sys.stdin.isatty():
                print(f"\n⚠️  WARNING: You are about to delete admin user: {email}")
                print(f"   User ID: {admin_id}")
                confirm = input("\nType 'DELETE' to confirm: ")
                if confirm != 'DELETE':
                    print("❌ Deletion cancelled")
                    return False
            else:
                # Non-interactive mode without --force, abort for safety
                print(f"❌ Non-interactive mode requires --force flag")
                print(f"   Use: --force to skip confirmation")
                return False

        # Delete the admin user
        print(f"🗑️  Deleting admin user...")
        delete_response = requests.delete(
            f'{KRATOS_ADMIN_URL}/admin/identities/{admin_id}',
            timeout=10,
            verify=False
        )

        if delete_response.status_code in [200, 204, 404]:
            print(f"✅ Admin user deleted successfully: {email}")
            print(f"   User ID: {admin_id}")
            return True
        else:
            print(f"❌ Failed to delete admin user: {delete_response.status_code}")
            print(f"   Response: {delete_response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to Kratos: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Delete admin user from Kratos')
    parser.add_argument('--email', required=True, help='Admin email address to delete')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    success = delete_admin(args.email, args.force)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
