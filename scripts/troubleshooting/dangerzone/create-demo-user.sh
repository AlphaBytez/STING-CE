#!/bin/bash
set -e

EMAIL="demo@example.com"  # Set a consistent email for easier debugging
NAME="STING"
LASTNAME="Demo"

echo "Creating demo user with email: $EMAIL"

# Uses curl with --insecure flag to bypass SSL certificate validation
# This is just for local development and testing

# Step 1: Get a new registration flow
FLOW_RESPONSE=$(curl -k -s -X GET "https://localhost:4433/self-service/registration/api")
FLOW_ID=$(echo $FLOW_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | grep -o '[^"]*$')

if [ -z "$FLOW_ID" ]; then
  echo "Error: Couldn't get flow ID from Kratos"
  echo "Response: $FLOW_RESPONSE"
  exit 1
fi

echo "Got registration flow ID: $FLOW_ID"

# Step 2: Get CSRF token from the flow
FLOW_DETAILS=$(curl -k -s "https://localhost:4433/self-service/registration/flows?id=$FLOW_ID")
CSRF_TOKEN=$(echo "$FLOW_DETAILS" | grep -o '"name":"csrf_token".*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)

if [ -z "$CSRF_TOKEN" ]; then
  echo "Error: Couldn't get CSRF token"
  echo "Flow details: $FLOW_DETAILS"
  exit 1
fi

echo "Got CSRF token: ${CSRF_TOKEN:0:20}..."

# Step 3: Submit the registration with profile method
REGISTRATION_DATA='{
  "method": "profile", 
  "csrf_token": "'"$CSRF_TOKEN"'", 
  "traits": {
    "email": "'"$EMAIL"'",
    "name": {
      "first": "'"$NAME"'", 
      "last": "'"$LASTNAME"'"
    }
  }
}'

echo "Submitting registration with data:"
echo "$REGISTRATION_DATA" | jq . 2>/dev/null || echo "$REGISTRATION_DATA"

REGISTRATION_RESULT=$(curl -k -s -X POST \
  -H "Content-Type: application/json" \
  "https://localhost:4433/self-service/registration?flow=$FLOW_ID" \
  -d "$REGISTRATION_DATA")

echo "Registration complete. Result:"
echo "$REGISTRATION_RESULT" | jq . 2>/dev/null || echo "$REGISTRATION_RESULT"

echo "Demo user created successfully. Use email $EMAIL to login and test the application."