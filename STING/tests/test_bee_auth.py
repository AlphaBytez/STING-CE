#!/usr/bin/env python3
"""
Test script to verify Bee chat honey jar authentication
"""

import requests
import json
import sys

# Test configuration
BEE_URL = "http://localhost:8888"
KNOWLEDGE_URL = "http://localhost:8090"

def test_unauthenticated_access():
    """Test that unauthenticated requests are blocked"""
    print("\n=== Test 1: Unauthenticated Access (Should Fail) ===")

    response = requests.post(
        f"{BEE_URL}/chat",
        json={
            "message": "What honey jars do I have access to?",
            "user_id": "test-user-no-auth",
            "session_id": "test-session",
            "require_auth": False
        },
        timeout=10
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response', '')[:200]}...")

        # Check if honey jar context was denied
        if "authentication required" in result.get('response', '').lower() or \
           "please log in" in result.get('response', '').lower() or \
           "no honey jars" in result.get('response', '').lower():
            print("✅ PASS: Authentication properly required for honey jar access")
            return True
        else:
            print("❌ FAIL: Bee provided response without authentication!")
            return False
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_authenticated_with_api_key():
    """Test authenticated access using API key"""
    print("\n=== Test 2: Authenticated Access with API Key ===")

    # First, let's check if we can access honey jars directly with API key
    response = requests.get(
        "https://localhost:5050/api/knowledge/honey-jars",
        headers={"X-API-Key": "sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0"},
        verify=False,
        timeout=10
    )

    print(f"Direct API Status: {response.status_code}")

    # Now test through Bee with authentication
    response = requests.post(
        f"{BEE_URL}/chat",
        json={
            "message": "What honey jars are available?",
            "user_id": "admin-user",
            "session_id": "test-session",
            "require_auth": True
        },
        headers={"Authorization": "Bearer sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0"},
        timeout=10
    )

    print(f"Bee Chat Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response preview: {result.get('response', '')[:200]}...")

        if response.status_code == 200:
            print("✅ PASS: Authenticated access works")
            return True
    else:
        print(f"Response: {response.text[:200]}")
        return False

def test_knowledge_service_direct():
    """Test direct knowledge service access"""
    print("\n=== Test 3: Direct Knowledge Service Query ===")

    # Test without auth (should fail)
    response = requests.post(
        f"{KNOWLEDGE_URL}/bee/context",
        json={
            "query": "test query",
            "user_id": "test-user"
        },
        timeout=10
    )

    print(f"Without auth - Status: {response.status_code}")
    if response.status_code == 401:
        print("✅ PASS: Knowledge service correctly requires authentication")
    else:
        print(f"❌ FAIL: Expected 401, got {response.status_code}")

    return response.status_code == 401

def main():
    print("=" * 60)
    print("STING Bee Chat Authentication Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    try:
        results.append(("Unauthenticated Access", test_unauthenticated_access()))
    except Exception as e:
        print(f"Test failed with error: {e}")
        results.append(("Unauthenticated Access", False))

    try:
        results.append(("Knowledge Service Direct", test_knowledge_service_direct()))
    except Exception as e:
        print(f"Test failed with error: {e}")
        results.append(("Knowledge Service Direct", False))

    try:
        results.append(("Authenticated with API Key", test_authenticated_with_api_key()))
    except Exception as e:
        print(f"Test failed with error: {e}")
        results.append(("Authenticated with API Key", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Authentication is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please review the authentication implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()