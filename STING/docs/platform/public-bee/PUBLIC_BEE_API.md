# Public Bee API Reference

**RESTful API for AI-as-a-Service Chatbot Platform**

## Base URL
```
https://your-sting-domain.com:8092/api/public
```

## Authentication

All API requests require authentication using an API key in the request headers:

```http
X-API-Key: sk_your-api-key-here
Content-Type: application/json
```

### API Key Types

- **Bot API Key**: Access to specific bot endpoints
- **Admin API Key**: Full management access (bot creation, analytics)
- **Read-Only Key**: View-only access to bot information

## Rate Limiting

Rate limits are enforced per API key:

- **Basic Tier**: 100 requests/hour
- **Professional**: 1,000 requests/hour  
- **Enterprise**: 10,000 requests/hour

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Chat Endpoints

### Send Message

Send a message to a specific bot and receive an AI-generated response.

```http
POST /chat/{bot-id}/message
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot-id` | string | Yes | Unique identifier for the bot |

#### Request Body

```json
{
  "message": "string",           // User's message (required)
  "session_id": "string",        // Session identifier (optional)
  "context": {                   // Additional context (optional)
    "user_id": "string",
    "user_name": "string",
    "metadata": {
      "key": "value"
    }
  },
  "options": {                   // Request options (optional)
    "max_tokens": 500,
    "temperature": 0.7,
    "include_sources": true,
    "stream": false
  }
}
```

#### Response

```json
{
  "success": true,
  "response": "AI-generated response text",
  "session_id": "sess_abc123",
  "bot_id": "support-bot",
  "message_id": "msg_xyz789",
  "timestamp": "2025-01-01T12:00:00Z",
  "metadata": {
    "response_time_ms": 1250,
    "tokens_used": 145,
    "model": "gpt-3.5-turbo",
    "confidence": 0.92
  },
  "sources": [                   // When include_sources=true
    {
      "document": "user-guide.pdf",
      "page": 5,
      "relevance": 0.95,
      "content_preview": "To reset your password..."
    }
  ],
  "suggested_actions": [          // Optional follow-up actions
    {
      "type": "link",
      "text": "View full documentation",
      "url": "https://docs.example.com/password-reset"
    }
  ]
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again in 60 seconds.",
    "details": {
      "retry_after": 60
    }
  }
}
```

### Get Conversation History

Retrieve conversation history for a specific session.

```http
GET /chat/{bot-id}/history?session_id={session_id}&limit=50&offset=0
```

#### Response

```json
{
  "success": true,
  "session_id": "sess_abc123",
  "messages": [
    {
      "message_id": "msg_1",
      "type": "user",
      "content": "How do I install STING?",
      "timestamp": "2025-01-01T12:00:00Z"
    },
    {
      "message_id": "msg_2", 
      "type": "bot",
      "content": "To install STING, follow these steps...",
      "timestamp": "2025-01-01T12:00:05Z",
      "sources": [...],
      "metadata": {...}
    }
  ],
  "total_messages": 2,
  "has_more": false
}
```

## Bot Management Endpoints (Admin Only)

### List Bots

Retrieve all bots accessible to the API key.

```http
GET /bots/list
```

#### Response

```json
{
  "success": true,
  "bots": [
    {
      "bot_id": "support-bot",
      "name": "Customer Support Bot",
      "description": "Helps customers with product questions",
      "status": "active",
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T11:00:00Z",
      "stats": {
        "total_conversations": 1250,
        "messages_today": 89,
        "avg_response_time_ms": 1100
      }
    }
  ]
}
```

### Get Bot Details

Retrieve detailed information about a specific bot.

```http
GET /bots/{bot-id}
```

#### Response

```json
{
  "success": true,
  "bot": {
    "bot_id": "support-bot",
    "name": "Customer Support Bot",
    "description": "Helps customers with product questions",
    "display_name": "SupportBot",
    "avatar_url": "https://cdn.example.com/bot-avatar.png",
    "status": "active",
    "configuration": {
      "system_prompt": "You are a helpful customer support assistant...",
      "max_tokens": 500,
      "temperature": 0.7,
      "response_format": "helpful",
      "knowledge_sources": [
        {
          "honey_jar_id": "jar_123",
          "name": "Product Documentation",
          "weight": 1.0
        }
      ]
    },
    "security": {
      "rate_limit": 100,
      "allowed_domains": ["example.com", "*.example.com"],
      "pii_filtering": true,
      "content_filter_level": "moderate"
    },
    "branding": {
      "primary_color": "#007bff",
      "welcome_message": "Hi! How can I help you today?",
      "placeholder_text": "Ask me anything..."
    },
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T11:00:00Z"
  }
}
```

### Create Bot (Admin Only)

Create a new chatbot.

```http
POST /bots/create
```

#### Request Body

```json
{
  "name": "Customer Support Bot",
  "description": "Helps customers with product questions",
  "display_name": "SupportBot",
  "honey_jar_ids": ["jar_123", "jar_456"],
  "configuration": {
    "system_prompt": "You are a helpful customer support assistant specialized in product questions. Always be polite and provide accurate information based on the knowledge base.",
    "max_tokens": 500,
    "temperature": 0.7,
    "response_format": "helpful"
  },
  "security": {
    "rate_limit": 100,
    "allowed_domains": ["example.com"],
    "pii_filtering": true,
    "content_filter_level": "moderate"
  },
  "branding": {
    "primary_color": "#007bff",
    "welcome_message": "Hi! How can I help you with our products today?",
    "placeholder_text": "Ask about features, pricing, setup..."
  }
}
```

#### Response

```json
{
  "success": true,
  "bot": {
    "bot_id": "bot_abc123",
    "name": "Customer Support Bot",
    "api_key": "sk_xyz789abc123def456",
    "status": "active",
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

### Update Bot (Admin Only)

Update an existing bot's configuration.

```http
PUT /bots/{bot-id}
```

### Delete Bot (Admin Only)

Delete a bot and all associated data.

```http
DELETE /bots/{bot-id}
```

## API Key Management (Admin Only)

### Generate API Key

Create a new API key for a bot.

```http
POST /bots/{bot-id}/api-keys
```

#### Request Body

```json
{
  "name": "Production Website Key",
  "permissions": ["chat", "history"],
  "rate_limit": 1000,
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### List API Keys

```http
GET /bots/{bot-id}/api-keys
```

### Revoke API Key

```http
DELETE /bots/{bot-id}/api-keys/{key-id}
```

## Analytics Endpoints (Admin Only)

### Conversation Analytics

Get detailed analytics for a bot.

```http
GET /bots/{bot-id}/analytics?start_date=2025-01-01&end_date=2025-01-31
```

#### Response

```json
{
  "success": true,
  "analytics": {
    "period": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31"
    },
    "metrics": {
      "total_conversations": 1250,
      "total_messages": 5680,
      "unique_users": 890,
      "avg_conversation_length": 4.5,
      "avg_response_time_ms": 1150,
      "satisfaction_score": 4.2
    },
    "usage_by_day": [
      {
        "date": "2025-01-01",
        "conversations": 45,
        "messages": 203
      }
    ],
    "top_questions": [
      {
        "question": "How do I reset my password?",
        "count": 89,
        "avg_satisfaction": 4.5
      }
    ],
    "knowledge_source_usage": [
      {
        "honey_jar_id": "jar_123",
        "name": "User Guide",
        "queries": 456,
        "relevance_score": 0.89
      }
    ]
  }
}
```

## Widget Integration

### JavaScript Widget

Include the widget script on your website:

```html
<script src="https://your-sting-domain.com:8092/widget/bot-widget.js"></script>
```

Initialize the widget:

```javascript
STINGChat.init({
  apiKey: 'sk_your-api-key',
  botId: 'your-bot-id',
  container: 'chat-container',
  options: {
    theme: 'light',
    position: 'bottom-right',
    welcomeMessage: 'Hi! How can I help you?',
    placeholder: 'Type your message...',
    height: '500px',
    width: '350px'
  },
  callbacks: {
    onMessage: function(message, response) {
      console.log('New message:', message, response);
    },
    onReady: function() {
      console.log('Chat widget ready');
    }
  }
});
```

### React Component

```jsx
import { STINGChatWidget } from '@sting/chat-widget';

function App() {
  return (
    <STINGChatWidget
      apiKey="sk_your-api-key"
      botId="your-bot-id"
      theme="light"
      onMessage={(message, response) => {
        console.log('Message:', message, response);
      }}
    />
  );
}
```

## Webhooks

### Configure Webhooks

Set up webhooks to receive real-time notifications about bot interactions.

```http
POST /bots/{bot-id}/webhooks
```

#### Request Body

```json
{
  "url": "https://your-app.com/webhook/sting",
  "events": ["message.sent", "conversation.started", "conversation.ended"],
  "secret": "webhook-secret-key"
}
```

### Webhook Events

#### Message Sent
```json
{
  "event": "message.sent",
  "timestamp": "2025-01-01T12:00:00Z",
  "data": {
    "bot_id": "support-bot",
    "session_id": "sess_abc123",
    "message": {
      "type": "user",
      "content": "How do I install STING?"
    },
    "response": {
      "content": "To install STING, follow these steps...",
      "response_time_ms": 1200,
      "sources": [...]
    }
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key is invalid or expired |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `BOT_NOT_FOUND` | 404 | Bot ID does not exist |
| `BOT_INACTIVE` | 403 | Bot is disabled or suspended |
| `INVALID_REQUEST` | 400 | Request format is invalid |
| `INSUFFICIENT_PERMISSIONS` | 403 | API key lacks required permissions |
| `INTERNAL_ERROR` | 500 | Server error occurred |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## SDK Examples

### Python

```python
import requests

class PublicBeeClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def send_message(self, bot_id, message, session_id=None):
        payload = {
            'message': message,
            'session_id': session_id
        }
        response = requests.post(
            f'{self.base_url}/chat/{bot_id}/message',
            json=payload,
            headers=self.headers
        )
        return response.json()

# Usage
client = PublicBeeClient('sk_your-api-key', 'https://sting.example.com:8092/api/public')
result = client.send_message('support-bot', 'How do I install STING?')
print(result['response'])
```

### Node.js

```javascript
const axios = require('axios');

class PublicBeeClient {
  constructor(apiKey, baseUrl) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.headers = {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json'
    };
  }

  async sendMessage(botId, message, sessionId) {
    const payload = {
      message: message,
      session_id: sessionId
    };
    
    try {
      const response = await axios.post(
        `${this.baseUrl}/chat/${botId}/message`,
        payload,
        { headers: this.headers }
      );
      return response.data;
    } catch (error) {
      throw new Error(`API Error: ${error.response.data.error.message}`);
    }
  }
}

// Usage
const client = new PublicBeeClient('sk_your-api-key', 'https://sting.example.com:8092/api/public');
client.sendMessage('support-bot', 'How do I install STING?')
  .then(result => console.log(result.response))
  .catch(error => console.error(error));
```

## Testing

### Using cURL

```bash
# Send a message
curl -X POST https://sting.example.com:8092/api/public/chat/support-bot/message \
  -H "X-API-Key: sk_your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I install STING?",
    "session_id": "test-session-123"
  }'

# Get bot info
curl -X GET https://sting.example.com:8092/api/public/bots/support-bot \
  -H "X-API-Key: sk_your-api-key"
```

### Postman Collection

Import the Public Bee API Postman collection for interactive testing:
```
https://sting.example.com:8092/api/public/postman/collection.json
```

---

**Need help?** Check the [Public Bee Setup Guide](PUBLIC_BEE_SETUP.md) or contact support for additional assistance.