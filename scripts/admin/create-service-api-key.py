#!/usr/bin/env python3
"""
Create STING Service API Key in Database
Creates a proper database API key for service-to-service authentication
"""

import os
import sys
import secrets
import hashlib
import base64
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

from app import create_app
from app.models.api_key_models import ApiKey
from app.models.user_models import User
from app.database import get_db_session

def create_service_api_key():
    """Create a service API key in the database"""

    print("🔑 Creating STING Service API Key")
    print("================================")

    app = create_app()

    with app.app_context():
        with get_db_session() as db:
            # Find or create a service user
            service_user = db.query(User).filter_by(email='service@sting.local').first()

            if not service_user:
                print("📝 Creating service user...")
                service_user = User(
                    email='service@sting.local',
                    kratos_user_id='service-user-internal',
                    first_name='STING',
                    last_name='Service',
                    is_active=True,
                    is_admin=True  # Service needs admin privileges
                )
                db.add(service_user)
                db.commit()
                print(f"✅ Created service user: {service_user.id}")
            else:
                print(f"✅ Using existing service user: {service_user.id}")

            # Check if service API key already exists
            existing_key = db.query(ApiKey).filter_by(
                user_id=service_user.id,
                name='STING Service Key',
                is_active=True
            ).first()

            if existing_key:
                print(f"⚠️  Service API key already exists: {existing_key.key_id}")
                print(f"   Created: {existing_key.created_at}")
                print(f"   Expires: {existing_key.expires_at}")
                return existing_key.key_preview

            # Create the service API key with the Vault key as the secret
            vault_key = "zluwZxtbqbaMVqQ9ubY/iFXxbTPfjFAFGigIubu7A24="

            # Generate key ID and hash the vault key
            key_id = f"sk_{base64.urlsafe_b64encode(secrets.token_bytes(32))[:43].decode()}"
            key_hash = hashlib.sha256(vault_key.encode()).hexdigest()

            print(f"🎲 Generated key ID: {key_id}")
            print(f"🔒 Using Vault key as secret: {vault_key[:10]}...")

            # Set expiration to 1 year
            expires_at = datetime.utcnow() + timedelta(days=365)

            # Create the API key
            api_key = ApiKey(
                key_id=key_id,
                key_hash=key_hash,
                key_preview=f"{key_id[:12]}...{key_id[-8:]}",
                user_id=service_user.id,
                user_email=service_user.email,
                name='STING Service Key',
                description='Internal service-to-service authentication key',
                scopes=['admin', 'read', 'write'],
                permissions={
                    'honey_jar_management': True,
                    'read_only': False,
                    'admin_access': True
                },
                rate_limit_per_minute=1000,  # High limit for service
                expires_at=expires_at,
                is_active=True,
                created_at=datetime.utcnow(),
                last_used_at=None
            )

            db.add(api_key)
            db.commit()

            print("✅ Service API key created successfully!")
            print(f"   Key ID: {key_id}")
            print(f"   User: {service_user.email}")
            print(f"   Scopes: {api_key.scopes}")
            print(f"   Expires: {expires_at.strftime('%Y-%m-%d')}")
            print("")
            print("🧪 Test with:")
            print(f"   curl -sk -H 'X-API-Key: {vault_key}' https://localhost:5050/api/keys/verify")

            return key_id

if __name__ == '__main__':
    try:
        create_service_api_key()
    except Exception as e:
        print(f"❌ Error creating service API key: {e}")
        sys.exit(1)