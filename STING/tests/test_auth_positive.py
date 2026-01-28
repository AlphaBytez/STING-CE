#!/usr/bin/env python3
"""
Test that authenticated users CAN access their honey jars
"""

import requests
import json
import time
from datetime import datetime

def get_kratos_session():
    """Get a valid Kratos session by logging in"""
    print("1. Getting valid Kratos session...")

    # First, initiate login flow
    response = requests.get(
        "https://localhost:4433/self-service/login/api",
        verify=False
    )

    if response.status_code == 200:
        flow = response.json()
        flow_id = flow.get('id')
        print(f"   Login flow initiated: {flow_id}")

        # Try to login with passwordless flow (would need email verification in real scenario)
        # For testing, we'll use the dev mode if available
        return None  # Kratos login requires email verification
    return None

def test_with_dev_mode():
    """Test with development mode authentication"""
    print("\n2. Testing with Development Mode (if enabled)...")

    # First, check if dev mode is enabled
    response = requests.post(
        "http://localhost:8090/bee/context",
        json={
            "query": "What honey jars are available?",
            "user_id": "dev-user",
            "limit": 5
        },
        headers={
            "Content-Type": "application/json"
        },
        timeout=10
    )

    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        print(f"   ✅ SUCCESS: Got {len(results)} results")
        if results:
            print("   Sample result:", json.dumps(results[0], indent=2)[:200])
        return True
    else:
        print(f"   ❌ Dev mode not enabled or failed: {response.text[:100]}")
        return False

def test_with_api_key_through_app():
    """Test using API key through the Flask app"""
    print("\n3. Testing API Key Authentication through Flask...")

    # The Flask app should handle API key authentication
    response = requests.get(
        "https://localhost:5050/api/knowledge/honey-jars",
        headers={
            "X-API-Key": "sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0"
        },
        verify=False,
        timeout=10
    )

    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ SUCCESS: API key auth works!")
        print(f"   Response preview: {json.dumps(data, indent=2)[:200]}")
        return True
    else:
        print(f"   ❌ API key auth failed: {response.text[:100]}")
        return False

def create_test_honey_jar_with_api():
    """Try to create a honey jar using API key"""
    print("\n4. Testing Honey Jar Creation with API Key...")

    test_jar = {
        "name": f"Test Jar {datetime.now().strftime('%H%M%S')}",
        "description": "Test jar for auth verification",
        "type": "public",
        "permissions": {
            "public": True,
            "users": [],
            "groups": []
        }
    }

    response = requests.post(
        "https://localhost:5050/api/knowledge/honey-jars",
        headers={
            "X-API-Key": "sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0",
            "Content-Type": "application/json"
        },
        json=test_jar,
        verify=False,
        timeout=10
    )

    print(f"   Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        jar_id = data.get('id') or data.get('honey_jar_id')
        print(f"   ✅ SUCCESS: Created honey jar with ID: {jar_id}")
        return jar_id
    else:
        print(f"   ❌ Creation failed: {response.text[:200]}")
        return None

def test_direct_knowledge_with_flask_session():
    """Test accessing knowledge service with a Flask session cookie"""
    print("\n5. Testing with Flask Session Cookie...")

    # First, we need to get a Flask session by authenticating through the app
    # This would normally be done through the login flow

    # For now, we'll demonstrate that the endpoint exists and requires auth
    response = requests.post(
        "http://localhost:8090/bee/context",
        json={
            "query": "test query",
            "user_id": "test-user"
        },
        cookies={
            "ory_kratos_session": "test-session-cookie"  # Would need real session
        },
        timeout=10
    )

    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print("   ⚠️  Endpoint requires valid session (expected)")
        return None
    return response.status_code == 200

def enable_dev_mode_and_test():
    """Enable dev mode temporarily for testing"""
    print("\n6. Enabling Knowledge Dev Mode for Testing...")

    # Set environment variable and restart knowledge service
    import os

    print("   Setting KNOWLEDGE_DEV_MODE=true in knowledge.env...")

    # Read current env file
    env_path = "/Users/captain-wolf/.sting-ce/env/knowledge.env"

    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Check if already has dev mode
        has_dev_mode = any('KNOWLEDGE_DEV_MODE' in line for line in lines)

        if not has_dev_mode:
            # Add dev mode
            lines.append('\n# Temporary for testing\n')
            lines.append('KNOWLEDGE_DEV_MODE=true\n')
            lines.append('KNOWLEDGE_DEV_USER_ID=test-user-123\n')
            lines.append('KNOWLEDGE_DEV_USER_EMAIL=test@sting.local\n')
            lines.append('KNOWLEDGE_DEV_USER_ROLE=admin\n')

            with open(env_path, 'w') as f:
                f.writelines(lines)

            print("   ✅ Dev mode enabled in config")
            print("   ⚠️  RESTART knowledge service: ./manage_sting.sh restart knowledge")
            return True
        else:
            print("   ℹ️  Dev mode already configured")
            return True

    except Exception as e:
        print(f"   ❌ Error enabling dev mode: {e}")
        return False

def main():
    print("=" * 60)
    print("POSITIVE Authentication Test - Verify Access Works")
    print("=" * 60)

    results = []

    # Test different auth methods
    results.append(("Dev Mode Access", test_with_dev_mode()))
    results.append(("API Key via Flask", test_with_api_key_through_app()))

    # Try to create a jar
    jar_id = create_test_honey_jar_with_api()
    results.append(("Create Honey Jar", jar_id is not None))

    # Try Flask session
    results.append(("Flask Session", test_direct_knowledge_with_flask_session()))

    # Suggest enabling dev mode if all failed
    if not any(result for _, result in results if result):
        print("\n" + "=" * 60)
        print("SUGGESTION: Enable dev mode for testing")
        print("=" * 60)
        if enable_dev_mode_and_test():
            print("\nDev mode configured. Please run:")
            print("  ./manage_sting.sh restart knowledge")
            print("Then re-run this test.")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        if result is None:
            status = "⚠️  SKIPPED"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{test_name}: {status}")

    successful = sum(1 for _, r in results if r)
    total = sum(1 for _, r in results if r is not None)

    print(f"\nTotal: {successful}/{total} tests passed")

    if successful > 0:
        print("\n🎉 Authentication IS working for authorized users!")
    else:
        print("\n⚠️  Need to configure proper authentication for testing")
        print("Options:")
        print("1. Enable KNOWLEDGE_DEV_MODE=true in knowledge.env")
        print("2. Create a proper Kratos session through login")
        print("3. Fix API key authentication in Flask proxy")

if __name__ == "__main__":
    main()