#!/bin/bash
# Quick fix for Kratos configuration issues

set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== STING Kratos Configuration Fix ===${NC}"

# Fix main.kratos.yml
echo -e "\n${BLUE}=== Fixing Kratos main configuration file ===${NC}"
MAIN_KRATOS_FILE="kratos/main.kratos.yml"
if [ -f "$MAIN_KRATOS_FILE" ]; then
  # Generate truly random secrets of exactly 32 characters
  COOKIE_SECRET=$(openssl rand -hex 16)
  CIPHER_SECRET=$(openssl rand -hex 16)
  
  # Update or add secrets section
  if grep -q "secrets:" "$MAIN_KRATOS_FILE"; then
    echo -e "${YELLOW}Updating secrets in $MAIN_KRATOS_FILE${NC}"
    # Use sed to replace the existing secrets section
    sed -i '' '/secrets:/,/cipher:/s/- .*/- '${COOKIE_SECRET}'/' "$MAIN_KRATOS_FILE"
    sed -i '' '/cipher:/,/session:/s/- .*/- '${CIPHER_SECRET}'/' "$MAIN_KRATOS_FILE"
  else
    echo -e "${YELLOW}Adding secrets section to $MAIN_KRATOS_FILE${NC}"
    # Insert secrets section before courier section
    sed -i '' '/courier:/i\
secrets:\
  cookie:\
    - '${COOKIE_SECRET}'\
  cipher:\
    - '${CIPHER_SECRET}'\
\
' "$MAIN_KRATOS_FILE"
  fi
  echo -e "${GREEN}✓ Fixed $MAIN_KRATOS_FILE${NC}"
else
  echo -e "${RED}✗ $MAIN_KRATOS_FILE not found${NC}"
fi

# Also fix kratos.yml if it exists
KRATOS_FILE="kratos/kratos.yml"
if [ -f "$KRATOS_FILE" ]; then
  echo -e "${YELLOW}Updating secrets in $KRATOS_FILE${NC}"
  if grep -q "secrets:" "$KRATOS_FILE"; then
    # Use sed to replace the existing secrets section
    sed -i '' '/secrets:/,/cipher:/s/- .*/- '${COOKIE_SECRET}'/' "$KRATOS_FILE"
    sed -i '' '/cipher:/,/session:/s/- .*/- '${CIPHER_SECRET}'/' "$KRATOS_FILE"
  else
    # Insert secrets section before courier section
    sed -i '' '/courier:/i\
secrets:\
  cookie:\
    - '${COOKIE_SECRET}'\
  cipher:\
    - '${CIPHER_SECRET}'\
\
' "$KRATOS_FILE"
  fi
  echo -e "${GREEN}✓ Fixed $KRATOS_FILE${NC}"
fi

# Ensure env directory exists
mkdir -p env

# Create db.env if it doesn't exist
if [ ! -f "env/db.env" ]; then
  echo -e "${YELLOW}Creating env/db.env${NC}"
  cat > "env/db.env" << EOL
POSTGRES_PASSWORD=postgres
POSTGRES_USER=postgres
POSTGRES_DB=sting_app
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_USER=postgres
POSTGRESQL_DATABASE_NAME=sting_app
POSTGRESQL_HOST=db
POSTGRESQL_PORT=5432
EOL
  chmod 600 "env/db.env"
  echo -e "${GREEN}✓ Created env/db.env${NC}"
fi

# Create kratos.env if it doesn't exist
if [ ! -f "env/kratos.env" ]; then
  echo -e "${YELLOW}Creating env/kratos.env${NC}"
  cat > "env/kratos.env" << EOL
DSN=postgresql://postgres:postgres@db:5432/sting_app?sslmode=disable
KRATOS_PUBLIC_URL=https://localhost:4433
KRATOS_ADMIN_URL=https://localhost:4434
FRONTEND_URL=https://localhost:3000
DEFAULT_RETURN_URL=https://localhost:3000
LOGIN_UI_URL=https://localhost:3000/login
REGISTRATION_UI_URL=https://localhost:3000/register
WEBAUTHN_ENABLED=true
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_DISPLAY_NAME=STING Authentication
WEBAUTHN_RP_ORIGIN=https://localhost:3000
PASSWORD_ENABLED=true
OIDC_ENABLED=false
EOL
  chmod 600 "env/kratos.env"
  echo -e "${GREEN}✓ Created env/kratos.env${NC}"
fi

# Fix the DSN in docker-compose.yml
DOCKER_COMPOSE_FILE="docker-compose.yml"
if [ -f "$DOCKER_COMPOSE_FILE" ]; then
  echo -e "${YELLOW}Updating DSN in $DOCKER_COMPOSE_FILE${NC}"
  # Use sed to ensure the DSN has a hardcoded postgres password
  sed -i '' 's/DSN=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/DSN=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"
  # Same for DATABASE_URL and SQLALCHEMY_DATABASE_URI
  sed -i '' 's/DATABASE_URL=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/DATABASE_URL=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"
  sed -i '' 's/SQLALCHEMY_DATABASE_URI=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/SQLALCHEMY_DATABASE_URI=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"
  echo -e "${GREEN}✓ Updated DSN in $DOCKER_COMPOSE_FILE${NC}"
fi

# Create identity schema if it doesn't exist in conf/kratos
mkdir -p conf/kratos
if [ ! -f "conf/kratos/identity.schema.json" ]; then
  echo -e "${YELLOW}Creating conf/kratos/identity.schema.json${NC}"
  cp "kratos/identity.schema.json" "conf/kratos/identity.schema.json" 2>/dev/null || cat > "conf/kratos/identity.schema.json" << EOL
{
  "$id": "https://schemas.ory.sh/presets/kratos/quickstart/email-password/identity.schema.json",
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Person",
  "type": "object",
  "properties": {
    "traits": {
      "type": "object",
      "properties": {
        "email": {
          "type": "string",
          "format": "email",
          "title": "E-Mail",
          "minLength": 3,
          "ory.sh/kratos": {
            "credentials": {
              "password": {
                "identifier": true
              }
            },
            "verification": {
              "via": "email"
            },
            "recovery": {
              "via": "email"
            }
          }
        },
        "name": {
          "type": "object",
          "properties": {
            "first": {
              "type": "string",
              "title": "First Name"
            },
            "last": {
              "type": "string",
              "title": "Last Name"
            }
          }
        }
      },
      "required": [
        "email"
      ],
      "additionalProperties": false
    }
  }
}
EOL
  echo -e "${GREEN}✓ Created conf/kratos/identity.schema.json${NC}"
fi

# Set up .env file for INSTALL_DIR
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}Creating .env with INSTALL_DIR${NC}"
  cat > ".env" << EOL
INSTALL_DIR=$(pwd)
POSTGRES_PASSWORD=postgres
POSTGRES_USER=postgres
POSTGRES_DB=sting_app
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_USER=postgres 
POSTGRESQL_DATABASE_NAME=sting_app
EOL
  chmod 600 ".env"
  echo -e "${GREEN}✓ Created .env file${NC}"
fi

# Ensure required Docker resources exist
echo -e "\n${BLUE}=== Checking Docker resources ===${NC}"
docker network create sting_local 2>/dev/null || true
docker volume create config_data 2>/dev/null || true
docker volume create postgres_data 2>/dev/null || true
docker volume create vault_data 2>/dev/null || true
docker volume create vault_file 2>/dev/null || true
docker volume create vault_logs 2>/dev/null || true
docker volume create sting_logs 2>/dev/null || true
docker volume create sting_certs 2>/dev/null || true
docker volume create llm_logs 2>/dev/null || true
echo -e "${GREEN}✓ Docker resources ready${NC}"

echo -e "\n${GREEN}=== Fix completed ===${NC}"
echo -e "${YELLOW}Now try installing or starting:${NC}"
echo -e "  ./manage_sting.sh install"
echo -e "  ./manage_sting.sh start"