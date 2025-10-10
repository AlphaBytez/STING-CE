#!/usr/bin/env python3
"""
Create Claude Development User
Creates a system user for Claude to use during development testing
"""

import sys
import os
import uuid
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, '/opt/sting-ce')
sys.path.insert(0, '/opt/sting-ce/app')

from app.models.api_key_models import ApiKey
from app.models.user_models import User
from app.database import get_db_session

def create_claude_user():
    """Create Claude system user and API key"""
    
    claude_email = "claude@sting.local"
    claude_user_id = str(uuid.uuid4())
    
    print(f"Creating Claude development user...")
    print(f"Email: {claude_email}")
    print(f"User ID: {claude_user_id}")
    
    try:
        with get_db_session() as session:
            # Check if Claude user already exists
            existing_user = session.query(User).filter(User.email == claude_email).first()
            if existing_user:
                print(f"Claude user already exists with ID: {existing_user.kratos_id}")
                claude_user_id = existing_user.kratos_id
            else:
                # Create user in STING database
                claude_user = User(
                    kratos_id=claude_user_id,
                    email=claude_email,
                    username="claude-dev",
                    display_name="Claude Development User",
                    is_admin=True,  # Give admin privileges for testing
                    is_super_admin=False
                )
                
                session.add(claude_user)
                session.commit()
                print(f"✅ Created Claude user in STING database")
            
            # Check if API key already exists
            existing_key = session.query(ApiKey).filter(
                ApiKey.user_id == claude_user_id,
                ApiKey.name == "Claude Development Key",
                ApiKey.is_active == True
            ).first()
            
            if existing_key:
                print(f"✅ API key already exists: {existing_key.key_id}")
                print(f"⚠️  Secret key was only shown during creation")
                return existing_key.key_id, None
            
            # Create API key for Claude
            api_key, secret = ApiKey.generate_key(
                user_id=claude_user_id,
                user_email=claude_email,
                name="Claude Development Key",
                scopes=["read", "write", "admin"],
                permissions={
                    "reports": ["read", "write", "create", "delete"],
                    "honey_jars": ["read", "write", "create", "delete"],
                    "files": ["read", "write", "upload", "download"],
                    "templates": ["read", "write", "create", "delete"],
                    "admin": ["read", "write"]
                },
                expires_in_days=365,  # 1 year expiration
                description="Development API key for Claude testing and automation"
            )
            
            # Set higher rate limit for development
            api_key.rate_limit_per_minute = 300  # 300 requests per minute
            
            session.add(api_key)
            session.commit()
            
            print(f"✅ Created API key: {api_key.key_id}")
            print(f"🔑 SECRET KEY (save this - won't be shown again): {secret}")
            print(f"🚀 Rate limit: {api_key.rate_limit_per_minute} requests/minute")
            print(f"📅 Expires: {api_key.expires_at}")
            
            return api_key.key_id, secret
            
    except Exception as e:
        print(f"❌ Error creating Claude user: {e}")
        return None, None

def test_api_key(secret):
    """Test the API key with a simple endpoint"""
    import requests
    
    if not secret:
        print("⚠️  No secret key to test")
        return
    
    try:
        headers = {
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json"
        }
        
        # Test with the validation endpoint
        response = requests.post(
            "https://localhost:3000/api/keys/validate",
            headers=headers,
            verify=False  # Skip SSL verification for local development
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API key test successful!")
            print(f"   Key ID: {data.get('key_id')}")
            print(f"   Scopes: {data.get('scopes')}")
        else:
            print(f"❌ API key test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"⚠️  Could not test API key (service may not be running): {e}")

if __name__ == "__main__":
    print("🤖 Claude Development User Setup")
    print("=" * 40)
    
    key_id, secret = create_claude_user()
    
    if key_id:
        print("\n" + "=" * 40)
        print("📝 SAVE THESE CREDENTIALS:")
        print(f"API Key ID: {key_id}")
        if secret:
            print(f"Secret Key: {secret}")
            print("\n⚠️  Store the secret key safely - it won't be shown again!")
            
            # Test the API key
            print("\n🧪 Testing API key...")
            test_api_key(secret)
        
        print("\n📋 Usage Example:")
        print("curl -H 'Authorization: Bearer <secret_key>' \\")
        print("     https://localhost:3000/api/reports/templates")
        
    else:
        print("❌ Failed to create Claude user")
        sys.exit(1)