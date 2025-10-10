import hvac
import secrets
import string
import os
import time
import requests
from typing import Dict

def wait_for_vault(url: str, max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for Vault to become available."""
    print("Waiting for Vault to start...")
    for attempt in range(max_retries):
        try:
            # Changed to use localhost instead of vault hostname
            response = requests.get(f"{url}/v1/sys/health", verify=False)
            if response.status_code in (200, 429, 473, 501, 503):
                print(f"Vault is ready! Status: {response.status_code}")
                return True
        except requests.exceptions.ConnectionError as e:
            print(f"Vault not ready, attempt {attempt + 1}/{max_retries}")
            print(f"Connection error: {str(e)}")
            time.sleep(delay)
    return False

def generate_secure_password(length: int = 32) -> str:
    """Generate a password using only Supertokens-compatible characters:
    - Alphanumeric (a-z, A-Z, 0-9)
    - Equals sign (=)
    - Hyphen (-)
    """
    # Only use Supertokens-compatible characters
    allowed_chars = string.ascii_letters + string.digits + "=-"
    
    while True:
        password = ''.join(secrets.choice(allowed_chars) for _ in range(length))
        # Ensure we have at least one of each required type
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            # Ensure at least one special character (= or -)
            any(c in "=-" for c in password)):
            return password

# Update token generation function too
def generate_api_token(length: int = 32) -> str:
    """Generate an API token using only Supertokens-compatible characters"""
    allowed_chars = string.ascii_letters + string.digits + "=-"
    return ''.join(secrets.choice(allowed_chars) for _ in range(length))

# And update the secrets_data structure:
secrets_data = {
    'database': {
        'postgres_user': 'postgres',
        'postgres_password': generate_secure_password(),
        'jdbc_url': 'jdbc:postgresql://db:5432/sting_app'
    },
    'supertokens': {
        'api_key': generate_api_token(),
        'dashboard_api_key': generate_api_token(),
        'jwt_secret': generate_api_token(64)  # Even for JWT, keep it compatible
    }
}

def init_vault_secrets():
    # Get Vault configuration from environment
    VAULT_ADDR = "http://localhost:8200"
    VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-only-token")

    #print(f"Using Vault address: {VAULT_ADDR}")  # Added debug output
    
    # Wait for Vault to be available
    if not wait_for_vault(VAULT_ADDR):
        print("Vault did not become available in time")
        return False

    # Initialize Vault client
    try:
        client = hvac.Client(
            url=VAULT_ADDR,
            token=VAULT_TOKEN,
            verify=False  # Added for dev mode
        )

        # Verify connection
        if not client.is_authenticated():
            print("Failed to authenticate with Vault")
            return False

        print("Successfully connected to Vault")

        # Store secrets in Vault
        try:
            # Enable KV v2 secrets engine if not already enabled
            mounted_secrets = client.sys.list_mounted_secrets_engines()
            print(f"Current mounted secrets engines: {mounted_secrets}")
            
            if 'sting/' not in mounted_secrets:
                print("Enabling KV v2 secrets engine at 'sting/'...")
                client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path='sting',
                    options={'version': 2}
                )

            # Store database secrets
            print("Storing database secrets...")
            client.secrets.kv.v2.create_or_update_secret(
                path='database',
                secret=secrets_data['database'],
                mount_point='sting'
            )

            # Store Supertokens secrets
            print("Storing Supertokens secrets...")
            client.secrets.kv.v2.create_or_update_secret(
                path='supertokens',
                secret=secrets_data['supertokens'],
                mount_point='sting'
            )

            print("\nSuccessfully stored secrets in Vault")
            
            # Print the secrets for initial setup (remove in production)
            print("\nDatabase Credentials:")
            print(f"Username: {secrets_data['database']['postgres_user']}")
            print(f"Password: {secrets_data['database']['postgres_password']}")
            print("\nSupertokens Credentials:")
            print(f"API Key: {secrets_data['supertokens']['api_key']}")
            print(f"Dashboard API Key: {secrets_data['supertokens']['dashboard_api_key']}")

            return True

        except Exception as e:
            print(f"Failed to store secrets: {str(e)}")
            import traceback  # Added traceback for better error reporting
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"Failed to initialize Vault client: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Initializing Vault secrets...")
    if init_vault_secrets():
        print("\nVault initialization completed successfully!")
    else:
        print("\nVault initialization failed!")
        exit(1)