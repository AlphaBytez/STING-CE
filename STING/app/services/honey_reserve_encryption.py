"""
Honey Reserve Encryption Service for STING-CE
Provides file encryption/decryption using Kratos-derived user keys.
"""

import os
import logging
import secrets
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import hashlib
import base64
import json

from app.utils.kratos_client import whoami

logger = logging.getLogger(__name__)

@dataclass
class EncryptedFile:
    """Represents an encrypted file with metadata."""
    encrypted_data: bytes
    encrypted_file_key: bytes
    file_hash: str
    encryption_metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class UserEncryptionContext:
    """User-specific encryption context derived from Kratos identity."""
    user_id: str
    derived_key: bytes
    key_salt: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None

class HoneyReserveEncryptionError(Exception):
    """Custom exception for encryption service errors."""
    pass

class HoneyReserveEncryption:
    """
    File encryption service that uses Kratos user identities for key derivation.
    
    Key Hierarchy:
    1. Master key (from environment/vault)
    2. User-derived key (HKDF from user ID + master key)
    3. File-specific key (random 256-bit AES key)
    4. Encrypted file key (file key encrypted with user key)
    """
    
    def _decode_base64_key(self, key_b64: str) -> bytes:
        """
        Decode base64 master key. Only accepts standard base64 format.
        
        Args:
            key_b64: Base64 encoded key string (standard format only)
            
        Returns:
            bytes: Decoded key
            
        Raises:
            ValueError: If decoding fails or key is wrong format
        """
        # Remove any whitespace
        key_b64 = key_b64.strip()
        
        try:
            # Only accept standard base64 format
            return base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 master key format. Expected standard base64 encoding. Error: {e}")
    
    def __init__(self):
        self.master_key = self._get_master_key()
        self.key_cache = {}  # Cache user keys for performance
        self.cache_ttl = timedelta(hours=1)  # Cache keys for 1 hour
        
    def _get_master_key(self) -> bytes:
        """Get the master encryption key from environment. Fails if not properly configured."""
        master_key_b64 = os.environ.get('HONEY_RESERVE_MASTER_KEY')
        
        if not master_key_b64:
            raise HoneyReserveEncryptionError(
                "HONEY_RESERVE_MASTER_KEY environment variable not set. "
                "This is required for encryption services."
            )
        
        try:
            master_key = self._decode_base64_key(master_key_b64)
            if len(master_key) != 32:
                raise ValueError("Master key must be 32 bytes (256 bits)")
            return master_key
        except Exception as e:
            raise HoneyReserveEncryptionError(
                f"Invalid HONEY_RESERVE_MASTER_KEY: {e}. "
                "Key must be a valid 32-byte base64-encoded string."
            )
    
    
    def _derive_user_key(self, user_id: str) -> Tuple[bytes, bytes]:
        """
        Derive a user-specific encryption key using HKDF.
        
        Args:
            user_id: Kratos user identity ID
            
        Returns:
            Tuple of (derived_key, salt)
        """
        # Use user ID as salt for deterministic key derivation
        salt = hashlib.sha256(user_id.encode('utf-8')).digest()
        
        # Derive 256-bit key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b'STING-CE-Honey-Reserve-v1',
            backend=default_backend()
        )
        
        derived_key = hkdf.derive(self.master_key)
        return derived_key, salt
    
    def get_user_encryption_context(self, user_id: str) -> UserEncryptionContext:
        """
        Get or create user encryption context with caching.
        
        Args:
            user_id: Kratos user identity ID
            
        Returns:
            UserEncryptionContext with derived key
        """
        # Check cache first
        if user_id in self.key_cache:
            context = self.key_cache[user_id]
            if context.expires_at and datetime.utcnow() < context.expires_at:
                return context
            else:
                # Cache expired, remove it
                del self.key_cache[user_id]
        
        # Derive new key
        derived_key, salt = self._derive_user_key(user_id)
        
        # Create context
        context = UserEncryptionContext(
            user_id=user_id,
            derived_key=derived_key,
            key_salt=salt,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + self.cache_ttl
        )
        
        # Cache for performance
        self.key_cache[user_id] = context
        
        logger.debug(f"Created encryption context for user {user_id}")
        return context
    
    def encrypt_file(self, file_data: bytes, user_id: str, metadata: Dict[str, Any] = None) -> EncryptedFile:
        """
        Encrypt a file for a specific user.
        
        Args:
            file_data: Raw file data to encrypt
            user_id: Kratos user identity ID
            metadata: Optional metadata to include
            
        Returns:
            EncryptedFile with encrypted data and keys
        """
        try:
            # Get user encryption context
            user_context = self.get_user_encryption_context(user_id)
            
            # Generate file-specific AES key
            file_key = secrets.token_bytes(32)  # 256-bit key
            
            # Create AEAD cipher for file encryption
            file_cipher = AESGCM(file_key)
            
            # Generate nonce for file encryption
            file_nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            
            # Encrypt file data
            encrypted_data = file_cipher.encrypt(file_nonce, file_data, None)
            
            # Combine nonce + encrypted data for storage
            file_encrypted_blob = file_nonce + encrypted_data
            
            # Encrypt file key with user's derived key
            user_cipher = AESGCM(user_context.derived_key)
            key_nonce = secrets.token_bytes(12)
            encrypted_file_key = user_cipher.encrypt(key_nonce, file_key, None)
            
            # Combine nonce + encrypted key for storage
            key_encrypted_blob = key_nonce + encrypted_file_key
            
            # Calculate file hash for integrity
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Create encryption metadata
            encryption_metadata = {
                'algorithm': 'AES-256-GCM',
                'key_derivation': 'HKDF-SHA256',
                'version': '1.0',
                'user_id': user_id,
                'file_size': len(file_data),
                'encrypted_size': len(file_encrypted_blob)
            }
            
            if metadata:
                encryption_metadata['user_metadata'] = metadata
            
            result = EncryptedFile(
                encrypted_data=file_encrypted_blob,
                encrypted_file_key=key_encrypted_blob,
                file_hash=file_hash,
                encryption_metadata=encryption_metadata,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"Successfully encrypted file for user {user_id}, size: {len(file_data)} -> {len(file_encrypted_blob)} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to encrypt file for user {user_id}: {e}")
            raise HoneyReserveEncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_file(self, encrypted_file: EncryptedFile, user_id: str) -> bytes:
        """
        Decrypt a file for a specific user.
        
        Args:
            encrypted_file: EncryptedFile object
            user_id: Kratos user identity ID
            
        Returns:
            Decrypted file data as bytes
        """
        try:
            # Verify user owns this file
            if encrypted_file.encryption_metadata.get('user_id') != user_id:
                raise HoneyReserveEncryptionError("User does not have access to this file")
            
            # Get user encryption context
            user_context = self.get_user_encryption_context(user_id)
            
            # Extract nonce and encrypted key
            key_nonce = encrypted_file.encrypted_file_key[:12]
            encrypted_key_data = encrypted_file.encrypted_file_key[12:]
            
            # Decrypt file key using user's derived key
            user_cipher = AESGCM(user_context.derived_key)
            file_key = user_cipher.decrypt(key_nonce, encrypted_key_data, None)
            
            # Extract nonce and encrypted file data
            file_nonce = encrypted_file.encrypted_data[:12]
            encrypted_file_data = encrypted_file.encrypted_data[12:]
            
            # Decrypt file data using file key
            file_cipher = AESGCM(file_key)
            decrypted_data = file_cipher.decrypt(file_nonce, encrypted_file_data, None)
            
            # Verify file integrity
            computed_hash = hashlib.sha256(decrypted_data).hexdigest()
            if computed_hash != encrypted_file.file_hash:
                raise HoneyReserveEncryptionError("File integrity check failed")
            
            logger.info(f"Successfully decrypted file for user {user_id}, size: {len(decrypted_data)} bytes")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt file for user {user_id}: {e}")
            raise HoneyReserveEncryptionError(f"Decryption failed: {str(e)}")
    
    def serialize_encrypted_file(self, encrypted_file: EncryptedFile) -> Dict[str, Any]:
        """
        Serialize EncryptedFile to a dictionary for storage.
        
        Args:
            encrypted_file: EncryptedFile object
            
        Returns:
            Dictionary representation for database storage
        """
        return {
            'encrypted_data': base64.b64encode(encrypted_file.encrypted_data).decode('utf-8'),
            'encrypted_file_key': base64.b64encode(encrypted_file.encrypted_file_key).decode('utf-8'),
            'file_hash': encrypted_file.file_hash,
            'encryption_metadata': json.dumps(encrypted_file.encryption_metadata),
            'created_at': encrypted_file.created_at.isoformat()
        }
    
    def deserialize_encrypted_file(self, data: Dict[str, Any]) -> EncryptedFile:
        """
        Deserialize dictionary to EncryptedFile object.
        
        Args:
            data: Dictionary from database
            
        Returns:
            EncryptedFile object
        """
        try:
            return EncryptedFile(
                encrypted_data=base64.b64decode(data['encrypted_data']),
                encrypted_file_key=base64.b64decode(data['encrypted_file_key']),
                file_hash=data['file_hash'],
                encryption_metadata=json.loads(data['encryption_metadata']),
                created_at=datetime.fromisoformat(data['created_at'])
            )
        except Exception as e:
            raise HoneyReserveEncryptionError(f"Failed to deserialize encrypted file: {e}")
    
    def validate_user_access(self, session_cookie: str) -> Optional[str]:
        """
        Validate user session and return user ID.
        
        Args:
            session_cookie: Kratos session cookie
            
        Returns:
            User ID if valid, None otherwise
        """
        try:
            identity = whoami(session_cookie)
            if not identity:
                return None
            
            user_id = identity.get('identity', {}).get('id')
            if not user_id:
                logger.warning("No user ID found in Kratos identity")
                return None
            
            return user_id
            
        except Exception as e:
            logger.warning(f"Failed to validate user session: {e}")
            return None
    
    def rotate_user_key(self, user_id: str) -> bool:
        """
        Rotate a user's encryption key by clearing the cache.
        This forces re-derivation on next access.
        
        Args:
            user_id: User ID to rotate key for
            
        Returns:
            True if successful
        """
        try:
            if user_id in self.key_cache:
                del self.key_cache[user_id]
                logger.info(f"Rotated encryption key for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate key for user {user_id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear all cached user keys."""
        self.key_cache.clear()
        logger.info("Cleared encryption key cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get encryption service statistics."""
        active_keys = 0
        expired_keys = 0
        
        for context in self.key_cache.values():
            if context.expires_at and datetime.utcnow() < context.expires_at:
                active_keys += 1
            else:
                expired_keys += 1
        
        return {
            'active_keys': active_keys,
            'expired_keys': expired_keys,
            'total_cached': len(self.key_cache),
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600
        }

# Global encryption service instance
_encryption_service = None

def get_encryption_service() -> HoneyReserveEncryption:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = HoneyReserveEncryption()
    return _encryption_service