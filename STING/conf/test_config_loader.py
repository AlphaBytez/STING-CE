import unittest
import os
import tempfile
from config_loader import load_config, validate_config, substitute_env_variables, ConfigurationError, sanitize_key, sanitize_path

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_load_config_yaml(self):
        config_content = """
        APP_PORT: 5000
        FLASK_DEBUG: true
        """
        config_path = os.path.join(self.temp_dir, 'config.yml')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        config = load_config(config_path)
        self.assertEqual(config['APP_PORT'], 5000)
        self.assertEqual(config['FLASK_DEBUG'], 'true')

    def test_load_config_json(self):
        config_content = """
        {
            "APP_PORT": 5000,
            "FLASK_DEBUG": "true"
        }
        """
        config_path = os.path.join(self.temp_dir, 'config.json')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        config = load_config(config_path)
        self.assertEqual(config['APP_PORT'], 5000)
        self.assertEqual(config['FLASK_DEBUG'], 'true')

    def test_load_config_file_not_found(self):
        with self.assertRaises(ConfigurationError):
            load_config('non_existent_file.yml')

    def test_validate_config(self):
        valid_config = {
            'APP_PORT': 5000,
            'FLASK_DEBUG': 'true',
            'FLASK_APP': 'app.py',
            'APP_ENV': 'development',
            'REACT_PORT': 8443,
            'APP_HOST': 'localhost',
            'POSTGRES_USER': 'user',
            'POSTGRES_PASSWORD': 'password',
            'DB_PORT': 5432,
            'KEYCLOAK_USER': 'admin',
            'KC_BOOTSTRAP_ADMIN_PASSWORD': 'password',
            'KC_DB': 'postgres',
            'KC_DB_URL': 'jdbc:postgresql://localhost:5432/keycloak',
            'KC_DB_USERNAME': 'keycloak',
            'KC_DB_PASSWORD': 'password',
            'KC_HEALTH_ENABLED': 'true',
            'KC_METRICS_ENABLED': 'true',
            'KC_BOOTSTRAP_ADMIN_USERNAME': 'admin',
            'KC_BOOTSTRAP_ADMIN_PASSWORD': 'admin',
            'KEYCLOAK_HOSTNAME': 'localhost',
            'KEYCLOAK_PORT': 8080,
            'KEYCLOAK_SECRET': 'secret',
            'KEYSTORE_PASSWORD': 'password',
            'KEYCLOAK_REDIRECT_URI': 'http://localhost:8443',
            'KEYCLOAK_CLIENT_ID': 'client',
            'KEYCLOAK_REALM': 'realm',
            'KEYCLOAK_URL': 'http://localhost:8080',
            'NEXT_PUBLIC_KEYCLOAK_CLIENT_ID': 'client',
            'NEXT_PUBLIC_KEYCLOAK_REALM': 'realm',
            'NEXT_PUBLIC_KEYCLOAK_URL': 'http://localhost:8080',
            'NEXT_PUBLIC_KEYCLOAK_REDIRECT_URI': 'http://localhost:8443',
            'LOG_MAX_SIZE': 1,
            'BACKUP_DEFAULT_DIRECTORY': '/backups',
            'BACKUP_COMPRESSION_LEVEL': 5,
            'BACKUP_RETENTION_COUNT': 5,
            'BACKUP_EXCLUDE_PATTERNS': '*.tmp,*.log'
        }
        
        try:
            validate_config(valid_config)
        except ConfigurationError:
            self.fail("validate_config() raised ConfigurationError unexpectedly!")

    def test_validate_config_missing_required(self):
        invalid_config = {
            'APP_PORT': 5000  # Missing many required fields
        }
        with self.assertRaises(ConfigurationError):
            validate_config(invalid_config)

    def test_validate_config_wrong_type(self):
        invalid_config = {
            'APP_PORT': '5000',  # Should be an integer
            'FLASK_DEBUG': 'true',  # Should be a boolean
            # ... other required fields ...
        }
        with self.assertRaises(ConfigurationError):
            validate_config(invalid_config)

    def test_substitute_env_variables(self):
        os.environ['TEST_VAR'] = 'test_value'
        config = {
            'TEST_KEY': '${TEST_VAR}',
            'NESTED': {
                'TEST_KEY': '${TEST_VAR}'
            }
        }
        substituted_config = substitute_env_variables(config)
        self.assertEqual(substituted_config['TEST_KEY'], 'test_value')
        self.assertEqual(substituted_config['NESTED']['TEST_KEY'], 'test_value')

    def test_sanitize_key(self):
        self.assertEqual(sanitize_key('VALID_KEY'), 'VALID_KEY')
        self.assertEqual(sanitize_key('invalid-key!'), 'invalidkey')

    def test_sanitize_path(self):
        self.assertEqual(sanitize_path('/valid/path'), '/valid/path')
        self.assertEqual(sanitize_path('../invalid/path'), 'invalid/path')

if __name__ == '__main__':
    unittest.main()