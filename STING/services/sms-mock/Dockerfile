FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask

# Copy application
COPY app.py .

# Expose port
EXPOSE 8030

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8030/health')" || exit 1

# Run the application
CMD ["python", "app.py"]