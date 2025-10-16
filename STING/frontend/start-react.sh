#!/bin/sh
set -e

echo "Starting React with HTTPS configuration..."

# Show certificate files and info
echo "Certificate locations:"
echo "SSL_CRT_FILE: $SSL_CRT_FILE"
echo "SSL_KEY_FILE: $SSL_KEY_FILE"

# Wait for certificates (up to 30 seconds)
WAIT_TIME=0
MAX_WAIT=30

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
  if [ -f "$SSL_CRT_FILE" ] && [ -f "$SSL_KEY_FILE" ]; then
    echo "✅ SSL certificates found after ${WAIT_TIME}s, enabling HTTPS"
    # Start with HTTPS enabled
    GENERATE_SOURCEMAP=false HTTPS=true SSL_CRT_FILE=$SSL_CRT_FILE SSL_KEY_FILE=$SSL_KEY_FILE exec npm start
  fi
  
  if [ $WAIT_TIME -eq 0 ]; then
    echo "⏳ Waiting for SSL certificates..."
  fi
  
  sleep 1
  WAIT_TIME=$((WAIT_TIME + 1))
done

# If we get here, certificates weren't found
echo "❌ SSL certificates not found after ${MAX_WAIT}s, falling back to HTTP"
# Start with HTTPS disabled
GENERATE_SOURCEMAP=false HTTPS=false exec npm start