#!/usr/bin/env python3
"""
Script to clear all sessions from Redis and check Kratos sessions
This helps diagnose and fix session persistence issues
"""

import redis
import requests
import sys
import os
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for local development
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def clear_redis_sessions():
    """Clear all Flask sessions from Redis"""
    try:
        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        
        print(f"Connecting to Redis at: {redis_url}")
        
        # List all session keys
        session_keys = []
        for key in r.scan_iter(match='flask_session:*'):
            session_keys.append(key)
        
        for key in r.scan_iter(match='sting:*'):
            session_keys.append(key)
            
        print(f"\nFound {len(session_keys)} session keys in Redis")
        
        if session_keys:
            print("\nSession keys found:")
            for key in session_keys[:10]:  # Show first 10
                print(f"  - {key.decode()}")
            if len(session_keys) > 10:
                print(f"  ... and {len(session_keys) - 10} more")
            
            # Clear all sessions
            response = input("\nDo you want to clear all Redis sessions? (yes/no): ")
            if response.lower() == 'yes':
                for key in session_keys:
                    r.delete(key)
                print(f"✓ Cleared {len(session_keys)} sessions from Redis")
            else:
                print("Skipped clearing Redis sessions")
        else:
            print("No sessions found in Redis")
            
    except Exception as e:
        print(f"Error accessing Redis: {e}")
        print("Make sure Redis is running and accessible")

def check_kratos_sessions():
    """Check active Kratos sessions via admin API"""
    try:
        kratos_admin_url = os.getenv('KRATOS_ADMIN_URL', 'http://localhost:4434')
        
        print(f"\nChecking Kratos sessions at: {kratos_admin_url}")
        
        # List all sessions
        response = requests.get(
            f"{kratos_admin_url}/admin/sessions",
            verify=False,
            params={'page_size': 100}
        )
        
        if response.status_code == 200:
            sessions = response.json()
            
            if isinstance(sessions, list):
                session_list = sessions
            else:
                # Handle paginated response
                session_list = sessions.get('sessions', [])
            
            print(f"\nFound {len(session_list)} active Kratos sessions:")
            
            for session in session_list[:5]:  # Show first 5
                identity = session.get('identity', {})
                traits = identity.get('traits', {})
                email = traits.get('email', 'Unknown')
                session_id = session.get('id', 'Unknown')
                authenticated_at = session.get('authenticated_at', 'Unknown')
                expires_at = session.get('expires_at', 'Unknown')
                
                print(f"\n  Session ID: {session_id[:20]}...")
                print(f"  Email: {email}")
                print(f"  Authenticated: {authenticated_at}")
                print(f"  Expires: {expires_at}")
                
            if len(session_list) > 5:
                print(f"\n  ... and {len(session_list) - 5} more sessions")
                
            # Offer to revoke all sessions
            if session_list:
                response = input("\nDo you want to revoke ALL Kratos sessions? (yes/no): ")
                if response.lower() == 'yes':
                    revoked_count = 0
                    for session in session_list:
                        session_id = session.get('id')
                        if session_id:
                            try:
                                revoke_response = requests.delete(
                                    f"{kratos_admin_url}/admin/sessions/{session_id}",
                                    verify=False
                                )
                                if revoke_response.status_code in [204, 200]:
                                    revoked_count += 1
                            except:
                                pass
                    print(f"✓ Revoked {revoked_count} Kratos sessions")
                else:
                    print("Skipped revoking Kratos sessions")
        else:
            print(f"Failed to get Kratos sessions: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error accessing Kratos admin API: {e}")
        print("Make sure Kratos is running and the admin API is accessible")

def main():
    print("=== STING Session Cleanup Tool ===\n")
    print("This tool will help diagnose and clear session persistence issues.\n")
    
    # Clear Redis sessions
    clear_redis_sessions()
    
    # Check Kratos sessions
    check_kratos_sessions()
    
    print("\n=== Cleanup Complete ===")
    print("\nTo test if the issue is fixed:")
    print("1. Open a new incognito/private browser window")
    print("2. Login to STING")
    print("3. Logout")
    print("4. Try to login again - you should need to enter your password")
    
    print("\nIf the issue persists, check:")
    print("- Browser developer tools > Application > Cookies")
    print("- Look for cookies: ory_kratos_session, ory_kratos_session, sting_session")
    print("- Clear all cookies manually if needed")

if __name__ == "__main__":
    main()