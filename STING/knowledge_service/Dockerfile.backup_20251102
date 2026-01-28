FROM python:3.12.8-slim

# Set working directory
WORKDIR /app

# Install system dependencies including build tools for ChromaDB
# Add retry logic for network issues
RUN apt-get update || apt-get update || apt-get update && \
    apt-get install -y --fix-missing \
    curl \
    gcc \
    g++ \
    python3-dev \
    libmagic1 \
    libmagic-dev \
    build-essential \
    cmake \
    || (apt-get update && apt-get install -y --fix-missing \
    curl \
    gcc \
    g++ \
    python3-dev \
    libmagic1 \
    libmagic-dev \
    build-essential \
    cmake) \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt

# Install setuptools and wheel first (required for some packages)
RUN pip install --no-cache-dir setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /var/log/knowledge-service /tmp/sting_uploads

# Set permissions
RUN chmod -R 755 /app && \
    find /app -type f -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \; && \
    chmod +x /app/startup.sh

# Environment variables
ENV PYTHONPATH=/app
ENV KNOWLEDGE_PORT=8090
ENV KNOWLEDGE_HOST=0.0.0.0
ENV CHROMA_URL=http://chroma:8000
ENV KNOWLEDGE_DEV_MODE=false

# Healthcheck defined in docker-compose.yml for consistency

# Expose port
EXPOSE 8090

# Run the application with database support
CMD ["/app/startup.sh"]