FROM python:3.12.8-slim

WORKDIR /app

# Install system dependencies needed for httpx and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./llm_service/requirements.common.txt /app/requirements.common.txt
COPY ./chatbot/requirements.txt /app/requirements.txt

# Install dependencies with error output
RUN pip install --no-cache-dir -r /app/requirements.common.txt && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY ./chatbot /app/chatbot
COPY ./llm_service/chat /app/llm_service/chat
COPY ./llm_service/filtering /app/llm_service/filtering
COPY ./conf /app/conf

# Create directories
RUN mkdir -p /app/env /app/logs

# Set permissions
RUN chmod -R 755 /app && \
    find /app -type f -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \; && \
    chmod +x /app/chatbot/entrypoint.sh || true

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8081

EXPOSE 8081

# Make entrypoint script executable
RUN chmod +x /app/chatbot/entrypoint.sh

# Use entrypoint script to start the service
ENTRYPOINT ["/bin/bash", "/app/chatbot/entrypoint.sh"]