# Honey Jar Technical Reference

## API Endpoints

### Honey Jar Management

#### Create Honey Jar
```http
POST /api/knowledge/honey-jars
Content-Type: application/json

{
  "name": "string",
  "description": "string",
  "type": "public|private|team|restricted",
  "tags": ["string"]
}
```

#### List Honey Jars
```http
GET /api/knowledge/honey-jars?page=1&page_size=20
```

#### Get Specific Honey Jar
```http
GET /api/knowledge/honey-jars/{honey_jar_id}
```

#### Delete Honey Jar
```http
DELETE /api/knowledge/honey-jars/{honey_jar_id}
```

### Document Management

#### Upload Documents
```http
POST /api/knowledge/honey-jars/{honey_jar_id}/documents
Content-Type: multipart/form-data

files: File[] (multiple files supported)
metadata: JSON string (optional)
```

Supported formats:
- PDF (.pdf)
- Word (.doc, .docx)
- Text (.txt)
- Markdown (.md)
- HTML (.html)
- JSON (.json)

#### List Documents
```http
GET /api/knowledge/honey-jars/{honey_jar_id}/documents
```

#### Delete Document
```http
DELETE /api/knowledge/honey-jars/{honey_jar_id}/documents/{document_id}
```

### Search Operations

#### Search Across Honey Jars
```http
POST /api/knowledge/search
Content-Type: application/json

{
  "query": "string",
  "top_k": 5  // Number of results
}
```

#### Get Bee Context
```http
POST /api/knowledge/bee/context
Content-Type: application/json

{
  "query": "string",
  "user_id": "string",
  "limit": 5,
  "honey_jar_id": "string"  // Optional: filter to specific jar
}
```

### Export/Import

#### Export Honey Jar
```http
GET /api/knowledge/honey-jars/{honey_jar_id}/export?format=hjx|json|tar
```

Export formats:
- `hjx`: STING Honey Jar Export (tar.gz with manifest.json)
- `json`: Plain JSON export
- `tar`: TAR archive of documents

#### Import Honey Jar
```http
POST /api/knowledge/honey-jars/import
Content-Type: multipart/form-data

file: .hjx file
```

## Data Models

### Honey Jar Schema
```python
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "type": "public|private|team|restricted",
  "status": "active|archived|processing",
  "owner": "string",
  "created_date": "datetime",
  "last_updated": "datetime",
  "tags": ["string"],
  "stats": {
    "document_count": 0,
    "embedding_count": 0,
    "total_size_bytes": 0,
    "last_accessed": "datetime",
    "query_count": 0,
    "average_query_time": 0.0
  }
}
```

### Document Schema
```python
{
  "id": "uuid",
  "honey_jar_id": "uuid",
  "filename": "string",
  "content_type": "string",
  "size_bytes": 0,
  "upload_date": "datetime",
  "status": "processing|ready|error",
  "metadata": {},
  "file_path": "string"  // Internal only
}
```

### HJX Format Specification

The HJX (Honey Jar Export) format is a tar.gz archive containing:

```
honey_jar_name.hjx/
├── manifest.json       # Honey jar metadata and document index
└── documents/         # Directory containing all documents
    ├── document1.pdf
    ├── document2.md
    └── ...
```

Manifest structure:
```json
{
  "version": "1.0",
  "export_date": "ISO 8601 datetime",
  "honey_jar": {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "type": "string",
    "tags": ["string"],
    "created_date": "ISO 8601 datetime",
    "stats": {}
  },
  "documents": [
    {
      "id": "uuid",
      "filename": "string",
      "content_type": "string",
      "size_bytes": 0,
      "upload_date": "ISO 8601 datetime",
      "metadata": {}
    }
  ]
}
```

## Frontend Integration

### React Components

#### HoneyPotPage Component
Main component at `/frontend/src/components/pages/HoneyPotPage.jsx`

Key features:
- Grid display of honey jars
- Modal for detailed view
- File upload with progress tracking
- Export dropdown menu
- Query with Bee integration

#### Integration with BeeChat
```javascript
// Navigate to chat with honey jar context
navigate('/dashboard/chat', { 
  state: { 
    honeyJarContext: {
      id: honeyJar.id,
      name: honeyJar.name,
      description: honeyJar.description,
      documentCount: honeyJar.stats?.document_count || 0
    },
    initialMessage: "Initial question about the honey jar"
  }
});
```

BeeChat receives context and:
- Displays active honey jar badge
- Filters searches to that honey jar
- Provides clear context button

### API Client

Located at `/frontend/src/services/knowledgeApi.js`

```javascript
// Example usage
import { honeyJarApi, knowledgeApi } from './services/knowledgeApi';

// Create honey jar
const newJar = await honeyJarApi.createHoneyJar({
  name: "My Knowledge Base",
  description: "Description",
  type: "private"
});

// Upload documents
const formData = new FormData();
formData.append('files', fileObject);
await honeyJarApi.uploadDocuments(jarId, formData);

// Search
const results = await knowledgeApi.search({
  query: "search term",
  top_k: 10
});
```

## Backend Architecture

### Service Configuration
- Port: 8090
- Framework: FastAPI
- Database: In-memory (development) / PostgreSQL (production)
- Vector DB: ChromaDB (when available)

### Document Processing Pipeline

1. **Upload**: Documents received via multipart form
2. **Storage**: Saved to `/tmp/sting_uploads/{honey_jar_id}/`
3. **Processing**: (Future) NectarProcessor extracts text
4. **Embedding**: (Future) Generate vector embeddings
5. **Indexing**: (Future) Store in ChromaDB

### Security Considerations

- File size limits: 50MB per file
- Allowed formats validated server-side
- Path traversal protection in file operations
- User permissions checked for each operation
- Temporary files cleaned up after processing

## Deployment Notes

### Environment Variables
```bash
KNOWLEDGE_PORT=8090
KNOWLEDGE_HOST=0.0.0.0
CHROMA_URL=http://chroma:8000
```

### Docker Configuration
Service defined in `docker-compose.yml`:
- Health check: `/health` endpoint
- Volumes for data persistence
- Network alias: `knowledge`

### Proxy Configuration
Frontend proxies `/api/knowledge` to the knowledge service:
```javascript
app.use('/api/knowledge', createProxyMiddleware({
  target: 'http://sting-ce-knowledge:8090',
  changeOrigin: true,
  pathRewrite: { '^/api/knowledge': '' }
}));
```

## Future Enhancements

### Planned Features
1. **NectarProcessor Integration**: Full document processing pipeline
2. **ChromaDB Integration**: Vector storage and similarity search
3. **Real-time Processing**: WebSocket updates for processing status
4. **Advanced Permissions**: Team and role-based access control
5. **Versioning**: Document version history
6. **Collaboration**: Comments and annotations
7. **Analytics**: Usage statistics and insights

### API Roadmap
- Batch operations for documents
- Streaming uploads for large files
- WebSocket notifications
- GraphQL endpoint for complex queries
- Webhook integration for external systems