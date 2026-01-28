FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY app/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/run_report_worker.py ./scripts/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WORKER_TYPE=report_worker

# Create log directory
RUN mkdir -p /var/log/report-worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the worker
CMD ["python", "scripts/run_report_worker.py"]