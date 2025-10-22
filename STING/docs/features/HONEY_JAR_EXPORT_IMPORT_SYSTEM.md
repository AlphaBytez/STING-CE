# Honey Jar Export/Import System

## Overview

STING-CE provides comprehensive export and import capabilities for Honey Jars, enabling knowledge base portability, backup and restore operations, and sharing of curated knowledge collections. The system supports multiple formats including HJX (Honey Jar Exchange), JSON, and TAR archives, with full preservation of metadata, vector embeddings, and document relationships.

## Architecture

### Export/Import Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Honey Jar     │───▶│   Export Engine │───▶│  Format Writers │
│   (Source)      │    │  (Processor)    │    │  (HJX/JSON/TAR) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────────────┐
│   Validation    │    │           Storage Layer                 │
│   Engine        │    │     (Files, Metadata, Vectors)         │
└─────────────────┘    │ ┌─────────────┐ ┌─────────────────────┐ │
        │               │ │ Documents   │ │    ChromaDB         │ │
        ▼               │ │   (Files)   │ │   (Embeddings)      │ │
┌─────────────────┐    │ └─────────────┘ └─────────────────────┘ │
│  Import Engine  │◀───└─────────────────────────────────────────┘
│  (Processor)    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│   Honey Jar     │
│  (Destination)  │
└─────────────────┘
```

### Key Components

1. **Export Engine**: Handles honey jar serialization and packaging
2. **Import Engine**: Processes and validates imported honey jars
3. **Format Handlers**: Support for multiple export/import formats
4. **Validation System**: Ensures data integrity and compatibility
5. **Conflict Resolution**: Handles naming and content conflicts
6. **Progress Tracking**: Real-time import/export progress monitoring

## Export Formats

### HJX (Honey Jar Exchange) Format

The native STING format optimized for full fidelity:

```json
{
  "format": "hjx",
  "version": "1.0",
  "created_at": "2024-08-22T10:30:45Z",
  "sting_version": "1.2.0",
  "honey_jar": {
    "id": "hj-uuid-1234567890",
    "name": "Technical Documentation",
    "description": "Complete technical documentation collection",
    "type": "private",
    "created_by": "user-uuid",
    "created_at": "2024-08-01T09:00:00Z",
    "updated_at": "2024-08-22T10:30:45Z",
    "metadata": {
      "tags": ["documentation", "technical", "api"],
      "language": "en",
      "domain": "software_development",
      "document_count": 156,
      "total_size_bytes": 52428800
    },
    "access_control": {
      "type": "private",
      "permissions": {
        "read": ["user-uuid", "admin-uuid"],
        "write": ["user-uuid"],
        "admin": ["admin-uuid"]
      }
    }
  },
  "documents": [
    {
      "id": "doc-uuid-1",
      "filename": "API_Reference.pdf",
      "content_type": "application/pdf",
      "size_bytes": 2048576,
      "checksum_sha256": "a1b2c3d4e5f6...",
      "upload_date": "2024-08-01T09:15:00Z",
      "metadata": {
        "author": "Technical Team",
        "title": "API Reference Guide",
        "category": "documentation",
        "extracted_text_length": 45000,
        "page_count": 120
      },
      "processing_status": "completed",
      "chunks": [
        {
          "chunk_id": "chunk-uuid-1-1",
          "content": "API Overview\nThis document provides...",
          "start_position": 0,
          "end_position": 1024,
          "chunk_index": 0,
          "metadata": {
            "page": 1,
            "section": "introduction"
          }
        }
      ],
      "embeddings": {
        "model": "all-MiniLM-L6-v2",
        "vectors": [
          {
            "chunk_id": "chunk-uuid-1-1",
            "vector": [0.123, -0.456, 0.789, ...],
            "dimension": 384
          }
        ]
      }
    }
  ],
  "vector_index": {
    "model_name": "all-MiniLM-L6-v2",
    "dimension": 384,
    "index_type": "hnsw",
    "index_parameters": {
      "hnsw:M": 16,
      "hnsw:construction_ef": 200,
      "hnsw:space": "cosine"
    },
    "collection_metadata": {
      "total_vectors": 1247,
      "created_at": "2024-08-01T09:00:00Z",
      "last_updated": "2024-08-22T10:30:45Z"
    }
  },
  "export_metadata": {
    "exported_by": "user-uuid",
    "export_timestamp": "2024-08-22T10:30:45Z",
    "export_options": {
      "include_embeddings": true,
      "include_raw_files": true,
      "compress_content": true
    },
    "integrity_hash": "sha256:abcdef123456..."
  }
}
```

### JSON Format

Lightweight format for metadata and text content:

```json
{
  "format": "json",
  "version": "1.0",
  "honey_jar": {
    "name": "Technical Documentation",
    "description": "Complete technical documentation collection",
    "type": "private"
  },
  "documents": [
    {
      "filename": "API_Reference.pdf",
      "content": "Extracted text content...",
      "metadata": {
        "author": "Technical Team",
        "title": "API Reference Guide"
      }
    }
  ]
}
```

### TAR Archive Format

File-based format preserving original document structure:

```
honey_jar_export.tar.gz
├── manifest.json          # Honey jar metadata
├── documents/
│   ├── API_Reference.pdf  # Original files
│   ├── User_Guide.docx
│   └── Technical_Spec.md
├── extracted_text/
│   ├── API_Reference.txt  # Extracted text
│   ├── User_Guide.txt
│   └── Technical_Spec.txt
├── embeddings/
│   └── vectors.json       # Vector embeddings
└── metadata/
    ├── documents.json     # Document metadata
    └── chunks.json        # Text chunks
```

## Export Implementation

### Export Engine

```python
# knowledge_service/core/export_engine.py
class HoneyJarExportEngine:
    def __init__(self, honeycomb_manager, file_service):
        self.honeycomb = honeycomb_manager
        self.file_service = file_service
        self.supported_formats = ['hjx', 'json', 'tar']
    
    async def export_honey_jar(self, honey_jar_id, export_format='hjx', 
                              include_embeddings=True, include_files=True,
                              progress_callback=None):
        """Export a honey jar to specified format"""
        
        if export_format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {export_format}")
        
        try:
            # Step 1: Gather honey jar metadata
            if progress_callback:
                progress_callback(10, "Collecting honey jar metadata")
            
            honey_jar = await self.get_honey_jar_metadata(honey_jar_id)
            
            # Step 2: Collect documents and content
            if progress_callback:
                progress_callback(30, "Collecting documents")
            
            documents = await self.collect_documents(honey_jar_id, include_files)
            
            # Step 3: Collect embeddings if requested
            embeddings = None
            if include_embeddings:
                if progress_callback:
                    progress_callback(60, "Collecting vector embeddings")
                
                embeddings = await self.collect_embeddings(honey_jar_id)
            
            # Step 4: Generate export package
            if progress_callback:
                progress_callback(80, f"Generating {export_format} export")
            
            export_data = await self.generate_export_package(
                honey_jar, documents, embeddings, export_format
            )
            
            # Step 5: Finalize and return
            if progress_callback:
                progress_callback(100, "Export completed")
            
            return export_data
            
        except Exception as e:
            logger.error(f"Export failed for honey jar {honey_jar_id}: {e}")
            raise ExportError(f"Export failed: {str(e)}")
    
    async def collect_documents(self, honey_jar_id, include_files=True):
        """Collect all documents and their content"""
        
        documents = []
        
        # Get document list from database
        with get_db_session() as session:
            db_documents = session.query(Document)\
                .filter(Document.honey_jar_id == honey_jar_id)\
                .all()
        
        for doc in db_documents:
            document_data = {
                'id': doc.id,
                'filename': doc.filename,
                'content_type': doc.content_type,
                'size_bytes': doc.size_bytes,
                'upload_date': doc.upload_date.isoformat(),
                'metadata': doc.metadata or {},
                'processing_status': doc.processing_status
            }
            
            # Include file content if requested
            if include_files and doc.file_id:
                try:
                    file_data = self.file_service.download_file(doc.file_id)
                    document_data['file_data'] = base64.b64encode(file_data).decode('utf-8')
                    document_data['checksum_sha256'] = hashlib.sha256(file_data).hexdigest()
                except Exception as e:
                    logger.warning(f"Could not include file data for {doc.filename}: {e}")
            
            # Include extracted text chunks
            chunks = await self.get_document_chunks(doc.id)
            document_data['chunks'] = chunks
            
            documents.append(document_data)
        
        return documents
    
    async def collect_embeddings(self, honey_jar_id):
        """Collect vector embeddings from ChromaDB"""
        
        collection_name = f"honey_jar_{honey_jar_id}"
        
        try:
            collection = self.honeycomb.get_collection(collection_name)
            if not collection:
                return None
            
            # Get all vectors from collection
            all_data = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            embeddings_data = {
                'model_name': getattr(collection._embedding_function, 'model_name', 'unknown'),
                'dimension': len(all_data['embeddings'][0]) if all_data['embeddings'] else 0,
                'index_type': 'hnsw',
                'index_parameters': collection.metadata,
                'vectors': []
            }
            
            # Package vectors with metadata
            for i, (doc, metadata, embedding) in enumerate(zip(
                all_data['documents'],
                all_data['metadatas'], 
                all_data['embeddings']
            )):
                embeddings_data['vectors'].append({
                    'id': all_data['ids'][i],
                    'document': doc,
                    'metadata': metadata,
                    'vector': embedding
                })
            
            return embeddings_data
            
        except Exception as e:
            logger.error(f"Failed to collect embeddings for {honey_jar_id}: {e}")
            return None
    
    async def generate_export_package(self, honey_jar, documents, embeddings, format_type):
        """Generate the final export package"""
        
        export_data = {
            'format': format_type,
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat(),
            'sting_version': self.get_sting_version(),
            'honey_jar': honey_jar,
            'documents': documents,
            'export_metadata': {
                'exported_by': honey_jar.get('created_by'),
                'export_timestamp': datetime.utcnow().isoformat(),
                'export_options': {
                    'include_embeddings': embeddings is not None,
                    'include_raw_files': any('file_data' in doc for doc in documents),
                    'compress_content': True
                }
            }
        }
        
        if embeddings:
            export_data['vector_index'] = embeddings
        
        # Generate integrity hash
        export_data['export_metadata']['integrity_hash'] = self.calculate_integrity_hash(export_data)
        
        # Format-specific processing
        if format_type == 'hjx':
            return await self.generate_hjx_package(export_data)
        elif format_type == 'json':
            return await self.generate_json_package(export_data)
        elif format_type == 'tar':
            return await self.generate_tar_package(export_data)
        
        raise ValueError(f"Unsupported format: {format_type}")
    
    async def generate_hjx_package(self, export_data):
        """Generate HJX format package (compressed JSON)"""
        
        json_content = json.dumps(export_data, indent=2)
        compressed_content = gzip.compress(json_content.encode('utf-8'))
        
        return {
            'format': 'hjx',
            'filename': f"{export_data['honey_jar']['name']}.hjx",
            'content': compressed_content,
            'mime_type': 'application/x-hjx',
            'size': len(compressed_content)
        }
    
    async def generate_tar_package(self, export_data):
        """Generate TAR archive package"""
        
        import tarfile
        import io
        
        tar_buffer = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add manifest
            manifest = {
                'honey_jar': export_data['honey_jar'],
                'export_metadata': export_data['export_metadata']
            }
            manifest_json = json.dumps(manifest, indent=2)
            manifest_info = tarfile.TarInfo(name='manifest.json')
            manifest_info.size = len(manifest_json)
            tar.addfile(manifest_info, io.BytesIO(manifest_json.encode()))
            
            # Add documents
            for doc in export_data['documents']:
                # Add original file if available
                if 'file_data' in doc:
                    file_data = base64.b64decode(doc['file_data'])
                    file_info = tarfile.TarInfo(name=f"documents/{doc['filename']}")
                    file_info.size = len(file_data)
                    tar.addfile(file_info, io.BytesIO(file_data))
                
                # Add extracted text
                if 'chunks' in doc and doc['chunks']:
                    text_content = '\n\n'.join([chunk['content'] for chunk in doc['chunks']])
                    text_filename = f"extracted_text/{os.path.splitext(doc['filename'])[0]}.txt"
                    text_info = tarfile.TarInfo(name=text_filename)
                    text_info.size = len(text_content.encode())
                    tar.addfile(text_info, io.BytesIO(text_content.encode()))
            
            # Add embeddings
            if 'vector_index' in export_data:
                embeddings_json = json.dumps(export_data['vector_index'], indent=2)
                embeddings_info = tarfile.TarInfo(name='embeddings/vectors.json')
                embeddings_info.size = len(embeddings_json)
                tar.addfile(embeddings_info, io.BytesIO(embeddings_json.encode()))
        
        tar_content = tar_buffer.getvalue()
        
        return {
            'format': 'tar',
            'filename': f"{export_data['honey_jar']['name']}.tar.gz",
            'content': tar_content,
            'mime_type': 'application/gzip',
            'size': len(tar_content)
        }
```

## Import Implementation

### Import Engine

```python
# knowledge_service/core/import_engine.py
class HoneyJarImportEngine:
    def __init__(self, honeycomb_manager, file_service):
        self.honeycomb = honeycomb_manager
        self.file_service = file_service
        self.supported_formats = ['hjx', 'json', 'tar']
    
    async def import_honey_jar(self, import_data, user_id, 
                              conflict_resolution='rename',
                              preserve_permissions=False,
                              progress_callback=None):
        """Import a honey jar from export data"""
        
        try:
            # Step 1: Validate and parse import data
            if progress_callback:
                progress_callback(10, "Validating import data")
            
            parsed_data = await self.parse_import_data(import_data)
            
            # Step 2: Validate compatibility
            if progress_callback:
                progress_callback(20, "Checking compatibility")
            
            validation_result = await self.validate_import_compatibility(parsed_data)
            if not validation_result['valid']:
                raise ImportError(f"Incompatible import: {validation_result['errors']}")
            
            # Step 3: Handle naming conflicts
            if progress_callback:
                progress_callback(30, "Resolving conflicts")
            
            resolved_data = await self.resolve_naming_conflicts(
                parsed_data, conflict_resolution
            )
            
            # Step 4: Create honey jar
            if progress_callback:
                progress_callback(40, "Creating honey jar")
            
            honey_jar = await self.create_honey_jar(resolved_data, user_id, preserve_permissions)
            
            # Step 5: Import documents
            if progress_callback:
                progress_callback(60, "Importing documents")
            
            await self.import_documents(honey_jar['id'], resolved_data['documents'])
            
            # Step 6: Import vector embeddings
            if 'vector_index' in resolved_data:
                if progress_callback:
                    progress_callback(80, "Importing vector embeddings")
                
                await self.import_embeddings(honey_jar['id'], resolved_data['vector_index'])
            
            # Step 7: Finalize import
            if progress_callback:
                progress_callback(100, "Import completed")
            
            return {
                'success': True,
                'honey_jar_id': honey_jar['id'],
                'honey_jar_name': honey_jar['name'],
                'documents_imported': len(resolved_data['documents']),
                'embeddings_imported': len(resolved_data.get('vector_index', {}).get('vectors', [])),
                'warnings': validation_result.get('warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise ImportError(f"Import failed: {str(e)}")
    
    async def parse_import_data(self, import_data):
        """Parse import data based on format"""
        
        # Detect format
        if isinstance(import_data, dict):
            format_type = import_data.get('format', 'json')
        else:
            # Try to detect from content
            try:
                # Try to decompress as HJX
                decompressed = gzip.decompress(import_data)
                parsed = json.loads(decompressed.decode('utf-8'))
                format_type = parsed.get('format', 'hjx')
                import_data = parsed
            except:
                try:
                    # Try to parse as JSON
                    if isinstance(import_data, bytes):
                        import_data = import_data.decode('utf-8')
                    parsed = json.loads(import_data)
                    format_type = parsed.get('format', 'json')
                    import_data = parsed
                except:
                    # Assume TAR format
                    format_type = 'tar'
        
        if format_type == 'tar':
            return await self.parse_tar_import(import_data)
        else:
            return import_data
    
    async def parse_tar_import(self, tar_data):
        """Parse TAR format import"""
        
        import tarfile
        import io
        
        if isinstance(tar_data, bytes):
            tar_buffer = io.BytesIO(tar_data)
        else:
            tar_buffer = tar_data
        
        parsed_data = {
            'format': 'tar',
            'documents': [],
            'honey_jar': {},
            'vector_index': {}
        }
        
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            # Extract manifest
            try:
                manifest_file = tar.extractfile('manifest.json')
                manifest = json.loads(manifest_file.read().decode('utf-8'))
                parsed_data['honey_jar'] = manifest['honey_jar']
                parsed_data['export_metadata'] = manifest.get('export_metadata', {})
            except KeyError:
                raise ImportError("Invalid TAR import: missing manifest.json")
            
            # Extract documents
            document_files = {}
            text_files = {}
            
            for member in tar.getmembers():
                if member.name.startswith('documents/'):
                    filename = os.path.basename(member.name)
                    file_data = tar.extractfile(member).read()
                    document_files[filename] = file_data
                
                elif member.name.startswith('extracted_text/'):
                    filename = os.path.basename(member.name)
                    text_content = tar.extractfile(member).read().decode('utf-8')
                    text_files[filename] = text_content
                
                elif member.name == 'embeddings/vectors.json':
                    embeddings_data = tar.extractfile(member).read()
                    parsed_data['vector_index'] = json.loads(embeddings_data.decode('utf-8'))
            
            # Combine document and text data
            for filename, file_data in document_files.items():
                base_name = os.path.splitext(filename)[0]
                text_filename = f"{base_name}.txt"
                
                doc_data = {
                    'filename': filename,
                    'file_data': base64.b64encode(file_data).decode('utf-8'),
                    'size_bytes': len(file_data),
                    'checksum_sha256': hashlib.sha256(file_data).hexdigest()
                }
                
                if text_filename in text_files:
                    # Convert text back to chunks
                    text_content = text_files[text_filename]
                    doc_data['chunks'] = [{
                        'chunk_id': f"imported-{uuid.uuid4()}",
                        'content': text_content,
                        'start_position': 0,
                        'end_position': len(text_content),
                        'chunk_index': 0
                    }]
                
                parsed_data['documents'].append(doc_data)
        
        return parsed_data
    
    async def validate_import_compatibility(self, import_data):
        """Validate import data compatibility"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check format version compatibility
        import_version = import_data.get('version', '1.0')
        if not self.is_version_compatible(import_version):
            validation_result['errors'].append(
                f"Incompatible format version: {import_version}"
            )
            validation_result['valid'] = False
        
        # Validate honey jar structure
        if 'honey_jar' not in import_data:
            validation_result['errors'].append("Missing honey jar metadata")
            validation_result['valid'] = False
        
        # Validate documents
        if 'documents' not in import_data:
            validation_result['warnings'].append("No documents found in import")
        else:
            for i, doc in enumerate(import_data['documents']):
                if 'filename' not in doc:
                    validation_result['errors'].append(
                        f"Document {i} missing filename"
                    )
                    validation_result['valid'] = False
        
        # Validate embeddings compatibility
        if 'vector_index' in import_data:
            vector_data = import_data['vector_index']
            current_model = "all-MiniLM-L6-v2"  # Default model
            
            if vector_data.get('model_name') != current_model:
                validation_result['warnings'].append(
                    f"Embedding model mismatch: import uses {vector_data.get('model_name')}, "
                    f"system uses {current_model}. Vectors will be regenerated."
                )
        
        return validation_result
    
    async def import_embeddings(self, honey_jar_id, vector_index_data):
        """Import vector embeddings into ChromaDB"""
        
        collection_name = f"honey_jar_{honey_jar_id}"
        
        try:
            # Create or get collection
            collection = self.honeycomb.get_or_create_collection(
                collection_name,
                metadata=vector_index_data.get('index_parameters', {})
            )
            
            # Prepare batch data
            batch_size = 100
            vectors = vector_index_data.get('vectors', [])
            
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                
                ids = [v['id'] for v in batch]
                documents = [v['document'] for v in batch]
                metadatas = [v['metadata'] for v in batch]
                embeddings = [v['vector'] for v in batch]
                
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
            
            logger.info(f"Imported {len(vectors)} embeddings for honey jar {honey_jar_id}")
            
        except Exception as e:
            logger.error(f"Failed to import embeddings: {e}")
            raise ImportError(f"Embedding import failed: {str(e)}")
```

## API Endpoints

### Export API

```python
# knowledge_service/app.py
@app.route('/honey-jars/<honey_jar_id>/export', methods=['POST'])
@require_auth
async def export_honey_jar(honey_jar_id):
    """Export a honey jar"""
    
    data = request.get_json() or {}
    
    export_format = data.get('format', 'hjx')
    include_embeddings = data.get('include_embeddings', True)
    include_files = data.get('include_files', True)
    
    # Validate user access
    if not await user_can_access_honey_jar(get_current_user_id(), honey_jar_id, 'read'):
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        export_engine = HoneyJarExportEngine(honeycomb_manager, file_service)
        
        # Create background job for large exports
        if data.get('async', False):
            job_id = str(uuid.uuid4())
            
            # Queue export job
            export_job = {
                'job_id': job_id,
                'honey_jar_id': honey_jar_id,
                'format': export_format,
                'options': {
                    'include_embeddings': include_embeddings,
                    'include_files': include_files
                },
                'user_id': get_current_user_id()
            }
            
            queue_manager.add_job('exports', export_job)
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'status': 'queued',
                'message': 'Export queued for processing'
            })
        
        else:
            # Synchronous export for smaller honey jars
            export_data = await export_engine.export_honey_jar(
                honey_jar_id,
                export_format=export_format,
                include_embeddings=include_embeddings,
                include_files=include_files
            )
            
            return send_file(
                io.BytesIO(export_data['content']),
                as_attachment=True,
                download_name=export_data['filename'],
                mimetype=export_data['mime_type']
            )
    
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return jsonify({'error': 'Export failed'}), 500

@app.route('/honey-jars/import', methods=['POST'])
@require_auth
async def import_honey_jar():
    """Import a honey jar"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get import options
    conflict_resolution = request.form.get('conflict_resolution', 'rename')
    preserve_permissions = request.form.get('preserve_permissions', 'false').lower() == 'true'
    async_import = request.form.get('async', 'false').lower() == 'true'
    
    try:
        file_content = file.read()
        
        if async_import:
            # Queue import job for large files
            job_id = str(uuid.uuid4())
            
            # Store file temporarily
            temp_file_id = await store_temp_file(file_content, file.filename)
            
            import_job = {
                'job_id': job_id,
                'temp_file_id': temp_file_id,
                'filename': file.filename,
                'options': {
                    'conflict_resolution': conflict_resolution,
                    'preserve_permissions': preserve_permissions
                },
                'user_id': get_current_user_id()
            }
            
            queue_manager.add_job('imports', import_job)
            
            return jsonify({
                'success': True,
                'job_id': job_id,
                'status': 'queued',
                'message': 'Import queued for processing'
            })
        
        else:
            # Synchronous import
            import_engine = HoneyJarImportEngine(honeycomb_manager, file_service)
            
            result = await import_engine.import_honey_jar(
                file_content,
                user_id=get_current_user_id(),
                conflict_resolution=conflict_resolution,
                preserve_permissions=preserve_permissions
            )
            
            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

@app.route('/honey-jars/export-jobs/<job_id>', methods=['GET'])
@require_auth
async def get_export_job_status(job_id):
    """Get export job status"""
    
    job_status = queue_manager.get_job_status(job_id)
    
    if not job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    # If job is completed and user owns it, provide download link
    if (job_status['status'] == 'completed' and 
        job_status['user_id'] == get_current_user_id()):
        
        download_url = f"/honey-jars/export-jobs/{job_id}/download"
        job_status['download_url'] = download_url
    
    return jsonify(job_status)
```

## Frontend Integration

### Export/Import UI

```javascript
// Frontend component for export/import operations
const HoneyJarPortability = ({ honeyJarId, honeyJarName }) => {
  const [exportFormat, setExportFormat] = useState('hjx');
  const [exportOptions, setExportOptions] = useState({
    include_embeddings: true,
    include_files: true,
    async: false
  });
  const [exportProgress, setExportProgress] = useState(null);
  const [importProgress, setImportProgress] = useState(null);
  
  const handleExport = async () => {
    try {
      setExportProgress({ status: 'starting', progress: 0 });
      
      const response = await fetch(`/api/knowledge/honey-jars/${honeyJarId}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format: exportFormat,
          ...exportOptions
        })
      });
      
      if (exportOptions.async) {
        // Handle async export
        const result = await response.json();
        const jobId = result.job_id;
        
        // Poll for completion
        const pollInterval = setInterval(async () => {
          const statusResponse = await fetch(`/api/knowledge/honey-jars/export-jobs/${jobId}`);
          const status = await statusResponse.json();
          
          setExportProgress({
            status: status.status,
            progress: status.progress || 0,
            message: status.message
          });
          
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            // Trigger download
            window.location.href = status.download_url;
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setExportProgress({ status: 'failed', error: status.error });
          }
        }, 2000);
        
      } else {
        // Handle sync export
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${honeyJarName}.${exportFormat}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        setExportProgress({ status: 'completed', progress: 100 });
      }
      
    } catch (error) {
      setExportProgress({ status: 'failed', error: error.message });
    }
  };
  
  const handleImport = async (file) => {
    try {
      setImportProgress({ status: 'starting', progress: 0 });
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('conflict_resolution', 'rename');
      formData.append('async', file.size > 50 * 1024 * 1024 ? 'true' : 'false'); // 50MB threshold
      
      const response = await fetch('/api/knowledge/honey-jars/import', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.job_id) {
        // Handle async import
        const jobId = result.job_id;
        
        const pollInterval = setInterval(async () => {
          const statusResponse = await fetch(`/api/knowledge/honey-jars/import-jobs/${jobId}`);
          const status = await statusResponse.json();
          
          setImportProgress({
            status: status.status,
            progress: status.progress || 0,
            message: status.message
          });
          
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            // Refresh honey jar list
            onImportComplete(status);
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            setImportProgress({ status: 'failed', error: status.error });
          }
        }, 2000);
        
      } else {
        // Sync import completed
        setImportProgress({ status: 'completed', progress: 100 });
        onImportComplete(result);
      }
      
    } catch (error) {
      setImportProgress({ status: 'failed', error: error.message });
    }
  };
  
  return (
    <div className="honey-jar-portability">
      {/* Export Section */}
      <div className="export-section">
        <h3>Export Honey Jar</h3>
        
        <div className="format-selection">
          <label>Export Format:</label>
          <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
            <option value="hjx">HJX (Full Fidelity)</option>
            <option value="json">JSON (Lightweight)</option>
            <option value="tar">TAR Archive (Files)</option>
          </select>
        </div>
        
        <div className="export-options">
          <label>
            <input
              type="checkbox"
              checked={exportOptions.include_embeddings}
              onChange={(e) => setExportOptions({
                ...exportOptions,
                include_embeddings: e.target.checked
              })}
            />
            Include Vector Embeddings
          </label>
          
          <label>
            <input
              type="checkbox"
              checked={exportOptions.include_files}
              onChange={(e) => setExportOptions({
                ...exportOptions,
                include_files: e.target.checked
              })}
            />
            Include Original Files
          </label>
        </div>
        
        <button onClick={handleExport} disabled={exportProgress?.status === 'starting'}>
          {exportProgress?.status === 'starting' ? 'Exporting...' : 'Export Honey Jar'}
        </button>
        
        {exportProgress && (
          <div className="progress-indicator">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${exportProgress.progress}%` }}
              />
            </div>
            <span>{exportProgress.message || exportProgress.status}</span>
          </div>
        )}
      </div>
      
      {/* Import Section */}
      <div className="import-section">
        <h3>Import Honey Jar</h3>
        
        <div className="file-drop-zone">
          <input
            type="file"
            accept=".hjx,.json,.tar.gz"
            onChange={(e) => e.target.files[0] && handleImport(e.target.files[0])}
          />
          <p>Drop HJX, JSON, or TAR files here to import</p>
        </div>
        
        {importProgress && (
          <div className="progress-indicator">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${importProgress.progress}%` }}
              />
            </div>
            <span>{importProgress.message || importProgress.status}</span>
          </div>
        )}
      </div>
    </div>
  );
};
```

## Security Considerations

### Access Control

- **Export Permissions**: Users must have 'read' access to export honey jars
- **Import Validation**: All imports validated for malicious content
- **User Isolation**: Imports create honey jars owned by importing user
- **Content Scanning**: Files scanned for malware and inappropriate content

### Data Protection

```python
class SecureImportHandler:
    def __init__(self):
        self.max_file_size = 1024 * 1024 * 1024  # 1GB limit
        self.allowed_formats = ['hjx', 'json', 'tar']
        self.virus_scanner = VirusScanner()
    
    def validate_import_security(self, import_data, filename):
        """Validate import for security issues"""
        
        # Check file size
        if len(import_data) > self.max_file_size:
            raise SecurityError("File too large")
        
        # Scan for malware
        scan_result = self.virus_scanner.scan_bytes(import_data)
        if scan_result['infected']:
            raise SecurityError(f"Malware detected: {scan_result['threat']}")
        
        # Validate content structure
        if filename.endswith('.hjx'):
            self.validate_hjx_structure(import_data)
        elif filename.endswith('.json'):
            self.validate_json_structure(import_data)
        elif filename.endswith('.tar.gz'):
            self.validate_tar_structure(import_data)
        
        return True
    
    def sanitize_honey_jar_metadata(self, metadata):
        """Sanitize metadata to prevent injection"""
        
        sanitized = {}
        
        # Whitelist allowed fields
        allowed_fields = ['name', 'description', 'type', 'tags']
        
        for field in allowed_fields:
            if field in metadata:
                value = metadata[field]
                
                # Sanitize strings
                if isinstance(value, str):
                    # Remove potentially dangerous characters
                    value = re.sub(r'[<>"\';\\]', '', value)
                    value = value[:1000]  # Limit length
                
                sanitized[field] = value
        
        return sanitized
```

## Troubleshooting

### Common Issues

#### Export Timeouts

**Symptoms:**
- Export operations timing out
- Large honey jars failing to export

**Solutions:**
```python
# Increase timeout limits
EXPORT_TIMEOUT = 1800  # 30 minutes

# Use async exports for large honey jars
async_threshold = 100 * 1024 * 1024  # 100MB

if estimated_size > async_threshold:
    return queue_export_job(honey_jar_id, options)
```

#### Import Format Errors

**Symptoms:**
- "Invalid format" errors
- Corrupted import files

**Solutions:**
```bash
# Validate HJX files
python -c "
import gzip, json
with open('honey_jar.hjx', 'rb') as f:
    data = gzip.decompress(f.read())
    json.loads(data.decode('utf-8'))
print('Valid HJX format')
"

# Check TAR archives
tar -tzf honey_jar.tar.gz | head -10
```

#### Memory Issues During Large Imports

**Symptoms:**
- Import process killed (OOM)
- System becomes unresponsive

**Solutions:**
```python
# Implement streaming import for large files
class StreamingImportHandler:
    def __init__(self, batch_size=1000):
        self.batch_size = batch_size
    
    async def stream_import_documents(self, documents):
        """Process documents in batches to avoid memory issues"""
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            await self.process_document_batch(batch)
            
            # Clear memory
            import gc
            gc.collect()
```

## Future Enhancements

### Planned Features

1. **Incremental Exports**: Export only changes since last export
2. **Selective Import**: Import specific documents or metadata only
3. **Cross-Platform Compatibility**: Import from other knowledge systems
4. **Automated Backups**: Scheduled honey jar backups
5. **Cloud Storage Integration**: Direct export/import to cloud services

### Integration Roadmap

- **Version Control**: Track changes and enable rollback
- **Collaboration**: Multi-user import/export workflows  
- **API Enhancements**: Bulk operations and batch processing
- **Analytics**: Track usage patterns and optimize formats

---

**Note**: The Honey Jar Export/Import system provides comprehensive portability for STING-CE knowledge collections while maintaining security, data integrity, and performance. It enables seamless migration, backup, and sharing of curated knowledge bases across different STING instances and environments.