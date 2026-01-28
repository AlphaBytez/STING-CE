FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY ./external_ai_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./external_ai_service/app.py .
COPY ./external_ai_service/providers ./providers
COPY ./external_ai_service/llm_queue_manager.py .
COPY ./external_ai_service/bee_context_manager.py .
COPY ./external_ai_service/bee_brain_v2.0.0.md .
COPY ./external_ai_service/bee_brains ./bee_brains
COPY ./external_ai_service/bee_brain_manager.py .
COPY ./external_ai_service/bee_system_prompt.txt .
COPY ./external_ai_service/conversation_cache.py .
COPY ./external_ai_service/conversation_semantic_search.py .
COPY ./external_ai_service/conversation_summarizer.py .
COPY ./external_ai_service/conversation_store.py .
COPY ./external_ai_service/web_search_provider.py .

# Copy PII middleware
COPY ./app/middleware /app/app/middleware

# Create non-root user with cache directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/.cache/chroma && \
    chown -R appuser:appuser /app /home/appuser/.cache
USER appuser

# Healthcheck defined in docker-compose.yml for consistency

# Expose port
EXPOSE 8091

# Run the application
CMD ["python", "app.py"]