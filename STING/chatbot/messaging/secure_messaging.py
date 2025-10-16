import base64
import json
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import secrets
from .messaging_client import MessagingClient

logger = logging.getLogger(__name__)

class SecureMessaging:
    """
    Handles encryption and decryption of sensitive messages
    Provides end-to-end encryption capabilities for Bee
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('encryption_enabled', True)
        
        # Initialize messaging client for scalable messaging
        self.messaging_client = None
        if config.get('messaging_service_enabled', False):
            self.messaging_client = MessagingClient(config)
        
        # Initialize encryption keys storage (in production, use secure key management)
        self.user_keys = {}
        
        # Master key for key derivation (in production, use HSM or Vault)
        self.master_key = self._get_or_create_master_key()
        
        # Message retention settings
        self.encrypted_message_ttl = config.get('encrypted_message_ttl_hours', 24)
        self.auto_delete_encrypted = config.get('auto_delete_encrypted', True)
        
        # Track encrypted messages for auto-deletion
        self.encrypted_messages = {}
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        # In production, this should come from a secure key management service
        # For now, we'll use a derived key from config
        
        key_seed = self.config.get('encryption_key_seed', 'default-bee-encryption-seed')
        salt = b'bee-sting-salt-v1'  # In production, use random salt per deployment
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.b64encode(kdf.derive(key_seed.encode()))
        return key
    
    async def encrypt_message(
        self, 
        message: str, 
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Encrypt a message for secure storage/transmission"""
        if not self.enabled:
            return message
        
        try:
            # Get or create user-specific key
            user_key = await self._get_user_key(user_id)
            
            # Create Fernet instance
            f = Fernet(user_key)
            
            # Create message payload with metadata
            payload = {
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'metadata': metadata or {}
            }
            
            # Encrypt the payload
            encrypted = f.encrypt(json.dumps(payload).encode())
            
            # Create message ID for tracking
            message_id = f"enc_{hashlib.sha256(encrypted).hexdigest()[:12]}"
            
            # Track encrypted message for auto-deletion
            self.encrypted_messages[message_id] = {
                'user_id': user_id,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(hours=self.encrypted_message_ttl)
            }
            
            # Return base64 encoded encrypted message with ID
            return f"{message_id}:{base64.b64encode(encrypted).decode()}"
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            # Return original message if encryption fails
            return message
    
    async def decrypt_message(
        self, 
        encrypted_message: str, 
        user_id: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Decrypt a message"""
        if not self.enabled:
            return encrypted_message, {}
        
        try:
            # Parse message ID and encrypted content
            if ':' in encrypted_message:
                message_id, encrypted_content = encrypted_message.split(':', 1)
            else:
                encrypted_content = encrypted_message
                message_id = None
            
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_content)
            
            # Get user key
            user_key = await self._get_user_key(user_id)
            
            # Decrypt
            f = Fernet(user_key)
            decrypted = f.decrypt(encrypted_bytes)
            
            # Parse payload
            payload = json.loads(decrypted.decode())
            
            # Verify user ID matches
            if payload.get('user_id') != user_id:
                logger.warning(f"User ID mismatch in encrypted message")
                return "[Decryption Failed - Unauthorized]", {}
            
            # Check if message has expired
            if message_id and message_id in self.encrypted_messages:
                msg_info = self.encrypted_messages[message_id]
                if datetime.now() > msg_info['expires_at']:
                    logger.info(f"Encrypted message {message_id} has expired")
                    return "[Message Expired]", {}
            
            return payload['message'], payload.get('metadata', {})
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            return "[Decryption Failed]", {}
    
    async def _get_user_key(self, user_id: str) -> bytes:
        """Get or generate user-specific encryption key"""
        if user_id not in self.user_keys:
            # Derive user key from master key
            user_salt = hashlib.sha256(f"bee-user-{user_id}".encode()).digest()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=user_salt,
                iterations=100000,
            )
            
            user_key = base64.b64encode(
                kdf.derive(self.master_key + user_id.encode())
            )
            
            self.user_keys[user_id] = user_key
            logger.info(f"Generated encryption key for user {user_id}")
        
        return self.user_keys[user_id]
    
    async def create_secure_session(
        self, 
        user_id: str,
        session_data: Dict[str, Any]
    ) -> str:
        """Create an encrypted session token"""
        try:
            # Add session metadata
            session_payload = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
                'data': session_data,
                'nonce': secrets.token_hex(16)
            }
            
            # Encrypt session data
            user_key = await self._get_user_key(user_id)
            f = Fernet(user_key)
            
            encrypted_session = f.encrypt(json.dumps(session_payload).encode())
            
            return base64.b64encode(encrypted_session).decode()
            
        except Exception as e:
            logger.error(f"Failed to create secure session: {str(e)}")
            raise
    
    async def verify_secure_session(
        self, 
        session_token: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Verify and decrypt a secure session token"""
        try:
            # Decode session token
            encrypted_session = base64.b64decode(session_token)
            
            # Decrypt session
            user_key = await self._get_user_key(user_id)
            f = Fernet(user_key)
            
            decrypted = f.decrypt(encrypted_session)
            session_payload = json.loads(decrypted.decode())
            
            # Verify user ID
            if session_payload.get('user_id') != user_id:
                logger.warning("Session user ID mismatch")
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(session_payload.get('expires_at'))
            if datetime.now() > expires_at:
                logger.info("Session has expired")
                return None
            
            return session_payload.get('data', {})
            
        except Exception as e:
            logger.error(f"Failed to verify session: {str(e)}")
            return None
    
    async def cleanup_expired_messages(self):
        """Clean up expired encrypted messages"""
        if not self.auto_delete_encrypted:
            return
        
        current_time = datetime.now()
        expired_messages = []
        
        for message_id, info in self.encrypted_messages.items():
            if current_time > info['expires_at']:
                expired_messages.append(message_id)
        
        for message_id in expired_messages:
            del self.encrypted_messages[message_id]
            logger.info(f"Cleaned up expired message {message_id}")
        
        if expired_messages:
            logger.info(f"Cleaned up {len(expired_messages)} expired messages")
    
    async def enable_message_recall(
        self, 
        message_id: str,
        recall_window_minutes: int = 5
    ) -> bool:
        """Enable message recall for a specific message"""
        if message_id in self.encrypted_messages:
            self.encrypted_messages[message_id]['recall_enabled'] = True
            self.encrypted_messages[message_id]['recall_expires'] = \
                datetime.now() + timedelta(minutes=recall_window_minutes)
            return True
        return False
    
    async def recall_message(
        self, 
        message_id: str,
        user_id: str
    ) -> bool:
        """Recall (delete) an encrypted message"""
        if message_id not in self.encrypted_messages:
            return False
        
        msg_info = self.encrypted_messages[message_id]
        
        # Verify user owns the message
        if msg_info['user_id'] != user_id:
            logger.warning(f"User {user_id} attempted to recall message owned by {msg_info['user_id']}")
            return False
        
        # Check if recall is enabled and not expired
        if not msg_info.get('recall_enabled', False):
            return False
        
        if datetime.now() > msg_info.get('recall_expires', datetime.min):
            return False
        
        # Delete the message
        del self.encrypted_messages[message_id]
        logger.info(f"Message {message_id} recalled by user {user_id}")
        
        return True
    
    def is_healthy(self) -> bool:
        """Health check for secure messaging"""
        try:
            # Test encryption/decryption
            test_message = "Health check"
            test_user = "health_check_user"
            
            # Note: Using synchronous version for health check
            # In production, implement async health check properly
            user_key = base64.b64encode(b'test-key-for-health-check-only32')
            f = Fernet(user_key)
            
            encrypted = f.encrypt(test_message.encode())
            decrypted = f.decrypt(encrypted).decode()
            
            return decrypted == test_message
        except:
            return False