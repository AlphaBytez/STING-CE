# STING API Reference

## Overview

This guide provides comprehensive API documentation for STING's REST endpoints. The STING platform exposes a RESTful API that enables programmatic access to all major features including Bee AI chat, Honey Jar management, authentication, and system administration.

**Base URL:** `https://your-sting-instance.com/api`
**Authentication:** All API requests require valid session cookies or bearer tokens from Ory Kratos
**Content-Type:** `application/json`
**API Version:** v1.0

For complete authentication details, see `authentication-guide.md` in this directory.

## Quick Start

```bash
# Example: Check if you're authenticated
curl -X GET https://your-sting.com/api/session/whoami \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"

# Example: Send a message to Bee AI
curl -X POST https://your-sting.com/api/bee/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN" \
  -d '{
    "message": "What are the main features of STING?",
    "conversation_id": null
  }'
```

## Table of Contents

1. [Authentication & Session Management](#authentication--session-management)
2. [Bee AI Chat](#bee-ai-chat)
3. [Honey Jar Management](#honey-jar-management)
4. [Admin & User Management](#admin--user-management)
5. [Metrics & Monitoring](#metrics--monitoring)
6. [Report Generation](#report-generation)
7. [External AI Proxy](#external-ai-proxy)

---

## Authentication & Session Management

### Check Authentication Status

Get information about the current authenticated user.

**Endpoint:** `GET /api/session/whoami`

**Example Request:**
```bash
curl -X GET https://your-sting.com/api/session/whoami \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "user": {
    "id": "abc-123-def-456",
    "email": "user@example.com",
    "traits": {
      "email": "user@example.com",
      "name": "John Doe"
    },
    "verifiable_addresses": [
      {
        "value": "user@example.com",
        "verified": true,
        "via": "email"
      }
    ]
  },
  "session": {
    "id": "session-xyz-789",
    "active": true,
    "authenticated_at": "2024-11-12T10:30:00Z",
    "expires_at": "2024-11-13T10:30:00Z",
    "authenticator_assurance_level": "aal1"
  }
}
```

### Logout

Terminate the current session.

**Endpoint:** `POST /api/session/logout`
**Alternative:** `DELETE /api/session/logout`

**Example Request:**
```bash
curl -X POST https://your-sting.com/api/session/logout \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "message": "Successfully logged out",
  "redirect_to": "/auth/login"
}
```

### Check AAL Status

Check the current Authenticator Assurance Level (AAL1 or AAL2).

**Endpoint:** `GET /api/auth/aal-status`

**Example Request:**
```bash
curl -X GET https://your-sting.com/api/auth/aal-status \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "current_aal": "aal1",
  "available_aal": "aal2",
  "can_step_up": true,
  "session_id": "session-xyz-789"
}
```

### Step Up to AAL2

Upgrade session security level to AAL2 (requires additional authentication factor).

**Endpoint:** `POST /api/auth/aal-step-up`

**Example Request:**
```bash
curl -X POST https://your-sting.com/api/auth/aal-step-up \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "totp"
  }'
```

**Example Response:**
```json
{
  "success": true,
  "flow_url": "/self-service/login?aal=aal2&return_to=/dashboard",
  "required": true
}
```

### Check AAL Requirements

Check if a specific operation requires AAL2.

**Endpoint:** `POST /api/auth/aal-check`

**Request Body:**
```json
{
  "operation": "honey_jar_access",
  "resource_id": "honey-jar-123"
}
```

**Example Response:**
```json
{
  "success": true,
  "current_aal": "aal1",
  "required_aal": "aal2",
  "needs_step_up": true,
  "step_up_url": "/self-service/login?aal=aal2"
}
```

---

## Bee AI Chat

### Send Chat Message

Send a message to the Bee AI assistant and receive an AI-generated response.

**Endpoint:** `POST /api/bee/chat`

**Request Body:**
```json
{
  "message": "Explain how Honey Jars work in STING",
  "conversation_id": "conv-abc-123",
  "honey_jar_id": "hj-def-456",
  "model": "microsoft/phi-4-reasoning-plus",
  "max_tokens": 2048,
  "temperature": 0.7
}
```

**Parameters:**
- `message` (required): User's message/question
- `conversation_id` (optional): ID to continue existing conversation, null for new
- `honey_jar_id` (optional): Honey Jar to query against for context
- `model` (optional): LLM model to use (defaults to platform default)
- `max_tokens` (optional): Maximum response length (default: 2048)
- `temperature` (optional): Response creativity 0.0-1.0 (default: 0.7)

**Example Request:**
```bash
curl -X POST https://your-sting.com/api/bee/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN" \
  -d '{
    "message": "What are the security features in STING?",
    "conversation_id": null
  }'
```

**Example Response:**
```json
{
  "success": true,
  "response": "STING provides comprehensive security features including:\n\n1. **Passwordless Authentication**: WebAuthn/FIDO2 support with biometric and hardware keys\n2. **PII Detection**: Automatic detection and redaction of 50+ PII types\n3. **Encryption**: AES-256 encryption for Honey Jars\n4. **AAL1/AAL2 Security Levels**: Graduated authentication assurance\n5. **Audit Logging**: Complete audit trails for compliance\n\nFor more details, see the authentication-guide.md documentation.",
  "conversation_id": "conv-new-789",
  "metadata": {
    "model": "microsoft/phi-4-reasoning-plus",
    "tokens_used": 234,
    "response_time_ms": 1250,
    "honey_jars_searched": 0
  },
  "classified_as": "general_query"
}
```

**Note:** If the query is classified as requiring long-form content (>4000 words), it will be automatically routed to the report generation system and return:
```json
{
  "success": true,
  "classified_as": "report",
  "report_id": "report-xyz-123",
  "message": "Your query is complex and will be processed as a report. You will be notified when it's ready.",
  "queue_position": 2,
  "estimated_completion": "2024-11-12T10:45:00Z"
}
```

### List Conversations

Get all conversations for the authenticated user.

**Endpoint:** `GET /api/bee/conversations`

**Query Parameters:**
- `limit` (optional): Number of conversations to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example Request:**
```bash
curl -X GET "https://your-sting.com/api/bee/conversations?limit=10" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv-abc-123",
      "created_at": "2024-11-12T09:00:00Z",
      "updated_at": "2024-11-12T10:30:00Z",
      "message_count": 5,
      "last_message": "Thank you for the explanation!",
      "title": "STING Security Features"
    },
    {
      "id": "conv-def-456",
      "created_at": "2024-11-11T15:20:00Z",
      "updated_at": "2024-11-11T15:45:00Z",
      "message_count": 3,
      "last_message": "How do I create a Honey Jar?",
      "title": "Honey Jar Creation"
    }
  ],
  "pagination": {
    "total": 24,
    "limit": 10,
    "offset": 0,
    "has_more": true
  }
}
```

### Check Bee Health

Check if the Bee AI service is available and healthy.

**Endpoint:** `GET /api/bee/health`

**Example Request:**
```bash
curl -X GET https://your-sting.com/api/bee/health
```

**Example Response:**
```json
{
  "success": true,
  "status": "healthy",
  "services": {
    "external_ai": "connected",
    "knowledge_base": "available",
    "vector_db": "healthy"
  },
  "models_available": [
    "microsoft/phi-4-reasoning-plus",
    "qwen2.5-14b-instruct"
  ],
  "uptime_seconds": 86400
}
```

---

## Honey Jar Management

**Note:** Honey Jar API endpoints are currently being documented. The Web UI provides full functionality through the Hive Manager interface. For programmatic access, contact support or see the upcoming API expansion in Pro/Enterprise editions.

**Available Operations (UI-based):**
- Create Honey Jars with custom names and categories
- Upload documents (PDF, Word, Markdown, JSON, HTML, text)
- Set access permissions (Public, Private, Team, Restricted)
- Export as HJX, JSON, or TAR archives
- Query Honey Jars through Bee chat using `honey_jar_id` parameter

For detailed Honey Jar concepts and usage, see `honey-jars-guide.md` in this directory.

---

## Admin & User Management

### Generate Admin Registration Token

Create a secure token for admin account creation (requires existing admin privileges).

**Endpoint:** `POST /api/admin-registration/generate-token`

**Request Body:**
```json
{
  "expires_in_hours": 24,
  "max_uses": 1,
  "metadata": {
    "issued_to": "New Administrator",
    "purpose": "Initial admin setup"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "token": "admin-token-secure-abc-123-def-456",
  "expires_at": "2024-11-13T10:30:00Z",
  "max_uses": 1,
  "registration_url": "https://your-sting.com/auth/admin-registration?token=admin-token-secure-abc-123-def-456"
}
```

### Verify Admin Registration Token

Check if an admin registration token is valid.

**Endpoint:** `POST /api/admin-registration/verify-token`

**Request Body:**
```json
{
  "token": "admin-token-secure-abc-123-def-456"
}
```

**Example Response:**
```json
{
  "success": true,
  "valid": true,
  "expires_at": "2024-11-13T10:30:00Z",
  "remaining_uses": 1
}
```

### Admin Registration Status

Check if any admins exist in the system (for initial setup).

**Endpoint:** `GET /api/admin-registration/status`

**Example Response:**
```json
{
  "success": true,
  "has_admin": false,
  "allow_emergency_upgrade": true,
  "system_initialized": false
}
```

---

## Metrics & Monitoring

### Get Session Metrics

Retrieve statistics about active sessions.

**Endpoint:** `GET /api/metrics/sessions`

**Example Response:**
```json
{
  "success": true,
  "active_sessions": 42,
  "total_sessions_today": 156,
  "average_session_duration_minutes": 35,
  "peak_concurrent_sessions": 67,
  "sessions_by_hour": [
    {"hour": 9, "count": 12},
    {"hour": 10, "count": 18},
    {"hour": 11, "count": 23}
  ]
}
```

### Get Message Metrics

Get statistics about Bee chat messages for today.

**Endpoint:** `GET /api/metrics/messages/today`

**Example Response:**
```json
{
  "success": true,
  "total_messages": 234,
  "by_classification": {
    "general_query": 123,
    "honey_jar_search": 45,
    "report": 12,
    "system_query": 54
  },
  "average_response_time_ms": 1250,
  "total_tokens_used": 45678
}
```

### Get User Metrics

Retrieve user account statistics.

**Endpoint:** `GET /api/metrics/users`

**Example Response:**
```json
{
  "success": true,
  "total_users": 87,
  "active_users_today": 42,
  "new_users_this_week": 5,
  "users_by_aal": {
    "aal1": 56,
    "aal2": 31
  },
  "authentication_methods": {
    "email": 87,
    "totp": 45,
    "webauthn": 23,
    "passkey": 12
  }
}
```

### System Health Check

Get comprehensive system health information.

**Endpoint:** `GET /api/system/health`

**Example Response:**
```json
{
  "success": true,
  "status": "healthy",
  "services": {
    "app": {
      "status": "healthy",
      "uptime_seconds": 86400,
      "memory_usage_mb": 512,
      "cpu_usage_percent": 23
    },
    "database": {
      "status": "healthy",
      "connections": 12,
      "query_time_avg_ms": 15
    },
    "redis": {
      "status": "healthy",
      "memory_usage_mb": 128,
      "connected_clients": 8
    },
    "external_ai": {
      "status": "connected",
      "response_time_ms": 1250,
      "models_available": 2
    },
    "vector_db": {
      "status": "healthy",
      "collections": 15,
      "total_embeddings": 12456
    }
  },
  "version": "1.0.0-ce",
  "timestamp": "2024-11-12T10:30:00Z"
}
```

---

## Report Generation

### Create Report

Generate a long-form report from a query (typically auto-triggered by complex Bee chat requests).

**Endpoint:** `POST /api/reports/`

**Request Body:**
```json
{
  "template_id": "bee_conversational_report",
  "title": "STING Security Analysis",
  "description": "Comprehensive security feature overview",
  "priority": "normal",
  "parameters": {
    "user_query": "Provide a detailed 4500+ word analysis of STING's security features",
    "conversation_id": null,
    "generation_mode": "conversational",
    "context": {}
  },
  "output_format": "pdf",
  "honey_jar_id": null,
  "scrambling_enabled": true
}
```

**Parameters:**
- `template_id`: Report template (usually "bee_conversational_report")
- `title`: Report title (auto-generated if not provided)
- `priority`: "urgent", "high", "normal", "low"
- `output_format`: "pdf", "md", "html"
- `scrambling_enabled`: Enable PII detection/scrubbing

**Example Response:**
```json
{
  "success": true,
  "report_id": "report-abc-123",
  "status": "queued",
  "queue_position": 2,
  "estimated_completion": "2024-11-12T10:45:00Z",
  "message": "Report queued for generation"
}
```

### Get Report Status

Check the status of a report.

**Endpoint:** `GET /api/reports/{report_id}`

**Example Response:**
```json
{
  "success": true,
  "report": {
    "id": "report-abc-123",
    "title": "STING Security Analysis",
    "status": "completed",
    "progress_percentage": 100,
    "created_at": "2024-11-12T10:30:00Z",
    "completed_at": "2024-11-12T10:35:00Z",
    "output_format": "pdf",
    "file_size_bytes": 2457600,
    "result_file_id": "file-xyz-789",
    "download_url": "/api/reports/report-abc-123/download"
  }
}
```

**Status Values:**
- `pending`: Waiting to be queued
- `queued`: In processing queue
- `processing`: Currently being generated
- `completed`: Ready for download
- `failed`: Generation failed (check error_message)

### List Reports

Get all reports for the authenticated user.

**Endpoint:** `GET /api/reports/`

**Query Parameters:**
- `limit` (optional): Number of reports (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by status
- `search` (optional): Search in title/description

**Example Request:**
```bash
curl -X GET "https://your-sting.com/api/reports/?limit=10&status=completed" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "reports": [
      {
        "id": "report-abc-123",
        "title": "Executive Summary: STING Analysis",
        "status": "completed",
        "created_at": "2024-11-12T10:30:00Z",
        "completed_at": "2024-11-12T10:35:00Z",
        "output_format": "pdf",
        "file_size_bytes": 2457600
      }
    ],
    "pagination": {
      "total": 24,
      "limit": 10,
      "offset": 0
    }
  }
}
```

### Download Report

Download a completed report file.

**Endpoint:** `GET /api/reports/{report_id}/download`

**Example Request:**
```bash
curl -X GET https://your-sting.com/api/reports/report-abc-123/download \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN" \
  -o report.pdf
```

**Response:** Binary file download (PDF, Markdown, or HTML based on output_format)

### Cancel Report

Cancel a pending or processing report.

**Endpoint:** `POST /api/reports/{report_id}/cancel`

**Example Response:**
```json
{
  "success": true,
  "message": "Report cancelled successfully"
}
```

### Retry Failed Report

Retry a failed report generation.

**Endpoint:** `POST /api/reports/{report_id}/retry`

**Example Response:**
```json
{
  "success": true,
  "report_id": "report-abc-123",
  "status": "queued",
  "message": "Report requeued for processing"
}
```

---

## External AI Proxy

### Proxy to External AI Service

Forward requests to the external AI service (for advanced users and integrations).

**Endpoint:** `ALL /api/external-ai/{path}`

**Example:**
```bash
curl -X POST https://your-sting.com/api/external-ai/bee/chat \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_TOKEN" \
  -d '{
    "message": "Hello from the proxy!",
    "model": "microsoft/phi-4-reasoning-plus"
  }'
```

**Note:** This is a pass-through endpoint for advanced integrations. Most users should use the `/api/bee/chat` endpoint directly.

---

## Error Handling

All API endpoints follow a consistent error response format:

```json
{
  "success": false,
  "error": "Detailed error message",
  "error_code": "AUTH_REQUIRED",
  "details": {
    "field": "email",
    "reason": "Invalid format"
  }
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions (may require AAL2)
- `404 Not Found`: Resource doesn't exist
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Common Error Codes

- `AUTH_REQUIRED`: Not authenticated
- `AAL2_REQUIRED`: Operation requires AAL2 security level
- `INVALID_REQUEST`: Malformed request body
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVICE_UNAVAILABLE`: External service (AI, database) unavailable

---

## Rate Limiting

API requests are rate limited to ensure fair usage:

- **Anonymous**: 10 requests/minute
- **Authenticated (AAL1)**: 100 requests/minute
- **Authenticated (AAL2)**: 200 requests/minute
- **Admin**: 500 requests/minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699800000
```

---

## Authentication Examples

### Python

```python
import requests

# Login and get session
session = requests.Session()
response = session.get('https://your-sting.com/api/session/whoami')

# Use session for subsequent requests
bee_response = session.post(
    'https://your-sting.com/api/bee/chat',
    json={
        'message': 'What are Honey Jars?',
        'conversation_id': None
    }
)
print(bee_response.json())
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://your-sting.com/api',
  withCredentials: true  // Include cookies
});

// Check authentication
const whoami = await client.get('/session/whoami');
console.log(whoami.data);

// Send chat message
const response = await client.post('/bee/chat', {
  message: 'Explain STING architecture',
  conversation_id: null
});
console.log(response.data.response);
```

### cURL with Session Management

```bash
# Login and save cookies
curl -X POST https://your-sting.com/self-service/login \
  -c cookies.txt \
  -d "identifier=user@example.com&password=yourpassword"

# Use saved cookies for API requests
curl -X POST https://your-sting.com/api/bee/chat \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Bee!"}'
```

---

## Versioning

The STING API follows semantic versioning. The current version is **v1.0**.

Future versions will be accessible via the base URL:
- `https://your-sting.com/api/v1/...` (current, default)
- `https://your-sting.com/api/v2/...` (future)

Breaking changes will only occur in major version updates (v1 → v2).

---

## Support & Resources

- **Documentation:** https://docs.stingassistant.com
- **GitHub:** https://github.com/AlphaBytez/STING-CE
- **Community:** GitHub Discussions
- **Email:** olliec@alphabytez.dev

For issues or feature requests, please open an issue on GitHub.

---

**Last Updated:** November 2024
**Version:** 1.0.0-ce
