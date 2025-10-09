# API Overview

STING CE Developer Preview provides RESTful APIs for all core services.

## Base URLs

- **Backend API**: `http://localhost:5050`
- **Knowledge Service**: `http://localhost:8090`
- **Chatbot Service**: `http://localhost:8888`
- **External AI Service**: `http://localhost:8091`
- **Messaging Service**: `http://localhost:8889`
- **Kratos Public**: `http://localhost:4433`
- **Kratos Admin**: `http://localhost:4434`

## Authentication

STING uses Ory Kratos for passwordless authentication:

### Session-Based Authentication

```bash
# 1. Initiate login flow
curl http://localhost:4433/self-service/login/browser

# 2. Submit identifier (email)
curl -X POST http://localhost:4433/self-service/login?flow=<flow_id> \
  -H "Content-Type: application/json" \
  -d '{"identifier": "user@example.com", "method": "link"}'

# 3. Check email for magic link
# Click link to establish session

# 4. Use session cookie in subsequent requests
curl http://localhost:5050/api/profile \
  -H "Cookie: ory_kratos_session=<session_token>"
```

### API Key Authentication (Nectar Bots)

```bash
# Create API key via web interface or CLI
# Use in X-API-Key header

curl http://localhost:8091/api/chat \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, Bee!"}'
```

## Core API Endpoints

### Backend API (`/api`)

#### Health Check
```
GET /health
```

#### User Profile
```
GET /api/profile
POST /api/profile
PUT /api/profile
```

#### Honey Jar (Documents)
```
GET /api/honey-jar              # List documents
POST /api/honey-jar             # Upload document
GET /api/honey-jar/{id}         # Get document
DELETE /api/honey-jar/{id}      # Delete document
```

#### Honey Reserve (Encrypted Storage)
```
GET /api/honey-reserve          # List files
POST /api/honey-reserve         # Upload file
GET /api/honey-reserve/{id}     # Download file
DELETE /api/honey-reserve/{id}  # Delete file
GET /api/honey-reserve/quota    # Check quota
```

#### Nectar Bots (API Keys)
```
GET /api/nectar-bots            # List API keys
POST /api/nectar-bots           # Create API key
DELETE /api/nectar-bots/{id}    # Revoke API key
GET /api/nectar-bots/{id}/usage # Usage statistics
```

### Knowledge Service

#### Search
```
POST /api/search
{
  "query": "search query",
  "top_k": 5,
  "collection": "default"
}
```

#### Document Ingestion
```
POST /api/ingest
{
  "content": "document content",
  "metadata": {
    "title": "Document Title",
    "source": "upload"
  }
}
```

### Chatbot Service

#### Chat Completion
```
POST /api/chat
{
  "message": "Your question here",
  "context": {
    "conversation_id": "uuid",
    "use_knowledge_base": true
  }
}
```

#### Streaming Chat
```
POST /api/chat/stream
{
  "message": "Your question here",
  "stream": true
}
```

### External AI Service

#### Generate Completion
```
POST /api/generate
{
  "model": "phi3:latest",
  "prompt": "Your prompt",
  "options": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

#### List Models
```
GET /api/models
```

### Messaging Service

#### Send Message
```
POST /api/messages
{
  "recipient": "user-id",
  "content": "Message content",
  "encrypted": true
}
```

#### Get Messages
```
GET /api/messages?conversation_id=<id>
```

## Response Formats

All APIs return JSON responses:

### Success Response
```json
{
  "status": "success",
  "data": {
    // Response data
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

## Rate Limiting

- **Authenticated requests**: 1000 requests/hour
- **Nectar Bot API**: Based on tier (see pricing)
- **Unauthenticated**: 100 requests/hour

## Pagination

APIs that return lists support pagination:

```
GET /api/resource?page=1&per_page=20
```

Response includes pagination metadata:

```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `UNAUTHORIZED` | Missing or invalid authentication |
| `FORBIDDEN` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Invalid request data |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

## WebSocket APIs

### Real-time Chat (Messaging Service)

```javascript
const ws = new WebSocket('ws://localhost:8889/ws/chat');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'subscribe',
    conversation_id: 'uuid'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

## Examples

See `docs/api/examples/` for complete code examples in:
- Python
- JavaScript/Node.js
- cURL

## API Versioning

APIs are currently at version 1. Future versions will be available at:
- `/api/v2/...`
- `/api/v3/...`

## SDK Support

Official SDKs (coming soon):
- Python SDK
- JavaScript SDK
- Go SDK
