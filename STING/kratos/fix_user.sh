#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== STING Kratos User Fix Script ===${NC}"

# Get database container
DB_CONTAINER=$(docker ps | grep -E 'postgres|db' | head -1 | awk '{print $NF}')
if [[ -z "$DB_CONTAINER" ]]; then
  echo -e "${RED}❌ No database container found${NC}"
  exit 1
fi

# Create test user with correct traits format
TEST_EMAIL="test@example.com"
TEST_PASSWORD="password"

echo -e "${YELLOW}Creating test user with email: ${TEST_EMAIL}${NC}"

# Delete old credentials
docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identity_credential_identifiers WHERE identifier = '${TEST_EMAIL}';"
docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identity_credentials WHERE identity_id = '594935c8-14b9-4c07-9523-ab6f099bcb99';"
docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identities WHERE id = '594935c8-14b9-4c07-9523-ab6f099bcb99';"

# Create identity with CORRECT traits format
USER_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
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
    '{\"traits\": {\"email\": \"${TEST_EMAIL}\"}}',
    NOW(),
    NOW(),
    'active'
  ) RETURNING id;
" | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')

echo -e "${GREEN}✓ Created user with ID: ${USER_ID}${NC}"

# Get password credential type
PASSWORD_TYPE_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
  SELECT id FROM identity_credential_types WHERE name = 'password';
" | sed 's/^[ \t]*//' | tr -d '\n')

# Create credential
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
    '${USER_ID}',
    NOW(),
    NOW(),
    '${PASSWORD_TYPE_ID}',
    '{\"hashed_password\": \"\$argon2id\$v=19\$m=65536,t=3,p=4\$YW55X3NhbHQ\$C6+/FgdArwYV6AWQ/zwGHaKL54IQFF+1+eYrVT2+vk0\"}',
    1
  ) RETURNING id;
" | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')

echo -e "${GREEN}✓ Created credential with ID: ${CREDENTIAL_ID}${NC}"

# Create credential identifier
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

echo -e "${GREEN}✓ Created credential identifier with ID: ${IDENTIFIER_ID}${NC}"

echo -e "${BLUE}=== User fix completed ===${NC}"
echo -e "${YELLOW}Try logging in with:${NC}"
echo -e "${YELLOW}Email: ${TEST_EMAIL}${NC}"
echo -e "${YELLOW}Password: ${TEST_PASSWORD}${NC}"