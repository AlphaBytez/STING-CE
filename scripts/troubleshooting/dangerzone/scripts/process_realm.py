#!/usr/bin/env python3
import json
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_realm_template(template_path, output_path):
    try:
        # Read template
        logger.info(f"Reading realm template from {template_path}")
        with open(template_path, 'r') as f:
            realm_config = json.load(f)
        
        # Get environment variables
        admin_password = os.environ.get('KC_BOOTSTRAP_ADMIN_PASSWORD')
        client_secret = os.environ.get('KEYCLOAK_CLIENT_SECRET')
        if not client_secret:
            logger.warning("KEYCLOAK_CLIENT_SECRET is not set. Generating a random secret.")
            client_secret = os.urandom(32).hex()
            logger.info(f"Generated client secret: {client_secret}")
        app_env = os.environ.get('APP_ENV', 'development')
        
        if not admin_password:
            logger.error("Required environment variables are not set")
            logger.error(f"KC_BOOTSTRAP_ADMIN_PASSWORD: {'SET' if admin_password else 'NOT SET'}")
            raise ValueError("Missing required environment variables")
        
        # Set environment-specific configurations
        if app_env.lower() == 'production':
            realm_config['sslRequired'] = 'external'
            realm_config['clients'][0]['redirectUris'] = [
                "https://*.your-domain.com/*"  # Update with your production domains
            ]
            realm_config['clients'][0]['webOrigins'] = [
                "https://*.your-domain.com"
            ]
        else:
            realm_config['sslRequired'] = 'none'
            realm_config['clients'][0]['redirectUris'] = [
                "http://localhost:3000/*",
                "http://localhost:3001/*",
                "http://localhost:3000",
                "http://localhost:3001"
            ]
            realm_config['clients'][0]['webOrigins'] = [
                "http://localhost:3000",
                "http://localhost:3001",
                "+"
            ]
            
        logger.info(f"Configured realm for {app_env} environment")
            
        # Update users
        users_updated = False
        for user in realm_config.get('users', []):
            if user['username'] == 'admin':
                for cred in user.get('credentials', []):
                    if cred['type'] == 'password':
                        cred['value'] = admin_password
                        users_updated = True
                        logger.info("Updated admin password in realm configuration")
        
        if not users_updated:
            logger.warning("No admin user found in realm configuration to update")
        
        # Update clients
        clients_updated = False
        for client in realm_config.get('clients', []):
            if client['clientId'] == 'sting-auth':
                client['secret'] = client_secret
                clients_updated = True
                logger.info("Updated client secret in realm configuration")
        
        if not clients_updated:
            logger.warning("No sting-auth client found in realm configuration to update")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Write processed config
        logger.info(f"Writing processed realm configuration to {output_path}")
        with open(output_path, 'w') as f:
            json.dump(realm_config, f, indent=2)
        
        logger.info("Realm configuration processing completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error processing realm template: {str(e)}")
        raise

if __name__ == '__main__':
    template_path = '/opt/keycloak/realm-template.json'
    output_path = '/opt/keycloak/data/import/realm-export.json'
    
    logger.info("Starting realm configuration processing")
    try:
        process_realm_template(template_path, output_path)
        logger.info("Realm template processing completed successfully")
    except Exception as e:
        logger.error(f"Failed to process realm template: {str(e)}")
        exit(1)