import os
import re
try:
    import yaml  # type: ignore
except ImportError:
    yaml = None
import json
import logging
import secrets
import string
import time
import sys  # Added sys import
import base64
import subprocess
from urllib.parse import quote as url_quote
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
try:
    import hvac  # type: ignore
except ImportError:
    hvac = None
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class ConfigurationError(Exception):
    """Exception raised for errors in the configuration loader."""
    pass

def check_config_exists(config_path: str) -> bool:
    """
    Check if config.yml exists, and if not, create it from the best available template.
    Automatically detects macOS and uses Mac-optimized template when available.
    Returns True if config exists or was created successfully, False otherwise.
    """
    if os.path.exists(config_path):
        return True
    
    # Platform detection for optimal template selection
    import platform
    is_macos = platform.system() == 'Darwin'
    
    # Choose the best template based on platform
    mac_config_path = config_path + '.default.mac'
    default_config_path = config_path + '.default'
    
    if is_macos and os.path.exists(mac_config_path):
        template_path = mac_config_path
        platform_name = "macOS/Apple Silicon"
    elif os.path.exists(default_config_path):
        template_path = default_config_path
        platform_name = "general"
    else:
        logger.error(f"❌ No configuration templates found!")
        logger.error(f"   Looked for: {mac_config_path if is_macos else default_config_path}")
        logger.error(f"   And: {default_config_path}")
        logger.error("Cannot proceed without configuration template.")
        return False
    
    logger.warning(f"⚠️  Configuration file not found: {config_path}")
    logger.info(f"🖥️  Detected platform: {platform.system()} ({platform.machine()})")
    logger.info(f"📝 Creating config.yml from {platform_name} template: {template_path}")
    
    try:
        import shutil
        shutil.copy2(template_path, config_path)
        logger.info(f"✅ Configuration file created successfully!")
        logger.info(f"💡 Mac-optimized configuration applied!" if is_macos and template_path.endswith('.mac') else f"💡 Please customize {config_path} for your environment.")
        
        if is_macos and template_path.endswith('.mac'):
            logger.info("🍎 Apple Silicon optimizations enabled:")
            logger.info("   - MPS (Metal Performance Shaders) acceleration")
            logger.info("   - fp16 precision for faster inference")
            logger.info("   - Model preloading for instant responses")
            logger.info("   - Unified memory optimization")
            logger.info("   - Response caching (10 minutes)")
        else:
            logger.info("   Key settings to review:")
            logger.info("   - application.install_dir")
            logger.info("   - application.models_dir") 
            logger.info("   - llm_service.performance.profile (for speed optimization)")
            logger.info("   - speed optimization presets (see bottom of config file)")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create config file: {e}")
        return False

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML or JSON file."""
    try:
        # Check if config file exists
        if not os.path.exists(config_path):
            raise ConfigurationError(f"Configuration file not found: {config_path}. Use check_config_exists() to create from template.")
        
        # Read file content
        with open(config_path, 'r') as f:
            content = f.read()
        # Determine format and parse accordingly
        if config_path.lower().endswith('.json'):
            config = json.loads(content)
        else:
            if yaml is not None:
                config = yaml.safe_load(content)
            else:
                # Simple YAML parser for key: value pairs
                config = {}
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' not in line:
                        continue
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    lower_val = val.lower()
                    if lower_val == 'true':
                        config[key] = True
                    elif lower_val == 'false':
                        config[key] = False
                    else:
                        try:
                            if '.' in val:
                                config[key] = float(val)
                            else:
                                config[key] = int(val)
                        except ValueError:
                            config[key] = val
        if not isinstance(config, dict):
            raise ConfigurationError(f"Configuration file must contain a mapping/dict, got {type(config)}")
        # Convert boolean values to lowercase strings
        result: Dict[str, Any] = {}
        for key, value in config.items():
            if isinstance(value, bool):
                result[key] = str(value).lower()
            else:
                result[key] = value
        return result
    except FileNotFoundError as e:
        raise ConfigurationError(f"Configuration file not found: {config_path}") from e
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ConfigurationError(f"Failed to parse configuration file: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e

def validate_config(config: Dict[str, Any]) -> None:
    """Validate that required configuration keys are present."""
    required_keys = [
        'APP_PORT', 'FLASK_DEBUG', 'FLASK_APP', 'APP_ENV',
        'REACT_PORT', 'APP_HOST',
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'DB_PORT',
        'LOG_MAX_SIZE', 'BACKUP_DEFAULT_DIRECTORY',
        'BACKUP_COMPRESSION_LEVEL', 'BACKUP_RETENTION_COUNT',
        'BACKUP_EXCLUDE_PATTERNS'
    ]
    missing = [key for key in required_keys if key not in config]
    if missing:
        raise ConfigurationError(f"Missing required configuration keys: {', '.join(missing)}")

def substitute_env_variables(config: Any) -> Any:
    """Recursively substitute environment variables in config values."""
    if isinstance(config, dict):
        return {k: substitute_env_variables(v) for k, v in config.items()}
    if isinstance(config, list):
        return [substitute_env_variables(item) for item in config]
    if isinstance(config, str):
        pattern = re.compile(r'\$\{([^}]+)\}')
        def repl(match: re.Match) -> str:
            return os.environ.get(match.group(1), '')
        return pattern.sub(repl, config)
    return config

def sanitize_key(key: str) -> str:
    """Remove invalid characters from configuration keys."""
    return ''.join(c for c in key if c.isalnum() or c == '_')

def sanitize_path(path: str) -> str:
    """Sanitize file paths by removing '..' segments and duplicates."""
    absolute = path.startswith('/')
    parts = path.split('/')
    new_parts = [p for p in parts if p and p != '..']
    sanitized = '/'.join(new_parts)
    return ('/' if absolute else '') + sanitized

@dataclass
class LLMServiceConfig:
    """LLM service configuration container."""
    enabled: bool
    default_model: str
    models: Dict[str, Dict[str, Any]]
    filtering: Dict[str, Any]
    routing: Dict[str, Any]
    model_lifecycle: Dict[str, Any]  # Add model lifecycle configuration
    ollama: Dict[str, Any]  # Add Ollama configuration
    external_ai: Dict[str, Any]  # Add External AI service configuration
    
    @classmethod
    def process_config(cls, raw_config: Dict) -> 'LLMServiceConfig':
        llm_config = raw_config.get('llm_service', {})
        
        return cls(
            enabled=llm_config.get('enabled', True),
            default_model=llm_config.get('default_model', 'phi3'),
            models=llm_config.get('models', {}),
            filtering=llm_config.get('filtering', {}),
            routing=llm_config.get('routing', {}),
            model_lifecycle=llm_config.get('model_lifecycle', {}),
            ollama=llm_config.get('ollama', {
                'enabled': True,
                'endpoint': 'http://localhost:11434',
                'default_model': 'phi3:mini',
                'models_to_install': ['phi3:mini', 'deepseek-r1:latest'],
                'auto_install': True
            }),
            external_ai=llm_config.get('external_ai', {
                'enabled': True,
                'port': 8091,
                'ollama_endpoint': 'http://localhost:11434'
            })
        )

@dataclass
class DatabaseConfig:
    """Database configuration container."""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    @classmethod
    def process_config(cls, raw_config: Dict) -> 'DatabaseConfig':
        db_config = raw_config.get('database', {})
        
        return cls(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            name=db_config.get('name', 'sting_app'),
            user=db_config.get('user', 'postgres'),
            password=db_config.get('password', 'postgres')
        )

# SupertokensConfig removed - deprecated in favor of Kratos authentication

@dataclass
class KratosConfig:
    """Ory Kratos configuration container."""
    public_url: str
    admin_url: str
    cookie_domain: str

    @classmethod
    def process_config(cls, raw_config: Dict[str, Any]) -> 'KratosConfig':
        kr = raw_config.get('kratos', {})
        return cls(
            public_url=kr.get('public_url', 'http://localhost:4433'),
            admin_url=kr.get('admin_url', 'http://localhost:4434'),
            cookie_domain=kr.get('cookie_domain', 'localhost')
        )

class ConfigurationManager:
    """Manages application configuration and secrets."""
    
    _config_cache = {}
    
    def __init__(self, config_file: str, mode: str = 'runtime'):
        
        mode = os.getenv('INIT_MODE', mode)
        logger.info(f"Initializing ConfigurationManager in {mode} mode")
        
        os.environ.setdefault('POSTGRES_USER', 'postgres')
        os.environ.setdefault('POSTGRES_PASSWORD', 'default_password')
        os.environ.setdefault('POSTGRES_DATABASE_NAME', 'sting_app')
        os.environ.setdefault('POSTGRES_HOST', 'db')
        os.environ.setdefault('POSTGRES_PORT', '5432')
        
        self.config_file = config_file
        # Base installation directory (can be overridden via INSTALL_DIR env var)
        self.install_dir = os.environ.get('INSTALL_DIR', '/app')
        # Directory containing configuration files
        self.config_dir = os.path.join(self.install_dir, 'conf')
        # Directory for generated environment files
        self.env_dir = os.path.join(self.install_dir, 'env')
        # Ensure environment directory exists
        os.makedirs(self.env_dir, exist_ok=True)
        self._database_config = None
        self._supertokens_config = None
        self.raw_config = {}
        self.processed_config = {}
        self.mode = mode  # Can be 'runtime', 'build', 'reinstall', 'initialize'
        self.cache_key = f"{config_file}:{mode}"
        self.state_file = os.path.join(self.config_dir, '.config_state')
        self._state_version = '2.0'  # Increment when config_loader changes require state refresh
        
        # Initialize Vault client based on mode
        self.vault_url = os.getenv("VAULT_ADDR", "http://vault:8200")
        self.vault_token = os.environ.get('VAULT_TOKEN', 'dev-only-token')
        self.vault_token = os.environ.get('VAULT_TOKEN') or self.vault_token

        # Always try to read vault token from file (even in bootstrap mode)
        self._read_vault_token_from_file()

        self.client = self._init_vault_client() if self._should_init_vault() else None
        
        # Get STING domain
        self.sting_domain = self._get_sting_domain()

        # Detect platform for Docker networking configuration
        self.platform = self._detect_platform()
        self.docker_host_gateway = self._get_docker_host_gateway()
        logger.info(f"Platform detected: {self.platform}, Docker host gateway: {self.docker_host_gateway}")

    @staticmethod
    def _resolve_config_value(value, fallback=None):
        """Resolve shell-style ${VAR:-default} template strings in config values.

        config.yml.default uses ${VAR:-default} patterns that YAML reads as literal
        strings. This method resolves them using os.environ with fallback to the
        embedded default value.
        """
        if not isinstance(value, str):
            return value
        m = re.match(r'^\$\{([^}:]+)(?::-(.*))?\}$', value)
        if m:
            var_name = m.group(1)
            default = m.group(2) if m.group(2) is not None else (fallback or '')
            return os.environ.get(var_name, default)
        return value

    def _read_vault_token_from_file(self):
        """Read vault token from file without connecting to Vault"""
        auto_init_file = os.path.join(self.config_dir, '.vault-auto-init.json')
        token_file = os.path.join(self.config_dir, '.vault_token')
        # Also check the vault keys directory (created during init)
        vault_keys_dir = os.path.join(os.path.dirname(self.config_dir), 'vault', 'keys')
        vault_init_json = os.path.join(vault_keys_dir, 'init.json')

        # Try auto-init file first (created by vault entrypoint)
        if os.path.exists(auto_init_file):
            try:
                with open(auto_init_file, 'r') as f:
                    vault_data = json.load(f)
                    auto_token = vault_data.get('root_token')
                    if auto_token:
                        logger.info(f"Found vault token in {auto_init_file}")
                        self.vault_token = auto_token
                        return
            except Exception as e:
                logger.warning(f"Could not read auto-init token: {e}")

        # Try vault keys directory (production installs)
        if os.path.exists(vault_init_json):
            try:
                with open(vault_init_json, 'r') as f:
                    vault_data = json.load(f)
                    auto_token = vault_data.get('root_token')
                    if auto_token:
                        logger.info(f"Found vault token in {vault_init_json}")
                        self.vault_token = auto_token
                        return
            except Exception as e:
                logger.warning(f"Could not read vault init.json: {e}")

        # Fall back to .vault_token file
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    self.vault_token = f.read().strip()
                    logger.info(f"Found vault token in {token_file}")
                    return
            except Exception as e:
                logger.warning(f"Could not read token file: {e}")

        # Check if token looks like a real hvs token vs placeholder
        if self.vault_token and self.vault_token.startswith('hvs.'):
            logger.debug(f"Using existing vault token from environment")
            return

        logger.warning(f"No vault token file found, using default: {self.vault_token} - this may cause auth failures")

    def _should_init_vault(self) -> bool:
        mode_actions = {
            'runtime': True,      # Full initialization
            'build': False,       # Skip vault during builds
            'reinstall': False,   # Skip during reinstall
            'initialize': True,    # Full initialization for first setup
            'bootstrap': False    # Skip during bootstrap
        }
        return mode_actions.get(self.mode, True)

    def _detect_platform(self) -> str:
        """
        Detect the platform STING is running on.
        Returns: 'macos', 'linux', 'wsl2', or 'unknown'
        """
        import platform

        system = platform.system()

        if system == 'Darwin':
            return 'macos'
        elif system == 'Linux':
            # Check if running in WSL2
            try:
                with open('/proc/version', 'r') as f:
                    version_str = f.read().lower()
                    if 'microsoft' in version_str:
                        # Check for WSL2 specifically
                        with open('/proc/sys/kernel/osrelease', 'r') as release:
                            if 'microsoft' in release.read().lower():
                                return 'wsl2'
            except FileNotFoundError:
                pass
            return 'linux'
        else:
            logger.warning(f"Unknown platform: {system}")
            return 'unknown'

    def _get_docker_host_gateway(self) -> str:
        """
        Get the appropriate Docker host gateway address based on platform.

        Returns:
        - macOS: 'host.docker.internal' (Docker Desktop native support)
        - WSL2 with Docker Desktop: 'host.docker.internal'
        - WSL2 native/Linux: 'host-gateway' (will be resolved via extra_hosts)
        """
        if self.platform == 'macos':
            return 'host.docker.internal'
        elif self.platform == 'wsl2':
            # Check if Docker Desktop is installed (docker.exe available)
            import shutil
            if shutil.which('docker.exe'):
                return 'host.docker.internal'
            else:
                # Native Docker in WSL2 - use host-gateway
                return 'host-gateway'
        elif self.platform == 'linux':
            # Native Linux Docker - use host-gateway
            # This will be resolved via extra_hosts in docker-compose.yml
            return 'host-gateway'
        else:
            # Default to host.docker.internal for unknown platforms
            logger.warning(f"Unknown platform {self.platform}, defaulting to host.docker.internal")
            return 'host.docker.internal'

    def _init_vault_client(self) -> Optional[Any]:
        token_file = os.path.join(self.config_dir, '.vault_token')
        init_file = os.path.join(self.config_dir, '.vault_init.json')
        # Check for auto-init script token first (shared via config volume)
        auto_init_file = os.path.join(self.config_dir, '.vault-auto-init.json')
        max_retries = 3
        retry_delay = 10

        # Quick health check first - no delay if vault is already responsive
        try:
            client = hvac.Client(url=self.vault_url)
            if client.sys.is_initialized():
                # Check if Vault is sealed (production mode)
                if client.sys.is_sealed():
                    logger.info("Vault is sealed, attempting to unseal...")
                    if os.path.exists(init_file):
                        with open(init_file, 'r') as f:
                            vault_data = json.load(f)
                            unseal_key = vault_data.get('unseal_key')
                            if unseal_key:
                                client.sys.submit_unseal_key(unseal_key)
                                logger.info("Vault unsealed successfully")

                # Check for auto-init script token first (shared via config volume)
                if os.path.exists(auto_init_file):
                    try:
                        with open(auto_init_file, 'r') as f:
                            vault_data = json.load(f)
                            auto_token = vault_data.get('root_token')
                            if auto_token:
                                logger.info("Found auto-init script token, using it")
                                self.vault_token = auto_token
                                client = hvac.Client(url=self.vault_url, token=self.vault_token)
                                if client.is_authenticated():
                                    logger.info("Vault connection established with auto-init token")
                                    return client
                    except Exception as e:
                        logger.warning(f"Could not read auto-init token: {e}")

                # Fallback to saved token file
                if os.path.exists(token_file):
                    with open(token_file, 'r') as f:
                        self.vault_token = f.read().strip()
                    client = hvac.Client(url=self.vault_url, token=self.vault_token)
                    if client.is_authenticated():
                        logger.info("Vault connection established with saved token")
                        return client
        except Exception:
            # Vault not ready, proceed with retry logic
            logger.info("Vault not immediately available, starting retry sequence")
            pass

        # Only delay if quick check failed
        initial_delay = 5
        time.sleep(initial_delay)

        for attempt in range(max_retries):
            try:
                client = hvac.Client(url=self.vault_url)
                if client.sys.is_initialized():
                    # Check if Vault is sealed (production mode)
                    if client.sys.is_sealed():
                        logger.info("Vault is sealed, attempting to unseal...")
                        if os.path.exists(init_file):
                            with open(init_file, 'r') as f:
                                vault_data = json.load(f)
                                unseal_key = vault_data.get('unseal_key')
                                if unseal_key:
                                    client.sys.submit_unseal_key(unseal_key)
                                    logger.info("Vault unsealed successfully")

                    if os.path.exists(token_file):
                        with open(token_file, 'r') as f:
                            self.vault_token = f.read().strip()
                        client = hvac.Client(url=self.vault_url, token=self.vault_token)
                        if client.is_authenticated():
                            return client
                else:
                    # Initialize Vault (works for both dev and prod modes)
                    result = client.sys.initialize(secret_shares=1, secret_threshold=1)
                    self.vault_token = result['root_token']
                    unseal_key = result['keys'][0] if 'keys' in result else result.get('keys_base64', [None])[0]

                    # Save both token and unseal key
                    vault_data = {
                        'root_token': self.vault_token,
                        'unseal_key': unseal_key,
                        'initialized_at': datetime.datetime.now().isoformat()
                    }

                    with open(token_file, 'w') as f:
                        f.write(self.vault_token)
                    os.chmod(token_file, 0o600)  # Restrict to owner read/write only

                    # Save complete init data
                    init_file = os.path.join(self.config_dir, '.vault_init.json')
                    with open(init_file, 'w') as f:
                        json.dump(vault_data, f)
                    os.chmod(init_file, 0o600)  # Restrict to owner read/write only

                    # Unseal if needed (production mode)
                    if client.sys.is_sealed() and unseal_key:
                        client.sys.submit_unseal_key(unseal_key)

                    # Enable KV v2 secrets engine at 'sting' path
                    vault_client = hvac.Client(url=self.vault_url, token=self.vault_token)
                    try:
                        vault_client.sys.enable_secrets_engine(
                            backend_type='kv',
                            path='sting',
                            options={'version': 2}
                        )
                        logger.info("Enabled KV v2 secrets engine at path 'sting'")
                    except Exception as e:
                        if "already in use" not in str(e):
                            logger.warning(f"Failed to enable KV engine: {e}")

                    return vault_client

                # Development fallback
                if os.getenv('APP_ENV') == 'development':
                    client = hvac.Client(url=self.vault_url, token=self.vault_token)
                    if client.is_authenticated():
                        with open(token_file, 'w') as f:
                            f.write(self.vault_token)
                        os.chmod(token_file, 0o600)  # Restrict to owner read/write only
                        return client

                time.sleep(retry_delay)
            except Exception as e:
                logger.warning(f"Vault initialization attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        return None
    
    def _get_sting_domain(self) -> str:
        """Get STING domain from config, file or environment.
        
        Priority order:
        1. .sting_domain file (set during installation - most reliable)
        2. STING_DOMAIN environment variable
        3. config.yml system.domain (if not a variable placeholder)
        4. Default to localhost
        
        This order ensures the actual installed domain takes precedence
        over template placeholders in config.yml.
        """
        # Check for domain file FIRST - this is set during installation
        # and represents the actual configured domain
        domain_file = os.path.join(self.install_dir, '.sting_domain')
        if os.path.exists(domain_file):
            try:
                with open(domain_file, 'r') as f:
                    domain = f.read().strip()
                    if domain and not domain.startswith('${'):
                        logger.debug(f"Using domain from .sting_domain file: {domain}")
                        return domain
            except Exception as e:
                logger.debug(f"Could not read .sting_domain file: {e}")
        
        # Check environment variable
        if 'STING_DOMAIN' in os.environ:
            domain = os.environ['STING_DOMAIN']
            if domain and not domain.startswith('${'):
                logger.debug(f"Using domain from STING_DOMAIN env: {domain}")
                return domain
        
        # Check config.yml - but skip variable placeholders like ${STING_HOSTNAME:-...}
        if self.raw_config:
            system_config = self.raw_config.get('system', {})
            domain = system_config.get('domain')
            # Only use if it's an actual domain, not a variable placeholder
            if domain and not domain.startswith('${'):
                logger.debug(f"Using domain from config.yml: {domain}")
                return domain
        
        # Default to localhost
        logger.debug("No domain configured, defaulting to localhost")
        return 'localhost'

    def _generate_secret(self, length: int = 32, supertokens_safe: bool = False) -> str:
        """Generate a secure secret using proper base64 encoding.
        
        Args:
            length: The length of the secret to generate (in bytes)
            supertokens_safe: Legacy parameter, ignored
        """
        # Generate proper base64-encoded secrets for all uses
        key_bytes = secrets.token_bytes(length)
        return base64.b64encode(key_bytes).decode('utf-8')
    
    def _generate_web_safe_password(self, length: int = 16) -> str:
        """Generate a web-safe password without problematic characters.

        Args:
            length: The length of the password to generate
        """
        # Use alphanumeric characters only (no +, /, =, etc.)
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _detect_server_ip(self) -> str:
        """Detect the primary server IP address for host machine.

        Uses 'ip route get 1' to determine the primary network interface IP.
        This is needed because Docker containers see internal Docker network IPs,
        not the actual host IP that clients use to access the server.

        Returns:
            The detected IP address as a string, or 'unknown' if detection fails
        """
        try:
            # Try primary method: ip route get 1
            result = subprocess.run(
                ['ip', 'route', 'get', '1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse output like: "1.0.0.0 via 192.168.1.1 dev eth0 src 192.168.1.100"
                # We want the IP after 'src'
                for i, word in enumerate(result.stdout.split()):
                    if word == 'src' and i + 1 < len(result.stdout.split()):
                        ip = result.stdout.split()[i + 1]
                        logger.info(f"Detected server IP: {ip}")
                        return ip

            # Fallback: Try hostname -I
            result = subprocess.run(
                ['hostname', '-I'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                all_ips = result.stdout.strip().split()
                # Prefer IPs that are NOT Docker internal (172.16-31.x.x.x range)
                for ip in all_ips:
                    if not (ip.startswith('172.1') or ip.startswith('172.2') or ip.startswith('172.3')):
                        logger.info(f"Detected server IP (via hostname -I): {ip}")
                        return ip
                # If all IPs are Docker internal, just use the first one
                if all_ips:
                    logger.warning(f"Only Docker internal IPs found, using: {all_ips[0]}")
                    return all_ips[0]
        except Exception as e:
            logger.warning(f"Failed to detect server IP: {e}")

        logger.warning("Could not detect server IP, returning 'unknown'")
        return 'unknown'

    # CRITICAL: Paths that contain encryption keys used to encrypt user data
    # These keys must NEVER be auto-regenerated as it would make existing data unreadable
    ENCRYPTION_KEY_PATHS = {'honey_reserve'}
    
    def _get_secret(self, path: str, key: str, supertokens_safe: bool = False) -> str:
        """Retrieve a secret from Vault with fallback to generation.
        
        For database passwords (path='database'), uses web-safe alphanumeric
        passwords to avoid URL-encoding issues in connection strings.
        
        CRITICAL: Encryption keys (honey_reserve) are NEVER auto-regenerated.
        Losing these keys means all encrypted files become unreadable.
        """
        is_encryption_key = path in self.ENCRYPTION_KEY_PATHS
        
        if self.client:
            try:
                logger.info(f"Attempting to read secret from path: sting/{path}")
                secret = self.client.secrets.kv.v2.read_secret_version(
                    mount_point='sting',
                    path=path
                ).get("data", {}).get("data", {}).get(key)
                
                logger.info(f"Secret read status for {path}: {'[EXISTS]' if secret else '[NOT_FOUND]'}")
                
                if secret and supertokens_safe:
                    if all(c in string.ascii_letters + string.digits + "=-" for c in secret):
                        return secret
                elif secret:
                    # Validate database passwords don't have problematic characters
                    if path == 'database' and key == 'password':
                        if not self._is_url_safe_password(secret):
                            logger.warning(f"Database password contains URL-unsafe characters, regenerating...")
                            # Fall through to regenerate
                        else:
                            return secret
                    else:
                        return secret
                    
            except Exception as e:
                logger.debug(f"Failed to retrieve secret from Vault: {e}")
                # For encryption keys, we must NOT generate a new one on read failure
                if is_encryption_key:
                    logger.error(f"CRITICAL: Failed to read encryption key from Vault path '{path}': {e}")
                    logger.error(f"Cannot generate new encryption key - this would make existing encrypted data unreadable!")
                    logger.error(f"Please restore the encryption key from backup or check Vault connectivity.")
                    raise RuntimeError(
                        f"Encryption key at '{path}' could not be read from Vault. "
                        f"Generating a new key would corrupt all encrypted data. "
                        f"Please restore from backup or check Vault connectivity."
                    )

        # CRITICAL: Never auto-regenerate encryption keys
        # Check if this is an encryption key path and if one already exists anywhere
        if is_encryption_key:
            # Check if there's an existing key in env files that should be migrated
            existing_key = self._check_existing_encryption_key(path, key)
            if existing_key:
                logger.warning(f"Found existing encryption key for '{path}' in env file - migrating to Vault")
                if self.client:
                    try:
                        self.client.secrets.kv.v2.create_or_update_secret(
                            mount_point='sting',
                            path=path,
                            secret={key: existing_key}
                        )
                        logger.info(f"Successfully migrated encryption key to Vault at sting/{path}")
                    except Exception as e:
                        logger.error(f"Failed to migrate encryption key to Vault: {e}")
                return existing_key
            
            # Only generate new encryption key during initial setup
            if self.mode not in ('initialize', 'bootstrap'):
                logger.error(f"CRITICAL: Encryption key at '{path}' not found in Vault!")
                logger.error(f"This key is required to decrypt user files. Options:")
                logger.error(f"  1. Restore the key from backup")
                logger.error(f"  2. Check if key exists in env/app.env and restart")
                logger.error(f"  3. If this is a fresh install, run with mode='initialize'")
                raise RuntimeError(
                    f"Encryption key at '{path}' not found. "
                    f"Cannot generate new key as this would make existing data unreadable. "
                    f"Please restore from backup or run initial setup."
                )
            
            logger.warning(f"Generating NEW encryption key for '{path}' (initialize mode)")
            logger.warning(f"IMPORTANT: Back up this key! Loss of this key means loss of all encrypted data!")

        # Generate new secret
        # For database passwords, use web-safe alphanumeric to avoid URL-encoding issues
        if path == 'database' and key == 'password':
            new_secret = self._generate_web_safe_password(length=32)
            logger.info(f"Generated web-safe database password (no special characters)")
        else:
            new_secret = self._generate_secret(length=32, supertokens_safe=False)
        
        if self.client:
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    mount_point='sting',
                    path=path,
                    secret={key: new_secret}
                )
                logger.info(f"Created new secret at sting/{path} with key: {key}")
                
                # Extra logging for encryption keys
                if is_encryption_key:
                    logger.warning(f"=" * 60)
                    logger.warning(f"NEW ENCRYPTION KEY GENERATED")
                    logger.warning(f"Path: sting/{path}")
                    logger.warning(f"BACK UP THIS KEY IMMEDIATELY!")
                    logger.warning(f"Loss of this key = loss of all encrypted user data")
                    logger.warning(f"=" * 60)
            except Exception as e:
                logger.debug(f"Failed to store secret in Vault: {e}")
        
        return new_secret
    
    def _check_existing_encryption_key(self, path: str, key: str) -> str:
        """Check if an encryption key exists in env files (for migration).
        
        This helps migrate keys from older installations that stored keys in .env files.
        """
        env_var_map = {
            'honey_reserve': 'HONEY_RESERVE_MASTER_KEY',
        }
        
        env_var = env_var_map.get(path)
        if not env_var:
            return None
        
        # Check environment variable first
        existing = os.environ.get(env_var)
        if existing:
            # Clean up quotes if present
            existing = existing.strip('"\'')
            if existing:
                logger.info(f"Found existing encryption key in environment: {env_var}")
                return existing
        
        # Check common env file locations
        env_files = [
            '/app/env/app.env',
            '/opt/sting-ce/env/app.env',
            'env/app.env',
        ]
        
        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.startswith(f'{env_var}='):
                                value = line.split('=', 1)[1].strip().strip('"\'')
                                if value:
                                    logger.info(f"Found existing encryption key in {env_file}")
                                    return value
                except Exception as e:
                    logger.debug(f"Error reading {env_file}: {e}")
        
        return None
    
    def _get_api_key_from_vault(self, provider: str) -> dict:
        """Get API key and configuration for any LLM provider from Vault.
        
        Provides a generic way to store and retrieve API keys for any provider.
        Stored at: sting/<provider> with keys: api_key, base_url, default_model, etc.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic', 'google', 'groq', 'azure')
            
        Returns:
            Dict with provider configuration or empty dict if not found
        """
        if not self.client:
            return {}
            
        try:
            vault_data = self.client.secrets.kv.v2.read_secret_version(
                mount_point='sting',
                path=provider
            ).get("data", {}).get("data", {})
            
            if vault_data and vault_data.get('api_key'):
                logger.info(f"Loaded {provider} credentials from Vault")
                return vault_data
        except Exception as e:
            logger.debug(f"No {provider} credentials in Vault: {e}")
        
        return {}
    
    def _is_url_safe_password(self, password: str) -> bool:
        """Check if a password is safe for use in URLs without encoding.
        
        Characters that cause issues in database connection URLs:
        +, /, =, @, :, ?, #, %, &
        """
        unsafe_chars = set('+/=@:?#%&')
        return not any(c in unsafe_chars for c in password)
    
    def _get_kratos_secret(self, path: str, key: str) -> str:
        """Retrieve a Kratos-compatible secret (32 hex chars) from Vault with fallback to generation."""
        if self.client:
            try:
                logger.info(f"Attempting to read Kratos secret from path: sting/{path}")
                secret = self.client.secrets.kv.v2.read_secret_version(
                    mount_point='sting',
                    path=path
                ).get("data", {}).get("data", {}).get(key)
                
                logger.info(f"Kratos secret read status for {path}: {'[EXISTS]' if secret else '[NOT_FOUND]'}")
                
                if secret and len(secret) == 32:
                    return secret
                elif secret:
                    logger.warning(f"Kratos secret {key} has wrong length ({len(secret)}), regenerating")
                    
            except Exception as e:
                logger.debug(f"Failed to read Kratos secret from Vault: {e}")
        
        # Generate 32-character hex secret for Kratos
        new_secret = secrets.token_hex(16)  # 16 bytes = 32 hex chars
        
        if self.client:
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    mount_point='sting',
                    path=path,
                    secret={key: new_secret}
                )
                logger.info(f"Created new Kratos secret at sting/{path} with key: {key}")
            except Exception as e:
                logger.debug(f"Failed to store Kratos secret in Vault: {e}")
        
        return new_secret
    
    def _refresh_vault_credentials(self) -> None:
        """Refresh LLM provider credentials from Vault.
        
        This is called even when using cached state to ensure API keys
        that were added/modified in Vault are picked up without requiring
        a config.yml change.
        
        Vault is the source of truth for API keys - they should NEVER be
        stored in config.yml or the state file.
        """
        logger.info("Refreshing LLM provider credentials from Vault...")
        
        # Get credentials from Vault for all providers
        vault_minimax = self._get_api_key_from_vault('minimax')
        vault_openai = self._get_api_key_from_vault('openai')
        vault_anthropic = self._get_api_key_from_vault('anthropic')
        vault_google = self._get_api_key_from_vault('google')
        vault_groq = self._get_api_key_from_vault('groq')
        vault_azure = self._get_api_key_from_vault('azure_openai')
        
        # Update processed_config with fresh Vault credentials
        # MiniMax
        if vault_minimax.get('api_key'):
            self.processed_config['MINIMAX_API_KEY'] = vault_minimax.get('api_key', '')
            self.processed_config['MINIMAX_BASE_URL'] = vault_minimax.get('base_url', 'https://api.minimax.io/v1')
            self.processed_config['MINIMAX_DEFAULT_MODEL'] = vault_minimax.get('default_model', 'MiniMax-Text-01')
            self.processed_config['MINIMAX_ENABLED'] = 'true'
            # Set as primary if provider specified in Vault
            if vault_minimax.get('provider'):
                self.processed_config['LLM_PRIMARY_PROVIDER'] = vault_minimax.get('provider')
            logger.info("✓ MiniMax credentials refreshed from Vault")
        
        # OpenAI
        if vault_openai.get('api_key'):
            self.processed_config['OPENAI_API_KEY'] = vault_openai.get('api_key', '')
            self.processed_config['OPENAI_BASE_URL'] = vault_openai.get('base_url', 'https://api.openai.com/v1')
            self.processed_config['OPENAI_DEFAULT_MODEL'] = vault_openai.get('default_model', 'gpt-4o')
            logger.info("✓ OpenAI credentials refreshed from Vault")
        
        # Anthropic
        if vault_anthropic.get('api_key'):
            self.processed_config['ANTHROPIC_API_KEY'] = vault_anthropic.get('api_key', '')
            self.processed_config['ANTHROPIC_DEFAULT_MODEL'] = vault_anthropic.get('default_model', 'claude-3-opus')
            logger.info("✓ Anthropic credentials refreshed from Vault")
        
        # Google
        if vault_google.get('api_key'):
            self.processed_config['GOOGLE_API_KEY'] = vault_google.get('api_key', '')
            self.processed_config['GOOGLE_DEFAULT_MODEL'] = vault_google.get('default_model', 'gemini-pro')
            logger.info("✓ Google credentials refreshed from Vault")
        
        # Groq
        if vault_groq.get('api_key'):
            self.processed_config['GROQ_API_KEY'] = vault_groq.get('api_key', '')
            self.processed_config['GROQ_DEFAULT_MODEL'] = vault_groq.get('default_model', 'llama-3.1-70b-versatile')
            logger.info("✓ Groq credentials refreshed from Vault")
        
        # Azure OpenAI
        if vault_azure.get('api_key'):
            self.processed_config['AZURE_OPENAI_API_KEY'] = vault_azure.get('api_key', '')
            self.processed_config['AZURE_OPENAI_ENDPOINT'] = vault_azure.get('endpoint', '')
            self.processed_config['AZURE_OPENAI_DEPLOYMENT'] = vault_azure.get('deployment', '')
            logger.info("✓ Azure OpenAI credentials refreshed from Vault")

    def load_config(self) -> None:
        """Load raw configuration from YAML or JSON file."""
        try:
            # First check if config exists, create from template if needed
            if not check_config_exists(self.config_file):
                raise ConfigurationError("Failed to create configuration file from template")
            
            # Delegate to top-level loader with YAML/JSON support
            self.raw_config = load_config(self.config_file)
        except ConfigurationError as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def validate_critical_variables(self):
        """Validate that all critical configuration variables are present."""
        critical_vars = [
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
            'POSTGRES_DB',
            'ST_API_KEY',
            'SUPERTOKENS_URL'
        ]

        missing_vars = [var for var in critical_vars if not self.processed_config.get(var)]
        if missing_vars:
            logger.error(f"Missing critical configuration variables: {', '.join(missing_vars)}")
            raise ValueError(f"Critical configuration missing: {', '.join(missing_vars)}")
        logger.info("All critical variables are present.")

    def _process_database_config(self) -> DatabaseConfig:
        """Process and return database configuration."""
        return DatabaseConfig(
            host=self.processed_config.get('POSTGRES_HOST', 'db'),
            port=int(self.processed_config.get('POSTGRES_PORT', 5432)),
            name=self.processed_config.get('POSTGRES_DB', 'sting_app'),
            user=self.processed_config.get('POSTGRES_USER', 'postgres'),
            password=self.processed_config.get('POSTGRES_PASSWORD', '')
        )

    # _process_supertokens_config removed - deprecated in favor of Kratos

    def _process_llm_service_config(self) -> LLMServiceConfig:
        """Process and return LLM service configuration."""
        return LLMServiceConfig.process_config(self.raw_config)
    
    def _process_profile_service_config(self) -> Dict[str, Any]:
        """Process and return profile service configuration."""
        profile_config = self.raw_config.get('profile_service', {})
        
        return {
            'enabled': profile_config.get('enabled', True),
            'port': profile_config.get('port', 8092),
            'max_file_size': profile_config.get('max_file_size', 52428800),  # 50MB
            'allowed_image_types': profile_config.get('allowed_image_types', [
                'image/jpeg', 'image/png', 'image/webp'
            ]),
            'image_processing': profile_config.get('image_processing', {
                'max_width': 1024,
                'max_height': 1024,
                'quality': 85
            }),
            'features': profile_config.get('features', {
                'profile_pictures': True,
                'profile_extensions': True,
                'activity_logging': True,
                'search': True
            }),
            'privacy': profile_config.get('privacy', {
                'default_visibility': 'private',
                'allow_public_profiles': True
            })
        }

    def invalidate_cache(self):
        """Invalidate the configuration cache."""
        if self.cache_key in self._config_cache:
            del self._config_cache[self.cache_key]
            logger.debug(f"Invalidated cache for {self.cache_key}")
            
    def process_config(self) -> Dict[str, Any]:
        # Load the configuration file if not already loaded
        if not self.raw_config:
            self.load_config()

        # Initialize instance attributes early to prevent AttributeError
        # These must be set before any early returns from cache/state checks
        # SuperTokens secrets removed - no longer used (Kratos handles auth)
        self.api_key = None  # SuperTokens removed, set to None to prevent AttributeError
        self.dashboard_api_key = None  # SuperTokens removed, set to None to prevent AttributeError

        # Initialize service keys early (before any early returns from cache/state)
        # These are accessed in generate_env_file() even when using cached config
        self.db_password = None
        self.honey_reserve_master_key = None
        self.service_api_key = None
        self.bee_service_api_key = None

        # Check cache first (after initializing attributes)
        if self.cache_key in self._config_cache:
            logger.debug(f"Using cached configuration for {self.cache_key}")
            self.processed_config = self._config_cache[self.cache_key]
            # Still need to populate secrets from Vault even when using in-memory cache
            # These are accessed directly by generate_env_file() and kratos.yml generation
            self.db_password = self._clean_value(self._get_secret('database', 'password', supertokens_safe=False))
            self.honey_reserve_master_key = self._clean_value(self._get_secret('honey_reserve', 'master_key', supertokens_safe=False))
            self.service_api_key = self._clean_value(self._get_secret('sting/service_auth', 'api_key', supertokens_safe=False))
            bee_api_secret = self._get_secret('service/bee-api-key', 'api_key')
            self.bee_service_api_key = self._clean_value(bee_api_secret) if bee_api_secret else None
            return self.processed_config

        # State management check
        if os.path.exists(self.state_file) and self.mode != 'initialize':
            logger.info("Found existing configuration state")
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
                if self._verify_state_validity(state_data):
                    self.processed_config = state_data
                    # Still need to populate secrets from Vault even when using cached state
                    # These are accessed directly by generate_env_file()
                    self.db_password = self._clean_value(self._get_secret('database', 'password', supertokens_safe=False))
                    self.honey_reserve_master_key = self._clean_value(self._get_secret('honey_reserve', 'master_key', supertokens_safe=False))
                    self.service_api_key = self._clean_value(self._get_secret('sting/service_auth', 'api_key', supertokens_safe=False))
                    bee_api_secret = self._get_secret('service/bee-api-key', 'api_key')
                    self.bee_service_api_key = self._clean_value(bee_api_secret) if bee_api_secret else None
                    
                    # CRITICAL: Always refresh LLM provider credentials from Vault
                    # These may have been added/changed without modifying config.yml
                    self._refresh_vault_credentials()
                    
                    return self.processed_config

        # Generate Flask secret key if not exists
        flask_secret = self._get_secret('flask', 'secret_key')
        logger.info(f"Generated/Retrieved Flask secret key status: {'[EXISTS]' if flask_secret else '[NOT_FOUND]'}")

        # Generate and set database password
        self.db_password = self._clean_value(self._get_secret('database', 'password', supertokens_safe=False))

        # Generate Honey Reserve encryption master key
        self.honey_reserve_master_key = self._clean_value(self._get_secret('honey_reserve', 'master_key', supertokens_safe=False))

        # Generate STING service API key for inter-service authentication
        self.service_api_key = self._clean_value(self._get_secret('sting/service_auth', 'api_key', supertokens_safe=False))

        # Get Bee service API key for agentic operations
        bee_api_secret = self._get_secret('service/bee-api-key', 'api_key')
        self.bee_service_api_key = self._clean_value(bee_api_secret) if bee_api_secret else None
        if not self.bee_service_api_key:
            logger.warning("Bee service API key not found in Vault - run bootstrap to generate")

        # Get system domain configuration
        system_config = self.raw_config.get('system', {})
        domain = self.sting_domain  # Use resolved domain (from .sting_domain file)
        protocol = system_config.get('protocol', 'https')
        ports = system_config.get('ports', {})
        
        # Determine frontend port: use standard HTTPS (443) for production domains
        # Use 8443 only for localhost, .local, or IP addresses
        # This logic must match update_hostname.sh for consistency
        import re
        is_ip_address = bool(re.match(r'^\d+\.\d+\.\d+\.\d+$', domain))
        is_production = (
            domain != 'localhost' and 
            '.local' not in domain and 
            not is_ip_address
        )
        if is_production:
            frontend_port = 443  # Standard HTTPS for production
        else:
            frontend_port = ports.get('frontend', 8443)  # Dev port for local
        
        api_port = ports.get('api', 5050)
        kratos_port = ports.get('kratos', 4433)
        
        # Build URLs based on domain configuration
        # For production (port 443), omit port from URL for cleaner URLs
        if frontend_port == 443:
            public_url = f"{protocol}://{domain}"
            kratos_public_url = f"{protocol}://{domain}/.ory"
        else:
            public_url = f"{protocol}://{domain}:{frontend_port}"
            kratos_public_url = f"{protocol}://{domain}:{frontend_port}/.ory"
        
        api_url = f"{protocol}://{domain}:{api_port}"
        kratos_browser_url = kratos_public_url  # Same as public for browser access
        
        # Store domain configuration in environment
        self.processed_config['STING_DOMAIN'] = domain
        self.processed_config['STING_PROTOCOL'] = protocol
        self.processed_config['PUBLIC_URL'] = public_url
        self.processed_config['KRATOS_PUBLIC_URL'] = kratos_public_url
        self.processed_config['KRATOS_BROWSER_URL'] = kratos_browser_url
        
        # Store timezone configuration (defaults to America/New_York for Eastern Time)
        timezone = system_config.get('timezone', 'America/New_York')
        self.processed_config['TZ'] = timezone
        
        api_domain = self.raw_config.get('application', {}).get('api_url', api_url)
        ssl_config = self.raw_config.get('application', {}).get('ssl', {})

        if not self.raw_config:
            self.load_config()
        
        # Get application config first
        app_config = self.raw_config.get('application', {})

        # Determine LLM models directory (users can override in config.yml)
        models_dir = app_config.get('models_dir')
        if not models_dir:
            models_dir = '${INSTALL_DIR}/models'
        self.processed_config['STING_MODELS_DIR'] = models_dir

        # Build database URL with URL-encoded password (handles special characters like +, /, =)
        db_user = self._clean_value('postgres')
        db_pass_raw = self._clean_value(self.db_password)
        db_pass_encoded = url_quote(db_pass_raw, safe='')
        # SECURITY: Never log passwords or database URLs with credentials
        database_url = f"postgresql://{db_user}:{db_pass_encoded}@db:5432/sting_app?sslmode=disable"

        # Set all database-related variables
        db_vars = {
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': self._clean_value(self.db_password),
            'POSTGRES_DB': 'sting_app',
            'POSTGRES_HOST': 'db',
            'POSTGRES_PORT': '5432',
            'POSTGRES_HOST_AUTH_METHOD': 'md5',
            'DATABASE_URL': database_url,  # Already URL-encoded, don't clean it
            'LANG': 'en_US.utf8',
            'LC_ALL': 'en_US.utf8'
        }

        # Clean Supertokens database variables
        st_db_vars = {
            'API_KEY': self._clean_value(self.api_key),
            'ST_API_KEY': self._clean_value(self.api_key),
            'ST_DASHBOARD_API_KEY': self._clean_value(self.dashboard_api_key),
            'POSTGRESQL_USER': self._clean_value(db_vars['POSTGRES_USER']),
            'POSTGRESQL_PASSWORD': self._clean_value(self.db_password),
            'POSTGRESQL_DATABASE_NAME': 'sting_app',
            'POSTGRESQL_HOST': 'db',
            'POSTGRESQL_PORT': '5432',
            'DATABASE_URL': database_url,  # Already URL-encoded, don't clean it
            'POSTGRESQL_CONNECTION_URI': database_url,  # Already URL-encoded, don't clean it
            # SuperTokens removed - using Kratos for authentication
            # 'SUPERTOKENS_API_DOMAIN': 'http://localhost:5050',
            # 'SUPERTOKENS_URL': 'http://supertokens:3567',
            # 'SUPERTOKENS_CORS_ORIGINS': 'http://localhost:8443'
        }
        
        self.processed_config.update({
            'SSL_ENABLED': ssl_config.get('enabled', True),
            'SSL_CERT_DIR': ssl_config.get('cert_dir', f"{self.install_dir}/certs"),
            'DOMAIN_NAME': ssl_config.get('domain', self.sting_domain),  # Use STING domain instead of defaulting to localhost
            'CERTBOT_EMAIL': ssl_config.get('email', 'your-email@example.com')
        })

        # Update processed config
        self.processed_config.update(db_vars)
        self.processed_config.update(st_db_vars)

        # Get HF token from environment, config.yml, or vault (env wins)
        # NOTE: HuggingFace integration is deprecated - these operations are non-fatal
        hf_token = os.environ.get('HF_TOKEN', '')
        if not hf_token:
            hf_token = self.raw_config.get('llm_service', {}).get('huggingface', {}).get('token', '') or ''
        if not hf_token and self.client:
            try:
                hf_token = self._get_secret('huggingface', 'token', False) or ''
            except Exception as e:
                logger.warning(f"Could not read deprecated HuggingFace token from Vault: {e}")
                hf_token = ''

        # Store token in processed config
        self.processed_config['HF_TOKEN'] = hf_token

        # Only store non-empty, non-placeholder tokens in Vault (deprecated, non-fatal)
        if hf_token and self.client and hf_token != "<REDACTED>" and hf_token.strip():
            try:
                self.client.secrets.kv.v2.create_or_update_secret(
                    path="sting/huggingface",
                    secret={"token": hf_token}
                )
            except Exception as e:
                logger.warning(f"Could not store deprecated HuggingFace token in Vault: {e}")

        # Get SERVER_IP from environment (set by host during install) or detect
        # Docker containers only see internal IPs, so this must come from host environment
        server_ip = os.environ.get('SERVER_IP', '')
        if not server_ip:
            # Fallback: try to detect, but this will likely return Docker IP
            server_ip = self._detect_server_ip()
            logger.warning(f"SERVER_IP not set in environment, detected: {server_ip}")
        else:
            logger.info(f"Using SERVER_IP from environment: {server_ip}")

        # Store SERVER_IP in processed config
        self.processed_config['SERVER_IP'] = server_ip

        # Set environment variables
        for key, value in db_vars.items():
            os.environ[key] = self._clean_value(str(value))

        # Process configurations
        db_config = self._process_database_config()
        # st_config removed - Supertokens deprecated in favor of Kratos
        llm_config = self._process_llm_service_config()
        profile_config = self._process_profile_service_config()

        # Add remaining configuration
        self.processed_config.update({
            'APP_ENV': app_config.get('env', 'development'),
            'APP_DEBUG': app_config.get('debug', True),
            'APP_HOST': app_config.get('host', 'localhost'),
            'APP_PORT': app_config.get('port', 5050),
            'APP_URL': api_domain,
            'INSTALL_DIR': self.install_dir,
            'FLASK_APP': 'app.run:app',
            'FLASK_DEBUG': app_config.get('env', 'development'),
            'FLASK_SECRET_KEY': flask_secret,
            'SECRET_KEY': flask_secret,
            'GUNICORN_WORKERS': str(app_config.get('gunicorn_workers', 4)),
            'GUNICORN_TIMEOUT': str(app_config.get('gunicorn_timeout', 120)),
            'DATABASE_URL': database_url,  # Already URL-encoded, don't clean it
            'SQLALCHEMY_DATABASE_URI': database_url,  # Already URL-encoded, don't clean it
            # SuperTokens API keys removed - no longer used
            # 'ST_API_KEY': self._clean_value(self.api_key),
            # 'API_KEY': self._clean_value(self.api_key),
            # 'ST_DASHBOARD_API_KEY': self._clean_value(self.dashboard_api_key),
            # SuperTokens removed - using Kratos for authentication
            # 'SUPERTOKENS_URL': 'http://supertokens:3567',
            # 'SUPERTOKENS_CORS_ORIGINS': 'http://localhost:8443',
            # 'SUPERTOKENS_API_DOMAIN': api_domain,
            'ST_ACCESS_TOKEN_VALIDITY': '3600',
            'ST_REFRESH_TOKEN_VALIDITY': '2592000',
            # REACT_PORT: Check both paths for compatibility with wizard and manual config
            # Primary: frontend.react.port (config_loader standard)
            # Fallback: system.ports.frontend (wizard metadata)
            'REACT_PORT': self.raw_config.get('frontend', {}).get('react', {}).get('port',
                          self.raw_config.get('system', {}).get('ports', {}).get('frontend', 8443)),
            'HF_TOKEN': hf_token,
            'REACT_APP_API_URL': api_domain,
            # 'REACT_APP_SUPERTOKENS_URL': 'http://localhost:3567',  # Removed - using Kratos
            'REACT_APP_KRATOS_PUBLIC_URL': self.processed_config.get('KRATOS_PUBLIC_URL', kratos_public_url),
            'REACT_APP_KRATOS_BROWSER_URL': self.processed_config.get('KRATOS_BROWSER_URL', kratos_browser_url),
            'NODE_ENV': app_config.get('env', 'development'),
            'VAULT_ADDR': 'http://vault:8200',
            'VAULT_TOKEN': self._clean_value(self.vault_token),
            'HEALTH_CHECK_INTERVAL': self.raw_config.get('monitoring', {}).get('health_checks', {}).get('interval', '30s'),
            'HEALTH_CHECK_TIMEOUT': self.raw_config.get('monitoring', {}).get('health_checks', {}).get('timeout', '10s'),
            'HEALTH_CHECK_RETRIES': str(self.raw_config.get('monitoring', {}).get('health_checks', {}).get('retries', 3)),
            'HEALTH_CHECK_START_PERIOD': self.raw_config.get('monitoring', {}).get('health_checks', {}).get('start_period', '40s'),
            # SuperTokens WebAuthn removed - Kratos handles this natively
            # 'SUPERTOKENS_WEBAUTHN_ENABLED': 'true',
            # 'SUPERTOKENS_WEBAUTHN_RP_ID': '${HOSTNAME:-localhost}',
            # 'SUPERTOKENS_WEBAUTHN_RP_NAME': 'STING',
            # 'SUPERTOKENS_WEBAUTHN_RP_ORIGINS': '["http://localhost:8443", "https://${HOSTNAME:-' +
            #     self.processed_config.get('APP_HOST','your-production-domain.com') +
            #     '}"]'
        })

        # Add LLM service specific ENV vars
        raw_llm_config = self.raw_config.get('llm_service', {})
        gateway_config = raw_llm_config.get('gateway', {})
        models_config = raw_llm_config.get('models', {})

        # Add LLM-specific configuration 
        self.processed_config.update({
            'LLM_SERVICE_ENABLED': str(llm_config.enabled).lower(),
            'LLM_DEFAULT_MODEL': llm_config.default_model,
            'LLM_FILTERING_ENABLED': str(llm_config.filtering.get('toxicity', {}).get('enabled', True)).lower() if hasattr(llm_config, 'filtering') else 'true',
            'LLM_TOXICITY_THRESHOLD': str(llm_config.filtering.get('toxicity', {}).get('threshold', 0.7)) if hasattr(llm_config, 'filtering') else '0.7',
            'LLM_DATA_LEAKAGE_ENABLED': str(llm_config.filtering.get('data_leakage', {}).get('enabled', True)).lower() if hasattr(llm_config, 'filtering') else 'true',
            # Ollama configuration
            'OLLAMA_ENABLED': str(llm_config.ollama.get('enabled', True)).lower(),
            'OLLAMA_ENDPOINT': llm_config.ollama.get('endpoint', 'http://localhost:11434'),
            'OLLAMA_DEFAULT_MODEL': llm_config.ollama.get('default_model', 'phi3:mini'),
            'OLLAMA_MODELS_TO_INSTALL': ','.join(llm_config.ollama.get('models_to_install', ['phi3:mini'])),
            'OLLAMA_AUTO_INSTALL': str(llm_config.ollama.get('auto_install', True)).lower(),
            # External AI service configuration
            'EXTERNAL_AI_ENABLED': str(llm_config.external_ai.get('enabled', True)).lower(),
            'EXTERNAL_AI_PORT': str(llm_config.external_ai.get('port', 8091)),
            'EXTERNAL_AI_OLLAMA_ENDPOINT': llm_config.external_ai.get('ollama_endpoint', 'http://localhost:11434'),
        })
        
        # Load API keys from Vault for all supported LLM providers
        # This allows credentials to persist across updates
        vault_minimax = self._get_api_key_from_vault('minimax')
        vault_openai = self._get_api_key_from_vault('openai')
        vault_anthropic = self._get_api_key_from_vault('anthropic')
        vault_google = self._get_api_key_from_vault('google')
        vault_groq = self._get_api_key_from_vault('groq')
        vault_azure = self._get_api_key_from_vault('azure_openai')
        
        # MiniMax configuration (check Vault first, then config.yml)
        minimax_config = llm_config.external_ai.get('minimax', {})
        minimax_api_key = vault_minimax.get('api_key', '') or minimax_config.get('api_key', '')
        
        # Determine primary provider from Vault or config
        minimax_provider = vault_minimax.get('provider', '') or llm_config.external_ai.get('primary_provider', 'ollama')
        
        self.processed_config.update({
            'MINIMAX_ENABLED': str(minimax_config.get('enabled', False) or bool(minimax_api_key)).lower(),
            'MINIMAX_API_KEY': minimax_api_key,
            'MINIMAX_BASE_URL': vault_minimax.get('base_url', '') or minimax_config.get('base_url', 'https://api.minimax.io/v1'),
            'MINIMAX_DEFAULT_MODEL': vault_minimax.get('default_model', '') or minimax_config.get('default_model', 'MiniMax-Text-01'),
            'LLM_PRIMARY_PROVIDER': minimax_provider,
        })
        
        # OpenAI configuration (from Vault)
        self.processed_config.update({
            'OPENAI_API_KEY': vault_openai.get('api_key', ''),
            'OPENAI_BASE_URL': vault_openai.get('base_url', 'https://api.openai.com/v1'),
            'OPENAI_DEFAULT_MODEL': vault_openai.get('default_model', 'gpt-4o'),
        })
        
        # Anthropic configuration (from Vault)
        self.processed_config.update({
            'ANTHROPIC_API_KEY': vault_anthropic.get('api_key', ''),
            'ANTHROPIC_DEFAULT_MODEL': vault_anthropic.get('default_model', 'claude-sonnet-4-20250514'),
        })
        
        # Google AI configuration (from Vault)
        self.processed_config.update({
            'GOOGLE_API_KEY': vault_google.get('api_key', ''),
            'GOOGLE_DEFAULT_MODEL': vault_google.get('default_model', 'gemini-pro'),
        })
        
        # Groq configuration (from Vault)
        self.processed_config.update({
            'GROQ_API_KEY': vault_groq.get('api_key', ''),
            'GROQ_DEFAULT_MODEL': vault_groq.get('default_model', 'llama-3.3-70b-versatile'),
        })
        
        # Azure OpenAI configuration (from Vault)
        self.processed_config.update({
            'AZURE_OPENAI_API_KEY': vault_azure.get('api_key', ''),
            'AZURE_OPENAI_ENDPOINT': vault_azure.get('endpoint', ''),
            'AZURE_OPENAI_DEPLOYMENT': vault_azure.get('deployment', ''),
        })
        
        # Add model lifecycle configuration
        lifecycle_config = llm_config.model_lifecycle if hasattr(llm_config, 'model_lifecycle') else {}
        self.processed_config.update({
            'LLM_LAZY_LOADING': str(lifecycle_config.get('lazy_loading', True)).lower(),
            'LLM_IDLE_TIMEOUT': str(lifecycle_config.get('idle_timeout', 30)),
            'LLM_MAX_LOADED_MODELS': str(lifecycle_config.get('max_loaded_models', 2)),
            'LLM_PRELOAD_ON_STARTUP': str(lifecycle_config.get('preload_on_startup', False)).lower(),
            'LLM_DEVELOPMENT_MODE': str(lifecycle_config.get('development_mode', False)).lower(),
        })

        # Generate gateway ENV vars
        self.processed_config.update({
            'LLM_GATEWAY_PORT': str(gateway_config.get('port', 8080)),
            'LLM_GATEWAY_LOG_LEVEL': gateway_config.get('log_level', 'INFO'),
            'LLM_DEFAULT_MODEL': llm_config.default_model,
            'LLM_SERVICE_TIMEOUT': str(gateway_config.get('timeout', 30)),
            'LLM_MAX_RETRIES': str(gateway_config.get('max_retries', 3)),
            'LLM_MODELS_ENABLED': ','.join([
                model for model, config in models_config.items() 
                if config.get('enabled', True)
            ]),
        })

        # Generate model-specific ENV vars
        for model, config in models_config.items():
            if config.get('enabled', True):
                model_env = {
                    f'{model.upper()}_MODEL_PATH': config.get('path', f'/app/models/{model}'),
                    f'{model.upper()}_MAX_TOKENS': str(config.get('max_tokens', 1024)),
                    f'{model.upper()}_TEMPERATURE': str(config.get('temperature', 0.7)),
                }
                self.processed_config.update(model_env)

        # Add Profile service specific ENV vars
        self.processed_config.update({
            'PROFILE_SERVICE_ENABLED': str(profile_config.get('enabled', True)).lower(),
            'PROFILE_SERVICE_PORT': str(profile_config.get('port', 8092)),
            'PROFILE_MAX_FILE_SIZE': str(profile_config.get('max_file_size', 52428800)),
            'PROFILE_ALLOWED_IMAGE_TYPES': ','.join(profile_config.get('allowed_image_types', [])),
            'PROFILE_IMAGE_MAX_WIDTH': str(profile_config.get('image_processing', {}).get('max_width', 1024)),
            'PROFILE_IMAGE_MAX_HEIGHT': str(profile_config.get('image_processing', {}).get('max_height', 1024)),
            'PROFILE_IMAGE_QUALITY': str(profile_config.get('image_processing', {}).get('quality', 85)),
            'PROFILE_FEATURES_PICTURES': str(profile_config.get('features', {}).get('profile_pictures', True)).lower(),
            'PROFILE_FEATURES_EXTENSIONS': str(profile_config.get('features', {}).get('profile_extensions', True)).lower(),
            'PROFILE_FEATURES_ACTIVITY_LOG': str(profile_config.get('features', {}).get('activity_logging', True)).lower(),
            'PROFILE_FEATURES_SEARCH': str(profile_config.get('features', {}).get('search', True)).lower(),
            'PROFILE_DEFAULT_VISIBILITY': profile_config.get('privacy', {}).get('default_visibility', 'private'),
            'PROFILE_ALLOW_PUBLIC': str(profile_config.get('privacy', {}).get('allow_public_profiles', True)).lower(),
        })
        
        # Add Honey Reserve configuration
        honey_reserve_config = self.raw_config.get('honey_reserve', {})
        file_upload_config = honey_reserve_config.get('file_upload', {})
        lifecycle_config = honey_reserve_config.get('lifecycle', {})
        quotas_config = honey_reserve_config.get('quotas', {})
        security_config = honey_reserve_config.get('security', {})
        
        self.processed_config.update({
            'HONEY_RESERVE_ENABLED': str(honey_reserve_config.get('enabled', True)).lower(),
            'HONEY_RESERVE_DEFAULT_QUOTA': str(honey_reserve_config.get('default_quota', 1073741824)),
            'HONEY_RESERVE_MAX_FILE_SIZE': str(file_upload_config.get('max_file_size', 104857600)),
            'HONEY_RESERVE_TEMP_RETENTION_HOURS': str(file_upload_config.get('temp_retention_hours', 48)),
            'HONEY_RESERVE_RATE_LIMIT_MINUTE': str(file_upload_config.get('rate_limit_per_minute', 10)),
            'HONEY_RESERVE_RATE_LIMIT_HOUR': str(file_upload_config.get('rate_limit_per_hour', 100)),
            'HONEY_RESERVE_WARNING_THRESHOLD': str(quotas_config.get('warning_threshold_percent', 90)),
            'HONEY_RESERVE_CRITICAL_THRESHOLD': str(quotas_config.get('critical_threshold_percent', 95)),
            'HONEY_RESERVE_AUTO_CLEANUP': str(quotas_config.get('auto_cleanup_at_percent', 100)),
            'HONEY_RESERVE_ACTIVE_DAYS': str(lifecycle_config.get('active_to_standard_days', 2)),
            'HONEY_RESERVE_STANDARD_DAYS': str(lifecycle_config.get('standard_to_archive_days', 30)),
            'HONEY_RESERVE_ARCHIVE_DAYS': str(lifecycle_config.get('archive_to_deletion_days', 365)),
            'HONEY_RESERVE_AUTO_ARCHIVE': str(lifecycle_config.get('auto_archive_enabled', True)).lower(),
            # Encryption settings
            'HONEY_RESERVE_ENCRYPT_AT_REST': str(security_config.get('encrypt_at_rest', True)).lower(),
            'HONEY_RESERVE_ENCRYPTION_ALGORITHM': security_config.get('encryption_algorithm', 'AES-256-GCM'),
            'HONEY_RESERVE_KEY_DERIVATION': security_config.get('key_derivation', 'HKDF-SHA256'),
            'HONEY_RESERVE_AUDIT_ACCESS': str(security_config.get('audit_all_access', True)).lower(),
            # Master encryption key for file encryption
            'HONEY_RESERVE_MASTER_KEY': self._clean_value(self.honey_reserve_master_key),
            # Service API key for inter-service authentication
            'STING_SERVICE_API_KEY': self._clean_value(self.service_api_key),
            # Alias for public-bee compatibility
            'STING_API_KEY': self._clean_value(self.service_api_key),
        })

        logger.info(f"Config keys present: {list(self.processed_config.keys())}")
        
        # Add debug logging for key values
        logger.info(f"Generated key configuration values:")
        for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'POSTGRES_HOST', 'POSTGRES_PORT', 'ST_API_KEY']:
            value = self.processed_config.get(key, 'NOT_SET')
            logger.info(f"  {key}: {'SET' if value and value != 'NOT_SET' else 'NOT_SET'}")
        
        # Cache and save state
        self._config_cache[self.cache_key] = self.processed_config
        try:
            self._save_config_state(self.processed_config)
        except OSError as e:
            logger.warning(f"Could not save config state (non-fatal): {e}")
        
        return self.processed_config
    
    def _load_existing_email_env(self):
        """Load existing email environment variables from email.env file."""
        email_env_vars = {}
        email_env_path = os.path.join(self.env_dir, 'email.env')
        
        if os.path.exists(email_env_path):
            try:
                with open(email_env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            email_env_vars[key] = value.strip('"\'')
            except Exception as e:
                logger.warning(f"Could not load existing email.env: {e}")
        
        return email_env_vars

    def _generate_email_env_vars(self):
        """Generate email configuration environment variables."""
        email_config = self.raw_config.get('email_service', {})
        
        # Load existing email environment variables
        existing_email_env = self._load_existing_email_env()
        
        # Determine email mode (development or production)
        email_mode = existing_email_env.get('EMAIL_MODE', os.environ.get('EMAIL_MODE', email_config.get('mode', 'development')))
        # Resolve shell-style template strings from config.yml.default (e.g. "${EMAIL_MODE:-development}")
        email_mode = self._resolve_config_value(email_mode, 'development')
        
        env_vars = {
            'EMAIL_MODE': email_mode
        }
        
        if email_mode == 'development':
            # Development mode - use mailpit
            dev_config = email_config.get('development', {})
            env_vars.update({
                'EMAIL_PROVIDER': 'mailpit',
                'SMTP_HOST': dev_config.get('host', 'mailpit'),
                'SMTP_PORT': str(dev_config.get('port', 1025)),
                'SMTP_USERNAME': '',
                'SMTP_PASSWORD': '',
                'SMTP_FROM': 'noreply@sting-ce.local',
                'SMTP_FROM_NAME': 'STING Platform',
                'SMTP_TLS_ENABLED': 'false',
                'SMTP_STARTTLS_ENABLED': 'false',
                'SMTP_SSL_VERIFY': 'false'
            })
            
            # Generate Kratos connection URI for mailpit
            smtp_uri = f"smtp://mailpit:1025/?skip_ssl_verify=true&disable_starttls=true"
            
        else:
            # Production mode - use external SMTP
            prod_config = email_config.get('production', {})
            smtp_config = prod_config.get('smtp', {})
            
            # Get SMTP credentials from existing email.env first, then environment, then config
            smtp_host = existing_email_env.get('SMTP_HOST') or os.environ.get('SMTP_HOST', self._resolve_config_value(smtp_config.get('host', ''), ''))
            smtp_port = existing_email_env.get('SMTP_PORT') or os.environ.get('SMTP_PORT', str(self._resolve_config_value(smtp_config.get('port', 587), '587')))
            smtp_username = existing_email_env.get('SMTP_USERNAME') or os.environ.get('SMTP_USERNAME', self._resolve_config_value(smtp_config.get('username', ''), ''))
            smtp_password = existing_email_env.get('SMTP_PASSWORD') or os.environ.get('SMTP_PASSWORD', self._resolve_config_value(smtp_config.get('password', ''), ''))
            smtp_from = existing_email_env.get('SMTP_FROM') or os.environ.get('SMTP_FROM', self._resolve_config_value(smtp_config.get('from_address', 'noreply@yourdomain.com'), 'noreply@yourdomain.com'))
            smtp_from_name = existing_email_env.get('SMTP_FROM_NAME') or os.environ.get('SMTP_FROM_NAME', self._resolve_config_value(smtp_config.get('from_name', 'STING Platform'), 'STING Platform'))
            smtp_tls = existing_email_env.get('SMTP_TLS_ENABLED') or os.environ.get('SMTP_TLS_ENABLED', str(smtp_config.get('tls_enabled', True)).lower())
            smtp_starttls = existing_email_env.get('SMTP_STARTTLS_ENABLED') or os.environ.get('SMTP_STARTTLS_ENABLED', str(smtp_config.get('starttls_enabled', True)).lower())
            
            env_vars.update({
                'EMAIL_PROVIDER': prod_config.get('provider', 'smtp'),
                'SMTP_HOST': smtp_host,
                'SMTP_PORT': smtp_port,
                'SMTP_USERNAME': smtp_username,
                'SMTP_PASSWORD': smtp_password,
                'SMTP_FROM': smtp_from,
                'SMTP_FROM_NAME': smtp_from_name,
                'SMTP_TLS_ENABLED': smtp_tls,
                'SMTP_STARTTLS_ENABLED': smtp_starttls,
                'SMTP_SSL_VERIFY': 'true'
            })
            
            # Generate Kratos connection URI for production SMTP
            # Check if we already have a correct COURIER_SMTP_CONNECTION_URI
            existing_courier_uri = existing_email_env.get('COURIER_SMTP_CONNECTION_URI', '')
            
            # If we have an existing URI with correct Brevo/external SMTP (not mailpit), use it
            if existing_courier_uri and 'mailpit' not in existing_courier_uri and smtp_host and smtp_host != 'mailpit':
                logger.info(f"Using existing COURIER_SMTP_CONNECTION_URI for {smtp_host}")
                smtp_uri = existing_courier_uri
            # Check if SMTP is properly configured for generation
            elif not smtp_host or not smtp_port:
                logger.warning("SMTP host/port not configured for production mode, falling back to mailpit")
                smtp_uri = f"smtp://mailpit:1025/?skip_ssl_verify=true&disable_starttls=true"
            elif smtp_username and smtp_password:
                # URL-encode credentials to handle special chars like @ in passwords
                encoded_username = url_quote(smtp_username, safe='')
                encoded_password = url_quote(smtp_password, safe='')
                # Use STARTTLS for standard ports (587, 25)
                if str(smtp_port) in ['587', '25']:
                    smtp_uri = f"smtp://{encoded_username}:{encoded_password}@{smtp_host}:{smtp_port}/?disable_starttls=false"
                # Use direct TLS for secure ports (465)
                elif str(smtp_port) == '465':
                    smtp_uri = f"smtps://{encoded_username}:{encoded_password}@{smtp_host}:{smtp_port}/"
                else:
                    # Default to SMTP with optional STARTTLS
                    smtp_uri = f"smtp://{encoded_username}:{encoded_password}@{smtp_host}:{smtp_port}/"
            else:
                logger.warning("SMTP credentials not configured for production mode, using host without auth")
                smtp_uri = f"smtp://{smtp_host}:{smtp_port}/"
        
        env_vars['COURIER_SMTP_CONNECTION_URI'] = smtp_uri
        env_vars['COURIER_SMTP_FROM_ADDRESS'] = env_vars['SMTP_FROM']
        env_vars['COURIER_SMTP_FROM_NAME'] = env_vars['SMTP_FROM_NAME']
        
        # Store in processed config for other services
        self.processed_config.update(env_vars)
        
        return env_vars

    def _generate_kratos_env_vars(self):
        """Generate environment variables for Kratos from the config file."""
        kratos_config = self.raw_config.get('kratos', {})
        
        # Database connection with proper password and SSL mode disabled
        db_user = self.processed_config.get('POSTGRES_USER', 'postgres')
        db_password = self.processed_config.get('POSTGRES_PASSWORD', 'postgres')
        db_host = self.processed_config.get('POSTGRES_HOST', 'db')
        db_port = self.processed_config.get('POSTGRES_PORT', '5432')
        db_name = self.processed_config.get('POSTGRES_DB', 'sting_app')
        
        dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=disable"
        
        # Log DSN with redacted password for debugging
        redacted_dsn = dsn.replace(db_password, "********")
        logger.info(f"Generated Kratos database connection string: {redacted_dsn}")
        
        # Basic URLs - use resolved domain (from .sting_domain file or env)
        # NOT raw config.yml which may contain unexpanded variables like ${STING_HOSTNAME:-...}
        system_config = self.raw_config.get('system', {})
        domain = self.sting_domain  # Use resolved domain, not raw config
        protocol = system_config.get('protocol', 'https')
        ports = system_config.get('ports', {})

        # KRATOS is behind nginx proxy at frontend_port with /.ory path prefix
        public_url = kratos_config.get('public_url', f"{protocol}://{domain}:{ports.get('frontend', 8443)}/.ory")
        admin_url = kratos_config.get('admin_url', f"{protocol}://{domain}:4434")
        # Build frontend URL using resolved domain
        frontend_url = f"{protocol}://{domain}:{ports.get('frontend', 8443)}"
        
        # Self-service configuration
        selfservice = kratos_config.get('selfservice', {})
        
        # Get configured values, but replace 'localhost' with actual domain if we have one
        # This handles cases where config.yml has hardcoded localhost that should be overridden
        def resolve_url(config_value: str, default: str) -> str:
            """Replace localhost in config value with actual domain if we have a real domain."""
            if not config_value:
                return default
            if 'localhost' in config_value and domain != 'localhost':
                return config_value.replace('localhost', domain)
            return config_value
        
        default_return_url = resolve_url(selfservice.get('default_return_url'), frontend_url)
        login_ui_url = resolve_url(selfservice.get('login', {}).get('ui_url'), f"{frontend_url}/login")
        login_lifespan = selfservice.get('login', {}).get('lifespan', '1h')
        registration_ui_url = resolve_url(selfservice.get('registration', {}).get('ui_url'), f"{frontend_url}/register")
        registration_lifespan = selfservice.get('registration', {}).get('lifespan', '1h')
        
        # Authentication methods
        methods = kratos_config.get('methods', {})
        
        # WebAuthn (Passkeys)
        # Check for WebAuthn config in deprecated supertokens section first
        supertokens_config = self.raw_config.get('security', {}).get('supertokens', {})
        webauthn_config = supertokens_config.get('webauthn', {})
        
        # If not found, check in methods
        if not webauthn_config:
            webauthn_config = methods.get('webauthn', {})
            
        webauthn_enabled = str(webauthn_config.get('enabled', True)).lower()
        
        # Get RP ID and expand HOSTNAME variable or use STING domain
        rp_id_raw = webauthn_config.get('rp_id', 'localhost')
        # Use STING domain first, then fall back to HOSTNAME (but avoid Docker container IDs)
        docker_hostname = os.environ.get('HOSTNAME', '')
        # If HOSTNAME looks like a Docker container ID (hex string), use STING domain instead
        if docker_hostname and len(docker_hostname) == 12 and all(c in '0123456789abcdef' for c in docker_hostname):
            hostname = self.sting_domain
        else:
            hostname = docker_hostname or self.sting_domain
        
        # If the rp_id contains a variable placeholder, use sting_domain instead
        # This handles ${HOSTNAME:-...}, ${STING_HOSTNAME:-...}, and nested variants
        if '${' in rp_id_raw:
            # For any variable placeholder, use the resolved sting_domain
            webauthn_rp_id = self.sting_domain
        elif rp_id_raw == 'localhost':
            # Use STING domain if rp_id is just 'localhost'
            webauthn_rp_id = self.sting_domain
        else:
            webauthn_rp_id = rp_id_raw
        
        webauthn_display_name = webauthn_config.get('rp_name', 'STING Authentication')
        
        # Handle rp_origins array
        rp_origins = webauthn_config.get('rp_origins', [])
        if rp_origins:
            # Expand HOSTNAME/STING_HOSTNAME in origins and fix port for production domains
            webauthn_origins = []
            for origin in rp_origins:
                expanded_origin = origin.replace('${HOSTNAME:-your-production-domain.com}', hostname)
                expanded_origin = expanded_origin.replace('${STING_HOSTNAME:-dev-ubuntu.local}', self.sting_domain)
                expanded_origin = expanded_origin.replace('${HOSTNAME:-${STING_HOSTNAME:-dev-ubuntu.local}}', self.sting_domain)
                # For production domains (not localhost), remove :8443 port since they use standard HTTPS
                if self.sting_domain != 'localhost' and '.local' not in self.sting_domain:
                    # Production domain - use standard HTTPS port (no port in URL)
                    expanded_origin = expanded_origin.replace(':8443', '')
                webauthn_origins.append(expanded_origin)
            # Deduplicate origins while preserving order
            seen = set()
            webauthn_origins = [x for x in webauthn_origins if not (x in seen or seen.add(x))]
            webauthn_origin = webauthn_origins[0] if webauthn_origins else frontend_url
        else:
            # Use STING domain for origin if not specified
            # For production domains, use standard HTTPS (no port)
            if self.sting_domain != 'localhost' and '.local' not in self.sting_domain:
                default_origin = f"https://{self.sting_domain}"
            else:
                default_origin = f"https://{self.sting_domain}:8443"
            
            # Check if config has a placeholder or actual value
            config_origin = webauthn_config.get('origin', '')
            if config_origin and '${' not in config_origin:
                webauthn_origin = config_origin
            else:
                webauthn_origin = default_origin
        
        # Password authentication
        password_enabled = str(methods.get('password', {}).get('enabled', True)).lower()
        
        # OIDC configuration
        oidc_enabled = str(methods.get('oidc', {}).get('enabled', False)).lower()
        oidc_providers = methods.get('oidc', {}).get('providers', [])
        
        # Generate email configuration first
        email_env_vars = self._generate_email_env_vars()
        
        # Use the generated email connection URI
        courier_smtp_uri = email_env_vars.get('COURIER_SMTP_CONNECTION_URI', 'smtp://mailpit:1025/?skip_ssl_verify=true')
        
        # Session secret from vault or generated
        session_secret = self.processed_config.get('FLASK_SECRET_KEY', self._get_secret('kratos', 'session_secret'))
        
        # Cookie secrets - generate and persist in Vault (Kratos needs exactly 32 hex chars)
        cookies_secret = self._get_kratos_secret('kratos', 'cookies_secret')
        cipher_secret = self._get_kratos_secret('kratos', 'cipher_secret')
        
        # Cookie configuration - use STING domain if available
        session_cookie_name = 'ory_kratos_session'
        session_cookie_domain = self.sting_domain if self.sting_domain != 'localhost' else domain
        
        # Convert all the config values into environment variables
        env_vars = {
            # Database connection
            'DSN': dsn,
            
            # Core URLs
            'KRATOS_PUBLIC_URL': public_url,
            'KRATOS_ADMIN_URL': admin_url,
            'FRONTEND_URL': frontend_url,
            
            # Identity schema location
            'IDENTITY_DEFAULT_SCHEMA_URL': 'file:///etc/config/kratos/identity.schema.json',
            
            # Session secret
            'SESSION_SECRET': session_secret,
            
            # Self-service flows
            'DEFAULT_RETURN_URL': default_return_url,
            'LOGIN_UI_URL': login_ui_url,
            'LOGIN_LIFESPAN': login_lifespan,
            'REGISTRATION_UI_URL': registration_ui_url,
            'REGISTRATION_LIFESPAN': registration_lifespan,
            
            # WebAuthn (Passkeys) configuration
            'WEBAUTHN_ENABLED': webauthn_enabled,
            'WEBAUTHN_RP_ID': webauthn_rp_id,
            'WEBAUTHN_RP_DISPLAY_NAME': webauthn_display_name,
            'WEBAUTHN_RP_ORIGIN': webauthn_origin,
            
            # Password authentication
            'PASSWORD_ENABLED': password_enabled,
            
            # OIDC configuration
            'OIDC_ENABLED': oidc_enabled,
            
            # Cookie secrets
            'COOKIES_SECRET': cookies_secret,
            'CIPHER_SECRET': cipher_secret,
            
            # Session cookie configuration
            'SESSION_COOKIE_NAME': session_cookie_name,
            'SESSION_COOKIE_DOMAIN': session_cookie_domain
        }
        
        # Add OIDC provider configuration if enabled
        if oidc_enabled == 'true' and oidc_providers:
            for idx, provider in enumerate(oidc_providers):
                prefix = f'OIDC_PROVIDER_{idx}'
                env_vars[f'{prefix}_ID'] = provider.get('id', '')
                env_vars[f'{prefix}_PROVIDER'] = provider.get('provider', '')
                env_vars[f'{prefix}_CLIENT_ID'] = provider.get('client_id', '')
                env_vars[f'{prefix}_CLIENT_SECRET'] = provider.get('client_secret', '')
                env_vars[f'{prefix}_SCOPES'] = ','.join(provider.get('scopes', []))
        
        # Add SMTP configuration
        env_vars['SMTP_CONNECTION_URI'] = courier_smtp_uri
        env_vars['COURIER_SMTP_FROM_ADDRESS'] = email_env_vars.get('COURIER_SMTP_FROM_ADDRESS', 'noreply@sting-ce.local')
        env_vars['COURIER_SMTP_FROM_NAME'] = email_env_vars.get('COURIER_SMTP_FROM_NAME', 'STING Platform')
        
        # Webhook token for Kratos → App webhooks (uses service API key from Vault)
        env_vars['KRATOS_WEBHOOK_TOKEN'] = self._clean_value(self.service_api_key) if self.service_api_key else ''
        
        # Add to processed_config so kratos.yml template substitution can access them
        self.processed_config['SMTP_CONNECTION_URI'] = courier_smtp_uri
        self.processed_config['KRATOS_WEBHOOK_TOKEN'] = env_vars['KRATOS_WEBHOOK_TOKEN']
        self.processed_config['COURIER_SMTP_FROM_ADDRESS'] = env_vars['COURIER_SMTP_FROM_ADDRESS']
        self.processed_config['COURIER_SMTP_FROM_NAME'] = env_vars['COURIER_SMTP_FROM_NAME']
        
        # Add WebAuthn values to processed_config for app.env generation
        self.processed_config['WEBAUTHN_RP_ID'] = webauthn_rp_id
        self.processed_config['WEBAUTHN_RP_NAME'] = webauthn_display_name
        self.processed_config['WEBAUTHN_RP_ORIGIN'] = webauthn_origin

        # Add VAULT_TOKEN to processed_config for app.env generation
        self.processed_config['VAULT_TOKEN'] = self._clean_value(self.vault_token)
        
        return env_vars

    def _generate_knowledge_env_vars(self):
        """Generate environment variables for Knowledge Service from the config file."""
        knowledge_config = self.raw_config.get('knowledge_service', {})
        honey_reserve_config = self.raw_config.get('honey_reserve', {})
        
        # Basic service configuration
        port = str(knowledge_config.get('port', 8090))
        host = knowledge_config.get('host', '0.0.0.0')
        
        # ChromaDB configuration
        chroma_config = knowledge_config.get('chroma', {})
        chroma_url = chroma_config.get('url', 'http://chroma:8000')
        chroma_enabled = str(chroma_config.get('enabled', True)).lower()
        
        # Authentication configuration
        auth_config = knowledge_config.get('authentication', {})
        dev_mode = str(auth_config.get('development_mode', False)).lower()
        kratos_public_url = auth_config.get('kratos_public_url', 'https://kratos:4433')
        kratos_admin_url = auth_config.get('kratos_admin_url', 'https://kratos:4434')
        
        # Access control configuration
        access_control = knowledge_config.get('access_control', {})
        creation_roles = ','.join(access_control.get('creation_roles', ['admin', 'support', 'moderator', 'editor']))
        team_based_access = str(access_control.get('team_based_access', True)).lower()
        
        # Honey jar configuration
        honey_jars = knowledge_config.get('honey_jars', {})
        max_per_user = str(honey_jars.get('max_per_user', 0))
        max_document_size = str(honey_jars.get('max_document_size', 52428800))
        allowed_document_types = ','.join(honey_jars.get('allowed_document_types', [
            'text/plain', 'text/markdown', 'text/html', 'application/pdf', 
            'application/json', 'application/xml', 'text/csv'
        ]))
        
        # Document processing
        processing = honey_jars.get('processing', {})
        chunk_size = str(processing.get('chunk_size', 1000))
        chunk_overlap = str(processing.get('chunk_overlap', 200))
        chunking_strategy = processing.get('chunking_strategy', 'sentence')
        
        # Session jar configuration
        session_jars_config = knowledge_config.get('session_jars', {})
        session_jars_enabled = str(session_jars_config.get('enabled', True)).lower()
        session_jars_max_size_mb = str(session_jars_config.get('max_size_mb', 50))
        session_jars_max_size_bytes = str(int(session_jars_config.get('max_size_mb', 50)) * 1024 * 1024)
        session_jars_max_files = str(session_jars_config.get('max_files_per_jar', 20))
        session_jars_cleanup_days = str(session_jars_config.get('cleanup_after_days', 30))
        session_jars_allowed_types = ','.join(session_jars_config.get('allowed_file_types', [
            'text/plain', 'text/markdown', 'text/html', 'application/pdf',
            'application/json', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]))
        promotion_config = session_jars_config.get('promotion', {})
        session_jars_ai_summary = str(promotion_config.get('ai_summary_enabled', True)).lower()
        session_jars_default_visibility = promotion_config.get('default_visibility', 'private')
        
        # Search configuration
        search_config = knowledge_config.get('search', {})
        max_results = str(search_config.get('max_results', 20))
        min_relevance_score = str(search_config.get('min_relevance_score', 0.3))
        semantic_search = str(search_config.get('semantic_search', True)).lower()
        keyword_fallback = str(search_config.get('keyword_fallback', True)).lower()
        
        # Bee integration
        bee_config = knowledge_config.get('bee_integration', {})
        bee_enabled = str(bee_config.get('enabled', True)).lower()
        max_context_items = str(bee_config.get('max_context_items', 5))
        context_threshold = str(bee_config.get('context_threshold', 0.5))
        
        # Audit configuration
        audit_config = knowledge_config.get('audit', {})
        audit_enabled = str(audit_config.get('enabled', True)).lower()
        retention_days = str(audit_config.get('retention_days', 90))
        
        # Honey Reserve configuration
        file_upload_config = honey_reserve_config.get('file_upload', {})
        lifecycle_config = honey_reserve_config.get('lifecycle', {})
        quotas_config = honey_reserve_config.get('quotas', {})
        
        # Convert all the config values into environment variables
        env_vars = {
            # Basic service configuration
            'KNOWLEDGE_PORT': port,
            'KNOWLEDGE_HOST': host,
            'PYTHONPATH': '/app',
            
            # ChromaDB configuration
            'CHROMA_URL': chroma_url,
            'CHROMA_ENABLED': chroma_enabled,
            
            # Authentication configuration
            'KNOWLEDGE_DEV_MODE': dev_mode,
            'KRATOS_PUBLIC_URL': kratos_public_url,
            'KRATOS_ADMIN_URL': kratos_admin_url,
            
            # Access control
            'KNOWLEDGE_CREATION_ROLES': creation_roles,
            'KNOWLEDGE_TEAM_BASED_ACCESS': team_based_access,
            
            # Honey jar configuration
            'KNOWLEDGE_MAX_PER_USER': max_per_user,
            'KNOWLEDGE_MAX_DOCUMENT_SIZE': max_document_size,
            'KNOWLEDGE_ALLOWED_DOCUMENT_TYPES': allowed_document_types,
            
            # Document processing
            'KNOWLEDGE_CHUNK_SIZE': chunk_size,
            'KNOWLEDGE_CHUNK_OVERLAP': chunk_overlap,
            'KNOWLEDGE_CHUNKING_STRATEGY': chunking_strategy,
            
            # Session jar configuration
            'SESSION_JAR_ENABLED': session_jars_enabled,
            'SESSION_JAR_MAX_SIZE_BYTES': session_jars_max_size_bytes,
            'SESSION_JAR_MAX_FILES': session_jars_max_files,
            'SESSION_JAR_CLEANUP_DAYS': session_jars_cleanup_days,
            'SESSION_JAR_ALLOWED_TYPES': session_jars_allowed_types,
            'SESSION_JAR_AI_SUMMARY': session_jars_ai_summary,
            'SESSION_JAR_DEFAULT_VISIBILITY': session_jars_default_visibility,
            
            # Search configuration
            'KNOWLEDGE_MAX_RESULTS': max_results,
            'KNOWLEDGE_MIN_RELEVANCE_SCORE': min_relevance_score,
            'KNOWLEDGE_SEMANTIC_SEARCH': semantic_search,
            'KNOWLEDGE_KEYWORD_FALLBACK': keyword_fallback,
            
            # Bee integration
            'KNOWLEDGE_BEE_ENABLED': bee_enabled,
            'KNOWLEDGE_MAX_CONTEXT_ITEMS': max_context_items,
            'KNOWLEDGE_CONTEXT_THRESHOLD': context_threshold,
            
            # Audit configuration
            'KNOWLEDGE_AUDIT_ENABLED': audit_enabled,
            'KNOWLEDGE_AUDIT_RETENTION_DAYS': retention_days,
            
            # Honey Reserve configuration
            'HONEY_RESERVE_ENABLED': str(honey_reserve_config.get('enabled', True)).lower(),
            'HONEY_RESERVE_DEFAULT_QUOTA': str(honey_reserve_config.get('default_quota', 1073741824)),
            'HONEY_RESERVE_MAX_FILE_SIZE': str(file_upload_config.get('max_file_size', 104857600)),
            'HONEY_RESERVE_TEMP_RETENTION_HOURS': str(file_upload_config.get('temp_retention_hours', 48)),
            'HONEY_RESERVE_WARNING_THRESHOLD': str(quotas_config.get('warning_threshold_percent', 90)),
            'HONEY_RESERVE_CRITICAL_THRESHOLD': str(quotas_config.get('critical_threshold_percent', 95)),
            'HONEY_RESERVE_RATE_LIMIT_MINUTE': str(file_upload_config.get('rate_limit_per_minute', 10)),
            'HONEY_RESERVE_RATE_LIMIT_HOUR': str(file_upload_config.get('rate_limit_per_hour', 100)),

            # Database configuration
            'POSTGRES_HOST': 'db',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'sting_app',
            'POSTGRES_USER': 'postgres',
            'POSTGRES_PASSWORD': self.processed_config.get('POSTGRES_PASSWORD', ''),
            'DATABASE_URL': self.processed_config.get('DATABASE_URL', '')
        }

        # Add development user configuration if in dev mode
        if dev_mode == 'true':
            dev_user = auth_config.get('development_user', {})
            env_vars.update({
                'KNOWLEDGE_DEV_USER_ID': dev_user.get('id', 'dev-user'),
                'KNOWLEDGE_DEV_USER_EMAIL': dev_user.get('email', 'dev@sting-ce.local'),
                'KNOWLEDGE_DEV_USER_ROLE': dev_user.get('role', 'admin'),
                'KNOWLEDGE_DEV_USER_FIRST_NAME': dev_user.get('name', {}).get('first', 'Dev'),
                'KNOWLEDGE_DEV_USER_LAST_NAME': dev_user.get('name', {}).get('last', 'User')
            })

        return env_vars

    def _generate_observability_env_vars(self):
        """Generate environment variables for Observability services (Grafana, Loki, Promtail)."""
        try:
            # Read observability config directly from root config
            observability_config = self.raw_config.get('observability', {})
            
            # Check if observability is enabled
            obs_enabled = str(observability_config.get('enabled', False)).lower()
            
            logger.info(f"Generating observability.env with enabled={obs_enabled}")
            
            # Grafana configuration
            grafana_config = observability_config.get('grafana', {})
            grafana_enabled = str(grafana_config.get('enabled', False)).lower()
            grafana_port = str(grafana_config.get('port', 3000))
            
            # Generate Grafana admin credentials and store in Vault
            grafana_admin_user = grafana_config.get('admin_user', 'admin')
            
            # Use web-safe password for Grafana admin (avoid +, /, = characters)
            try:
                grafana_admin_password = self._get_secret('observability', 'grafana_admin_password')
                # If the password has problematic characters, regenerate
                if any(c in grafana_admin_password for c in ['+', '/', '=']):
                    grafana_admin_password = self._generate_web_safe_password(16)
            except:
                grafana_admin_password = self._generate_web_safe_password(16)
            
            try:
                grafana_secret_key = self._get_secret('observability', 'grafana_secret_key')
            except:
                grafana_secret_key = self._generate_web_safe_password(32)
            
            # Loki configuration
            loki_config = observability_config.get('loki', {})
            loki_enabled = str(loki_config.get('enabled', False)).lower()
            loki_port = str(loki_config.get('port', 3100))
            
            # Loki storage and performance settings
            storage_config = loki_config.get('storage', {})
            retention_period = storage_config.get('retention_period', '168h')
            compaction_interval = storage_config.get('compaction_interval', '10m')
            
            limits_config = loki_config.get('limits', {})
            max_line_size = limits_config.get('max_line_size', '256KB')
            max_streams_per_user = str(limits_config.get('max_streams_per_user', 5000))
            ingestion_rate_mb = str(limits_config.get('ingestion_rate_mb', 4))
            ingestion_burst_size_mb = str(limits_config.get('ingestion_burst_size_mb', 6))
            
            # Promtail configuration
            promtail_config = observability_config.get('promtail', {})
            promtail_enabled = str(promtail_config.get('enabled', False)).lower()
            promtail_port = str(promtail_config.get('port', 9080))
            
            # Sanitization settings
            sanitization_config = promtail_config.get('sanitization', {})
            sanitization_enabled = str(sanitization_config.get('enabled', True)).lower()
            
            # Vault integration settings
            vault_integration = sanitization_config.get('vault_integration', {})
            vault_references_enabled = str(vault_integration.get('enabled', True)).lower()
            vault_reference_format = vault_integration.get('reference_format', '<VAULT_REF:sting/data/{category}/{field}>')
            
            # Log forwarding configuration
            log_forwarding = observability_config.get('log_forwarding', {})
            log_forwarding_enabled = str(log_forwarding.get('enabled', False)).lower()
            
            # Alerting configuration
            alerting_config = observability_config.get('alerting', {})
            alerting_enabled = str(alerting_config.get('enabled', False)).lower()
            
            # Environment variables for all observability services
            env_vars = {
                # Global observability settings
                'OBSERVABILITY_ENABLED': obs_enabled,
                
                # Grafana environment variables
                'GRAFANA_ENABLED': grafana_enabled,
                'GRAFANA_PORT': grafana_port,
                'GRAFANA_ADMIN_USER': grafana_admin_user,
                'GRAFANA_ADMIN_PASSWORD': grafana_admin_password,
                'GRAFANA_SECRET_KEY': grafana_secret_key,
                'GF_SECURITY_ADMIN_USER': grafana_admin_user,
                'GF_SECURITY_ADMIN_PASSWORD': grafana_admin_password,
                'GF_SECURITY_SECRET_KEY': grafana_secret_key,
                'GF_SECURITY_ALLOW_EMBEDDING': 'false',
                'GF_SECURITY_COOKIE_SECURE': 'true',
                'GF_SECURITY_COOKIE_SAMESITE': 'strict',
                'GF_SECURITY_STRICT_TRANSPORT_SECURITY': 'true',
                'GF_ANALYTICS_REPORTING_ENABLED': 'false',
                'GF_ANALYTICS_CHECK_FOR_UPDATES': 'false',
                'GF_SNAPSHOTS_EXTERNAL_ENABLED': 'false',
                
                # Loki environment variables
                'LOKI_ENABLED': loki_enabled,
                'LOKI_PORT': loki_port,
                'LOKI_RETENTION_PERIOD': retention_period,
                'LOKI_COMPACTION_INTERVAL': compaction_interval,
                'LOKI_MAX_LINE_SIZE': max_line_size,
                'LOKI_MAX_STREAMS_PER_USER': max_streams_per_user,
                'LOKI_INGESTION_RATE_MB': ingestion_rate_mb,
                'LOKI_INGESTION_BURST_SIZE_MB': ingestion_burst_size_mb,
                
                # Promtail environment variables
                'PROMTAIL_ENABLED': promtail_enabled,
                'PROMTAIL_PORT': promtail_port,
                'PROMTAIL_SANITIZATION_ENABLED': sanitization_enabled,
                'PROMTAIL_VAULT_REFERENCES_ENABLED': vault_references_enabled,
                'PROMTAIL_VAULT_REFERENCE_FORMAT': vault_reference_format,
                
                # Log forwarding
                'LOG_FORWARDING_ENABLED': log_forwarding_enabled,
                
                # Alerting
                'ALERTING_ENABLED': alerting_enabled,
                
                # Service URLs for inter-service communication
                'LOKI_URL': 'http://loki:3100',
                'GRAFANA_URL': 'http://grafana:3000',
                'PROMTAIL_URL': 'http://promtail:9080',
                
                # Health check configuration
                'HEALTH_CHECK_INTERVAL': '30s',
                'HEALTH_CHECK_TIMEOUT': '10s',
                'HEALTH_CHECK_RETRIES': '5',
                'HEALTH_CHECK_START_PERIOD': '60s'
            }
        
            # Add external log forwarding targets if configured
            targets = log_forwarding.get('targets', [])
            for i, target in enumerate(targets):
                if target.get('enabled', False):
                    prefix = f'LOG_FORWARD_TARGET_{i}_'
                    env_vars.update({
                        f'{prefix}NAME': target.get('name', f'target_{i}'),
                        f'{prefix}TYPE': target.get('type', 'syslog'),
                        f'{prefix}ENDPOINT': target.get('endpoint', ''),
                        f'{prefix}FORMAT': target.get('format', 'json'),
                        f'{prefix}ENABLED': 'true'
                    })
            
            # Add alerting channels if configured
            channels = alerting_config.get('channels', [])
            for i, channel in enumerate(channels):
                prefix = f'ALERT_CHANNEL_{i}_'
                env_vars.update({
                    f'{prefix}NAME': channel.get('name', f'channel_{i}'),
                    f'{prefix}TYPE': channel.get('type', 'webhook'),
                    f'{prefix}URL': channel.get('url', ''),
                    f'{prefix}RECIPIENTS': ','.join(channel.get('recipients', []))
                })
            
            return env_vars
        except Exception as e:
            logger.error(f"Failed to generate observability environment variables: {e}")
            # Return minimal fallback configuration to ensure observability.env is created
            return {
                'OBSERVABILITY_ENABLED': 'false',
                'GRAFANA_ENABLED': 'false',
                'GRAFANA_ADMIN_USER': 'admin',
                'GRAFANA_ADMIN_PASSWORD': 'admin',
                'GRAFANA_SECRET_KEY': 'changeme',
                'LOKI_ENABLED': 'false',
                'PROMTAIL_ENABLED': 'false',
                'LOG_FORWARDING_ENABLED': 'false',
                'ALERTING_ENABLED': 'false'
            }

    def _generate_headscale_env_vars(self):
        """Generate headscale environment variables from configuration"""
        try:
            headscale_config = self.raw_config.get('headscale', {})
            server_config = headscale_config.get('server', {})
            database_config = headscale_config.get('database', {})
            security_config = headscale_config.get('security', {})
            support_config = headscale_config.get('support_sessions', {})
            community_config = support_config.get('community', {})
            professional_config = support_config.get('professional', {})
            logging_config = headscale_config.get('logging', {})

            logger.info(f"Generating headscale.env with enabled={headscale_config.get('enabled', False)}")
            
            return {
                # Core headscale configuration
                'HEADSCALE_DATABASE_TYPE': database_config.get('type', 'sqlite'),
                'HEADSCALE_DATABASE_SQLITE_PATH': database_config.get('path', '/var/lib/headscale/db.sqlite'),
                'HEADSCALE_EPHEMERAL_NODE_INACTIVITY_TIMEOUT': security_config.get('ephemeral_node_timeout', '30m'),
                'HEADSCALE_BASE_DOMAIN': server_config.get('base_domain', 'support.sting-ce.local'),
                'HEADSCALE_LISTEN_ADDR': server_config.get('listen_addr', '0.0.0.0:8070'),
                'HEADSCALE_METRICS_LISTEN_ADDR': f"0.0.0.0:{server_config.get('metrics_port', 9090)}",
                
                # Security settings
                'HEADSCALE_RANDOMIZE_CLIENT_PORT': str(security_config.get('randomize_client_port', True)).lower(),
                'HEADSCALE_ENABLE_ROUTING': str(security_config.get('enable_routing', False)).lower(),
                
                # Support session configuration
                'HEADSCALE_COMMUNITY_BUNDLE_DURATION': community_config.get('bundle_download_duration', '48h'),
                'HEADSCALE_COMMUNITY_SECURE_LINK': str(community_config.get('secure_link_enabled', True)).lower(),
                'HEADSCALE_COMMUNITY_LIVE_TUNNEL': str(community_config.get('live_tunnel_enabled', False)).lower(),
                'HEADSCALE_PROFESSIONAL_TUNNEL_DURATION': professional_config.get('tunnel_duration', '4h'),
                'HEADSCALE_PROFESSIONAL_BUNDLE_DURATION': professional_config.get('bundle_download_duration', '7d'),
                'HEADSCALE_PROFESSIONAL_LIVE_TUNNEL': str(professional_config.get('live_tunnel_enabled', True)).lower(),
                
                # Logging configuration
                'HEADSCALE_LOG_LEVEL': logging_config.get('level', 'info'),
                'HEADSCALE_LOG_FILE': logging_config.get('file', '/var/log/headscale/headscale.log'),
                
                # Policy file
                'HEADSCALE_POLICY_PATH': headscale_config.get('policy_file', '/etc/headscale/policy.hujson'),
                
                # Service metadata
                'HEADSCALE_ENABLED': str(headscale_config.get('enabled', True)).lower(),
                'HEADSCALE_PORT': str(server_config.get('port', 8070)),
                'HEADSCALE_METRICS_PORT': str(server_config.get('metrics_port', 9090))
            }

        except Exception as e:
            logger.error(f"Failed to generate headscale environment variables: {e}")
            # Return minimal fallback configuration
            return {
                'HEADSCALE_ENABLED': 'false',
                'HEADSCALE_DATABASE_TYPE': 'sqlite',
                'HEADSCALE_DATABASE_SQLITE_PATH': '/var/lib/headscale/db.sqlite',
                'HEADSCALE_EPHEMERAL_NODE_INACTIVITY_TIMEOUT': '30m',
                'HEADSCALE_BASE_DOMAIN': 'support.sting-ce.local',
                'HEADSCALE_LISTEN_ADDR': '0.0.0.0:8070',
                'HEADSCALE_METRICS_LISTEN_ADDR': '0.0.0.0:9090',
                'HEADSCALE_LOG_LEVEL': 'info',
                'HEADSCALE_LOG_FILE': '/var/log/headscale/headscale.log',
                'HEADSCALE_POLICY_PATH': '/etc/headscale/policy.hujson',
                'HEADSCALE_PORT': '8070',
                'HEADSCALE_METRICS_PORT': '9090'
            }

    def _generate_nectar_worker_env_vars(self):
        """Generate nectar-worker environment variables from configuration"""
        try:
            # Get nectar_worker config from top-level section
            nectar_config = self.raw_config.get('nectar_worker', {})

            if not nectar_config:
                logger.warning("No nectar_worker config found, using defaults")
                nectar_config = {}

            logger.info(f"Generating nectar-worker.env with enabled={nectar_config.get('enabled', False)}")

            # Support both flat structure and nested structure
            # Flat: nectar_worker.llm_provider, nectar_worker.llm_endpoint, nectar_worker.llm_model
            # Nested: nectar_worker.ollama.url, nectar_worker.ollama.default_model

            # Try flat structure first
            llm_provider = nectar_config.get('llm_provider')
            llm_endpoint = nectar_config.get('llm_endpoint')
            llm_model = nectar_config.get('llm_model')

            # Fall back to nested structure
            if not llm_endpoint:
                ollama_config = nectar_config.get('ollama', {})
                llm_endpoint = ollama_config.get('url', 'http://localhost:11434')
                llm_model = llm_model or ollama_config.get('default_model', 'phi3:mini')
                llm_provider = llm_provider or 'openai-compatible'  # LM Studio default

            # Resolve nested config sections
            ollama_config = nectar_config.get('ollama', {})
            limits_config = nectar_config.get('limits', {})
            performance_config = nectar_config.get('performance', {})

            # STING API (internal service-to-service calls)
            sting_api_key = self._get_secret('nectar_worker', 'api_key') if hasattr(self, '_get_secret') else ''
            if not sting_api_key:
                sting_api_key = self.processed_config.get('STING_INTERNAL_API_KEY', '')

            llm_endpoint_resolved = (llm_endpoint or ollama_config.get('url', 'http://llm-gateway-proxy:11434')).rstrip('/')
            llm_model_resolved = llm_model or ollama_config.get('default_model', 'phi3:mini')
            llm_provider_resolved = llm_provider or 'openai-compatible'
            keep_alive = ollama_config.get('keep_alive', '30m')

            return {
                # STING API (internal)
                'STING_API_URL': 'http://app:5000',
                'STING_API_KEY': sting_api_key,

                # Redis Configuration
                'REDIS_HOST': 'redis',
                'REDIS_PORT': '6379',
                'REDIS_DB': str(nectar_config.get('redis_db', 2)),
                'CONVERSATION_TTL': str(nectar_config.get('conversation_ttl', 3600)),

                # LLM Configuration (LLM-agnostic)
                'LLM_PROVIDER': llm_provider_resolved,
                'LLM_ENDPOINT': llm_endpoint_resolved,
                'LLM_MODEL': llm_model_resolved,
                'LLM_API_KEY': nectar_config.get('llm_api_key', ''),

                # Ollama-specific aliases (used by main.py / ollama_client.py)
                'OLLAMA_URL': llm_endpoint_resolved,
                'OLLAMA_KEEP_ALIVE': keep_alive,
                'DEFAULT_MODEL': llm_model_resolved,

                # Feature limits
                'MAX_HONEY_JARS_PER_BOT': str(limits_config.get('max_honey_jars_per_bot', 3)),
                'MAX_CONTEXT_TOKENS': str(limits_config.get('max_context_tokens', 2000)),

                # Caching
                'BOT_CACHE_TTL': str(performance_config.get('bot_config_cache_ttl', 300)),
                'CONTEXT_CACHE_TTL': str(performance_config.get('honey_jar_cache_ttl', 300)),

                # PII config path
                'CONFIG_PATH': '/app/conf/config.yml',

                # Service metadata
                'NECTAR_WORKER_ENABLED': str(nectar_config.get('enabled', True)).lower(),
                'NECTAR_WORKER_PORT': str(nectar_config.get('port', 9002)),
                'LOG_LEVEL': nectar_config.get('logging', {}).get('level', 'INFO')
            }

        except Exception as e:
            logger.error(f"Failed to generate nectar-worker environment variables: {e}")
            return {
                'STING_API_URL': 'http://app:5000',
                'STING_API_KEY': '',
                'REDIS_HOST': 'redis',
                'REDIS_PORT': '6379',
                'REDIS_DB': '2',
                'CONVERSATION_TTL': '3600',
                'LLM_PROVIDER': 'openai-compatible',
                'LLM_ENDPOINT': 'http://llm-gateway-proxy:11434',
                'LLM_MODEL': 'phi3:mini',
                'LLM_API_KEY': '',
                'OLLAMA_URL': 'http://llm-gateway-proxy:11434',
                'OLLAMA_KEEP_ALIVE': '30m',
                'DEFAULT_MODEL': 'phi3:mini',
                'MAX_HONEY_JARS_PER_BOT': '3',
                'MAX_CONTEXT_TOKENS': '2000',
                'BOT_CACHE_TTL': '300',
                'CONTEXT_CACHE_TTL': '300',
                'CONFIG_PATH': '/app/conf/config.yml',
                'NECTAR_WORKER_ENABLED': 'true',
                'NECTAR_WORKER_PORT': '9002',
                'LOG_LEVEL': 'INFO'
            }

    def _generate_public_bee_env_vars(self):
        """Generate public-bee environment variables from configuration"""
        try:
            # Get public_bee config from top-level section if it exists
            public_bee_config = self.raw_config.get('public_bee', {})

            # Get database credentials (URL-encoded password for DATABASE_URL)
            from urllib.parse import quote_plus
            postgres_user = self.processed_config.get('POSTGRES_USER', 'postgres')
            postgres_password = self.processed_config.get('POSTGRES_PASSWORD', '')
            postgres_db = self.processed_config.get('POSTGRES_DB', 'sting_app')

            # URL-encode the password to handle special characters
            encoded_password = quote_plus(postgres_password) if postgres_password else ''

            # Hive Mode / ChatOps config (Phase 3-4.5)
            hive_config = public_bee_config.get('hive', {})
            sting_api_key = self.processed_config.get('STING_API_KEY', '')
            system_hostname = self.raw_config.get('system', {}).get('hostname', 'localhost')

            return {
                'PUBLIC_BEE_PORT': str(public_bee_config.get('port', 8092)),
                'PUBLIC_BEE_HOST': public_bee_config.get('host', '0.0.0.0'),
                'DATABASE_URL': f"postgresql://{postgres_user}:{encoded_password}@db:5432/{postgres_db}",
                'EXTERNAL_AI_URL': public_bee_config.get('external_ai_url', 'http://external-ai:8091'),
                'CHATBOT_URL': public_bee_config.get('chatbot_url', 'http://chatbot:8888'),
                'KNOWLEDGE_SERVICE_URL': public_bee_config.get('knowledge_service_url', 'http://knowledge:8090'),
                'LOG_LEVEL': public_bee_config.get('log_level', 'INFO'),
                # Hive Mode — Bee Connector
                'HIVE_MODE': str(hive_config.get('enabled', False)).lower(),
                'PUBLIC_BEE_BASE_URL': hive_config.get('base_url', f'https://{system_hostname}'),
                # ChatOps Authorization
                'STING_API_URL': 'http://app:5000',
                'STING_API_KEY': sting_api_key,
                'CHATOPS_CHALLENGE_SECRET': hive_config.get('challenge_secret', sting_api_key),
                'CHATOPS_MAGIC_LINK_TTL': str(hive_config.get('magic_link_ttl_minutes', 15)),
                'CHATOPS_SESSION_TTL': str(hive_config.get('session_ttl_hours', 8) * 3600),
                'CHATOPS_MAX_ATTEMPTS': str(hive_config.get('max_challenge_attempts', 3)),
            }
        except Exception as e:
            logger.error(f"Failed to generate public-bee environment variables: {e}")
            return {
                'PUBLIC_BEE_PORT': '8092',
                'PUBLIC_BEE_HOST': '0.0.0.0',
                'DATABASE_URL': 'postgresql://postgres:password@db:5432/sting_app',
                'EXTERNAL_AI_URL': 'http://external-ai:8091',
                'CHATBOT_URL': 'http://chatbot:8888',
                'KNOWLEDGE_SERVICE_URL': 'http://knowledge:8090',
                'LOG_LEVEL': 'INFO',
                'HIVE_MODE': 'false',
                'PUBLIC_BEE_BASE_URL': 'http://localhost:8092',
                'STING_API_URL': 'http://app:5000',
                'STING_API_KEY': '',
                'CHATOPS_CHALLENGE_SECRET': '',
                'CHATOPS_MAGIC_LINK_TTL': '15',
                'CHATOPS_SESSION_TTL': '28800',
                'CHATOPS_MAX_ATTEMPTS': '3',
            }

    def _generate_report_bee_env_vars(self):
        """Generate report-bee (QE Bee) environment variables from config.yml review_bee section"""
        try:
            ai_config = self.raw_config.get('ai', {})
            review_bee_config = ai_config.get('review_bee', {})
            critic_config = review_bee_config.get('critic', {})

            # Resolve model: critic model → fallback_model → global fallback
            global_fallback = self.processed_config.get('LLM_DEFAULT_MODEL', 'qwen3.5-1m:latest')
            model = critic_config.get('model', '') or critic_config.get('fallback_model', '') or global_fallback

            return {
                'APP_SERVICE_URL': 'https://app:5050',
                'LLM_SERVICE_URL': 'http://external-ai:8091',
                'QE_BEE_LLM_ENABLED': str(review_bee_config.get('enabled', False)).lower(),
                'QE_BEE_MODEL': model,
                'QE_BEE_TIMEOUT': str(critic_config.get('timeout_seconds', 30)),
                'QE_BEE_POLL_INTERVAL': str(review_bee_config.get('poll_interval', 5)),
            }
        except Exception as e:
            logger.error(f"Failed to generate report-bee environment variables: {e}")
            return {
                'APP_SERVICE_URL': 'https://app:5050',
                'LLM_SERVICE_URL': 'http://external-ai:8091',
                'QE_BEE_LLM_ENABLED': 'false',
                'QE_BEE_MODEL': 'qwen3.5-1m:latest',
                'QE_BEE_TIMEOUT': '30',
                'QE_BEE_POLL_INTERVAL': '5',
            }

    def _generate_email_secrets(self):
        email_secrets = {
            'smtp_password': self._generate_secret(),
            'smtp_username': 'your-email@gmail.com'
        }
        self.write_secret('email/credentials', email_secrets)
    
    def _verify_state_validity(self, state_data: Dict) -> bool:
        """Verify if stored state is valid, complete, and current.
        
        Checks:
        1. Required keys exist in state
        2. Config.yml hash matches (state is current with config file)
        3. State was created by the same config_loader version
        4. Domain hasn't changed (from .sting_domain file)
        """
        required_keys = [
            'POSTGRES_USER',
            'POSTGRES_PASSWORD',
            'ST_API_KEY',
            'VAULT_TOKEN'
        ]
        
        # Check required keys exist
        if not all(key in state_data for key in required_keys):
            logger.info("State file missing required keys, will regenerate")
            return False
        
        # Check if config.yml has changed since state was saved
        stored_hash = state_data.get('_config_hash', '')
        current_hash = self._get_config_hash()
        if stored_hash != current_hash:
            logger.info(f"Config.yml has changed (hash mismatch), will regenerate from scratch")
            logger.debug(f"Stored hash: {stored_hash[:16]}..., Current hash: {current_hash[:16]}...")
            return False
        
        # Check state version (invalidate if config_loader was updated)
        state_version = state_data.get('_state_version', '1.0')
        if state_version != self._state_version:
            logger.info(f"State version mismatch ({state_version} vs {self._state_version}), will regenerate")
            return False
        
        # Check if domain has changed (from .sting_domain file or env)
        stored_domain = state_data.get('_sting_domain', '')
        current_domain = self.sting_domain
        if stored_domain and stored_domain != current_domain:
            logger.info(f"Domain changed from '{stored_domain}' to '{current_domain}', will regenerate")
            return False
        
        # Check if stored URLs contain 'localhost' but we now have a real domain
        stored_public_url = state_data.get('PUBLIC_URL', '')
        if 'localhost' in stored_public_url and current_domain != 'localhost':
            logger.info(f"State has localhost URLs but domain is {current_domain}, will regenerate")
            return False
        
        logger.info("Using cached configuration state (config.yml unchanged)")
        return True
    
    def _get_config_hash(self) -> str:
        """Generate a hash of config.yml for change detection."""
        import hashlib
        try:
            with open(self.config_file, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash config file: {e}")
            return ''

    def _save_config_state(self, config: Dict) -> None:
        """Save configuration state to persistent storage with metadata.
        
        Adds metadata for cache invalidation:
        - _config_hash: SHA256 of config.yml (detect file changes)
        - _state_version: Config loader version (invalidate on upgrades)
        - _sting_domain: Current domain (invalidate if domain changes)
        - _created_at: Timestamp for debugging
        """
        # Add metadata for cache validation
        config_with_meta = config.copy()
        config_with_meta['_config_hash'] = self._get_config_hash()
        config_with_meta['_state_version'] = self._state_version
        config_with_meta['_sting_domain'] = self.sting_domain
        config_with_meta['_created_at'] = datetime.datetime.now().isoformat()
        
        with open(self.state_file, 'w') as f:
            json.dump(config_with_meta, f, indent=2)
        os.chmod(self.state_file, 0o600)  # Secure file permissions
        logger.info(f"Saved configuration state with hash: {config_with_meta['_config_hash'][:16]}...")

    def _clean_value(self, value: str) -> str:
        """Clean configuration values by removing quotes."""
        if isinstance(value, str):
            return value.replace('"', '').replace("'", '')
        return str(value)

            
    def generate_env_file(self, env_path: Optional[str] = None, service_specific: bool = True) -> None:
        """Generate service-specific .env files with processed configuration."""
        # ALWAYS remove any supertokens.env file if it exists (no conditions)
        st_env_files = [
            os.path.join(self.env_dir, "supertokens.env"),
            os.path.join(self.config_dir, "supertokens.env"),
            os.path.join(os.path.expanduser("~/.sting-ce/env"), "supertokens.env")
        ]
        
        for st_file in st_env_files:
            if os.path.exists(st_file):
                try:
                    os.remove(st_file)
                    logger.info(f"Removed deprecated supertokens.env file at {st_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove supertokens.env at {st_file}: {e}")
            
        # Debug logging before processing
        logger.info("===== BEFORE ENV GENERATION =====")
        for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'HF_TOKEN']:
            logger.info(f"{key}: {'[SET]' if self.processed_config.get(key) else '[EMPTY]'}")
        
        self.processed_config = {}  # Clear existing config
        self.process_config()  # Generate fresh configuration
        
        # Ensure HF_TOKEN is in processed_config (add this check)
        # SECURITY: Don't log token values, only whether they're set
        hf_token = self.processed_config.get('HF_TOKEN')
        logger.info(f"HF_TOKEN in processed_config: {'[SET]' if hf_token else '[NOT_SET]'}")
        
        sensitive_keys = {
            'API_KEY', 'ST_API_KEY', 'ST_DASHBOARD_API_KEY',
            'POSTGRESQL_PASSWORD', 'POSTGRES_PASSWORD',
            'DATABASE_URL', 'POSTGRESQL_CONNECTION_URI',
            'SQLALCHEMY_DATABASE_URI',
            'POSTGRESQL_USER', 'POSTGRES_USER',
            'POSTGRESQL_DATABASE_NAME', 'POSTGRES_DB',
            'POSTGRESQL_HOST', 'POSTGRES_HOST',
            'POSTGRESQL_PORT', 'POSTGRES_PORT',
            'FLASK_SECRET_KEY', 'SECRET_KEY',
            'HF_TOKEN'  # Add HF_TOKEN to sensitive keys
        }

        if service_specific:
            # Pre-generate configs that populate processed_config values needed by other configs
            # This ensures WebAuthn values are available for app.env
            kratos_env = self._generate_kratos_env_vars()
            knowledge_env = self._generate_knowledge_env_vars()
            
            # Define service-specific configurations
            service_configs = {
                'app.env': {
                    'APP_ENV', 'FLASK_DEBUG', 'DATABASE_URL', 'ST_API_KEY',
                    'SQLALCHEMY_DATABASE_URI', 'FLASK_APP', 'APP_PORT', 'API_URL',
                    'FLASK_SECRET_KEY','SECRET_KEY', 'SUPERTOKENS_URL', 'SUPERTOKENS_API_DOMAIN',
                    'WEBAUTHN_RP_ID', 'WEBAUTHN_RP_NAME', 'WEBAUTHN_RP_ORIGIN',
                    'HONEY_RESERVE_ENABLED', 'HONEY_RESERVE_DEFAULT_QUOTA', 'HONEY_RESERVE_MAX_FILE_SIZE',
                    'HONEY_RESERVE_TEMP_RETENTION_HOURS', 'HONEY_RESERVE_WARNING_THRESHOLD',
                    'HONEY_RESERVE_CRITICAL_THRESHOLD', 'HONEY_RESERVE_RATE_LIMIT_MINUTE',
                    'HONEY_RESERVE_RATE_LIMIT_HOUR', 'HONEY_RESERVE_ENCRYPT_AT_REST',
                    'HONEY_RESERVE_MASTER_KEY', 'HONEY_RESERVE_ENCRYPTION_ALGORITHM',
                    'HONEY_RESERVE_KEY_DERIVATION', 'HONEY_RESERVE_AUDIT_ACCESS',
                    'VAULT_TOKEN', 'SERVER_IP', 'TZ',
                    # SMTP settings for email/verification codes
                    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD',
                    'SMTP_FROM', 'SMTP_FROM_NAME', 'SMTP_TLS_ENABLED', 'SMTP_STARTTLS_ENABLED',
                    'SMTP_SSL_VERIFY'
                },
                'db.env': {
                    'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
                    'POSTGRES_HOST', 'POSTGRES_PORT'
                },
                'vault.env': {
                    'VAULT_TOKEN', 'VAULT_ADDR', 'VAULT_API_ADDR'
                },
                'frontend.env': {
                    'REACT_APP_API_URL', 'REACT_APP_SUPERTOKENS_URL',
                    'REACT_APP_KRATOS_PUBLIC_URL', 'REACT_APP_KRATOS_BROWSER_URL',
                    'NODE_ENV', 'REACT_PORT', 'PUBLIC_URL'
                },
                'llm-gateway.env': {
                    'PORT': self.processed_config.get('LLM_GATEWAY_PORT', '8080'),
                    'LOG_LEVEL': self.processed_config.get('LLM_GATEWAY_LOG_LEVEL', 'INFO'),
                    'DEFAULT_MODEL': self.processed_config.get('LLM_DEFAULT_MODEL', 'llama3'),
                    'HF_TOKEN': self.processed_config.get('HF_TOKEN', ''),
                    'OLLAMA_HOST': self.raw_config.get('llm_service', {}).get('ollama', {}).get('endpoint', 'http://localhost:11434'),
                    'EXTERNAL_AI_HOST': 'http://host.docker.internal:8091'
                },
                'chatbot.env': {
                    'PORT': '8081',
                    'BEE_PORT': '8888',
                    'HOST': '0.0.0.0',
                    'LOG_LEVEL': 'INFO',
                    'CHATBOT_NAME': self.raw_config.get('chatbot', {}).get('name', 'Bee'),
                    'CHATBOT_MODEL': self.raw_config.get('chatbot', {}).get('model', 'phi3'),
                    'CHATBOT_CONTEXT_WINDOW': str(self.raw_config.get('chatbot', {}).get('context_window', 10)),
                    'CHATBOT_SYSTEM_PROMPT': self.raw_config.get('chatbot', {}).get('default_system_prompt', 'You are Bee, a helpful and friendly assistant for the STING platform.'),
                    'CHATBOT_TOOLS_ENABLED': 'true',
                    'CHATBOT_ALLOWED_TOOLS': 'search,summarize,analyze',
                    'CHATBOT_REQUIRE_AUTH': 'true',
                    'CHATBOT_LOG_CONVERSATIONS': 'true',
                    'CHATBOT_CONTENT_FILTER_LEVEL': 'strict',
                    'LLM_GATEWAY_URL': 'http://llm-gateway:8080',
                    'NATIVE_LLM_URL': 'http://host.docker.internal:8086',
                    'BEE_MESSAGING_SERVICE_ENABLED': 'true',
                    'MESSAGING_SERVICE_URL': 'http://messaging:8889',
                    'BEE_SENTIMENT_ENABLED': 'true',
                    'BEE_ENCRYPTION_ENABLED': 'true',
                    'BEE_TOOLS_ENABLED': 'true',
                    'KRATOS_PUBLIC_URL': 'https://kratos:4433',
                    'KRATOS_ADMIN_URL': 'https://kratos:4434',
                    'BEE_HOST': '0.0.0.0',
                    'KNOWLEDGE_SERVICE_URL': 'http://knowledge:8090',
                    'KNOWLEDGE_ENABLED': 'true',
                    'STING_SERVICE_API_KEY': self.processed_config.get('STING_SERVICE_API_KEY', ''),
                    'BEE_SERVICE_API_KEY': self.bee_service_api_key or '',  # Bee's service API key for agentic operations
                    # Database configuration
                    'POSTGRES_HOST': 'db',
                    'POSTGRES_PORT': '5432',
                    'POSTGRES_DB': 'sting_app',
                    'POSTGRES_USER': 'postgres',
                    'POSTGRES_PASSWORD': self.processed_config.get('POSTGRES_PASSWORD', ''),
                    'DATABASE_URL': self.processed_config.get('DATABASE_URL', ''),
                    # Conversation management settings
                    'BEE_CONVERSATION_MAX_TOKENS': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('max_tokens', 4096)),
                    'BEE_CONVERSATION_MAX_MESSAGES': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('max_messages', 50)),
                    'BEE_CONVERSATION_TOKEN_BUFFER_PERCENT': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('token_buffer_percent', 20)),
                    'BEE_CONVERSATION_PERSISTENCE_ENABLED': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('persistence_enabled', True)).lower(),
                    'BEE_CONVERSATION_SESSION_TIMEOUT_HOURS': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('session_timeout_hours', 24)),
                    'BEE_CONVERSATION_ARCHIVE_AFTER_DAYS': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('archive_after_days', 30)),
                    'BEE_CONVERSATION_CLEANUP_INTERVAL_HOURS': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('cleanup_interval_hours', 1)),
                    'BEE_CONVERSATION_SUMMARIZATION_ENABLED': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('summarization_enabled', True)).lower(),
                    'BEE_CONVERSATION_SUMMARIZE_AFTER_MESSAGES': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('summarize_after_messages', 20)),
                    'BEE_CONVERSATION_SUMMARY_MAX_TOKENS': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('summary_max_tokens', 200)),
                    'BEE_CONVERSATION_SUMMARY_MODEL': self.raw_config.get('chatbot', {}).get('conversation', {}).get('summary_model', 'phi3:mini'),
                    'BEE_CONVERSATION_PRUNING_STRATEGY': self.raw_config.get('chatbot', {}).get('conversation', {}).get('pruning_strategy', 'sliding_window'),
                    'BEE_CONVERSATION_KEEP_SYSTEM_MESSAGES': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('keep_system_messages', True)).lower(),
                    'BEE_CONVERSATION_KEEP_RECENT_MESSAGES': str(self.raw_config.get('chatbot', {}).get('conversation', {}).get('keep_recent_messages', 10))
                },
                'kratos.env': kratos_env,  # Use pre-generated values
                'knowledge.env': knowledge_env,  # Use pre-generated values
                'profile.env': {
                    'PROFILE_SERVICE_ENABLED': 'true',
                    'PROFILE_SERVICE_PORT': '8092',
                    'FLASK_ENV': self.processed_config.get('APP_ENV', 'development'),
                    'FLASK_SECRET_KEY': self.processed_config.get('FLASK_SECRET_KEY', ''),
                    'DATABASE_URL': self.processed_config.get('DATABASE_URL', ''),
                    'VAULT_ADDR': 'http://vault:8200',
                    'VAULT_TOKEN': self.processed_config.get('VAULT_TOKEN', 'root'),
                    'KRATOS_PUBLIC_URL': self.processed_config.get('KRATOS_PUBLIC_URL', 'https://kratos:4433'),
                    'KRATOS_ADMIN_URL': 'http://kratos:4434',
                    'PROFILE_MAX_FILE_SIZE': '52428800',
                    'PROFILE_ALLOWED_IMAGE_TYPES': 'image/jpeg,image/png,image/webp',
                    'PROFILE_IMAGE_MAX_WIDTH': '1024',
                    'PROFILE_IMAGE_MAX_HEIGHT': '1024',
                    'PROFILE_IMAGE_QUALITY': '85',
                    'PROFILE_FEATURES_PICTURES': 'true',
                    'PROFILE_FEATURES_EXTENSIONS': 'true',
                    'PROFILE_FEATURES_ACTIVITY_LOG': 'true',
                    'PROFILE_FEATURES_SEARCH': 'true',
                    'PROFILE_DEFAULT_VISIBILITY': 'private',
                    'PROFILE_ALLOW_PUBLIC': 'true',
                    'HEALTH_CHECK_INTERVAL': '30s',
                    'HEALTH_CHECK_TIMEOUT': '10s',
                    'HEALTH_CHECK_RETRIES': '5',
                    'HEALTH_CHECK_START_PERIOD': '60s'
                },
                'messaging.env': {
                    'MESSAGING_PORT': '8889',
                    'MESSAGING_HOST': '0.0.0.0',
                    'MESSAGING_ENCRYPTION_ENABLED': 'true',
                    'MESSAGING_QUEUE_ENABLED': 'true',
                    'MESSAGING_NOTIFICATIONS_ENABLED': 'true',
                    'MESSAGING_STORAGE_BACKEND': 'postgresql',
                    # Messaging uses its own database (sting_messaging) for message storage
                    'DATABASE_URL': f"postgresql://{self.processed_config.get('POSTGRES_USER', 'postgres')}:{url_quote(self.processed_config.get('POSTGRES_PASSWORD', ''), safe='')}@db:5432/sting_messaging?sslmode=disable",
                    'REDIS_URL': 'redis://redis:6379',
                    'MAX_MESSAGE_SIZE': '1048576',
                    'MESSAGE_RETENTION_DAYS': '30',
                    'PYTHONPATH': '/app'
                },
                'external-ai.env': {
                    'EXTERNAL_AI_HOST': '0.0.0.0',
                    'EXTERNAL_AI_PORT': self.raw_config.get('llm_service', {}).get('external_ai', {}).get('port', '8091'),
                    'OLLAMA_BASE_URL': self.raw_config.get('llm_service', {}).get('ollama', {}).get('endpoint', 'http://localhost:11434'),
                    'LLM_PRIMARY_PROVIDER': self.processed_config.get('LLM_PRIMARY_PROVIDER', 'ollama'),
                    'REDIS_HOST': 'redis',
                    'REDIS_PORT': '6379',
                    'REDIS_LLM_DB': '1',
                    'LLM_MAX_QUEUE_SIZE': '1000',
                    'LLM_REQUEST_TIMEOUT': '300',
                    'LLM_MAX_RETRIES': '3',
                    'LLM_QUEUE_POLL_INTERVAL': '0.1',
                    'CORS_ORIGINS': self.processed_config.get('PUBLIC_URL', f"https://{self.sting_domain}"),
                    'LOG_LEVEL': 'INFO',
                    'BEE_SERVICE_API_KEY': self.bee_service_api_key or '',  # Service API key for report generation
                    'STING_API_URL': 'https://app:5050',  # For API calls back to main app
                    # Web search configuration for report research
                    'WEB_SEARCH_ENABLED': str(self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('enabled', False)).lower(),
                    'WEB_SEARCH_PROVIDER': self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('provider', 'searxng'),
                    'SEARXNG_URL': self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('searxng_url', 'http://searxng:8080'),
                    'WEB_SEARCH_FETCH_CONTENT': str(self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('fetch_content', True)).lower(),
                    'WEB_SEARCH_MAX_RESULTS': str(self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('max_results', 5)),
                    'WEB_SEARCH_TIMEOUT': str(self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}).get('timeout', 5)),
                    # Model configuration for sub-tasks (query optimization, summarization)
                    # These default to empty string, letting the code pick a sensible default from available models
                    'QUERY_OPTIMIZER_MODEL': (
                        self.raw_config.get('llm_service', {}).get('external_ai', {}).get('query_optimizer_model', '') or
                        self.raw_config.get('ai', {}).get('external_ai', {}).get('query_optimizer_model', '')
                    ),
                    'BEE_CONVERSATION_SUMMARY_MODEL': (
                        self.raw_config.get('llm_service', {}).get('external_ai', {}).get('conversation_summary_model', '') or
                        self.raw_config.get('ai', {}).get('external_ai', {}).get('conversation_summary_model', '')
                    ),
                    # System timezone for Bee and time-related features
                    'SYSTEM_TIMEZONE': self.raw_config.get('system', {}).get('timezone', 'UTC'),
                    # Bee Chat Enhancement Settings
                    # Chat-first logic: determine if queries should be handled in chat vs reports
                    'BEE_CHAT_FIRST_ENABLED': str(self.raw_config.get('ai', {}).get('bee', {}).get('chat_first', {}).get('enabled', True)).lower(),
                    # ReviewBee for chat: uses same model as report review (critic model or fallback)
                    'BEE_CHAT_REVIEW_ENABLED': str(self.raw_config.get('ai', {}).get('review_bee', {}).get('enabled', False)).lower(),
                    'BEE_CHAT_REVIEW_THRESHOLD': str(self.raw_config.get('ai', {}).get('review_bee', {}).get('revision_threshold', 0.75)),
                    # Review model: use ReviewBee critic model, or fall back to default local model
                    'BEE_REVIEW_MODEL': self.raw_config.get('ai', {}).get('review_bee', {}).get('critic', {}).get('model', '') or self.processed_config.get('LLM_DEFAULT_MODEL', 'phi4'),
                    # PostgreSQL credentials for conversation persistence (sting_messaging database)
                    'POSTGRES_HOST': 'db',
                    'POSTGRES_PORT': '5432',
                    'POSTGRES_USER': self.processed_config.get('POSTGRES_USER', 'app_user'),
                    'POSTGRES_PASSWORD': self.processed_config.get('POSTGRES_PASSWORD', ''),
                    'MESSAGING_DATABASE_URL': f"postgresql://{self.processed_config.get('POSTGRES_USER', 'app_user')}:{self.processed_config.get('POSTGRES_PASSWORD', '')}@db:5432/sting_messaging"
                },
                'observability.env': self._generate_observability_env_vars(),
                'headscale.env': self._generate_headscale_env_vars(),
                'public-bee.env': self._generate_public_bee_env_vars(),
                'email.env': self._generate_email_env_vars(),
                'nectar-worker.env': self._generate_nectar_worker_env_vars(),
                'report-bee.env': self._generate_report_bee_env_vars()
                # SUPERTOKENS IS COMPLETELY REMOVED - DO NOT UNCOMMENT
                # DO NOT ADD ANY SUPERTOKENS ENV FILES HERE
            }
            
            # Generate service-specific env files in both config and env directories
            for filename, config in service_configs.items():
                # Paths for config_dir and env_dir
                paths = [
                    os.path.join(self.config_dir, filename),
                    os.path.join(self.env_dir, filename)
                ]
                for service_env_path in paths:
                    # Skip any supertokens.env files
                    if "supertokens.env" in service_env_path:
                        logger.warning(f"Skipping deprecated {service_env_path}, SuperTokens is no longer used")
                        continue
                        
                    logger.info(f"Generating {filename} at {service_env_path}")
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(service_env_path), exist_ok=True)
                    with open(service_env_path, 'w', opener=lambda path, flags: os.open(path, flags, 0o600)) as f:
                        # Config-based writing for services
                        if isinstance(config, dict):
                            items = config.items()
                        else:
                            items = ((key, self.processed_config.get(key, '')) for key in config)
                        for key, value in items:
                            if key in sensitive_keys:
                                f.write(f'{key}={value}\n')
                            else:
                                f.write(f'{key}="{str(value)}"\n')
        else:
            # Generate single combined .env file
            env_path = env_path or os.path.join(self.config_dir, '.env')
            logger.info(f"Generating combined .env file at {env_path}")
        
            with open(env_path, 'w', opener=lambda path, flags: os.open(path, flags, 0o600)) as f:
                for key, value in sorted(self.processed_config.items()):
                    if key in sensitive_keys:
                        f.write(f'{key}={str(value)}\n')
                    else:
                        if isinstance(value, bool):
                            value = str(value).lower()
                        elif isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        elif value is None:
                            value = ''
                        f.write(f'{key}="{str(value)}"\n')
                        
        # Debug logging after processing
        logger.info("===== AFTER ENV GENERATION =====")
        for key in ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'HF_TOKEN']:
            logger.info(f"{key}: {'[SET]' if self.processed_config.get(key) else '[EMPTY]'}")

        # ─── Generate SearXNG settings.yml ───
        # Substitutes the Brave Search API key from config.yml into the SearXNG template
        # Must run before Kratos generation (which may return early)
        self._generate_searxng_config()

        # Generate a concrete Kratos YAML configuration based on environment variables
        kratos_conf_dir = os.path.join(self.config_dir, 'kratos')
        os.makedirs(kratos_conf_dir, exist_ok=True)

        # Generate kratos.yml to ${INSTALL_DIR}/kratos/ (where docker-compose expects it)
        kratos_path = os.path.join(self.install_dir, 'kratos', 'kratos.yml')

        # Always regenerate kratos.yml from template to ensure env vars (SMTP, webhooks,
        # hostnames) are current. Back up existing config before overwriting.
        if os.path.exists(kratos_path):
            backup_path = kratos_path + '.prev'
            try:
                import shutil
                shutil.copy2(kratos_path, backup_path)
                logger.info(f"Backed up existing Kratos config to {backup_path}")
            except Exception as e:
                logger.warning(f"Could not backup Kratos config: {e}")

        # Generate from template — templates are in ${INSTALL_DIR}/kratos/
        template_kratos_path = os.path.join(self.install_dir, 'kratos', 'kratos.yml.template')
        minimal_kratos_path = os.path.join(self.install_dir, 'kratos', 'minimal.kratos.yml')

        # Prefer template, then minimal as fallback
        if os.path.exists(template_kratos_path):
            template_path = template_kratos_path
            template_type = "template"
        else:
            template_path = minimal_kratos_path
            template_type = "minimal"

        if os.path.exists(template_path):
            try:
                # Read template content
                with open(template_path, 'r') as src:
                    content = src.read()

                # If using template, substitute hostname and port
                if template_type == "template":
                    # Use resolved sting_domain (from .sting_domain file, env, or config)
                    sting_hostname = self.sting_domain
                    content = content.replace('__STING_HOSTNAME__', sting_hostname)
                    
                    # Resolve frontend port — use 443 for production domains, 8443 for local dev
                    ports = self.raw_config.get('ports', {})
                    if sting_hostname not in ('localhost', '127.0.0.1') and '.' in sting_hostname:
                        frontend_port = 443
                    else:
                        frontend_port = ports.get('frontend', 8443)
                    
                    # Replace port: standard HTTPS (443) doesn't need explicit port in URLs
                    if frontend_port == 443:
                        content = content.replace(':8443', '')
                    elif frontend_port != 8443:
                        content = content.replace(':8443', f':{frontend_port}')
                    
                    logger.info(f"Generated Kratos config from template with hostname: {sting_hostname}, port: {frontend_port}")
                else:
                    # For non-template files (full/minimal), replace localhost with actual domain
                    if self.sting_domain != 'localhost':
                        content = content.replace('localhost', self.sting_domain)
                        logger.info(f"Replaced localhost with {self.sting_domain} in Kratos config")

                # Update os.environ with generated env vars so template substitution works
                for key, value in self.processed_config.items():
                    if value and isinstance(value, str):
                        os.environ[key] = value
                
                # Ensure critical kratos template vars are in os.environ
                if self.service_api_key:
                    os.environ['KRATOS_WEBHOOK_TOKEN'] = self._clean_value(self.service_api_key)
                else:
                    logger.warning("service_api_key not available — KRATOS_WEBHOOK_TOKEN will be empty")

                # Substitute all environment variables in template content
                # This handles ${VAR} patterns like ${SMTP_CONNECTION_URI}
                def substitute_env_vars(match):
                    var_name = match.group(1)
                    default_value = ''
                    if ':-' in var_name:
                        var_name, default_value = var_name.split(':-', 1)
                    return os.environ.get(var_name, default_value)
                content = re.sub(r'\$\{([^}:]+)(?::-[^}]*)?\}', substitute_env_vars, content)

                # Write to destination
                with open(kratos_path, 'w') as dest:
                    dest.write(content)

                os.chmod(kratos_path, 0o644)
                logger.info(f"Copied Kratos {template_type} config from {template_path} to {kratos_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to copy Kratos template: {e}")
                # Fall back to generating config
        else:
            logger.warning(f"No Kratos template found at {template_path}, falling back to generated config")
            return False
        
        # Fallback: Generate a simple config that uses environment variables
        kratos_config = {
            'version': 'v0.8.2-alpha.1',
            'dsn': '${DSN}',
            'log': {
                'level': 'info'
            },
            'serve': {
                'public': {
                    'base_url': '${KRATOS_PUBLIC_URL}',
                    'cors': {
                        'enabled': True,
                        'allowed_origins': [
                            'http://localhost:8443',
                            'https://localhost:8443'
                        ],
                        'allowed_methods': [
                            'GET',
                            'POST',
                            'OPTIONS'
                        ],
                        'allowed_headers': ['*'],
                        'allow_credentials': True
                    }
                },
                'admin': {
                    'base_url': '${KRATOS_ADMIN_URL}'
                }
            },
            'identity': {
                'schemas': [{
                    'id': 'default',
                    'url': '${IDENTITY_DEFAULT_SCHEMA_URL}'
                }]
            },
            'selfservice': {
                'default_browser_return_url': '${DEFAULT_RETURN_URL}',
                'flows': {
                    'login': {
                        'ui_url': '${LOGIN_UI_URL}',
                        'lifespan': '${LOGIN_LIFESPAN}'
                    },
                    'registration': {
                        'ui_url': '${REGISTRATION_UI_URL}',
                        'lifespan': '${REGISTRATION_LIFESPAN}'
                    }
                },
                'methods': {
                    'password': {
                        'enabled': True
                    },
                    'webauthn': {
                        'enabled': True,
                        'config': {
                            'rp': {
                                'id': '${WEBAUTHN_RP_ID}',
                                'display_name': '${WEBAUTHN_RP_DISPLAY_NAME}',
                                'origin': '${WEBAUTHN_RP_ORIGIN}'
                            }
                        }
                    }
                }
            },
            'courier': {
                'smtp': {
                    'connection_uri': '${SMTP_CONNECTION_URI}'
                }
            }
        }
        kratos_path = os.path.join(kratos_conf_dir, 'kratos.yml')
        try:
            # Substitute environment variables in the config dict
            def substitute_value(val):
                if isinstance(val, str):
                    def replace_var(match):
                        var_name = match.group(1)
                        default_value = ''
                        if ':-' in var_name:
                            var_name, default_value = var_name.split(':-', 1)
                        return os.environ.get(var_name, default_value)
                    return re.sub(r'\$\{([^}:]+)(?::-[^}]*)?\}', replace_var, val)
                return val

            def substitute_recursive(obj):
                if isinstance(obj, dict):
                    return {k: substitute_recursive(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [substitute_recursive(item) for item in obj]
                else:
                    return substitute_value(obj)

            kratos_config = substitute_recursive(kratos_config)

            # Dump YAML for Kratos
            with open(kratos_path, 'w') as f:
                yaml.safe_dump(kratos_config, f)
            os.chmod(kratos_path, 0o644)
            logger.info(f"Generated Kratos config at {kratos_path}")
        except Exception as e:
            logger.error(f"Failed to generate Kratos config: {e}")

    def _generate_searxng_config(self):
        """Generate SearXNG settings.yml with Brave Search API key from config.

        The SearXNG settings template in the repo uses a __BRAVE_SEARCH_API_KEY__
        placeholder. This method reads the key from config.yml (under
        llm_service.external_ai.web_search.brave_search_api_key or
        ai.external_ai.web_search.brave_search_api_key) and writes the
        resolved settings.yml to ${INSTALL_DIR}/searxng/.
        """
        searxng_dir = os.path.join(self.install_dir, 'searxng')
        settings_path = os.path.join(searxng_dir, 'settings.yml')
        template_path = os.path.join(searxng_dir, 'settings.yml')

        # Read API key from config — support both config structures
        web_search = (
            self.raw_config.get('llm_service', {}).get('external_ai', {}).get('web_search', {}) or
            self.raw_config.get('ai', {}).get('external_ai', {}).get('web_search', {})
        )
        brave_api_key = web_search.get('brave_search_api_key', '') or ''

        if not os.path.exists(template_path):
            logger.debug("SearXNG settings.yml not found — skipping generation")
            return

        try:
            with open(template_path, 'r') as f:
                content = f.read()

            # Only write if the placeholder is present (avoid re-processing already-resolved files)
            if '__BRAVE_SEARCH_API_KEY__' in content:
                content = content.replace('__BRAVE_SEARCH_API_KEY__', brave_api_key)

                # If no API key provided, disable braveapi engine to avoid errors
                if not brave_api_key:
                    content = content.replace(
                        "    disabled: false\n    weight: 2.5\n    results_per_page: 10",
                        "    disabled: true  # No API key configured — enable by setting brave_search_api_key in config.yml\n    weight: 2.5\n    results_per_page: 10",
                    )
                    logger.warning(
                        "No Brave Search API key configured. braveapi engine disabled in SearXNG. "
                        "Get a free key at https://brave.com/search/api/ and set "
                        "llm_service.external_ai.web_search.brave_search_api_key in config.yml"
                    )

                with open(settings_path, 'w') as f:
                    f.write(content)
                os.chmod(settings_path, 0o644)
                logger.info(f"Generated SearXNG config at {settings_path} (brave_api_key={'configured' if brave_api_key else 'empty'})")
            else:
                logger.debug("SearXNG settings.yml has no placeholder — already resolved or manually configured")
        except Exception as e:
            logger.error(f"Failed to generate SearXNG config: {e}")
        """Refresh Vault token if needed"""
        if self.client and self.client.is_authenticated():
            try:
                self.client.auth.token.renew_self()
                return True
            except Exception:
                return False
        return False

    def generate_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Generate service-specific configurations."""
        if not self.processed_config:
            self.process_config()
        
        return {
            'supertokens': {
                'environment': {
                    'POSTGRESQL_CONNECTION_URI': self.processed_config['DATABASE_URL'],
                    'API_KEY': self.processed_config['ST_API_KEY'],
                    'DASHBOARD_API_KEY': self.processed_config.get('ST_DASHBOARD_API_KEY', ''),
                }
            },
            'app': {
                'environment': {
                    'APP_ENV': self.processed_config['APP_ENV'],
                    'FLASK_DEBUG': str(self.processed_config['APP_DEBUG']).lower(),
                    'DATABASE_URL': self.processed_config['DATABASE_URL'],
                    'ST_API_KEY': self.processed_config['ST_API_KEY'],
                }
            },
            'frontend': {
                'environment': {
                    'NODE_ENV': self.processed_config['APP_ENV'],
                    'REACT_APP_API_URL': self.processed_config['REACT_APP_API_URL'],
                    'REACT_APP_SUPERTOKENS_URL': self.processed_config['REACT_APP_SUPERTOKENS_URL'],
                }
            }
        }


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='STING Configuration Manager')
    parser.add_argument('config_file', help='Path to configuration YAML file')
    parser.add_argument('--env-file', help='Path to output .env file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--mode', default=os.getenv('INIT_MODE', 'runtime'),
                       choices=['runtime', 'build', 'reinstall', 'initialize', 'bootstrap'],
                       help='Configuration initialization mode')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        manager = ConfigurationManager(args.config_file, mode=args.mode)
        manager.process_config()
        manager.generate_env_file(args.env_file)
        logger.info("Configuration processing completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Configuration processing failed: {e}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1

if __name__ == '__main__':
    sys.exit(main())
    
