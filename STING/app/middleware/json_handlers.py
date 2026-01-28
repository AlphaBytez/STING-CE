# app/middleware/json_handlers.py
from datetime import timedelta
from flask.json.provider import DefaultJSONProvider
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class ConfigJSONProvider(DefaultJSONProvider):
    """Custom JSON provider for configuration objects"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, timedelta):
            # Convert timedelta to seconds for serialization
            return f"{obj.total_seconds()}s"
            
        # For any other type, try the parent class's default method
        return super().default(obj)

def init_json_provider(app):
        """Initialize custom JSON provider for the Flask app"""
        app.json_provider_class = ConfigJSONProvider
        app.json = ConfigJSONProvider(app)

def sanitize_config_for_debug(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize configuration for debug output
    Removes sensitive data and ensures all values are serializable
    """
    SENSITIVE_KEYS = {
        'SECRET', 'KEY', 'PASSWORD', 'TOKEN', 'CREDENTIAL',
        'PRIVATE', 'AUTH', 'SIGN', 'CERT'
    }
    
    def is_sensitive(key: str) -> bool:
        return any(sensitive in key.upper() for sensitive in SENSITIVE_KEYS)

    def sanitize_value(key: str, value: Any) -> Any:
        if is_sensitive(key):
            return "[REDACTED]"
        
        if isinstance(value, dict):
            return {k: sanitize_value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [sanitize_value(key, item) for item in value]
        if isinstance(value, timedelta):
            return str(value.total_seconds()) + "s"
        
        return value

    


    return {
        key: sanitize_value(key, value)
        for key, value in config.items()
    }
    
    