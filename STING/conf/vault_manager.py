import os
import hvac
import logging
from typing import Optional, Dict, Any, List
import json
from pathlib import Path
import requests
import string
import secrets
import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VaultError(Exception):
    """Custom exception for Vault-related errors."""
    pass

class VaultManager:
    """Manages interactions with HashiCorp Vault."""
    
    def __init__(self,
                 url: str = "http://vault:8200",
                 token: str = None,
                 mount_point: str = "sting",
                 max_retries: int = 5,
                 retry_delay: int = 2):
        logger.debug(f"Initializing VaultManager with URL: {url}")
        self.url = url
        self.token = token or os.environ.get('VAULT_TOKEN', 'root')
        self.mount_point = mount_point
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.debug("Creating Vault client...")
        self.client = self._initialize_client_with_retry()
        logger.debug("Vault client created successfully")

    def _initialize_client_with_retry(self) -> hvac.Client:
        """Initialize client with retry logic for container startup."""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting to connect to Vault (attempt {attempt + 1}/{self.max_retries})")
                return self._initialize_client()
            except Exception as e:
                logger.warning(f"Vault connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("All Vault connection attempts failed")
                    raise VaultError(f"Failed to connect to Vault after {self.max_retries} attempts: {str(e)}")

    def _initialize_client(self) -> hvac.Client:
        try:
            client = hvac.Client(
                url=self.url,
                token=self.token,
                session=requests.Session()
            )

            # Verify the connection
            if not client.sys.is_initialized():
                raise VaultError("Vault is not initialized")

            # Check if client is authenticated
            if not client.is_authenticated():
                logger.warning(f"Vault client not authenticated with token: {self.token}")
                raise VaultError("Vault client authentication failed")

            # Check if KV v2 secrets engine is already mounted
            try:
                mounted_engines = client.sys.list_mounted_secrets_engines()
                if self.mount_point not in mounted_engines:
                    client.sys.enable_secrets_engine(
                        backend_type='kv',
                        path=self.mount_point,
                        options={'version': 2}
                    )
                    logger.info(f"Enabled KV v2 secrets engine at '{self.mount_point}'")
                else:
                    logger.info(f"KV v2 secrets engine already mounted at '{self.mount_point}'")
            except Exception as mount_error:
                logger.warning(f"Could not check/mount secrets engine: {mount_error}")
                # Continue anyway - the mount might already exist or we might not have permissions

            return client

        except Exception as e:
            raise VaultError(f"Failed to initialize Vault client: {str(e)}")

    def write_secret(self, path: str, data: Dict[str, Any]) -> bool:
            """
            Write a secret to Vault.
            
            Args:
                path: Secret path (e.g., 'supertokens/credentials')
                data: Dictionary containing secret data
                
            Returns:
                bool: True if successful
            """
            try:
                full_path = f"{self.mount_point}/{path}"
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=data,
                    mount_point=self.mount_point
                )
                logger.info(f"Successfully wrote secret to {full_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to write secret to {full_path}: {str(e)}")
                return False

    def read_secret(self, path: str, key: Optional[str] = None) -> Optional[Any]:
        """
        Read a secret from Vault.
        
        Args:
            path: Secret path
            key: Optional specific key to retrieve
            
        Returns:
            The secret value or None if not found
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point
            )
            
            if not response or 'data' not in response['data']:
                return None
                
            secret_data = response['data']['data']
            
            if key:
                return secret_data.get(key)
            return secret_data
            
        except Exception as e:
            logger.error(f"Failed to read secret from {path}: {str(e)}")
            return None

    def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from Vault.
        
        Args:
            path: Secret path
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point
            )
            logger.info(f"Successfully deleted secret at {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret at {path}: {str(e)}")
            return False

    def migrate_secrets_from_config(self, config_path: str) -> bool:
        """
        Migrate secrets from config.yml to Vault.
        
        Args:
            config_path: Path to config.yml file
            
        Returns:
            bool: True if successful
        """
        try:
            import yaml
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # MigratwSupertokens secrets
            supertokens_secrets = {
                'api_key': config.get('security', {}).get('supertokens', {}).get('api_key'),
                'api_base_path': config.get('security', {}).get('supertokens', {}).get('api_base_path'),
                'connection_uri': config.get('security', {}).get('supertokens', {}).get('connection_uri')
            }
            self.write_secret('supertokens', supertokens_secrets)
            
            # Migrate Database secrets
            db_secrets = {
                'postgres_user': config.get('database', {}).get('user'),
                'postgres_password': config.get('database', {}).get('password')
            }
            self.write_secret('database', db_secrets)
            
            logger.info("Successfully migrated secrets to Vault")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate secrets: {str(e)}")
            return False

    def initialize_vault(self) -> bool:
        """
        Initialize Vault with default policies and secrets.
        
        Returns:
            bool: True if successful
        """
        try:
            # Check if already initialized
            if self.client.sys.is_initialized():
                logger.info("Vault is already initialized")
                return True
                
            # Create default policies
            app_policy = '''
                path "sting/supertokens/*" {
                    capabilities = ["read"]
                }
                path "sting/database/*" {
                    capabilities = ["read"]
                }
            '''
            
            self.client.sys.create_or_update_policy(
                name='sting-app',
                policy=app_policy
            )
                        
            logger.info("Successfully initialized Vault")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Vault: {str(e)}")


    def create_token(self, 
                    policies: List[str], 
                    ttl: str = '1h',
                    num_uses: int = 0) -> Optional[str]:
        """
        Create a new token with specified policies.
        
        Args:
            policies: List of policy names
            ttl: Token time-to-live
            num_uses: Number of uses (0 for unlimited)
            
        Returns:
            str: Token if successful, None otherwise
        """
        try:
            token = self.client.auth.token.create(
                policies=policies,
                ttl=ttl,
                num_uses=num_uses
            )
            return token['auth']['client_token']
        except Exception as e:
            logger.error(f"Failed to create token: {str(e)}")
            return None

    def rotate_secrets(self) -> bool:
        """
        Rotate all application secrets.
        
        Returns:
            bool: True if successful
        """
        try:
            # Read current secrets
            supertokens_secrets = self.read_secret('supertokens')
            db_secrets = self.read_secret('database')
            
            # Generate new passwords
            new_supertokens = {
            'api_key': os.urandom(32).hex(),
            'api_base_path': supertokens_secrets['api_base_path'],
            'connection_uri': supertokens_secrets['connection_uri']
}
            
            new_db = {
                'postgres_user': db_secrets['postgres_user'],
                'postgres_password': os.urandom(32).hex()
            }
            
            # Write new secrets
            self.write_secret('supertokens', new_supertokens)
            self.write_secret('database', new_db)
            
            logger.info("Successfully rotated all secrets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secrets: {str(e)}")
            return False
        
    def _generate_supertokens_secret(self, length: int = 32) -> str:
        allowed_chars = string.ascii_letters + string.digits + "=-"
        while True:
            secret = ''.join(secrets.choice(allowed_chars) for _ in range(length))
            if (any(c.islower() for c in secret) and
                any(c.isupper() for c in secret) and
                any(c.isdigit() for c in secret) and
                any(c in "=-" for c in secret)):
                return secret

    def initialize_secrets(self):
        """Initialize all application secrets"""
        db_password = self._generate_supertokens_secret()
        self.write_secret('database', {'password': db_password})
        
        st_api_key = self._generate_supertokens_secret()
        self.write_secret('supertokens', {
            'api_key': st_api_key,
            'dashboard_key': self._generate_supertokens_secret()
        })


if __name__ == "__main__":
    # Example usage
    vault = VaultManager()
    vault.initialize_vault()