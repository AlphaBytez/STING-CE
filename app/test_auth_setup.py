# test_auth_setup.py
import sys
import base64

def test_imports():
    print("Testing imports...")
    
    # Test Supertokens imports (DEPRECATED, now using Kratos)
    print("\nTesting Supertokens imports (DEPRECATED):")
    supertokens_ok = False
    try:
        from supertokens_python import init, InputAppInfo, SupertokensConfig
        from supertokens_python.recipe import passwordless, session
        from supertokens_python.recipe.passwordless import ContactEmailOnlyConfig
        print("✓ Supertokens imports successful (legacy support)")
        supertokens_ok = True
    except ImportError as e:
        print(f"✗ Supertokens import error: {e}")
        print("Note: This is expected since we are migrating to Kratos")

    # Test WebAuthn imports
    print("\nTesting WebAuthn imports:")
    try:
        import webauthn
        from webauthn.helpers.cose import COSEAlgorithmIdentifier
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            UserVerificationRequirement,
            AuthenticatorAttachment
        )
        print("✓ WebAuthn imports successful")
        print(f"✓ WebAuthn version: {webauthn.__version__}")
    except ImportError as e:
        print(f"✗ WebAuthn import error: {e}")
        return False

    # Test creating basic WebAuthn options
    print("\nTesting WebAuthn basic functionality:")
    try:
        # Convert test user ID to bytes
        test_user_id = base64.urlsafe_b64encode(b"test_user_123")
        options = webauthn.generate_registration_options(
            rp_id="localhost",
            rp_name="Test App",
            user_id=test_user_id,
            user_name="test@example.com"
        )
        print("✓ WebAuthn can generate registration options")
    except Exception as e:
        print(f"✗ WebAuthn registration options error: {e}")
        return False

    # Test Kratos client
    print("\nTesting Kratos client:")
    try:
        import requests
        print("✓ Requests library available for Kratos client")
        
        # Optional - try to connect to Kratos health endpoint
        try:
            response = requests.get("https://localhost:4433/health/ready", verify=False, timeout=2)
            print(f"✓ Kratos health check status: {response.status_code}")
        except Exception as e:
            print(f"✗ Kratos health check error (this is OK if Kratos isn't running): {e}")
            
    except ImportError as e:
        print(f"✗ Requests library import error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    success = test_imports()
    if success:
        print("\n✓ All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)