#!/bin/bash
# Fix for config loader issue
set -e

SOURCE_DIR=$(dirname "$0")
cd "$SOURCE_DIR"

echo "Creating config_data volume if it doesn't exist..."
docker volume create config_data

echo "Copying config_loader.py to config_data volume..."
# Create a temporary container to mount the volume
docker run --rm -v config_data:/config_data -v "$PWD/conf:/app/conf" alpine sh -c "cp /app/conf/config_loader.py /config_data/config_loader.py && chmod 755 /config_data/config_loader.py && cp /app/conf/config.yml /config_data/config.yml && chmod 644 /config_data/config.yml && mkdir -p /config_data/env && echo 'Config files copied successfully!'"

echo "Verifying copy operation..."
docker run --rm -v config_data:/config_data alpine sh -c "ls -la /config_data"

echo "Updating Dockerfile.config..."
cat > Dockerfile.config.fixed << 'EOF'
FROM python:3.12-slim

ARG POSTGRESQL_USER
ARG POSTGRESQL_DATABASE_NAME
ARG POSTGRESQL_HOST
ARG POSTGRESQL_PORT

# Set environment variables
ENV POSTGRESQL_USER=${POSTGRESQL_USER} \
    POSTGRESQL_DATABASE_NAME=${POSTGRESQL_DATABASE_NAME} \
    POSTGRESQL_HOST=${POSTGRESQL_HOST} \
    POSTGRESQL_PORT=${POSTGRESQL_PORT}

# Set working directory 
WORKDIR /app

# Create conf directory
RUN mkdir -p /app/conf

# Copy configuration files
COPY ./conf/ /app/conf/

# Set permissions
RUN chmod -R 755 /app/conf/ && \
    find /app/conf/ -type f -exec chmod 644 {} \;

# Clear Python cache during build
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete

# Install dependencies
RUN pip install pyyaml hvac requests

# Run config_loader - use the file from the volume
CMD ["sh", "-c", "if [ -f /app/conf/config_loader.py ]; then python /app/conf/config_loader.py /app/conf/config.yml; else echo 'Using volume-mounted config_loader.py'; python /config_data/config_loader.py /app/conf/config.yml; fi"]
EOF

echo "Backing up original Dockerfile.config..."
cp Dockerfile.config Dockerfile.config.bak.$(date +%Y%m%d%H%M%S)

echo "Installing fixed Dockerfile.config..."
mv Dockerfile.config.fixed Dockerfile.config
chmod 644 Dockerfile.config

echo "Fix completed. You can now try running ./manage_sting.sh start llm-gateway again."