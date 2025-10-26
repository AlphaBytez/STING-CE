# STING Platform API Reference

## Overview

The STING Platform provides a comprehensive REST API for all system functionality, including authentication, chat interactions, knowledge management, and system administration.

**Base URL:** `https://localhost:5050/api`  
**Authentication:** Session-based with Ory Kratos integration  
**Content-Type:** `application/json`  
**API Version:** v1

## Authentication APIs

### Session Management

#### Check Authentication Status
```http
GET /api/auth/session
```

**Response:**
```json
{
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "traits": {
      "name": "User Name"
    }
  },
  "session_id": "session_uuid"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "session_token": "session_token_here",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

#### Logout
```http
POST /api/auth/logout
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

#### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "secure_password",
  "traits": {
    "name": "New User"
  }
}
```

### WebAuthn (Passwordless)

#### Initialize WebAuthn Registration
```http
POST /api/auth/webauthn/register/init
```

#### Complete WebAuthn Registration
```http
POST /api/auth/webauthn/register/complete
Content-Type: application/json

{
  "credential": "webauthn_credential_object"
}
```

#### Initialize WebAuthn Login
```http
POST /api/auth/webauthn/login/init
```

#### Complete WebAuthn Login
```http
POST /api/auth/webauthn/login/complete
Content-Type: application/json

{
  "assertion": "webauthn_assertion_object"
}
```

## Chat & AI APIs

### Conversation Management

#### Send Message to Bee
```http
POST /api/chat/message
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "message": "Hello, what can you help me with?",
  "conversation_id": "optional_conversation_uuid",
  "context": {
    "model": "phi3",
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

**Response:**
```json
{
  "response": "Hello! I'm Bee, your STING assistant. I can help you with...",
  "conversation_id": "conversation_uuid",
  "message_id": "message_uuid",
  "model_used": "phi3",
  "response_time": 1.23,
  "metadata": {
    "tokens_used": 156,
    "model_load_time": 0.45
  }
}
```

#### Get Conversation History
```http
GET /api/chat/conversations/{conversation_id}
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:30:00Z",
  "messages": [
    {
      "id": "message_uuid",
      "type": "user",
      "content": "Hello",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    {
      "id": "message_uuid",
      "type": "assistant",
      "content": "Hello! How can I help you?",
      "timestamp": "2024-01-01T00:00:01Z",
      "model": "phi3"
    }
  ]
}
```

#### List User Conversations
```http
GET /api/chat/conversations
Authorization: Bearer <session_token>
Query Parameters:
  - limit: number (default: 20)
  - offset: number (default: 0)
  - sort: string (created_at|updated_at, default: updated_at)
  - order: string (asc|desc, default: desc)
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "uuid",
      "title": "STING Platform Discussion",
      "last_message": "Thanks for the help!",
      "updated_at": "2024-01-01T00:30:00Z",
      "message_count": 12
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

#### Delete Conversation
```http
DELETE /api/chat/conversations/{conversation_id}
Authorization: Bearer <session_token>
```

#### Get Conversation Token Usage
```http
GET /api/chat/conversations/{conversation_id}/token-usage
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "total": 2847,
  "by_role": {
    "system": 512,
    "user": 1203,
    "assistant": 1132
  },
  "context_limit": 4096,
  "max_allowed_tokens": 3276,
  "utilization_percent": 86.9,
  "model": "llama3.2:latest",
  "last_pruning": {
    "timestamp": "2024-01-01T00:30:00Z",
    "messages_pruned": 15,
    "tokens_saved": 1200
  }
}
```

#### Manually Prune Conversation
```http
POST /api/chat/conversations/{conversation_id}/prune
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "success": true,
  "pruning_result": {
    "messages_pruned": 15,
    "messages_kept": 10,
    "tokens_before": 4200,
    "tokens_after": 1800,
    "summary": "User discussed project setup, asked about deployment options..."
  }
}
```

**Note:** Pruning is only available when database persistence is enabled. The system uses tiktoken for accurate token counting across different model families.

### Model Management

#### List Available Models
```http
GET /api/chat/models
```

**Response:**
```json
{
  "models": [
    {
      "name": "phi3",
      "display_name": "Phi-3 Medium",
      "description": "Microsoft's enterprise-grade model",
      "parameters": "14B",
      "size": "8GB",
      "capabilities": ["chat", "reasoning", "code"],
      "status": "loaded",
      "last_used": "2024-01-01T00:30:00Z"
    },
    {
      "name": "deepseek-1.5b",
      "display_name": "DeepSeek R1 Distill",
      "description": "Reasoning model with code capabilities",
      "parameters": "1.5B",
      "size": "3GB",
      "capabilities": ["reasoning", "code"],
      "status": "available",
      "last_used": null
    }
  ],
  "default_model": "phi3",
  "loaded_models": ["phi3"],
  "max_loaded": 2
}
```

#### Get Model Status
```http
GET /api/chat/models/{model_name}
```

**Response:**
```json
{
  "name": "phi3",
  "status": "loaded",
  "memory_usage": "7.8GB",
  "load_time": "4.2s",
  "inference_count": 156,
  "last_used": "2024-01-01T00:30:00Z",
  "hardware": "mps",
  "performance": {
    "avg_response_time": 1.23,
    "tokens_per_second": 45.6
  }
}
```

#### Load Model
```http
POST /api/chat/models/{model_name}/load
Authorization: Bearer <session_token>
```

#### Unload Model
```http
POST /api/chat/models/{model_name}/unload
Authorization: Bearer <session_token>
```

## Knowledge Management APIs

### Honey Jar Management

#### Create Honey Jar
```http
POST /api/knowledge/honey-pots
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "name": "Company Handbook",
  "description": "Internal policies and procedures",
  "visibility": "private",
  "tags": ["hr", "policies", "handbook"],
  "settings": {
    "allow_search": true,
    "allow_export": false,
    "encryption_enabled": true
  }
}
```

**Response:**
```json
{
  "id": "honey_jar_uuid",
  "name": "Company Handbook",
  "description": "Internal policies and procedures",
  "owner_id": "user_uuid",
  "visibility": "private",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "document_count": 0,
  "embedding_count": 0,
  "tags": ["hr", "policies", "handbook"]
}
```

#### List Honey Pots
```http
GET /api/knowledge/honey-pots
Authorization: Bearer <session_token>
Query Parameters:
  - visibility: string (public|private|shared)
  - owner: string (user_id)
  - tag: string (filter by tag)
  - search: string (text search)
  - limit: number (default: 20)
  - offset: number (default: 0)
```

**Response:**
```json
{
  "honey_jars": [
    {
      "id": "uuid",
      "name": "Company Handbook",
      "description": "Internal policies and procedures",
      "visibility": "private",
      "document_count": 25,
      "embedding_count": 1250,
      "last_updated": "2024-01-01T00:30:00Z",
      "tags": ["hr", "policies"],
      "owner": {
        "id": "user_uuid",
        "name": "Admin User"
      }
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

#### Get Honey Jar Details
```http
GET /api/knowledge/honey-pots/{honey_jar_id}
Authorization: Bearer <session_token>
```

#### Update Honey Jar
```http
PUT /api/knowledge/honey-pots/{honey_jar_id}
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "name": "Updated Name",
  "description": "Updated description",
  "tags": ["updated", "tags"]
}
```

#### Delete Honey Jar
```http
DELETE /api/knowledge/honey-pots/{honey_jar_id}
Authorization: Bearer <session_token>
```

### Document Management

#### Upload Document
```http
POST /api/knowledge/honey-pots/{honey_jar_id}/documents
Content-Type: multipart/form-data
Authorization: Bearer <session_token>

Form Data:
  - file: (binary file data)
  - metadata: {
      "title": "Document Title",
      "description": "Document description",
      "tags": ["tag1", "tag2"]
    }
```

**Response:**
```json
{
  "id": "document_uuid",
  "filename": "company_policy.pdf",
  "title": "Company Policy Document",
  "size": 2048576,
  "mime_type": "application/pdf",
  "status": "processing",
  "uploaded_at": "2024-01-01T00:00:00Z",
  "processing_progress": 0
}
```

#### Get Document Status
```http
GET /api/knowledge/documents/{document_id}
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "id": "document_uuid",
  "filename": "company_policy.pdf",
  "title": "Company Policy Document",
  "status": "processed",
  "chunk_count": 45,
  "embedding_count": 45,
  "processing_time": 12.5,
  "metadata": {
    "pages": 15,
    "word_count": 3500,
    "language": "en"
  }
}
```

#### List Documents
```http
GET /api/knowledge/honey-pots/{honey_jar_id}/documents
Authorization: Bearer <session_token>
```

#### Delete Document
```http
DELETE /api/knowledge/documents/{document_id}
Authorization: Bearer <session_token>
```

### Search & Query

#### Search Knowledge
```http
POST /api/knowledge/search
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "query": "company vacation policy",
  "honey_jar_ids": ["uuid1", "uuid2"],
  "filters": {
    "document_types": ["pdf", "docx"],
    "tags": ["hr", "policies"]
  },
  "limit": 10,
  "include_content": true
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "result_uuid",
      "document_id": "doc_uuid",
      "honey_jar_id": "hp_uuid",
      "title": "Employee Handbook - Vacation Policy",
      "content": "Our vacation policy allows...",
      "score": 0.85,
      "metadata": {
        "page": 12,
        "section": "Benefits"
      }
    }
  ],
  "total_results": 25,
  "query_time": 0.15,
  "searched_documents": 150
}
```

#### Ask Question (RAG)
```http
POST /api/knowledge/ask
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "question": "What is the company vacation policy?",
  "honey_jar_ids": ["uuid1"],
  "context_limit": 5,
  "model": "phi3"
}
```

**Response:**
```json
{
  "answer": "Based on the company handbook, employees receive...",
  "sources": [
    {
      "document_id": "doc_uuid",
      "title": "Employee Handbook",
      "page": 12,
      "relevance_score": 0.9
    }
  ],
  "confidence": 0.85,
  "model_used": "phi3",
  "response_time": 2.1
}
```

## Marketplace APIs

### Marketplace Listings

#### List Marketplace Items
```http
GET /api/marketplace/honey-pots
Query Parameters:
  - category: string
  - price_min: number
  - price_max: number
  - rating_min: number
  - search: string
  - sort: string (price|rating|created_at)
  - limit: number
  - offset: number
```

#### Get Marketplace Item
```http
GET /api/marketplace/honey-pots/{listing_id}
```

#### Purchase Honey Jar
```http
POST /api/marketplace/honey-pots/{listing_id}/purchase
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "payment_method": "credit_card",
  "billing_address": {
    "name": "John Doe",
    "email": "john@example.com",
    "address": "123 Main St",
    "city": "City",
    "state": "State",
    "zip": "12345"
  }
}
```

#### Create Marketplace Listing
```http
POST /api/marketplace/honey-pots
Content-Type: application/json
Authorization: Bearer <session_token>

{
  "honey_jar_id": "uuid",
  "title": "Premium Industry Knowledge",
  "description": "Comprehensive industry analysis and insights",
  "price": 99.99,
  "category": "business",
  "license_type": "single_use",
  "preview_enabled": true
}
```

## System Administration APIs

### Health & Monitoring

#### System Health
```http
GET /api/system/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": "healthy",
    "llm_service": "healthy",
    "knowledge_service": "healthy",
    "authentication": "healthy"
  },
  "version": "1.0.0",
  "uptime": 86400
}
```

#### Service Status
```http
GET /api/system/status
Authorization: Bearer <admin_token>
```

#### System Metrics
```http
GET /api/system/metrics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "performance": {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 23.1
  },
  "requests": {
    "total_today": 1250,
    "average_response_time": 1.23,
    "error_rate": 0.02
  },
  "models": {
    "total_inferences": 450,
    "average_inference_time": 1.8,
    "active_models": ["phi3"]
  }
}
```

### User Management

#### List Users (Admin)
```http
GET /api/admin/users
Authorization: Bearer <admin_token>
```

#### Get User Details (Admin)
```http
GET /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
```

#### Update User (Admin)
```http
PUT /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
```

#### Deactivate User (Admin)
```http
POST /api/admin/users/{user_id}/deactivate
Authorization: Bearer <admin_token>
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    },
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_uuid"
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Common Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | User must be authenticated |
| `INVALID_CREDENTIALS` | Login credentials are incorrect |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `PERMISSION_DENIED` | User lacks required permissions |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `MODEL_UNAVAILABLE` | Requested AI model is not available |
| `PROCESSING_ERROR` | Document processing failed |
| `STORAGE_ERROR` | File storage operation failed |

## Rate Limiting

| Endpoint Category | Limit | Window |
|------------------|-------|---------|
| Authentication | 5 requests | 1 minute |
| Chat | 60 requests | 1 minute |
| Knowledge Search | 100 requests | 1 minute |
| Document Upload | 10 requests | 1 minute |
| General API | 1000 requests | 1 hour |

Rate limit headers are included in all responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

## WebSocket APIs

### Real-time Chat
```javascript
// Connect to WebSocket
const ws = new WebSocket('wss://localhost:5050/api/chat/ws');

// Send message
ws.send(JSON.stringify({
  type: 'message',
  data: {
    message: 'Hello Bee!',
    conversation_id: 'uuid'
  }
}));

// Receive streaming response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'response_chunk') {
    // Handle streaming response chunk
    console.log(data.chunk);
  }
};
```

### Model Status Updates
```javascript
// Subscribe to model status changes
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'model_status'
}));

// Receive model status updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'model_loaded') {
    console.log(`Model ${data.model} loaded`);
  }
};
```

This API reference provides comprehensive documentation for integrating with the STING Platform. All endpoints are designed for enterprise use with proper authentication, error handling, and rate limiting.