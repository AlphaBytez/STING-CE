FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy messaging service code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Create volume for message storage
VOLUME ["/app/data"]

# Expose ports
EXPOSE 8889

# Healthcheck defined in docker-compose.yml for consistency

# Run the messaging service
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8889"]