FROM python:3.11-slim

# Install necessary system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    libpq-dev \
    curl \
    openssl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/sting-ce/app

# ENV POSTGRES_USER=postgres \
#     POSTGRES_PASSWORD=default_password \
#     POSTGRES_DB=sting_app \
#     POSTGRES_HOST=db \
#     POSTGRES_PORT=5432 \
#     FLASK_APP=run:app

# Set pip configuration for better performance
ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/opt/sting-ce

# Copy requirements and install dependencies
COPY conf/requirements.in /opt/sting-ce/conf/
COPY app/requirements.txt /opt/sting-ce/app/
RUN pip install --upgrade pip && \
    pip install -r /opt/sting-ce/conf/requirements.in && \
    pip install -r /opt/sting-ce/app/requirements.txt 

# Copy the conf directory (needed for vault_manager import)
COPY conf/ /opt/sting-ce/conf/

# Copy the rest of the application
COPY app/ .

# Verify critical directories were copied correctly
RUN if [ ! -d "models" ]; then \
        echo "ERROR: models directory not found after COPY!"; \
        echo "Contents of /opt/sting-ce/app:"; \
        ls -la /opt/sting-ce/app/; \
        exit 1; \
    fi && \
    if [ ! -f "models/__init__.py" ]; then \
        echo "ERROR: models/__init__.py not found!"; \
        echo "Contents of models directory:"; \
        ls -la models/; \
        exit 1; \
    fi && \
    echo "✓ Verified models directory and __init__.py exist" && \
    echo "✓ Model files found:" && \
    ls -1 models/*.py | wc -l

# Expose the application port
EXPOSE 5050

ENTRYPOINT []
CMD ["python", "run.py"]
