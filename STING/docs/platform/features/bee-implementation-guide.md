# 🐝 Bee Implementation Guide

## Overview

Bee is the AI-powered assistant for the STING platform, providing secure, intelligent chat capabilities with advanced features including:

- **Kratos Authentication Integration** with passkey/WebAuthn support
- **End-to-End Encryption** for sensitive messages
- **Context Retention** across conversations with intelligent token management
- **Sentiment Analysis** for better user experience
- **Role-Based Access Control** (RBAC)
- **Tool Integration** for advanced functionality
- **Analytics and Reporting**
- **Scalable Messaging Service**

## Architecture

### Services

1. **Bee Chatbot Service** (Port 8888)
   - Main AI assistant interface
   - Handles conversation management
   - Integrates with all other services

2. **Messaging Service** (Port 8889)
   - Standalone microservice for scalable messaging
   - Handles encryption, queuing, and notifications
   - Uses Redis for message queuing
   - PostgreSQL for message storage

3. **Integration Points**
   - **Kratos**: Authentication and identity management
   - **LLM Gateway**: Language model integration
   - **Frontend**: React-based UI components
   - **Database**: PostgreSQL for persistence
   - **Redis**: Message queuing and caching

## Features

### 1. Authentication & Security

- **Passkey Support**: Integrated with Kratos for passwordless authentication
- **Session Management**: Secure session handling with token validation
- **Role-Based Access**: Three user roles with hierarchical permissions:
  - `end_user`: Basic chat and search capabilities
  - `support`: Additional tools and user assistance features
  - `admin`: Full system configuration and management

### 2. Secure Messaging

- **End-to-End Encryption**: Using Fernet symmetric encryption
- **Message Recall**: Time-limited ability to recall sent messages
- **Self-Destructing Messages**: Automatic expiration of sensitive content
- **Audit Trail**: Complete logging of message activities

### 3. Context & Intelligence

- **Conversation Memory**: Maintains context across interactions with token-aware pruning
- **Sentiment Analysis**: Real-time emotional intelligence
- **Topic Extraction**: Automatic identification of conversation themes
- **User Preferences**: Learns and adapts to user behavior
- **Token Management**: Intelligent conversation pruning using tiktoken for accurate token counting
- **Conversation Summarization**: Automatic summarization of pruned messages to preserve context
- **Database Persistence**: Optional PostgreSQL storage for conversation history across restarts

### 4. Tools & Capabilities

Available tools based on user role:

- **Search**: Document and database search (all users)
- **Analytics**: Report generation and data visualization (all users)
- **Database Query**: Direct database access (support/admin)
- **Notify**: Send notifications (support/admin)
- **System Config**: Modify system settings (admin only)

### 5. Analytics & Reporting

- **Usage Metrics**: Track interactions, response times, tool usage
- **Sentiment Tracking**: Monitor user satisfaction over time
- **Performance Analytics**: System performance and bottlenecks
- **Admin Reports**: Detailed insights for administrators

## Implementation Details

### Starting Bee

1. **Using Docker Compose**:
```bash
./manage_sting.sh start chatbot messaging redis
```

2. **Accessing Bee**:
- Chatbot API: http://localhost:8081
- Bee API: http://localhost:8888
- Messaging API: http://localhost:8889

### Configuration

Key environment variables:

```bash
# Bee Configuration
BEE_PORT=8888
BEE_SYSTEM_PROMPT="You are Bee, a helpful AI assistant..."
BEE_MAX_HISTORY=100
BEE_CONTEXT_WINDOW=10
BEE_SENTIMENT_ENABLED=true
BEE_ENCRYPTION_ENABLED=true
BEE_TOOLS_ENABLED=true
BEE_MESSAGING_SERVICE_ENABLED=true

# Conversation Management
BEE_CONVERSATION_MAX_TOKENS=4096
BEE_CONVERSATION_MAX_MESSAGES=50
BEE_CONVERSATION_TOKEN_BUFFER_PERCENT=20
BEE_CONVERSATION_PERSISTENCE_ENABLED=true
BEE_CONVERSATION_SESSION_TIMEOUT_HOURS=24
BEE_CONVERSATION_SUMMARIZATION_ENABLED=true
BEE_CONVERSATION_SUMMARY_MODEL=llama3.2:latest
BEE_CONVERSATION_PRUNING_STRATEGY=sliding_window
BEE_CONVERSATION_KEEP_RECENT_MESSAGES=10

# Messaging Service
MESSAGING_SERVICE_URL=http://messaging:8889
MESSAGING_ENCRYPTION_ENABLED=true
MESSAGING_QUEUE_ENABLED=true
MESSAGING_NOTIFICATIONS_ENABLED=true

# Authentication
KRATOS_PUBLIC_URL=https://kratos:4433
KRATOS_ADMIN_URL=https://kratos:4434
```

### API Endpoints

#### Bee Chatbot Service

- `POST /chat` - Send a message to Bee
- `GET /conversations/{id}` - Get conversation history
- `GET /conversations/{id}/token-usage` - Get token usage statistics
- `POST /conversations/{id}/prune` - Manually trigger conversation pruning
- `DELETE /conversations/{id}/clear` - Clear conversation
- `GET /tools` - List available tools
- `POST /analytics/report` - Generate analytics report
- `GET /admin/config` - Get Bee configuration (admin)
- `PUT /admin/config` - Update configuration (admin)

#### Messaging Service

- `POST /messages/send` - Send a secure message
- `GET /messages/{id}` - Retrieve a message
- `GET /conversations/{id}` - Get conversation messages
- `DELETE /messages/{id}/recall` - Recall a message
- `GET /notifications/settings/{user_id}` - Get notification preferences
- `PUT /notifications/settings/{user_id}` - Update notification preferences

### Frontend Integration

Update your React components to use Bee:

```javascript
// Example: Sending a message to Bee
const sendMessage = async (message) => {
  const response = await fetch('http://localhost:8888/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      message: message,
      user_id: userId,
      conversation_id: conversationId,
      require_auth: true,
      encryption_required: sensitiveMode,
      tools_enabled: ['search', 'analytics']
    })
  });
  
  const data = await response.json();
  return data;
};
```

### Security Considerations

1. **Authentication Required**: Most endpoints require authentication
2. **Encryption**: Sensitive data is automatically encrypted
3. **Rate Limiting**: Implement rate limiting in production
4. **Input Validation**: All inputs are validated
5. **Access Control**: Role-based permissions enforced

## Testing

### Health Checks

```bash
# Check Bee health
curl http://localhost:8888/health

# Check Messaging Service health
curl http://localhost:8889/health
```

### Test Chat

```bash
# Send a test message
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello Bee!",
    "user_id": "test-user",
    "require_auth": false
  }'
```

### Test with Authentication

```bash
# First get a Kratos session token
# Then use it to authenticate with Bee
curl -X POST http://localhost:8888/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -d '{
    "message": "Show me sales analytics",
    "user_id": "authenticated-user",
    "tools_enabled": ["analytics"],
    "require_auth": true
  }'
```

## Troubleshooting

### Common Issues

1. **Bee not responding**:
   - Check if all services are healthy: `./manage_sting.sh status`
   - Verify LLM Gateway is running
   - Check logs: `./manage_sting.sh logs chatbot`

2. **Authentication errors**:
   - Ensure Kratos is running and healthy
   - Verify session tokens are valid
   - Check Kratos configuration

3. **Messaging service issues**:
   - Ensure Redis is running
   - Check database connectivity
   - Verify message queue is processing

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG ./manage_sting.sh start chatbot
```

## Future Enhancements

1. **Voice Integration**: Add speech-to-text and text-to-speech
2. **Multi-language Support**: Expand beyond English
3. **Custom Tool Development**: SDK for third-party tools
4. **Advanced Analytics**: Machine learning insights
5. **Mobile SDK**: Native mobile integration

## Development

### Adding New Tools

1. Create a new tool class in `chatbot/tools/`:

```python
class CustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="My custom tool",
            required_role="end_user"
        )
    
    async def execute(self, input_data, context, user_info):
        # Tool implementation
        return {
            "name": self.name,
            "status": "success",
            "result": "Tool output"
        }
```

2. Register the tool in `ToolManager`
3. Add to enabled tools in configuration

### Extending Bee's Personality

Modify the system prompt in the configuration to adjust Bee's personality:

```python
config['system_prompt'] = """
You are Bee, a helpful and friendly AI assistant for the STING platform.
[Add custom personality traits here]
"""
```

## Performance Optimization

1. **Enable Redis caching** for frequently accessed data
2. **Use connection pooling** for database connections
3. **Implement message batching** for high-volume scenarios
4. **Configure appropriate resource limits** in Docker
5. **Use CDN for static assets** in production
6. **Token management** with tiktoken for accurate context window management
7. **Automatic conversation pruning** to maintain optimal performance

## Monitoring

Recommended monitoring setup:

1. **Prometheus metrics** (coming soon)
2. **Grafana dashboards** for visualization
3. **Log aggregation** with ELK stack
4. **Error tracking** with Sentry
5. **Uptime monitoring** with external service

## Support

For issues or questions:

1. Check the logs: `./manage_sting.sh logs chatbot messaging`
2. Review health status: `curl http://localhost:8888/health`
3. Enable debug mode for detailed information
4. Submit issues to the STING repository

---

🐝 Happy chatting with Bee!