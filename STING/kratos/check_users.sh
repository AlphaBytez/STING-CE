#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Checking Kratos Database for Users ===${NC}"

# Get database container name
DB_CONTAINER=$(docker ps | grep -E 'postgres|db' | head -1 | awk '{print $NF}')

if [[ -z "$DB_CONTAINER" ]]; then
  echo -e "${RED}❌ No database container found${NC}"
  echo -e "${YELLOW}Is the database running? Check with 'docker ps'${NC}"
  exit 1
else
  echo -e "${GREEN}✓ Found database container: ${DB_CONTAINER}${NC}"
fi

# Check if sting_app database exists
echo -e "\n${BLUE}=== Checking for 'sting_app' database ===${NC}"
DB_EXISTS=$(docker exec $DB_CONTAINER psql -U postgres -lqt | grep -w sting_app | wc -l)

if [[ "$DB_EXISTS" == "0" ]]; then
  echo -e "${RED}❌ Database 'sting_app' not found${NC}"
  echo -e "${YELLOW}Available databases:${NC}"
  docker exec $DB_CONTAINER psql -U postgres -c '\l' | grep -v "rows\)"
  exit 1
else
  echo -e "${GREEN}✓ Database 'sting_app' exists${NC}"
fi

# Check for identities table 
echo -e "\n${BLUE}=== Checking for Kratos tables in 'sting_app' ===${NC}"
TABLES=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -c '\dt' | grep -E 'identities|identity_credentials')

if [[ -z "$TABLES" ]]; then
  echo -e "${RED}❌ Kratos tables not found${NC}"
  echo -e "${YELLOW}Available tables in sting_app:${NC}"
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -c '\dt'
  exit 1
else
  echo -e "${GREEN}✓ Kratos tables found:${NC}"
  echo "$TABLES"
fi

# Count identities
echo -e "\n${BLUE}=== Checking for registered identities ===${NC}"
IDENTITY_COUNT=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c 'SELECT COUNT(*) FROM identities;' | tr -d ' ')

echo -e "${YELLOW}Found ${IDENTITY_COUNT} identity/identities${NC}"

# List identities with their details
if [[ "$IDENTITY_COUNT" != "0" ]]; then
  echo -e "\n${BLUE}=== Registered Identities ===${NC}"
  IDENTITIES=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "SELECT id, traits->'traits'->>'email' as email, created_at FROM identities;")
  
  echo -e "${YELLOW}ID | Email | Created At${NC}"
  echo "$IDENTITIES" | sed 's/^[ \t]*//' | while read -r line; do
    echo -e "${GREEN}$line${NC}"
  done
fi

# Optionally create a test identity via SQL if requested
if [[ "$1" == "--create" ]]; then
  echo -e "\n${BLUE}=== Creating a test identity directly in the database ===${NC}"
  TIMESTAMP=$(date +%s)
  TEST_EMAIL="test_sql_${TIMESTAMP}@example.com"
  
  # Create identity JSON
  IDENTITY_JSON=$(cat <<EOF
{"traits":{"email":"${TEST_EMAIL}"}}
EOF
)
  
  # View the identity JSON for debugging
  echo -e "${YELLOW}Using identity JSON: ${IDENTITY_JSON}${NC}"
  
  # Create identity directly in the database with all required fields
  INSERT_RESULT=$(docker exec -i $DB_CONTAINER psql -U postgres -d sting_app -t -c "
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
      '${IDENTITY_JSON}'::jsonb,
      NOW(),
      NOW(),
      'active'
    ) RETURNING id;")
  
  if [[ ! -z "$INSERT_RESULT" ]]; then
    IDENTITY_ID=$(echo "$INSERT_RESULT" | tr -d ' \n')
    echo -e "${GREEN}✓ Created new identity with ID: ${IDENTITY_ID}${NC}"
    echo -e "${GREEN}✓ Email: ${TEST_EMAIL}${NC}"
  else
    echo -e "${RED}❌ Failed to create identity${NC}"
  fi
fi

echo -e "\n${BLUE}=== Check completed ===${NC}"