import hvac
import os
from typing import Dict, Optional

def get_vault_secrets() -> Dict[str, str]:
    """Fetch secrets from Vault and format them for environment variables."""
    
    
    VAULT_ADDR = os.getenv("VAULT_ADDR", "http://0.0.0.0:8200")
    VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-only-token")
    
    client = hvac.Client(
        url=VAULT_ADDR,
        token='VAULT_TOKEN'
    )

    env_vars = {}
    
    try:
        # Fetch database secrets
        db_secrets = client.secrets.kv.v2.read_secret_version(
            path='database',
            mount_point='sting'
        )['data']['data']
        
        env_vars.update({
            'POSTGRES_USER': db_secrets['postgres_user'],
            'POSTGRES_PASSWORD': db_secrets['postgres_password'],
        })



        return env_vars

    except Exception as e:
        print(f"Failed to fetch secrets: {str(e)}")
        raise

def update_env_file(secrets: Dict[str, str], env_file: str = '/opt/sting-ce/conf/.env'):
    """Update the .env file with secrets from Vault."""
    try:
        # Read existing env file
        existing_env = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        existing_env[key] = value

        # Update with new secrets
        existing_env.update(secrets)

        # Write back to file
        with open(env_file, 'w') as f:
            for key, value in existing_env.items():
                f.write(f'{key}={value}\n')

        print(f"Successfully updated {env_file} with secrets from Vault")

    except Exception as e:
        print(f"Failed to update env file: {str(e)}")
        raise

if __name__ == "__main__":
    secrets = get_vault_secrets()
    update_env_file(secrets)