"""
Vault File Client for secure file storage and retrieval.
Handles file operations with HashiCorp Vault for sensitive user files.
"""

import os
import sys
import base64
import hashlib
import logging
from typing import Optional, Dict, Any, BinaryIO, List
from pathlib import Path
import hvac

# Add project root to Python path to import conf modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from conf.vault_manager import VaultManager, VaultError

logger = logging.getLogger(__name__)

class VaultFileClient:
    """Client for storing and retrieving files in HashiCorp Vault."""
    
    def __init__(self, mount_point: str = "sting"):
        """
        Initialize Vault file client.
        
        Args:
            mount_point: Vault mount point for file storage
        """
        self.vault_manager = VaultManager(mount_point=mount_point)
        self.mount_point = mount_point
        self._ensure_mount_point()
    
    def _ensure_mount_point(self):
        """Ensure the file storage mount point exists."""
        try:
            mounted_engines = self.vault_manager.client.sys.list_mounted_secrets_engines()
            if f"{self.mount_point}/" not in mounted_engines:
                self.vault_manager.client.sys.enable_secrets_engine(
                    backend_type='kv',
                    path=self.mount_point,
                    options={'version': 2}
                )
                logger.info(f"Created file storage mount point: {self.mount_point}")
        except Exception as e:
            logger.error(f"Failed to ensure mount point {self.mount_point}: {e}")
            raise VaultError(f"Mount point setup failed: {e}")
    
    def store_file(self, file_id: str, file_data: bytes, metadata: Dict[str, Any] = None) -> bool:
        """
        Store a file in Vault.
        
        Args:
            file_id: Unique identifier for the file
            file_data: Binary file data
            metadata: Optional metadata dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Encode file data as base64 for JSON storage
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            # Calculate file hash for integrity
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Prepare secret data
            secret_data = {
                'data': encoded_data,
                'hash': file_hash,
                'size': len(file_data),
                'metadata': metadata or {}
            }
            
            # Store in Vault
            path = f"files/{file_id}"
            success = self.vault_manager.write_secret(path, secret_data)
            
            if success:
                logger.info(f"Successfully stored file {file_id} in Vault")
            else:
                logger.error(f"Failed to store file {file_id} in Vault")
                
            return success
            
        except Exception as e:
            logger.error(f"Error storing file {file_id}: {e}")
            return False
    
    def retrieve_file(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a file from Vault using storage path.

        Args:
            storage_path: Vault storage path (can be simple file_id or complex path)

        Returns:
            Dict containing file data and metadata, or None if not found
        """
        try:
            # Handle both simple file IDs and complex storage paths
            if '/' in storage_path:
                # Complex path: use as-is with files/ prefix
                path = f"files/{storage_path}"
            else:
                # Simple file ID: use legacy format
                path = f"files/{storage_path}"
            secret_data = self.vault_manager.read_secret(path)
            
            if not secret_data:
                logger.warning(f"File {storage_path} not found in Vault at path: {path}")
                return None
            
            # Decode file data
            encoded_data = secret_data.get('data')
            if not encoded_data:
                logger.error(f"No data found for file {file_id}")
                return None
            
            file_data = base64.b64decode(encoded_data.encode('utf-8'))
            
            # Verify file integrity
            stored_hash = secret_data.get('hash')
            calculated_hash = hashlib.sha256(file_data).hexdigest()
            
            if stored_hash != calculated_hash:
                logger.error(f"File integrity check failed for {file_id}")
                return None
            
            return {
                'data': file_data,
                'size': secret_data.get('size', len(file_data)),
                'hash': stored_hash,
                'metadata': secret_data.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error retrieving file {file_id}: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Vault.
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            bool: True if successful
        """
        try:
            path = f"files/{file_id}"
            
            # Use Vault's delete operation
            self.vault_manager.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point
            )
            
            logger.info(f"Successfully deleted file {file_id} from Vault")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def file_exists(self, file_id: str) -> bool:
        """
        Check if a file exists in Vault.
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            bool: True if file exists
        """
        try:
            path = f"files/{file_id}"
            secret_data = self.vault_manager.read_secret(path)
            return secret_data is not None
            
        except Exception as e:
            logger.error(f"Error checking file existence {file_id}: {e}")
            return False
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata without retrieving the actual file data.
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Dict containing metadata, or None if not found
        """
        try:
            path = f"files/{file_id}"
            secret_data = self.vault_manager.read_secret(path)
            
            if not secret_data:
                return None
            
            return {
                'size': secret_data.get('size'),
                'hash': secret_data.get('hash'),
                'metadata': secret_data.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting metadata for file {file_id}: {e}")
            return None
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file IDs
        """
        try:
            # List all files in the mount point
            path = "files/"
            if prefix:
                path += prefix
            
            response = self.vault_manager.client.secrets.kv.v2.list_secrets(
                path="files",
                mount_point=self.mount_point
            )
            
            keys = response.get('data', {}).get('keys', [])
            
            if prefix:
                keys = [k for k in keys if k.startswith(prefix)]
            
            return keys
            
        except Exception as e:
            logger.error(f"Error listing files with prefix '{prefix}': {e}")
            return []

class FileUploadHandler:
    """Helper class for handling file uploads with validation."""
    
    # File type configurations
    FILE_TYPE_CONFIGS = {
        'profile_picture': {
            'max_size': 5 * 1024 * 1024,  # 5MB
            'allowed_types': ['image/jpeg', 'image/png', 'image/webp'],
            'allowed_extensions': ['.jpg', '.jpeg', '.png', '.webp']
        },
        'user_document': {
            'max_size': 50 * 1024 * 1024,  # 50MB
            'allowed_types': ['application/pdf', 'text/plain', 'image/jpeg', 'image/png'],
            'allowed_extensions': ['.pdf', '.txt', '.jpg', '.jpeg', '.png']
        },
        'report': {
            'max_size': 100 * 1024 * 1024,  # 100MB for reports
            'allowed_types': ['application/pdf', 'text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/json'],
            'allowed_extensions': ['.pdf', '.csv', '.xlsx', '.json']
        }
    }
    
    def __init__(self, vault_client: VaultFileClient):
        self.vault_client = vault_client
    
    def validate_file(self, file_data: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Validate file before upload.
        
        Args:
            file_data: Binary file data
            filename: Original filename
            file_type: File type category (e.g., 'profile_picture')
            
        Returns:
            Dict with validation results
        """
        result = {'valid': True, 'errors': []}
        
        config = self.FILE_TYPE_CONFIGS.get(file_type)
        if not config:
            result['valid'] = False
            result['errors'].append(f"Unknown file type: {file_type}")
            return result
        
        # Check file size
        if len(file_data) > config['max_size']:
            result['valid'] = False
            result['errors'].append(f"File too large. Max size: {config['max_size']} bytes")
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in config['allowed_extensions']:
            result['valid'] = False
            result['errors'].append(f"Invalid file extension. Allowed: {config['allowed_extensions']}")
        
        # Basic file signature check (magic bytes)
        if not self._check_file_signature(file_data, file_ext):
            result['valid'] = False
            result['errors'].append("File signature doesn't match extension")
        
        return result
    
    def _check_file_signature(self, file_data: bytes, extension: str) -> bool:
        """Check file signature (magic bytes) matches extension."""
        if len(file_data) < 8:
            return False
        
        # Common file signatures
        signatures = {
            '.jpg': [b'\xff\xd8\xff'],
            '.jpeg': [b'\xff\xd8\xff'],
            '.png': [b'\x89\x50\x4e\x47'],
            '.webp': [b'RIFF', b'WEBP'],
            '.pdf': [b'%PDF'],
            '.txt': []  # Text files don't have a consistent signature
        }
        
        expected_sigs = signatures.get(extension, [])
        if not expected_sigs:
            return True  # Skip check for files without signatures
        
        for sig in expected_sigs:
            if file_data.startswith(sig):
                return True
        
        return False
    
    def upload_file(self, file_data: bytes, filename: str, file_type: str,
                   user_id: str, metadata: Dict[str, Any] = None, skip_validation: bool = False,
                   file_id: str = None) -> Dict[str, Any]:
        """
        Upload and store a file with validation.

        Args:
            file_data: Binary file data
            filename: Original filename
            file_type: File type category
            user_id: User ID for file ownership
            metadata: Additional metadata
            skip_validation: Skip file validation (for encrypted content)
            file_id: Pre-calculated file ID (optional, will be generated if not provided)

        Returns:
            Dict with upload results
        """
        # Validate file (unless skipped for encrypted content)
        if not skip_validation:
            validation = self.validate_file(file_data, filename, file_type)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
        
        # Use provided file_id or generate one
        if file_id is None:
            # Generate unique file ID
            file_hash = hashlib.sha256(file_data).hexdigest()
            file_id = f"{user_id}/{file_type}/{file_hash[:16]}"
        else:
            # Extract hash from the provided file_id for consistency
            file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Prepare metadata
        upload_metadata = {
            'original_filename': filename,
            'file_type': file_type,
            'user_id': user_id,
            'upload_timestamp': int(os.path.getmtime(__file__)),
            **(metadata or {})
        }
        
        # Store file
        success = self.vault_client.store_file(file_id, file_data, upload_metadata)
        
        if success:
            return {
                'success': True,
                'file_id': file_id,
                'size': len(file_data),
                'hash': file_hash
            }
        else:
            return {
                'success': False,
                'errors': ['Failed to store file in Vault']
            }