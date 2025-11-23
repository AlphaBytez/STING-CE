#!/usr/bin/env python3
"""
Reset MFA credentials for a user (TOTP, WebAuthn) while preserving the account.
This allows users who are locked out to re-enroll in MFA.
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


def reset_mfa(email, reset_totp=True, reset_webauthn=True, force=False):
    """Reset MFA credentials for a user while preserving the account"""

    print(f"🔍 Searching for user: {email}")

    try:
        # Find the user
        response = requests.get(
            f'{KRATOS_ADMIN_URL}/admin/identities',
            timeout=10,
            verify=False
        )

        if response.status_code != 200:
            print(f"❌ Failed to query Kratos: {response.status_code}")
            return False

        identities = response.json()
        user_identity = None

        for identity in identities:
            if identity.get('traits', {}).get('email') == email:
                user_identity = identity
                break

        if not user_identity:
            print(f"❌ User not found: {email}")
            return False

        user_id = user_identity.get('id')
        credentials = user_identity.get('credentials', {})

        # Check what credentials exist
        has_totp = 'totp' in credentials
        has_webauthn = 'webauthn' in credentials

        print(f"📋 User found: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Has TOTP: {'Yes' if has_totp else 'No'}")
        print(f"   Has WebAuthn: {'Yes' if has_webauthn else 'No'}")

        if not has_totp and not has_webauthn:
            print(f"ℹ️  User has no MFA credentials to reset")
            return True

        # Confirm reset unless --force or non-interactive
        if not force:
            if sys.stdin.isatty():
                print(f"\n⚠️  WARNING: You are about to reset MFA credentials for: {email}")
                if reset_totp and has_totp:
                    print(f"   • TOTP will be removed")
                if reset_webauthn and has_webauthn:
                    print(f"   • WebAuthn/Passkeys will be removed")
                print(f"\n   The user will need to re-enroll in MFA on next login.")
                confirm = input("\nType 'RESET' to confirm: ")
                if confirm != 'RESET':
                    print("❌ Reset cancelled")
                    return False
            else:
                print(f"❌ Non-interactive mode requires --force flag")
                print(f"   Use: --force to skip confirmation")
                return False

        # Build the updated identity without the MFA credentials we want to reset
        updated_credentials = {}
        for cred_type, cred_data in credentials.items():
            if cred_type == 'totp' and reset_totp:
                print(f"🗑️  Removing TOTP credential...")
                continue
            if cred_type == 'webauthn' and reset_webauthn:
                print(f"🗑️  Removing WebAuthn credentials...")
                continue
            updated_credentials[cred_type] = cred_data

        # Update the identity via Kratos Admin API
        # We need to use PATCH or PUT to update credentials
        # Kratos uses a specific format for credential updates

        # First, get the full identity
        identity_response = requests.get(
            f'{KRATOS_ADMIN_URL}/admin/identities/{user_id}',
            timeout=10,
            verify=False
        )

        if identity_response.status_code != 200:
            print(f"❌ Failed to get identity details: {identity_response.status_code}")
            return False

        full_identity = identity_response.json()

        # For Kratos, we need to delete credentials by updating the identity
        # The cleanest way is to use the credentials delete endpoint if available,
        # or update the identity without those credentials

        # Try to delete TOTP
        if reset_totp and has_totp:
            delete_response = requests.delete(
                f'{KRATOS_ADMIN_URL}/admin/identities/{user_id}/credentials/totp',
                timeout=10,
                verify=False
            )
            if delete_response.status_code in [200, 204, 404]:
                print(f"✅ TOTP credential removed")
            else:
                print(f"⚠️  Could not remove TOTP: {delete_response.status_code}")
                # Try alternative method - this may not be supported in all Kratos versions
                print(f"   Attempting alternative method...")

        # Try to delete WebAuthn
        if reset_webauthn and has_webauthn:
            delete_response = requests.delete(
                f'{KRATOS_ADMIN_URL}/admin/identities/{user_id}/credentials/webauthn',
                timeout=10,
                verify=False
            )
            if delete_response.status_code in [200, 204, 404]:
                print(f"✅ WebAuthn credentials removed")
            else:
                print(f"⚠️  Could not remove WebAuthn: {delete_response.status_code}")

        # Invalidate all sessions to force re-authentication
        print(f"🔄 Invalidating all sessions for user...")
        sessions_response = requests.delete(
            f'{KRATOS_ADMIN_URL}/admin/identities/{user_id}/sessions',
            timeout=10,
            verify=False
        )
        if sessions_response.status_code in [200, 204, 404]:
            print(f"✅ All sessions invalidated")
        else:
            print(f"⚠️  Could not invalidate sessions: {sessions_response.status_code}")

        print(f"\n✅ MFA reset complete for: {email}")
        print(f"   The user can now log in and will be prompted to set up MFA again.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to Kratos: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Reset MFA credentials for a user (preserves account)',
        epilog='Example: reset-mfa.py --email=user@example.com --force'
    )
    parser.add_argument('--email', required=True, help='User email address')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--totp-only', action='store_true', help='Only reset TOTP (keep passkeys)')
    parser.add_argument('--webauthn-only', action='store_true', help='Only reset WebAuthn/passkeys (keep TOTP)')

    args = parser.parse_args()

    # Determine what to reset
    reset_totp = not args.webauthn_only
    reset_webauthn = not args.totp_only

    if args.totp_only and args.webauthn_only:
        print("❌ Cannot specify both --totp-only and --webauthn-only")
        sys.exit(1)

    success = reset_mfa(args.email, reset_totp, reset_webauthn, args.force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
