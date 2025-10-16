# File Asset Management Architecture

## Overview

STING-CE implements a hybrid file asset management system that balances security, performance, and scalability. The architecture leverages existing infrastructure components while providing a foundation for future expansion.

## Architecture Components

### 1. Storage Layers

| Layer | Technology | Use Case | Security Level |
|-------|------------|----------|----------------|
| **Vault Storage** | HashiCorp Vault | User-generated sensitive files | High |
| **PostgreSQL Metadata** | PostgreSQL | File metadata, permissions, relationships | Medium |
| **MinIO/S3 (Future)** | MinIO (S3-compatible) | Large files, reports, bulk storage | Medium |
| **Filesystem** | Local/Docker volumes | Static assets, templates | Low |

### 2. File Categories

#### Sensitive Files (Vault Storage)
- **Profile Pictures**: User avatars, personal images
- **User Documents**: Private files, certificates, personal data
- **Encrypted Reports**: Sensitive system reports requiring access control

#### System Files (PostgreSQL + Optional MinIO)
- **Generated Reports**: System logs, analytics reports
- **Bulk Data**: Large datasets, backups
- **Temporary Files**: Processing artifacts, cache files

#### Static Assets (Filesystem)
- **UI Assets**: Icons, themes, templates
- **System Resources**: Configuration files, documentation

## Implementation Details

### File Service Architecture

```
/app/services/file_service.py          # Core file operations
/app/models/file_models.py             # File metadata models
/app/routes/file_routes.py             # File upload/download APIs
/app/utils/vault_file_client.py        # Vault file operations
/app/utils/minio_client.py             # MinIO operations (future)
```

### Database Schema

```sql
-- File metadata table
CREATE TABLE file_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    storage_backend VARCHAR(20) NOT NULL, -- 'vault', 'minio', 'filesystem'
    storage_path TEXT NOT NULL,
    owner_id UUID REFERENCES users(id),
    access_level VARCHAR(20) DEFAULT 'private', -- 'public', 'private', 'restricted'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL
);

-- File permissions table
CREATE TABLE file_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID REFERENCES file_assets(id),
    user_id UUID REFERENCES users(id),
    permission_type VARCHAR(20) NOT NULL, -- 'read', 'write', 'delete'
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NULL
);
```

### API Endpoints

```
POST   /api/files/upload           # Upload file
GET    /api/files/{id}             # Download file
GET    /api/files/{id}/metadata    # Get file metadata
PUT    /api/files/{id}/metadata    # Update file metadata
DELETE /api/files/{id}             # Delete file
GET    /api/files/                 # List user's files
POST   /api/files/{id}/share       # Share file with user
```

## Security Model

### Access Control
- **Authentication**: All file operations require valid Kratos session
- **Authorization**: File ownership and permission-based access
- **Encryption**: Vault provides encryption at rest for sensitive files
- **Audit Trail**: All file operations logged for compliance

### File Validation
- **Type Validation**: MIME type checking and file signature verification
- **Size Limits**: Configurable per file type and user role
- **Virus Scanning**: Integration point for antivirus scanning
- **Content Filtering**: Prevent malicious file uploads

## Performance Considerations

### Caching Strategy
- **Metadata Caching**: Redis cache for frequently accessed file metadata
- **Thumbnail Generation**: Automatic thumbnail creation for images
- **CDN Integration**: Future MinIO integration with CDN capabilities

### Optimization
- **Streaming Uploads**: Support for large file uploads via streaming
- **Compression**: Automatic compression for applicable file types
- **Deduplication**: Hash-based deduplication to save storage space

## MinIO Integration (Future Phase)

### Why MinIO?
- **Open Source**: Apache License 2.0, fully open source
- **S3 Compatible**: Standard S3 API for easy integration
- **High Performance**: Optimized for cloud-native applications
- **Scalable**: Horizontal scaling with erasure coding

### MinIO Configuration
```yaml
# docker-compose.yml addition
minio:
  image: minio/minio:latest
  environment:
    MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
    MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
  volumes:
    - minio_data:/data
  ports:
    - "9000:9000"
    - "9001:9001"
  command: server /data --console-address ":9001"
```

## Migration Strategy

### Phase 1: Vault-Based Foundation
1. Implement core file service with Vault storage
2. Create file metadata models and APIs
3. Integrate with profile management system
4. Add basic file validation and security

### Phase 2: MinIO Integration
1. Add MinIO service to docker-compose
2. Implement MinIO client utilities
3. Create storage backend abstraction layer
4. Migrate large files to MinIO

### Phase 3: Advanced Features
1. Add thumbnail generation service
2. Implement file sharing and collaboration
3. Add virus scanning integration
4. Create file analytics and reporting

## Configuration

### Environment Variables
```bash
# File service configuration
FILE_SERVICE_ENABLED=true
FILE_MAX_SIZE=100MB
FILE_ALLOWED_TYPES=image/*,application/pdf,text/*

# Vault file storage
VAULT_FILE_MOUNT=file-storage
VAULT_FILE_PATH=files/

# MinIO configuration (future)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=sting-files
```

### File Type Policies
```yaml
file_policies:
  profile_pictures:
    max_size: 5MB
    allowed_types: [image/jpeg, image/png, image/webp]
    storage_backend: vault
    
  user_documents:
    max_size: 50MB
    allowed_types: [application/pdf, text/*, image/*]
    storage_backend: vault
    
  system_reports:
    max_size: 500MB
    allowed_types: [application/json, text/csv, application/pdf]
    storage_backend: minio
```

## Monitoring and Maintenance

### Health Checks
- Storage backend connectivity
- File service API availability
- Storage space monitoring
- Performance metrics

### Backup Strategy
- **Vault Files**: Included in Vault backup procedures
- **MinIO Files**: S3-compatible backup tools
- **Metadata**: PostgreSQL backup procedures
- **Retention Policies**: Configurable file retention periods

## Integration Points

### Profile Management
- Profile picture upload and storage
- User document management
- Avatar generation and caching

### Reporting System
- Report file generation and storage
- Automated report archival
- Report sharing and distribution

### Knowledge System
- Document ingestion for ChromaDB
- File-based knowledge base updates
- Attachment handling for chat system

## Future Enhancements

### Advanced Features
- **File Versioning**: Track file changes over time
- **Collaborative Editing**: Real-time document collaboration
- **Advanced Search**: Full-text search across file contents
- **Workflow Integration**: File-based approval workflows

### Scalability
- **Multi-Region Support**: Distributed file storage
- **Edge Caching**: Global CDN integration
- **Load Balancing**: Multiple file service instances
- **Auto-Scaling**: Dynamic resource allocation

---

*This document is part of the STING-CE Architecture Documentation. For implementation details, see the corresponding service documentation.*