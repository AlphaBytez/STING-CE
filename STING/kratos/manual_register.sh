#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check for email parameter
if [ -z "$1" ]; then
  # Generate a test email if none provided
  TIMESTAMP=$(date +%s)
  TEST_EMAIL="test${TIMESTAMP}@example.com"
  echo -e "${YELLOW}No email provided, using generated email: ${TEST_EMAIL}${NC}"
else
  TEST_EMAIL="$1"
  echo -e "${YELLOW}Using provided email: ${TEST_EMAIL}${NC}"
fi

if [ -z "$2" ]; then
  # Generate a test password if none provided
  TEST_PASSWORD="Test1234!"
  echo -e "${YELLOW}No password provided, using default password: ${TEST_PASSWORD}${NC}"
else
  TEST_PASSWORD="$2"
  echo -e "${YELLOW}Using provided password: ${TEST_PASSWORD}${NC}"
fi

# Get database container name
DB_CONTAINER=$(docker ps | grep -E 'postgres|db' | head -1 | awk '{print $NF}')

if [[ -z "$DB_CONTAINER" ]]; then
  echo -e "${RED}❌ No database container found${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Found database container: ${DB_CONTAINER}${NC}"
fi

echo -e "\n${BLUE}=== Creating new user directly in Kratos database ===${NC}"

# Create identity JSON with proper traits
IDENTITY_JSON=$(cat << EOF
{"traits": {"email": "${TEST_EMAIL}"}}
EOF
)

# Insert the identity
echo -e "${YELLOW}Step 1: Creating identity record${NC}"
IDENTITY_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
  INSERT INTO identities (
    id, 
    schema_id, 
    traits, 
    created_at,
    updated_at,
    state
  ) VALUES (
    gen_random_uuid(), 
    'default', 
    '${IDENTITY_JSON}',
    NOW(),
    NOW(),
    'active'
  ) RETURNING id;
" | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')

if [[ -z "$IDENTITY_ID" ]]; then
  echo -e "${RED}❌ Failed to create identity record${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Created identity with ID: ${IDENTITY_ID}${NC}"
fi

# Create password hash
echo -e "${YELLOW}Step 2: Generating password hash${NC}"
# Use Argon2 parameters that match Kratos default
HASHED_PASSWORD=$(docker exec $DB_CONTAINER bash -c "
  echo -n '${TEST_PASSWORD}' | argon2 any_salt -id -t 3 -k 65536 -m 16 -p 4 -l 32 2>/dev/null | cut -d' ' -f 2
")

if [[ -z "$HASHED_PASSWORD" || "$HASHED_PASSWORD" == *"Error"* ]]; then
  echo -e "${RED}❌ Failed to generate password hash${NC}"
  # Fallback test hash (don't use this in production)
  HASHED_PASSWORD='$argon2id$v=19$m=65536,t=3,p=4$YW55X3NhbHQ$C6+/FgdArwYV6AWQ/zwGHaKL54IQFF+1+eYrVT2+vk0'
  echo -e "${YELLOW}Using fallback test hash${NC}"
fi

# Create identity credentials
echo -e "${YELLOW}Step 3: Creating identity credentials${NC}"
# Get the password credential type ID
PASSWORD_TYPE_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
  SELECT id FROM identity_credential_types WHERE name = 'password';
" | sed 's/^[ \t]*//' | tr -d '\n')

if [[ -z "$PASSWORD_TYPE_ID" ]]; then
  echo -e "${RED}❌ Could not find password credential type${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Found password credential type: ${PASSWORD_TYPE_ID}${NC}"
fi

CREDENTIAL_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
  INSERT INTO identity_credentials (
    id,
    identity_id,
    created_at,
    updated_at,
    identity_credential_type_id,
    config,
    version
  ) VALUES (
    gen_random_uuid(),
    '${IDENTITY_ID}',
    NOW(),
    NOW(),
    '${PASSWORD_TYPE_ID}',
    '{\"hashed_password\": \"${HASHED_PASSWORD}\"}',
    1
  ) RETURNING id;
" | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')

if [[ -z "$CREDENTIAL_ID" ]]; then
  echo -e "${RED}❌ Failed to create credentials${NC}"
  # Remove the identity if we couldn't create credentials
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identities WHERE id = '${IDENTITY_ID}';" || echo "Failed to clean up identity"
  exit 1
else
  echo -e "${GREEN}✓ Created credentials with ID: ${CREDENTIAL_ID}${NC}"
fi

# Create identity credential identifier
echo -e "${YELLOW}Step 4: Creating credential identifier${NC}"

# Create a credential identifier (for login)
IDENTIFIER_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
  INSERT INTO identity_credential_identifiers (
    id,
    identifier,
    identity_credential_id,
    created_at,
    updated_at,
    identity_credential_type_id
  ) VALUES (
    gen_random_uuid(),
    '${TEST_EMAIL}',
    '${CREDENTIAL_ID}',
    NOW(),
    NOW(),
    '${PASSWORD_TYPE_ID}'
  ) RETURNING id;
" | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')

if [[ -z "$IDENTIFIER_ID" ]]; then
  echo -e "${RED}❌ Failed to create credential identifier${NC}"
  echo -e "${YELLOW}User may not be able to log in with email${NC}"
else
  echo -e "${GREEN}✓ Created credential identifier with ID: ${IDENTIFIER_ID}${NC}"
fi

echo -e "\n${GREEN}SUCCESS: User created successfully${NC}"
echo -e "${GREEN}Email: ${TEST_EMAIL}${NC}"
echo -e "${GREEN}Password: ${TEST_PASSWORD}${NC}"
echo -e "${YELLOW}Try logging in with these credentials now.${NC}"