#!/bin/bash
# manual_verify_email.sh - Manually trigger email verification

set -euo pipefail

EMAIL="${1:-test@example.com}"

echo "Manually triggering email verification for: $EMAIL"
echo "============================================"

# Create verification flow via browser endpoint (redirect to API)
echo "Creating verification flow..."

# First, we need to get a flow
FLOW_RESPONSE=$(curl -s -k -L -H "Accept: application/json" \
  "https://localhost:4433/self-service/verification/browser")

if echo "$FLOW_RESPONSE" | jq -e '.id' >/dev/null 2>&1; then
    FLOW_ID=$(echo "$FLOW_RESPONSE" | jq -r '.id')
    echo "Flow ID: $FLOW_ID"
    
    # Submit email for verification
    echo "Submitting email for verification..."
    VERIFY_RESPONSE=$(curl -s -k -X POST \
      "https://localhost:4433/self-service/verification?flow=$FLOW_ID" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -H "Accept: application/json" \
      -d "method=link&email=$EMAIL")
    
    echo "Response:"
    echo "$VERIFY_RESPONSE" | jq '.'
    
    # Check mailpit
    echo ""
    echo "Checking mailpit for emails..."
    sleep 2
    curl -s http://localhost:8025/api/v1/messages | jq '.messages[] | select(.To[0].Address == "'$EMAIL'") | {to: .To[0].Address, subject: .Subject}'
else
    echo "Error creating verification flow:"
    echo "$FLOW_RESPONSE"
fi