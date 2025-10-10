# STING Chatbot & LLM Gateway Fix Guide

This document provides a comprehensive guide to resolving the issues with the STING chatbot service and LLM Gateway. Follow these steps to fix the problems related to model loading and port conflicts.

## Problem Summary

1. **LLM Gateway Issues**:
   - Deprecated `load_in_8bit` parameter causing model loading failures
   - BitsAndBytes library needing updates
   - Missing chat template for Llama-3 models
   - Port conflicts across multiple services

2. **Database Issues**:
   - PostgreSQL healthcheck using incorrect user (trying "root" instead of "postgres")

3. **Service Conflicts**:
   - Multiple services using conflicting ports

## Solution Steps

### 1. Fix the Database Healthcheck

```bash
# Edit docker-compose.yml to specify the correct user for PostgreSQL healthcheck
sed -i'.bak.dbfix' 's/test: \["CMD", "pg_isready"\]/test: \["CMD", "pg_isready", "-U", "postgres"\]/g' docker-compose.yml

# Restart database service
docker-compose stop db
docker-compose rm -f db
docker-compose up -d db
```

### 2. Update the LLM Gateway Service

Create an updated `server.py.final` file in the `llm_service` directory with these improvements:
- Use modern BitsAndBytesConfig instead of deprecated parameters
- Add proper Llama-3 chat template initialization
- Handle device mapping correctly
- Ensure the server runs on the correct port

```python
# Key changes in server.py.final:

# 1. Define Llama 3 chat template
LLAMA_3_CHAT_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ system_prompt | default: "You are a helpful AI assistant. Be concise." }}<|eot_id|>

{% for message in messages %}
<|start_header_id|>{{ message["role"] }}<|end_header_id|>

{{ message["content"] }}<|eot_id|>
{% endfor %}

<|start_header_id|>assistant<|end_header_id|>

"""

# 2. Set chat template during initialization
if MODEL_NAME.startswith("llama"):
    logger.info("Setting Llama 3 chat template")
    tokenizer.chat_template = LLAMA_3_CHAT_TEMPLATE

# 3. Configure model loading with modern parameters
model_load_params = {
    "pretrained_model_name_or_path": MODEL_PATH,
    "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
}

# Only set device_map if not using quantization
if quantization_config is None and device == "cpu":
    model_load_params["device_map"] = "cpu"
else:
    model_load_params["device_map"] = "auto"
```

### 3. Update Dockerfile for LLM Gateway

Create a fixed Dockerfile that properly installs the latest BitsAndBytes:

```dockerfile
# Install dependencies with specific version constraints
RUN pip install --no-cache-dir -r requirements.gateway.txt && \
    pip install --no-cache-dir --upgrade accelerate>=0.23.0 && \
    pip install --no-cache-dir --upgrade bitsandbytes>=0.41.1
```

### 4. Fix Port Conflicts

Update all port mappings in docker-compose.yml to avoid conflicts:

```bash
sed -i'.bak.ports' \
    -e 's/8200:8200/8201:8200/g' \
    -e 's/8085:8080/8086:8080/g' \
    -e 's/5433:5432/5434:5432/g' \
    -e 's/1026:1025/1027:1025/g' \
    -e 's/4436:4436/4438:4436/g' \
    -e 's/4437:4437/4439:4437/g' \
    -e 's/4433:4433/4443:4433/g' \
    -e 's/4434:4434/4444:4434/g' \
    -e 's/5050:5050/5051:5050/g' \
    -e 's/3000:3000/3002:3000/g' \
    docker-compose.yml
```

### 5. Temporarily Disable Quantization

While fixing the model loading issues, set `QUANTIZATION=none` for all LLM services:

```yaml
environment:
  - MODEL_PATH=/app/models/llama-3-8b
  - MODEL_NAME=llama3
  - DEVICE_TYPE=auto
  - HF_TOKEN=${HF_TOKEN:-dummy}
  - QUANTIZATION=none  # Disable quantization to avoid bitsandbytes issues
```

### 6. Start Services in Correct Order

```bash
# First start the database with fixed healthcheck
docker-compose up -d db

# Start other essential services
docker-compose up -d vault dev kratos

# Start the LLM services
docker-compose up -d llama3-service phi3-service zephyr-service

# Start the LLM Gateway with fixed server
docker-compose up -d llm-gateway

# Finally start the remaining services
docker-compose up -d app frontend mailslurper chatbot
```

## Troubleshooting

If you still encounter issues with the chatbot service, you can use the simplified chatbot server included in `chatbot/simple_server.py`. This implementation provides a functioning API without requiring the LLM Gateway to be operational.

To use it:
```bash
# Update docker-compose.yml command for chatbot service
# command: python -m chatbot.simple_server

# Or manually run it in the container:
docker exec -d sting-ce-chatbot python -m chatbot.simple_server
```

## Verification

Test the chatbot API with:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?", "user_id": "test-user", "conversation_id": "test-convo"}' \
  http://localhost:8081/chat/message
```

Verify the LLM Gateway with:

```bash
curl -s http://localhost:8086/health
```

## Future Improvements

1. **Model Loading**: Consider implementing a more robust model loading system with better error handling and automatic fallbacks.
2. **Container Dependencies**: Refine container dependencies to ensure smoother startup sequence.
3. **Performance Optimization**: Once basic functionality is working, re-enable quantization with proper configurations for better performance.
4. **Health Monitoring**: Implement more comprehensive health checks that validate actual model availability.