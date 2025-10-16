#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# URLs
KRATOS_PUBLIC_URL="https://localhost:4433"
FRONTEND_URL="https://localhost:3000"

# Email and password to test
TEST_EMAIL="admin@example.com" 
TEST_PASSWORD="Admin123!"

echo -e "${BLUE}=== Testing direct HTTP auth flow ===${NC}"
echo -e "${YELLOW}Testing with user: ${TEST_EMAIL}${NC}"

# Step 1: Let's verify users in database
echo -e "\n${BLUE}=== Step 1: Verifying users in database ===${NC}"
# Get database container name
DB_CONTAINER=$(docker ps | grep -E 'postgres|db' | head -1 | awk '{print $NF}')
QUERY="SELECT id, traits->'traits'->>'email' as email FROM identities WHERE traits->'traits'->>'email' = '${TEST_EMAIL}';"
USER_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "$QUERY" | grep -v "^$" | sed 's/^[ \t]*//' | cut -d'|' -f1 | tr -d ' ')

if [[ -z "$USER_ID" ]]; then
  echo -e "${RED}❌ User ${TEST_EMAIL} not found in database${NC}"
  
  # Show all users
  echo -e "${YELLOW}Showing all users in database:${NC}"
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "SELECT id, traits->'traits'->>'email' as email FROM identities;" | grep -v "^$" | sed 's/^[ \t]*//'
else
  echo -e "${GREEN}✓ Found user ID: ${USER_ID}${NC}"
fi

# Step 2: Check credentials in database
echo -e "\n${BLUE}=== Step 2: Checking credentials for user ===${NC}"
CREDENTIALS_QUERY="SELECT ic.id FROM identity_credentials ic JOIN identity_credential_identifiers ici ON ic.id = ici.identity_credential_id WHERE ici.identifier = '${TEST_EMAIL}';"
CREDENTIAL_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "$CREDENTIALS_QUERY" | grep -v "^$" | sed 's/^[ \t]*//')

if [[ -z "$CREDENTIAL_ID" ]]; then
  echo -e "${RED}❌ No credential found for ${TEST_EMAIL}${NC}"
  
  # Show all credentials
  echo -e "${YELLOW}Checking credential identifiers:${NC}"
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "SELECT * FROM identity_credential_identifiers;" 
else
  echo -e "${GREEN}✓ Found credential ID: ${CREDENTIAL_ID}${NC}"
fi

# Step 3: Get fresh login cookies by visiting login page
echo -e "\n${BLUE}=== Step 3: Getting login cookies ===${NC}"
BROWSER_RESPONSE=$(curl -k -v "${KRATOS_PUBLIC_URL}/self-service/login/browser" 2>&1)
LOGIN_FLOW_URL=$(echo "$BROWSER_RESPONSE" | grep -o 'Location: [^"]*' | tail -1 | sed 's/Location: //')
LOGIN_FLOW_ID=$(echo "$LOGIN_FLOW_URL" | grep -o 'flow=[^&]*' | sed 's/flow=//')
COOKIES=$(echo "$BROWSER_RESPONSE" | grep -i 'set-cookie:' | sed 's/set-cookie: //')

echo -e "${YELLOW}Login Flow ID: ${LOGIN_FLOW_ID}${NC}"
echo -e "${YELLOW}Cookies: ${COOKIES}${NC}"

# Step 4: Get the login form with flow ID
echo -e "\n${BLUE}=== Step 4: Fetching login form ===${NC}"
FORM_RESPONSE=$(curl -k -s "${KRATOS_PUBLIC_URL}/self-service/login/flows?id=${LOGIN_FLOW_ID}")
CSRF_TOKEN=$(echo "$FORM_RESPONSE" | grep -o '"csrf_token","value":"[^"]*"' | cut -d'"' -f6)

echo -e "${YELLOW}CSRF Token: ${CSRF_TOKEN}${NC}"

# Show available methods
METHODS=$(echo "$FORM_RESPONSE" | grep -o '"method","type":"submit","value":"[^"]*"' | grep -o 'value":"[^"]*"' | cut -d'"' -f3)
echo -e "${YELLOW}Available methods:${NC}"
echo "$METHODS" | while read method; do
  echo -e "  - ${method}"
done

# Step 5: Create a session manually in database
echo -e "\n${BLUE}=== Step 5: Creating a session manually ===${NC}"

if [[ -z "$USER_ID" ]]; then
  echo -e "${RED}❌ Cannot create session without user ID${NC}"
else
  # Generate a session ID
  SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
  
  # Create the session
  SESSION_QUERY="INSERT INTO sessions (
    id, 
    nid, 
    identity_id, 
    created_at, 
    updated_at, 
    expires_at, 
    active
  ) VALUES (
    '${SESSION_ID}', 
    NULL, 
    '${USER_ID}', 
    NOW(), 
    NOW(), 
    NOW() + INTERVAL '24 hours', 
    true
  ) RETURNING id;"
  
  SESSION_RESULT=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "$SESSION_QUERY" 2>&1 || echo "Failed to create session")
  
  if [[ "$SESSION_RESULT" == *"Failed"* ]]; then
    echo -e "${RED}❌ Failed to create session: ${SESSION_RESULT}${NC}"
  else
    echo -e "${GREEN}✓ Created session ID: ${SESSION_ID}${NC}"
    echo -e "${YELLOW}Try accessing the frontend with session cookie: ory_kratos_session=${SESSION_ID}${NC}"
  fi
fi

echo -e "\n${BLUE}=== Test completed ===${NC}"