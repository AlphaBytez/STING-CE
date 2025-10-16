"""
File Service for STING-CE
Handles file operations, storage, and access control.
"""

import os
import logging
import hashlib
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.file_models import (
    FileAsset, FilePermission, FileUploadSession,
    StorageBackend, AccessLevel, PermissionType,
    get_file_by_id, get_user_files, check_file_permission
)
from app.utils.vault_file_client import VaultFileClient, FileUploadHandler
from app.database import get_db_session
from app.services.honey_reserve_encryption import get_encryption_service, HoneyReserveEncryptionError

logger = logging.getLogger(__name__)

class FileServiceError(Exception):
    """Custom exception for file service errors."""
    pass

class FileService:
    """Main file service for handling file operations."""
    
    def __init__(self):
        self.vault_client = VaultFileClient()
        self.upload_handler = FileUploadHandler(self.vault_client)
        self.encryption_service = get_encryption_service()
        
        # Check if encryption is enabled for Honey Reserve
        self.honey_reserve_encryption_enabled = os.environ.get('HONEY_RESERVE_ENCRYPT_AT_REST', 'true').lower() == 'true'
    
    def upload_file(self, file_data: bytes, filename: str, file_type: str,
                   user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Upload a file with validation and storage.
        
        Args:
            file_data: Binary file data
            filename: Original filename
            file_type: File type category
            user_id: User ID for ownership
            metadata: Additional metadata
            
        Returns:
            Dict with upload results
        """
        try:
            # Validate file first BEFORE encryption
            validation_result = self.upload_handler.validate_file(file_data, filename, file_type)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'errors': validation_result['errors']
                }

            # Calculate file hash early for use in database creation
            file_hash = hashlib.sha256(file_data).hexdigest()
            vault_file_id = f"{user_id}/{file_type}/{file_hash[:16]}"

            # Determine if file should be encrypted based on type and configuration
            should_encrypt = self._should_encrypt_file(file_type)

            # Prepare data for storage
            storage_data = file_data
            encryption_info = None

            if should_encrypt:
                try:
                    # Encrypt file using Honey Reserve encryption
                    encrypted_file = self.encryption_service.encrypt_file(
                        file_data, user_id, metadata
                    )

                    # Serialize encrypted file for storage
                    encryption_info = self.encryption_service.serialize_encrypted_file(encrypted_file)

                    # Store the serialized encryption data instead of raw file
                    import json
                    storage_data = json.dumps(encryption_info).encode('utf-8')

                    logger.info(f"Encrypted file {filename} for user {user_id}")

                except HoneyReserveEncryptionError as e:
                    logger.error(f"Failed to encrypt file {filename}: {e}")
                    return {
                        'success': False,
                        'errors': [f'Encryption failed: {str(e)}']
                    }

            # Upload file to Vault (either raw data or encrypted data)
            # Skip validation for encrypted content since we validate before encryption
            # Pass the vault_file_id to ensure consistent storage path
            upload_result = self.upload_handler.upload_file(
                storage_data, filename, file_type, user_id,
                metadata=metadata, skip_validation=should_encrypt, file_id=vault_file_id
            )
            
            if not upload_result['success']:
                return upload_result
            
            # Create database record
            with get_db_session() as session:
                # Add encryption metadata to file metadata
                file_metadata = metadata or {}
                if should_encrypt:
                    file_metadata['encrypted'] = True
                    file_metadata['encryption_version'] = '1.0'
                    file_metadata['encryption_algorithm'] = 'AES-256-GCM'
                else:
                    file_metadata['encrypted'] = False
                
                file_asset = FileAsset(
                    filename=filename,
                    original_filename=filename,
                    file_type=file_type,
                    file_size=len(file_data),  # Store original file size
                    checksum=file_hash,
                    storage_backend=StorageBackend.VAULT.value,
                    storage_path=vault_file_id,
                    owner_id=user_id,
                    access_level=AccessLevel.PRIVATE.value,
                    metadata=file_metadata
                )
                
                session.add(file_asset)
                session.commit()
                
                result = {
                    'success': True,
                    'file_id': str(file_asset.file_id),
                    'vault_file_id': vault_file_id,
                    'size': len(file_data),
                    'hash': file_hash,
                    'encrypted': should_encrypt
                }
                
                if should_encrypt:
                    result['encryption_info'] = {
                        'algorithm': 'AES-256-GCM',
                        'key_derivation': 'HKDF-SHA256'
                    }
                
                return result
                
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {
                'success': False,
                'errors': [f'Upload failed: {str(e)}']
            }
    
    def _should_encrypt_file(self, file_type: str) -> bool:
        """
        Determine if a file should be encrypted based on type and configuration.
        
        Args:
            file_type: File type category
            
        Returns:
            True if file should be encrypted
        """
        if not self.honey_reserve_encryption_enabled:
            return False
        
        # Encrypt all Honey Reserve related files
        encrypt_types = {
            'temporary',           # Bee Chat temporary uploads
            'honey_jar_document',  # Honey jar documents
            'user_document',       # User uploaded documents
            'profile_picture',     # User profile pictures
            'report',             # Generated reports
            'export'              # Exported data
        }
        
        return file_type in encrypt_types
    
    def download_file(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Download a file with permission checking and decryption if needed.

        Args:
            file_id: File ID
            user_id: User ID requesting download

        Returns:
            Dict with file data and metadata, or None if not accessible
        """
        try:
            logger.info(f"[FILE_DOWNLOAD] Starting download: file_id={file_id}, user_id={user_id}")

            with get_db_session() as session:
                # Check permissions with detailed logging
                permission_granted = check_file_permission(session, file_id, user_id, PermissionType.READ.value)
                logger.info(f"[FILE_DOWNLOAD] Permission check result: {permission_granted} for user {user_id} on file {file_id}")

                if not permission_granted:
                    logger.warning(f"[FILE_DOWNLOAD] User {user_id} denied access to file {file_id}")
                    return None

                # Get file metadata with detailed logging
                file_asset = get_file_by_id(session, file_id)
                if not file_asset:
                    logger.error(f"[FILE_DOWNLOAD] File {file_id} not found in database")
                    return None

                logger.info(f"[FILE_DOWNLOAD] File found: filename={file_asset.filename}, "
                           f"storage_backend={file_asset.storage_backend}, "
                           f"storage_path={file_asset.storage_path}, "
                           f"owner_id={file_asset.owner_id}, "
                           f"file_size={file_asset.file_size}")

                # Retrieve file from storage
                if file_asset.storage_backend_enum == StorageBackend.VAULT:
                    logger.info(f"[FILE_DOWNLOAD] Attempting Vault retrieval with path: {file_asset.storage_path}")

                    vault_response = self.vault_client.retrieve_file(file_asset.storage_path)

                    if not vault_response:
                        logger.error(f"[FILE_DOWNLOAD] Vault client returned None for file {file_id} at path {file_asset.storage_path}")
                        return None

                    logger.info(f"[FILE_DOWNLOAD] Vault response received. Type: {type(vault_response)}, "
                               f"Keys: {vault_response.keys() if isinstance(vault_response, dict) else 'N/A'}")

                    if 'data' not in vault_response:
                        logger.error(f"[FILE_DOWNLOAD] Vault response missing 'data' key. Response: {vault_response}")
                        return None
                    
                    raw_data = vault_response['data']
                    logger.info(f"[FILE_DOWNLOAD] Raw data retrieved. Size: {len(raw_data) if isinstance(raw_data, (bytes, str)) else 'Unknown'} bytes, Type: {type(raw_data)}")

                    # Check if file is encrypted based on metadata
                    is_encrypted = file_asset.file_metadata.get('encrypted', False) if file_asset.file_metadata else False
                    logger.info(f"[FILE_DOWNLOAD] Metadata encryption status: {is_encrypted}, metadata: {file_asset.file_metadata}")

                    # FALLBACK: Detect encrypted data even if metadata says unencrypted
                    # This handles cases where files were stored encrypted but metadata is incorrect
                    if not is_encrypted and isinstance(raw_data, (bytes, str)):
                        # Check if data looks like encrypted JSON
                        try:
                            if isinstance(raw_data, bytes):
                                data_str = raw_data.decode('utf-8')
                            else:
                                data_str = raw_data

                            # Look for encrypted data format: {"encrypted_data": "..."}
                            if (data_str.strip().startswith('{"encrypted_data"') or
                                data_str.strip().startswith('{"data"') or
                                '"encrypted_data"' in data_str[:200]):

                                logger.warning(f"[FILE_DOWNLOAD] Detected encrypted data despite metadata saying unencrypted for file {file_id}")
                                logger.warning(f"[FILE_DOWNLOAD] Data sample: {data_str[:100]}...")
                                is_encrypted = True
                                logger.info(f"[FILE_DOWNLOAD] Overriding encryption status to True based on data format")

                        except (UnicodeDecodeError, AttributeError):
                            # If we can't decode as text, it's likely binary (which is good for PDFs)
                            logger.info(f"[FILE_DOWNLOAD] Data appears to be binary (expected for unencrypted files)")

                    logger.info(f"[FILE_DOWNLOAD] Final encryption status: {is_encrypted}")

                    if is_encrypted:
                        try:
                            logger.info(f"[FILE_DOWNLOAD] Starting decryption process for file {file_id}")
                            # Import json for parsing
                            import json

                            # The raw_data should be JSON containing encrypted file info
                            if isinstance(raw_data, bytes):
                                encryption_data = json.loads(raw_data.decode('utf-8'))
                            elif isinstance(raw_data, str):
                                encryption_data = json.loads(raw_data)
                            else:
                                encryption_data = raw_data

                            logger.info(f"[FILE_DOWNLOAD] Parsed encryption data structure successfully")

                            # Deserialize encrypted file
                            encrypted_file = self.encryption_service.deserialize_encrypted_file(encryption_data)

                            # Decrypt file data
                            decrypted_data = self.encryption_service.decrypt_file(encrypted_file, user_id)

                            logger.info(f"[FILE_DOWNLOAD] Successfully decrypted file {file_id} for user {user_id}. Result size: {len(decrypted_data)} bytes")

                            return {
                                'data': decrypted_data,
                                'filename': file_asset.original_filename,
                                'mime_type': file_asset.mime_type,
                                'size': file_asset.file_size,
                                'metadata': file_asset.file_metadata,
                                'encrypted': True
                            }

                        except (HoneyReserveEncryptionError, json.JSONDecodeError, Exception) as e:
                            logger.error(f"[FILE_DOWNLOAD] Failed to decrypt file {file_id} for user {user_id}: {e}")
                            logger.error(f"[FILE_DOWNLOAD] Raw data type: {type(raw_data)}, sample: {str(raw_data)[:200]}...")
                            return None
                    else:
                        # File is not encrypted, return raw data
                        logger.info(f"[FILE_DOWNLOAD] File {file_id} is unencrypted, returning raw data")
                        return {
                            'data': raw_data,
                            'filename': file_asset.original_filename,
                            'mime_type': file_asset.mime_type,
                            'size': file_asset.file_size,
                            'metadata': file_asset.file_metadata,
                            'encrypted': False
                        }
                else:
                    logger.error(f"[FILE_DOWNLOAD] Unsupported storage backend: {file_asset.storage_backend}")
                    return None

        except Exception as e:
            logger.error(f"[FILE_DOWNLOAD] Exception in download_file for {file_id}: {e}", exc_info=True)
            return None
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete a file with permission checking.
        
        Args:
            file_id: File ID
            user_id: User ID requesting deletion
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                # Check permissions (only owner can delete)
                file_asset = get_file_by_id(session, file_id, user_id)
                if not file_asset:
                    logger.warning(f"User {user_id} cannot delete file {file_id} (not owner)")
                    return False
                
                # Soft delete in database
                file_asset.deleted_at = datetime.utcnow()
                session.commit()
                
                # Delete from storage backend
                if file_asset.storage_backend_enum == StorageBackend.VAULT:
                    vault_success = self.vault_client.delete_file(file_asset.storage_path)
                    if not vault_success:
                        logger.warning(f"Failed to delete file {file_id} from Vault, but marked as deleted in DB")
                
                logger.info(f"Successfully deleted file {file_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def get_file_metadata(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata with permission checking.
        
        Args:
            file_id: File ID
            user_id: User ID requesting metadata
            
        Returns:
            Dict with file metadata, or None if not accessible
        """
        try:
            with get_db_session() as session:
                # Check permissions
                if not check_file_permission(session, file_id, user_id, PermissionType.READ.value):
                    return None
                
                file_asset = get_file_by_id(session, file_id)
                if not file_asset:
                    return None
                
                return file_asset.to_dict()
                
        except Exception as e:
            logger.error(f"Error getting metadata for file {file_id}: {e}")
            return None
    
    def list_user_files(self, user_id: str, file_type: str = None,
                       limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List files owned by a user.
        
        Args:
            user_id: User ID
            file_type: Optional file type filter
            limit: Maximum number of files to return
            offset: Offset for pagination
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            with get_db_session() as session:
                files = get_user_files(session, user_id, file_type, limit, offset)
                return [file_asset.to_dict(include_metadata=False) for file_asset in files]
                
        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {e}")
            return []
    
    def share_file(self, file_id: str, owner_id: str, target_user_id: str,
                  permission_type: str, expires_at: Optional[datetime] = None) -> bool:
        """
        Share a file with another user.
        
        Args:
            file_id: File ID
            owner_id: File owner ID
            target_user_id: User to share with
            permission_type: Type of permission to grant
            expires_at: Optional expiration time
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                # Verify ownership
                file_asset = get_file_by_id(session, file_id, owner_id)
                if not file_asset:
                    logger.warning(f"User {owner_id} cannot share file {file_id} (not owner)")
                    return False
                
                # Check if permission already exists
                existing_permission = session.query(FilePermission).filter(
                    FilePermission.file_id == file_id,
                    FilePermission.user_id == target_user_id,
                    FilePermission.permission_type == permission_type,
                    FilePermission.revoked_at.is_(None)
                ).first()
                
                if existing_permission:
                    # Update expiration if needed
                    if expires_at:
                        existing_permission.expires_at = expires_at
                        session.commit()
                    return True
                
                # Create new permission
                permission = FilePermission(
                    file_id=file_id,
                    user_id=target_user_id,
                    granted_by=owner_id,
                    permission_type=permission_type,
                    expires_at=expires_at
                )
                
                session.add(permission)
                session.commit()
                
                logger.info(f"File {file_id} shared with user {target_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error sharing file {file_id}: {e}")
            return False
    
    def revoke_file_access(self, file_id: str, owner_id: str, target_user_id: str) -> bool:
        """
        Revoke file access from a user.
        
        Args:
            file_id: File ID
            owner_id: File owner ID
            target_user_id: User to revoke access from
            
        Returns:
            bool: True if successful
        """
        try:
            with get_db_session() as session:
                # Verify ownership
                file_asset = get_file_by_id(session, file_id, owner_id)
                if not file_asset:
                    return False
                
                # Revoke all permissions for the user
                permissions = session.query(FilePermission).filter(
                    FilePermission.file_id == file_id,
                    FilePermission.user_id == target_user_id,
                    FilePermission.revoked_at.is_(None)
                ).all()
                
                for permission in permissions:
                    permission.revoked_at = datetime.utcnow()
                
                session.commit()
                
                logger.info(f"Revoked access to file {file_id} from user {target_user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error revoking access to file {file_id}: {e}")
            return False
    
    def cleanup_expired_uploads(self) -> int:
        """
        Clean up expired upload sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            with get_db_session() as session:
                expired_sessions = session.query(FileUploadSession).filter(
                    FileUploadSession.expires_at < datetime.utcnow(),
                    FileUploadSession.status.in_(['pending', 'uploading'])
                ).all()
                
                count = 0
                for session_obj in expired_sessions:
                    session_obj.status = 'expired'
                    count += 1
                
                session.commit()
                
                logger.info(f"Cleaned up {count} expired upload sessions")
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired uploads: {e}")
            return 0
    
    def get_honey_reserve_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get Honey Reserve usage statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with usage statistics
        """
        try:
            with get_db_session() as session:
                # Get user's files with size information
                user_files = get_user_files(session, user_id, limit=None)
                
                total_bytes = 0
                file_count = 0
                breakdown = {
                    'temporary': {'bytes': 0, 'count': 0},
                    'honey_jar': {'bytes': 0, 'count': 0},
                    'reports': {'bytes': 0, 'count': 0},
                    'other': {'bytes': 0, 'count': 0}
                }
                
                for file_asset in user_files:
                    if file_asset.deleted_at:
                        continue
                        
                    file_size = file_asset.file_size or 0
                    total_bytes += file_size
                    file_count += 1
                    
                    # Categorize file
                    file_type = file_asset.file_type
                    if file_type == 'temporary':
                        breakdown['temporary']['bytes'] += file_size
                        breakdown['temporary']['count'] += 1
                    elif file_type in ['honey_jar_document', 'user_document']:
                        breakdown['honey_jar']['bytes'] += file_size
                        breakdown['honey_jar']['count'] += 1
                    elif file_type in ['report', 'export']:
                        breakdown['reports']['bytes'] += file_size
                        breakdown['reports']['count'] += 1
                    else:
                        breakdown['other']['bytes'] += file_size
                        breakdown['other']['count'] += 1
                
                # Get user's quota (default 1GB)
                default_quota = int(os.environ.get('HONEY_RESERVE_DEFAULT_QUOTA', '1073741824'))
                
                return {
                    'total_bytes': total_bytes,
                    'total_files': file_count,
                    'quota_bytes': default_quota,
                    'usage_percentage': round((total_bytes / default_quota) * 100, 2),
                    'remaining_bytes': max(0, default_quota - total_bytes),
                    'breakdown': breakdown,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting Honey Reserve usage for user {user_id}: {e}")
            return {
                'total_bytes': 0,
                'total_files': 0,
                'quota_bytes': 1073741824,
                'usage_percentage': 0,
                'remaining_bytes': 1073741824,
                'breakdown': {},
                'error': str(e)
            }
    
    def get_user_quota(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's Honey Reserve quota information.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with quota information
        """
        try:
            # Get quota from environment or config
            default_quota = int(os.environ.get('HONEY_RESERVE_DEFAULT_QUOTA', '1073741824'))
            warning_threshold = int(os.environ.get('HONEY_RESERVE_WARNING_THRESHOLD', '90'))
            critical_threshold = int(os.environ.get('HONEY_RESERVE_CRITICAL_THRESHOLD', '95'))
            
            # Get current usage
            usage_data = self.get_honey_reserve_usage(user_id)
            
            return {
                'quota_bytes': default_quota,
                'quota_formatted': self._format_bytes(default_quota),
                'used_bytes': usage_data['total_bytes'],
                'used_formatted': self._format_bytes(usage_data['total_bytes']),
                'remaining_bytes': usage_data['remaining_bytes'],
                'remaining_formatted': self._format_bytes(usage_data['remaining_bytes']),
                'usage_percentage': usage_data['usage_percentage'],
                'warning_threshold': warning_threshold,
                'critical_threshold': critical_threshold,
                'status': self._get_quota_status(usage_data['usage_percentage'], warning_threshold, critical_threshold),
                'files_count': usage_data['total_files']
            }
            
        except Exception as e:
            logger.error(f"Error getting user quota for {user_id}: {e}")
            return {'error': str(e)}
    
    def cleanup_expired_files(self, user_id: str) -> Dict[str, Any]:
        """
        Clean up expired temporary files for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with cleanup results
        """
        try:
            retention_hours = int(os.environ.get('HONEY_RESERVE_TEMP_RETENTION_HOURS', '48'))
            cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)
            
            with get_db_session() as session:
                # Find expired temporary files
                expired_files = session.query(FileAsset).filter(
                    FileAsset.owner_id == user_id,
                    FileAsset.file_type == 'temporary',
                    FileAsset.created_at < cutoff_time,
                    FileAsset.deleted_at.is_(None)
                ).all()
                
                cleaned_count = 0
                bytes_freed = 0
                
                for file_asset in expired_files:
                    try:
                        # Soft delete in database
                        file_asset.deleted_at = datetime.utcnow()
                        bytes_freed += file_asset.file_size or 0
                        cleaned_count += 1
                        
                        # Delete from storage backend
                        if file_asset.storage_backend_enum == StorageBackend.VAULT:
                            self.vault_client.delete_file(file_asset.storage_path)
                            
                    except Exception as e:
                        logger.warning(f"Failed to delete expired file {file_asset.id}: {e}")
                
                session.commit()
                
                logger.info(f"Cleaned up {cleaned_count} expired files for user {user_id}, freed {bytes_freed} bytes")
                
                return {
                    'files_cleaned': cleaned_count,
                    'bytes_freed': bytes_freed,
                    'bytes_freed_formatted': self._format_bytes(bytes_freed),
                    'retention_hours': retention_hours,
                    'cutoff_time': cutoff_time.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error cleaning up expired files for user {user_id}: {e}")
            return {'error': str(e)}
    
    def bulk_delete_files(self, file_ids: List[str], user_id: str) -> Dict[str, Any]:
        """
        Bulk delete files for a user.
        
        Args:
            file_ids: List of file IDs to delete
            user_id: User ID
            
        Returns:
            Dict with deletion results
        """
        try:
            results = {
                'deleted': [],
                'failed': [],
                'total_bytes_freed': 0
            }
            
            for file_id in file_ids:
                try:
                    # Get file info first
                    file_info = self.get_file_metadata(file_id, user_id)
                    if not file_info:
                        results['failed'].append({
                            'file_id': file_id,
                            'error': 'File not found or access denied'
                        })
                        continue
                    
                    # Delete the file
                    if self.delete_file(file_id, user_id):
                        results['deleted'].append({
                            'file_id': file_id,
                            'filename': file_info.get('filename', 'unknown'),
                            'size': file_info.get('file_size', 0)
                        })
                        results['total_bytes_freed'] += file_info.get('file_size', 0)
                    else:
                        results['failed'].append({
                            'file_id': file_id,
                            'error': 'Delete operation failed'
                        })
                        
                except Exception as e:
                    results['failed'].append({
                        'file_id': file_id,
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'summary': {
                    'deleted_count': len(results['deleted']),
                    'failed_count': len(results['failed']),
                    'total_bytes_freed': results['total_bytes_freed'],
                    'total_bytes_freed_formatted': self._format_bytes(results['total_bytes_freed'])
                },
                'details': results
            }
            
        except Exception as e:
            logger.error(f"Error in bulk delete for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_storage_breakdown(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed storage breakdown by category.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with detailed breakdown
        """
        try:
            with get_db_session() as session:
                # Get all user files
                user_files = get_user_files(session, user_id, limit=None)
                
                breakdown = {
                    'by_type': {},
                    'by_date': {},
                    'largest_files': [],
                    'oldest_files': [],
                    'total_stats': {
                        'total_files': 0,
                        'total_bytes': 0
                    }
                }
                
                all_files = []
                
                for file_asset in user_files:
                    if file_asset.deleted_at:
                        continue
                    
                    file_size = file_asset.file_size or 0
                    file_type = file_asset.file_type
                    created_date = file_asset.created_at.strftime('%Y-%m')
                    
                    # By type breakdown
                    if file_type not in breakdown['by_type']:
                        breakdown['by_type'][file_type] = {'count': 0, 'bytes': 0}
                    breakdown['by_type'][file_type]['count'] += 1
                    breakdown['by_type'][file_type]['bytes'] += file_size
                    
                    # By date breakdown
                    if created_date not in breakdown['by_date']:
                        breakdown['by_date'][created_date] = {'count': 0, 'bytes': 0}
                    breakdown['by_date'][created_date]['count'] += 1
                    breakdown['by_date'][created_date]['bytes'] += file_size
                    
                    # Collect for largest/oldest
                    all_files.append({
                        'id': str(file_asset.id),
                        'filename': file_asset.filename,
                        'size': file_size,
                        'created_at': file_asset.created_at.isoformat(),
                        'file_type': file_type
                    })
                    
                    # Update totals
                    breakdown['total_stats']['total_files'] += 1
                    breakdown['total_stats']['total_bytes'] += file_size
                
                # Sort for largest and oldest
                breakdown['largest_files'] = sorted(all_files, key=lambda x: x['size'], reverse=True)[:10]
                breakdown['oldest_files'] = sorted(all_files, key=lambda x: x['created_at'])[:10]
                
                return breakdown
                
        except Exception as e:
            logger.error(f"Error getting storage breakdown for user {user_id}: {e}")
            return {'error': str(e)}
    
    def extract_text_content(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Extract text content from a file for analysis.
        
        Args:
            file_id: File ID
            user_id: User ID
            
        Returns:
            Dict with extracted text
        """
        try:
            # Download the file
            file_data = self.download_file(file_id, user_id)
            if not file_data:
                return {'success': False, 'error': 'File not found or access denied'}
            
            # Simple text extraction based on file type
            content = file_data['data']
            filename = file_data['filename']
            
            if filename.lower().endswith('.txt'):
                # Plain text
                text = content.decode('utf-8', errors='ignore')
            elif filename.lower().endswith('.md'):
                # Markdown
                text = content.decode('utf-8', errors='ignore')
            elif filename.lower().endswith('.json'):
                # JSON
                import json
                try:
                    data = json.loads(content.decode('utf-8'))
                    text = json.dumps(data, indent=2)
                except:
                    text = content.decode('utf-8', errors='ignore')
            else:
                # Try to decode as text
                text = content.decode('utf-8', errors='ignore')
            
            return {
                'success': True,
                'text': text[:10000],  # Limit to 10KB for now
                'filename': filename,
                'size': len(text)
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from file {file_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _get_quota_status(self, usage_percentage: float, warning_threshold: int, critical_threshold: int) -> str:
        """Get quota status based on usage percentage."""
        if usage_percentage >= critical_threshold:
            return 'critical'
        elif usage_percentage >= warning_threshold:
            return 'warning'
        else:
            return 'normal'

# Profile-specific file operations
class ProfileFileService:
    """Specialized service for profile-related files."""
    
    def __init__(self):
        self.file_service = FileService()
    
    def upload_profile_picture(self, file_data: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """Upload a profile picture."""
        metadata = {
            'category': 'profile_picture',
            'usage': 'avatar'
        }
        
        return self.file_service.upload_file(
            file_data, filename, 'profile_picture', user_id, metadata
        )
    
    def get_profile_picture(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current profile picture."""
        files = self.file_service.list_user_files(user_id, 'profile_picture', limit=1)
        if not files:
            return None
        
        return self.file_service.download_file(files[0]['id'], user_id)
    
    def update_profile_picture(self, file_data: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """Update profile picture (delete old, upload new)."""
        # Delete existing profile picture
        existing_files = self.file_service.list_user_files(user_id, 'profile_picture')
        for file_info in existing_files:
            self.file_service.delete_file(file_info['id'], user_id)
        
        # Upload new profile picture
        return self.upload_profile_picture(file_data, filename, user_id)

# Global file service instance
_file_service = None

def get_file_service() -> FileService:
    """Get the global file service instance."""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service