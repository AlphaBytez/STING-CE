#!/usr/bin/env python3
"""
Check if admin user exists in Kratos
Returns exit code 0 if admin exists, 1 otherwise
"""

import sys
import argparse
import requests
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Kratos configuration
KRATOS_ADMIN_URL = 'http://kratos:4434'

def check_admin_exists(email):
    """Check if admin user exists in Kratos"""
    try:
        response = requests.get(
            f'{KRATOS_ADMIN_URL}/admin/identities',
            timeout=10,
            verify=False
        )

        if response.status_code != 200:
            print(f"Failed to query Kratos: {response.status_code}")
            return False

        identities = response.json()

        # Check if admin with this email exists
        for identity in identities:
            if identity.get('traits', {}).get('email') == email:
                # Check if has credentials
                credentials = identity.get('credentials', {})
                if credentials:
                    print(f"✅ Admin user found: {email}")
                    return True
                else:
                    print(f"⚠️  Admin user exists but has no credentials: {email}")
                    return False

        print(f"❌ Admin user not found: {email}")
        return False

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Kratos: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Check if admin user exists in Kratos')
    parser.add_argument('--email', required=True, help='Admin email address to check')

    args = parser.parse_args()

    exists = check_admin_exists(args.email)
    sys.exit(0 if exists else 1)

if __name__ == '__main__':
    main()
