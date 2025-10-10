FROM python:3.12.8-slim

WORKDIR /app

# Install system dependencies needed for httpx and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from the original chatbot
COPY ./llm_service/requirements.common.txt /app/requirements.common.txt
COPY ./chatbot/requirements.txt /app/requirements.txt

# Install dependencies with additional upgrades
RUN pip install --no-cache-dir -r /app/requirements.common.txt && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir --upgrade accelerate && \
    pip install --no-cache-dir --upgrade bitsandbytes

# Copy application code
COPY ./chatbot /app/chatbot
COPY ./llm_service/chat /app/llm_service/chat
COPY ./llm_service/filtering /app/llm_service/filtering

# Create directories
RUN mkdir -p /app/env /app/logs

# Set permissions
RUN chmod -R 755 /app && \
    find /app -type f -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \;

# Copy our custom entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8082 \
    HOST=0.0.0.0 \
    LOG_LEVEL=DEBUG \
    CHATBOT_NAME=TestBee \
    CHATBOT_MODEL=llama3 \
    CHATBOT_CONTEXT_WINDOW=10 \
    CHATBOT_SYSTEM_PROMPT="You are TestBee, a test assistant for the STING platform." \
    CHATBOT_TOOLS_ENABLED=true \
    CHATBOT_ALLOWED_TOOLS=search,summarize,analyze \
    CHATBOT_REQUIRE_AUTH=false \
    CHATBOT_LOG_CONVERSATIONS=true \
    CHATBOT_CONTENT_FILTER_LEVEL=none \
    LLM_GATEWAY_URL=http://sting-ce-llm-gateway-1:8080

EXPOSE 8082

# Use our custom entrypoint script to start the service
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]