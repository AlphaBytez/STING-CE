#!/bin/bash
set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== STING Kratos Configuration Fix Script ===${NC}"

# Step 1: Check current config
echo -e "${BLUE}=== Step 1: Checking Kratos configuration ===${NC}"
CONFIG_FILE="/Users/captain-wolf/Documents/GitHub/STING-CE/STING/kratos/kratos.yml"
cp "/Users/captain-wolf/Documents/GitHub/STING-CE/STING/kratos/main.kratos.yml" "$CONFIG_FILE"

# Step 2: Create a simpler identity schema
echo -e "${BLUE}=== Step 2: Creating simplified identity schema ===${NC}"
cat > "/Users/captain-wolf/Documents/GitHub/STING-CE/STING/kratos/identity.schema.json" << 'EOL'
{
  "$id": "https://example.com/schemas/identity.schema.json",
  "title": "Identity Schema",
  "type": "object",
  "properties": {
    "traits": {
      "type": "object",
      "properties": {
        "email": {
          "type": "string",
          "format": "email",
          "title": "Email",
          "description": "Your email address"
        }
      },
      "required": ["email"],
      "additionalProperties": false
    }
  }
}
EOL

echo -e "${GREEN}✓ Created simplified identity schema${NC}"

# Step 3: Create a standard Kratos config
echo -e "${BLUE}=== Step 3: Creating simplified Kratos config ===${NC}"
cat > "$CONFIG_FILE" << 'EOL'
version: v1.0.0

dsn: postgresql://postgres:password@db:5432/sting_app?sslmode=disable

log:
  level: debug

serve:
  public:
    base_url: https://localhost:4433
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key
    cors:
      enabled: true
      allowed_origins:
        - http://localhost:3000
        - https://localhost:3000
      allowed_methods:
        - GET
        - POST
        - OPTIONS
      allowed_headers:
        - "*" 
      allow_credentials: true

  admin:
    base_url: https://localhost:4434
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key

identity:
  default_schema_id: default
  schemas:
    - id: default
      url: file:///etc/config/kratos/identity.schema.json

selfservice:
  default_browser_return_url: https://localhost:3000
  
  flows:
    settings:
      ui_url: https://localhost:3000/settings
      
    login:
      ui_url: https://localhost:3000/login
      lifespan: 1h
      after:
        password:
          hooks:
            - hook: session
    
    registration:
      ui_url: https://localhost:3000/register
      lifespan: 1h
      after:
        password:
          hooks:
            - hook: session
  
  methods:
    password:
      enabled: true
      config:
        haveibeenpwned_enabled: false
        identifier_similarity_check_enabled: false
    
    webauthn:
      enabled: true
      config:
        rp:
          id: localhost
          display_name: STING Authentication
          origin: https://localhost:3000

secrets:
  cookie:
    - PLEASE-CHANGE-ME-I-AM-VERY-INSECURE
  cipher:
    - 32-LONG-SECRET-NOT-SECURE-AT-ALL

session:
  cookie:
    domain: localhost
  lifespan: 24h

courier:
  smtp:
    connection_uri: smtps://test:test@mailslurper:1025/?skip_ssl_verify=true
EOL

echo -e "${GREEN}✓ Created simplified Kratos config${NC}"

# Step 4: Create a test user
echo -e "${BLUE}=== Step 4: Creating a test user ===${NC}"
# Get database container name
DB_CONTAINER=$(docker ps | grep -E 'postgres|db' | head -1 | awk '{print $NF}')

TEST_EMAIL="test@example.com"
TEST_PASSWORD="password"

echo -e "${YELLOW}Creating user with email: ${TEST_EMAIL} and password: ${TEST_PASSWORD}${NC}"

# Create the user manually
if [[ ! -z "$DB_CONTAINER" ]]; then
  # First clean up any existing users with this email
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identity_credential_identifiers WHERE identifier = '$TEST_EMAIL';"
  docker exec $DB_CONTAINER psql -U postgres -d sting_app -c "DELETE FROM identities WHERE traits->>'email' = '$TEST_EMAIL' OR traits->'traits'->>'email' = '$TEST_EMAIL';"
  
  # Create new identity with proper traits format
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
      '{\"email\": \"${TEST_EMAIL}\"}',
      NOW(),
      NOW(),
      'active'
    ) RETURNING id;
  " | grep -v "INSERT" | sed 's/^[ \t]*//' | tr -d '\n')
  
  echo -e "${GREEN}✓ Created test user ID: ${USER_ID}${NC}"
  
  # Get password credential type
  PASSWORD_TYPE_ID=$(docker exec $DB_CONTAINER psql -U postgres -d sting_app -t -c "
    SELECT id FROM identity_credential_types WHERE name = 'password';
  " | sed 's/^[ \t]*//' | tr -d '\n')
  
  # Create credential for the user
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
  
  echo -e "${GREEN}✓ Created credential ID: ${CREDENTIAL_ID}${NC}"
  
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
  
  echo -e "${GREEN}✓ Created credential identifier ID: ${IDENTIFIER_ID}${NC}"
else
  echo -e "${RED}❌ No database container found${NC}"
fi

# Step 5: Restart services
echo -e "${BLUE}=== Step 5: Restarting services ===${NC}"
cd "/Users/captain-wolf/Documents/GitHub/STING-CE/STING"
./manage_sting.sh restart kratos
./manage_sting.sh restart frontend

echo -e "\n${GREEN}=== Configuration fix completed ===${NC}"
echo -e "${YELLOW}You can now try to log in with:${NC}"
echo -e "${YELLOW}Email: ${TEST_EMAIL}${NC}"
echo -e "${YELLOW}Password: ${TEST_PASSWORD}${NC}"
echo -e "${YELLOW}Visit: https://localhost:3000/login${NC}"