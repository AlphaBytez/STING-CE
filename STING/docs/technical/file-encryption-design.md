# 🔐 File Encryption Design for Honey Reserve

## Overview

This document outlines the encryption architecture for user-uploaded files in STING's Honey Reserve system. The design leverages Kratos identity management for key derivation and access control, ensuring that only authorized users can decrypt and access files.

## Encryption Architecture

### Key Hierarchy

```
┌─────────────────────┐
│   Master Key (KEK)  │ ← Stored in HashiCorp Vault
└──────────┬──────────┘
           │
    ┌──────▼──────────┐
    │  User Key (DEK) │ ← Derived from Kratos Identity
    └──────────┬──────┘
               │
         ┌─────▼─────┐    ┌──────────┐    ┌──────────┐
         │ File Key  │    │ File Key │    │ File Key │
         └───────────┘    └──────────┘    └──────────┘
              │                 │               │
         ┌────▼────┐      ┌────▼────┐    ┌────▼────┐
         │ File 1  │      │ File 2  │    │ File 3  │
         └─────────┘      └─────────┘    └─────────┘
```

### Encryption Flow

```python
class HoneyReserveEncryption:
    def __init__(self):
        self.vault_client = hvac.Client()
        self.kratos_client = KratosClient()
    
    def encrypt_file(self, file_data: bytes, user_id: str) -> EncryptedFile:
        # 1. Get user's derived encryption key
        user_key = self.derive_user_key(user_id)
        
        # 2. Generate file-specific key
        file_key = secrets.token_bytes(32)  # 256-bit key
        
        # 3. Encrypt file with file key
        encrypted_data = self.aes_encrypt(file_data, file_key)
        
        # 4. Encrypt file key with user key
        encrypted_file_key = self.aes_encrypt(file_key, user_key)
        
        # 5. Store metadata
        return EncryptedFile(
            data=encrypted_data,
            encrypted_key=encrypted_file_key,
            algorithm='AES-256-GCM',
            user_id=user_id
        )
```

## Key Management

### User Key Derivation

```python
def derive_user_key(self, user_id: str) -> bytes:
    """Derive encryption key from Kratos identity"""
    
    # 1. Get user identity from Kratos
    identity = self.kratos_client.get_identity(user_id)
    
    # 2. Combine with master key from Vault
    master_key = self.vault_client.read('secret/sting/master-key')['data']['key']
    
    # 3. Derive user-specific key using HKDF
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'sting-honey-reserve',
        info=f'user-key-{user_id}'.encode()
    )
    
    return kdf.derive(master_key + identity.id.encode())
```

### Key Storage

| Key Type | Storage Location | Rotation Period | Access Control |
|----------|------------------|-----------------|----------------|
| Master Key (KEK) | HashiCorp Vault | Annually | Admin only |
| User Keys (DEK) | Derived on-demand | Never stored | Per-user |
| File Keys | Encrypted with user key | Per file | Via user key |

## Access Control Integration

### Kratos-based Permissions

```python
async def can_decrypt_file(self, user_id: str, file_id: str) -> bool:
    """Check if user can decrypt file using Kratos identity"""
    
    # 1. Get file metadata
    file_meta = await self.get_file_metadata(file_id)
    
    # 2. Check ownership
    if file_meta.owner_id == user_id:
        return True
    
    # 3. Check shared access
    if user_id in file_meta.shared_with:
        return True
    
    # 4. Check role-based access
    user_roles = await self.kratos_client.get_user_roles(user_id)
    if 'admin' in user_roles and file_meta.admin_accessible:
        return True
    
    # 5. Check honey jar permissions
    if file_meta.honey_jar_id:
        return await self.check_honey_jar_access(user_id, file_meta.honey_jar_id)
    
    return False
```

### File Sharing

```python
async def share_file(self, file_id: str, owner_id: str, 
                    recipient_id: str, permissions: List[str]):
    """Share encrypted file with another user"""
    
    # 1. Verify owner
    if not await self.verify_ownership(file_id, owner_id):
        raise PermissionError("Not file owner")
    
    # 2. Get file's encrypted key
    file_meta = await self.get_file_metadata(file_id)
    owner_key = self.derive_user_key(owner_id)
    
    # 3. Decrypt file key with owner's key
    file_key = self.aes_decrypt(file_meta.encrypted_key, owner_key)
    
    # 4. Re-encrypt with recipient's key
    recipient_key = self.derive_user_key(recipient_id)
    recipient_encrypted_key = self.aes_encrypt(file_key, recipient_key)
    
    # 5. Store sharing record
    await self.store_sharing_record(
        file_id=file_id,
        recipient_id=recipient_id,
        encrypted_key=recipient_encrypted_key,
        permissions=permissions
    )
```

## Encryption Implementation

### Algorithm Selection

```python
ENCRYPTION_CONFIG = {
    'algorithm': 'AES-256-GCM',
    'key_size': 256,  # bits
    'iv_size': 96,    # bits for GCM
    'tag_size': 128,  # bits
    'kdf': 'HKDF-SHA256',
    'iterations': 100000  # for password-based keys
}
```

### File Encryption Process

```python
def aes_encrypt(self, plaintext: bytes, key: bytes) -> EncryptedData:
    """Encrypt data using AES-256-GCM"""
    
    # 1. Generate random IV
    iv = os.urandom(12)  # 96 bits for GCM
    
    # 2. Create cipher
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    )
    
    # 3. Encrypt data
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    # 4. Return encrypted data with metadata
    return EncryptedData(
        ciphertext=ciphertext,
        iv=iv,
        tag=encryptor.tag,
        algorithm='AES-256-GCM'
    )
```

### Streaming Encryption

For large files, use streaming encryption:

```python
async def encrypt_file_stream(self, file_stream, user_id: str, chunk_size: int = 1024*1024):
    """Encrypt file in chunks for memory efficiency"""
    
    user_key = self.derive_user_key(user_id)
    file_key = secrets.token_bytes(32)
    iv = os.urandom(12)
    
    cipher = Cipher(
        algorithms.AES(file_key),
        modes.GCM(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    async for chunk in file_stream:
        encrypted_chunk = encryptor.update(chunk)
        yield encrypted_chunk
    
    # Finalize and get authentication tag
    encryptor.finalize()
    
    # Return metadata
    return {
        'encrypted_key': self.aes_encrypt(file_key, user_key),
        'iv': iv,
        'tag': encryptor.tag
    }
```

## Security Considerations

### Key Security

1. **Key Derivation**
   - Use HKDF for key derivation
   - Include user ID in derivation to ensure uniqueness
   - Salt all key derivations

2. **Key Storage**
   - Never store user keys directly
   - File keys encrypted at rest
   - Master key in HSM-backed Vault

3. **Key Rotation**
   - Master key: Annual rotation with re-encryption
   - User keys: Derived fresh each time
   - File keys: Immutable (re-encrypt for rotation)

### Threat Model

| Threat | Mitigation |
|--------|------------|
| Database compromise | File keys encrypted with user keys |
| User account takeover | 2FA required for key operations |
| Admin insider threat | Audit logging, dual control |
| Key extraction | HSM for master key |
| Cryptanalysis | AES-256, regular algorithm review |

## Performance Optimization

### Caching Strategy

```python
class KeyCache:
    def __init__(self, ttl: int = 300):  # 5 minute TTL
        self.cache = TTLCache(maxsize=1000, ttl=ttl)
    
    def get_user_key(self, user_id: str) -> Optional[bytes]:
        """Get cached user key if available"""
        return self.cache.get(f"user_key:{user_id}")
    
    def set_user_key(self, user_id: str, key: bytes):
        """Cache user key temporarily"""
        self.cache[f"user_key:{user_id}"] = key
```

### Parallel Processing

```python
async def encrypt_multiple_files(self, files: List[File], user_id: str):
    """Encrypt multiple files in parallel"""
    
    # Derive user key once
    user_key = self.derive_user_key(user_id)
    
    # Process files in parallel
    tasks = []
    for file in files:
        task = self.encrypt_file_async(file, user_key)
        tasks.append(task)
    
    return await asyncio.gather(*tasks)
```

## Compliance Features

### GDPR Compliance

```python
async def handle_erasure_request(self, user_id: str):
    """Handle GDPR right to erasure"""
    
    # 1. Find all files owned by user
    files = await self.get_user_files(user_id)
    
    # 2. Crypto-shred by deleting encrypted keys
    for file in files:
        await self.delete_encrypted_key(file.id)
    
    # 3. Mark files for physical deletion
    await self.mark_files_for_deletion(files)
    
    # 4. Remove user key derivation ability
    await self.revoke_user_access(user_id)
```

### Audit Logging

```python
@audit_log
async def decrypt_file(self, file_id: str, user_id: str):
    """Decrypt file with audit logging"""
    
    # Log access attempt
    await self.audit_logger.log({
        'action': 'file_decrypt',
        'user_id': user_id,
        'file_id': file_id,
        'timestamp': datetime.utcnow(),
        'ip_address': request.remote_addr
    })
    
    # Perform decryption
    return await self._decrypt_file_internal(file_id, user_id)
```

## Emergency Access

### Break-Glass Procedure

```python
async def emergency_decrypt(self, file_id: str, admin_id: str, 
                          second_admin_id: str, reason: str):
    """Emergency file decryption with dual control"""
    
    # 1. Verify both admins
    if not (await self.verify_admin(admin_id) and 
            await self.verify_admin(second_admin_id)):
        raise PermissionError("Dual admin control required")
    
    # 2. Log emergency access
    await self.audit_logger.critical({
        'action': 'emergency_decrypt',
        'file_id': file_id,
        'admin1': admin_id,
        'admin2': second_admin_id,
        'reason': reason
    })
    
    # 3. Use master key directly
    master_key = await self.get_master_key_with_dual_control(
        admin_id, second_admin_id
    )
    
    # 4. Decrypt file
    return await self.decrypt_with_master(file_id, master_key)
```

## Migration Strategy

### Encrypting Existing Files

```python
async def migrate_unencrypted_files(self, batch_size: int = 100):
    """Migrate existing unencrypted files"""
    
    while True:
        # Get batch of unencrypted files
        files = await self.get_unencrypted_files(limit=batch_size)
        if not files:
            break
        
        for file in files:
            try:
                # Read unencrypted data
                data = await self.read_file(file.id)
                
                # Encrypt with owner's key
                encrypted = await self.encrypt_file(data, file.owner_id)
                
                # Replace with encrypted version
                await self.replace_file(file.id, encrypted)
                
                # Mark as migrated
                await self.mark_migrated(file.id)
                
            except Exception as e:
                logger.error(f"Failed to migrate file {file.id}: {e}")
```

---

*This encryption design ensures that Honey Reserve files are protected with industry-standard encryption while maintaining usability and compliance.*