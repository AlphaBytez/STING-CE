# 🐝 Bee Conversation Management

## Overview

Bee's conversation management system provides intelligent context retention with automatic token management, conversation summarization, and optional database persistence. This ensures optimal performance while maintaining conversation continuity.

## Key Features

### 1. **Token-Aware Context Management**
- Accurate token counting using [tiktoken](https://github.com/openai/tiktoken) library
- Model-specific token encodings (GPT-4, Llama, Phi, etc.)
- Configurable token limits with buffer for response generation
- Real-time token usage tracking

### 2. **Intelligent Conversation Pruning**
- Automatic pruning when token or message limits are exceeded
- Sliding window strategy preserves recent messages
- System messages always retained
- Configurable pruning thresholds

### 3. **Conversation Summarization**
- LLM-powered summarization of pruned messages
- Extracts key topics, entities, action items
- Summaries stored for context preservation
- Maintains conversation continuity despite pruning

### 4. **Flexible Persistence Options**
- **Memory Mode**: Fast, in-memory storage (default for development)
- **Database Mode**: PostgreSQL persistence across restarts
- Automatic migration of conversations between modes
- Configurable via environment variables

## Configuration

### Environment Variables

```bash
# Token Management
BEE_CONVERSATION_MAX_TOKENS=4096              # Maximum tokens per conversation
BEE_CONVERSATION_MAX_MESSAGES=50              # Maximum messages to keep
BEE_CONVERSATION_TOKEN_BUFFER_PERCENT=20      # Reserve 20% for response

# Persistence
BEE_CONVERSATION_PERSISTENCE_ENABLED=true     # Enable database storage
BEE_CONVERSATION_SESSION_TIMEOUT_HOURS=24     # Session expiration
BEE_CONVERSATION_ARCHIVE_AFTER_DAYS=30        # Archive old conversations
BEE_CONVERSATION_CLEANUP_INTERVAL_HOURS=1     # Cleanup frequency

# Summarization
BEE_CONVERSATION_SUMMARIZATION_ENABLED=true   # Enable auto-summarization
BEE_CONVERSATION_SUMMARIZE_AFTER_MESSAGES=20  # Trigger threshold
BEE_CONVERSATION_SUMMARY_MAX_TOKENS=200       # Summary length limit
BEE_CONVERSATION_SUMMARY_MODEL=llama3.2:latest # Model for summaries

# Pruning Strategy
BEE_CONVERSATION_PRUNING_STRATEGY=sliding_window  # Pruning algorithm
BEE_CONVERSATION_KEEP_SYSTEM_MESSAGES=true       # Preserve system prompts
BEE_CONVERSATION_KEEP_RECENT_MESSAGES=10         # Always keep recent msgs
```

### Configuration in config.yml

```yaml
chatbot:
  conversation:
    # Token management
    max_tokens: 4096
    max_messages: 50
    token_buffer_percent: 20
    
    # Persistence
    persistence_enabled: true
    session_timeout_hours: 24
    archive_after_days: 30
    
    # Summarization
    summarization_enabled: true
    summarize_after_messages: 20
    summary_max_tokens: 200
    summary_model: "llama3.2:latest"
```

## API Endpoints

### Get Token Usage
```bash
GET /conversations/{id}/token-usage

# Response:
{
  "total": 2847,
  "by_role": {
    "system": 512,
    "user": 1203,
    "assistant": 1132
  },
  "context_limit": 4096,
  "max_allowed_tokens": 3276,  # 80% of limit
  "utilization_percent": 86.9,
  "model": "llama3.2:latest"
}
```

### Manual Pruning
```bash
POST /conversations/{id}/prune

# Response:
{
  "success": true,
  "pruning_result": {
    "messages_pruned": 15,
    "messages_kept": 10,
    "tokens_before": 4200,
    "tokens_after": 1800,
    "summary": "User discussed project setup..."
  }
}
```

## Database Schema

### conversation_summaries Table
```sql
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    summary_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    message_count INTEGER NOT NULL,
    start_timestamp TIMESTAMP WITH TIME ZONE,
    end_timestamp TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Enhanced conversations Table
```sql
ALTER TABLE conversations ADD COLUMN total_tokens INTEGER DEFAULT 0;
ALTER TABLE conversations ADD COLUMN active_tokens INTEGER DEFAULT 0;
ALTER TABLE conversations ADD COLUMN pruning_strategy VARCHAR(50) DEFAULT 'sliding_window';
```

## Implementation Details

### Token Counting Service

The `TokenCounter` service (`chatbot/services/token_counter.py`) provides:
- Model-specific encodings using tiktoken
- Token counting for individual messages and conversations
- Message truncation to fit token limits
- Intelligent message fitting algorithms

### Conversation Summarizer

The `ConversationSummarizer` service (`chatbot/services/conversation_summarizer.py`) provides:
- LLM-powered summarization with fallback strategies
- Topic and entity extraction
- Configurable summary lengths
- JSON-structured summaries

### Persistence Layer

The `ConversationManagerDB` (`chatbot/core/conversation_manager_db.py`) provides:
- Automatic pruning on message addition
- Database-backed conversation storage
- Summary generation and storage
- Token usage tracking

## Usage Examples

### Python Integration
```python
from chatbot.services.token_counter import get_token_counter
from chatbot.services.conversation_summarizer import get_conversation_summarizer

# Count tokens
counter = get_token_counter("llama3.2:latest")
tokens = counter.count_tokens("Hello, how are you?")

# Summarize messages
summarizer = get_conversation_summarizer()
summary = await summarizer.summarize_messages(messages)
```

### Frontend Integration
```javascript
// Get token usage
const response = await fetch(`/api/conversations/${conversationId}/token-usage`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const usage = await response.json();

// Display usage
console.log(`Using ${usage.utilization_percent}% of token limit`);
```

## Performance Considerations

1. **Token Counting Overhead**: Tiktoken is optimized for performance but adds ~1-2ms per message
2. **Summarization Latency**: LLM summarization takes 1-3 seconds depending on content
3. **Database Writes**: Pruning operations are batched within transactions
4. **Memory Usage**: In-memory mode keeps all active sessions (plan for ~10KB per session)

## Troubleshooting

### Common Issues

1. **"Conversation exceeds token limit"**
   - Increase `BEE_CONVERSATION_MAX_TOKENS`
   - Enable summarization
   - Reduce `BEE_CONVERSATION_SUMMARIZE_AFTER_MESSAGES`

2. **Summaries not generating**
   - Check LLM service is healthy
   - Verify `BEE_CONVERSATION_SUMMARIZATION_ENABLED=true`
   - Check logs for summarization errors

3. **Conversations lost on restart**
   - Enable persistence: `BEE_CONVERSATION_PERSISTENCE_ENABLED=true`
   - Ensure PostgreSQL is running
   - Check database migration status

## Credits

This implementation uses the following open-source libraries:

- **[tiktoken](https://github.com/openai/tiktoken)** - OpenAI's fast BPE tokenizer for accurate token counting
  - License: MIT
  - Used for model-specific token counting and text truncation

## Future Enhancements

1. **Importance-based pruning** - Keep important messages regardless of age
2. **User-controlled summarization** - Manual summary triggers
3. **Export with summaries** - Include summaries in conversation exports
4. **Multi-model token counting** - Support for more model families
5. **Streaming token updates** - Real-time token usage in UI

---

🐝 Keeping conversations buzzing efficiently!