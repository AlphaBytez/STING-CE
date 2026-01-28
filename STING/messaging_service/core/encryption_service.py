import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    """Handles message encryption and decryption"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('encryption_enabled', True)
        self._master_key = self._get_master_key()
        self._user_keys = {}
    
    def _get_master_key(self) -> bytes:
        """Get or create master encryption key"""
        # In production, this should come from a secure key management service
        key_seed = self.config.get('encryption_key_seed', 'messaging-service-key')
        salt = b'sting-messaging-salt'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.b64encode(kdf.derive(key_seed.encode()))
        return key
    
    def _get_user_key(self, user_id: str) -> bytes:
        """Get or create user-specific encryption key"""
        if user_id not in self._user_keys:
            salt = f"user-{user_id}".encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.b64encode(
                kdf.derive(self._master_key + user_id.encode())
            )
            self._user_keys[user_id] = key
        
        return self._user_keys[user_id]
    
    async def encrypt_message(
        self,
        content: str,
        sender_id: str,
        recipient_id: str
    ) -> str:
        """Encrypt a message"""
        if not self.enabled:
            return content
        
        try:
            # Use recipient's key for encryption
            key = self._get_user_key(recipient_id)
            f = Fernet(key)
            
            encrypted = f.encrypt(content.encode())
            return base64.b64encode(encrypted).decode()
        
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    async def decrypt_message(
        self,
        encrypted_content: str,
        recipient_id: str
    ) -> str:
        """Decrypt a message"""
        if not self.enabled:
            return encrypted_content
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_content)
            
            # Use recipient's key for decryption
            key = self._get_user_key(recipient_id)
            f = Fernet(key)
            
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def is_healthy(self) -> bool:
        """Health check"""
        try:
            # Test encryption/decryption
            test_msg = "health check"
            encrypted = Fernet(self._master_key).encrypt(test_msg.encode())
            decrypted = Fernet(self._master_key).decrypt(encrypted).decode()
            return decrypted == test_msg
        except:
            return False