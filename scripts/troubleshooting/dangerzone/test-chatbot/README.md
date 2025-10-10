# Test Chatbot Services for STING

This directory contains standalone test implementations for the STING chatbot service. These implementations are designed to help diagnose and isolate issues with the chatbot functionality.

## Available Test Services

### 1. Standalone Chatbot (Port 8082)

A completely standalone implementation that uses no external dependencies. It provides a simple rule-based chatbot experience.

**Features:**
- No dependencies on LLM or other services
- Simple HTTP server implementation
- Basic conversation tracking
- Always responds successfully

**To start:**
```bash
./start-standalone.sh
```

**To test:**
```bash
curl -X POST http://localhost:8082/chat/message -H "Content-Type: application/json" -d '{"message": "Hello", "user_id": "test_user"}'
```

### 2. Advanced Chatbot (Port 8083)

A more advanced implementation that attempts to connect to the LLM Gateway but falls back to simple responses if the connection fails.

**Features:**
- Tries to use the LLM Gateway for responses
- Falls back to rule-based responses if the LLM Gateway is unavailable
- Designed to help diagnose LLM Gateway connectivity issues

**To start:**
```bash
./start-advanced.sh
```

**To test:**
```bash
curl -X POST http://localhost:8083/chat/message -H "Content-Type: application/json" -d '{"message": "Hello", "user_id": "test_user"}'
```

## Troubleshooting the Original Chatbot Service

If you're experiencing issues with the main STING chatbot service, try these diagnostic steps:

1. **Check if the LLM Gateway is responsive:**
   ```bash
   curl -X POST http://localhost:8085/generate -H "Content-Type: application/json" -d '{"message": "test", "max_tokens": 10, "model": "llama3"}'
   ```

2. **Check the model directories:**
   ```bash
   ls -la ~/Downloads/llm_models/
   ```

3. **Check logs from chatbot and LLM Gateway:**
   ```bash
   docker logs sting-ce-chatbot
   docker logs sting-ce-llm-gateway-1
   ```

## Integration with Frontend

The test chatbot services can be used with the existing frontend by modifying the `REACT_APP_CHATBOT_URL` environment variable:

For standalone chatbot:
```
REACT_APP_CHATBOT_URL=http://localhost:8082/chat
```

For advanced chatbot:
```
REACT_APP_CHATBOT_URL=http://localhost:8083/chat
```

## Common Issues

1. **Permission denied errors**: Make sure all script files are executable with `chmod +x *.sh`
2. **Network connectivity**: All containers must be on the `sting_local` network
3. **Port conflicts**: Make sure ports 8082 and 8083 are available