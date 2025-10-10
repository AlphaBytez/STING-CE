#!/bin/bash
# Script to fix installation issues in STING
# This script addresses the configuration path problems and ensures consistent
# environment files that are causing the install command to fail

set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

INSTALL_DIR=$(pwd)
ENV_DIR="${INSTALL_DIR}/env"
CONF_DIR="${INSTALL_DIR}/conf"
CONF_ENV_DIR="${CONF_DIR}/env"

echo -e "${BLUE}=== STING Installation Fix ===${NC}"

# Step 1: Clean up containers
echo -e "\n${BLUE}=== Step 1: Cleaning up any running containers ===${NC}"
docker rm -f $(docker ps -a -q --filter "name=sting-ce" 2>/dev/null) 2>/dev/null || true
docker rm -f $(docker ps -a -q --filter "name=sting_" 2>/dev/null) 2>/dev/null || true
echo -e "${GREEN}✓ Container cleanup done${NC}"

# Step 2: Ensure directories exist
echo -e "\n${BLUE}=== Step 2: Creating directory structure ===${NC}"
mkdir -p "${ENV_DIR}"
mkdir -p "${CONF_ENV_DIR}"
mkdir -p "${CONF_DIR}/kratos"
mkdir -p "${INSTALL_DIR}/certs"

# Step 3: Fix database environment file
echo -e "\n${BLUE}=== Step 3: Creating consistent database configuration ===${NC}"
cat > "${ENV_DIR}/db.env" << EOL
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
chmod 600 "${ENV_DIR}/db.env"
echo -e "${GREEN}✓ Created db.env${NC}"

# Step 4: Create Kratos environment file
echo -e "\n${BLUE}=== Step 4: Creating Kratos configuration ===${NC}"
cat > "${ENV_DIR}/kratos.env" << EOL
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
chmod 600 "${ENV_DIR}/kratos.env"
echo -e "${GREEN}✓ Created kratos.env${NC}"

# Step 5: Create minimal Kratos schema
echo -e "\n${BLUE}=== Step 5: Creating Kratos identity schema ===${NC}"
cat > "${CONF_DIR}/kratos/identity.schema.json" << EOL
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
              },
              "webauthn": {
                "identifier": true
              }
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
echo -e "${GREEN}✓ Created identity schema${NC}"

# Step 6: Fix LLM environment files
echo -e "\n${BLUE}=== Step 6: Creating LLM environment files ===${NC}"
for model in llama3 phi3 zephyr; do
  cat > "${ENV_DIR}/${model}.env" << EOL
MODEL_NAME=${model}
MODEL_PATH=/app/models/${model}
DEFAULT_MAX_TOKENS=1024
DEFAULT_TEMPERATURE=0.7
HF_TOKEN=${HF_TOKEN:-}
EOL
  chmod 600 "${ENV_DIR}/${model}.env"
  cp "${ENV_DIR}/${model}.env" "${CONF_ENV_DIR}/${model}.env"
  echo -e "${GREEN}✓ Created ${model}.env${NC}"
done

cat > "${ENV_DIR}/llm-gateway.env" << EOL
PORT=8080
LOG_LEVEL=INFO
DEFAULT_MODEL=llama3
HF_TOKEN=${HF_TOKEN:-}
EOL
chmod 600 "${ENV_DIR}/llm-gateway.env"
cp "${ENV_DIR}/llm-gateway.env" "${CONF_ENV_DIR}/llm-gateway.env"
echo -e "${GREEN}✓ Created llm-gateway.env${NC}"

# Step 7: Create app.env file
echo -e "\n${BLUE}=== Step 7: Creating app environment file ===${NC}"
cat > "${ENV_DIR}/app.env" << EOL
FLASK_APP=app.run:app
FLASK_DEBUG=True
DATABASE_URL=postgresql://postgres:postgres@db:5432/sting_app?sslmode=disable
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@db:5432/sting_app?sslmode=disable
SECRET_KEY=dev-secret-key-change-in-production
ST_API_KEY=test-api-key
SUPERTOKENS_URL=http://supertokens:3567
EOL
chmod 600 "${ENV_DIR}/app.env"
echo -e "${GREEN}✓ Created app.env${NC}"

# Step 8: Create frontend.env file
echo -e "\n${BLUE}=== Step 8: Creating frontend environment file ===${NC}"
cat > "${ENV_DIR}/frontend.env" << EOL
REACT_APP_API_URL=https://localhost:5050
REACT_APP_SUPERTOKENS_URL=http://localhost:3567
REACT_APP_KRATOS_PUBLIC_URL=https://localhost:4433
EOL
chmod 600 "${ENV_DIR}/frontend.env"
echo -e "${GREEN}✓ Created frontend.env${NC}"

# Step 9: Create self-signed certificates if they don't exist
echo -e "\n${BLUE}=== Step 9: Creating SSL certificates if needed ===${NC}"
if [ ! -f "${INSTALL_DIR}/certs/server.key" ] || [ ! -f "${INSTALL_DIR}/certs/server.crt" ]; then
  echo -e "${YELLOW}Creating self-signed certificates...${NC}"
  openssl req -x509 -newkey rsa:4096 -keyout "${INSTALL_DIR}/certs/server.key" -out "${INSTALL_DIR}/certs/server.crt" -days 365 -nodes -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
  chmod 600 "${INSTALL_DIR}/certs/server.key"
  echo -e "${GREEN}✓ Created self-signed certificates${NC}"
else
  echo -e "${GREEN}✓ SSL certificates already exist${NC}"
fi

# Step 10: Create .env file with default values
echo -e "\n${BLUE}=== Step 10: Creating .env file with default values ===${NC}"
cat > "${INSTALL_DIR}/.env" << EOL
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
INSTALL_DIR=${INSTALL_DIR}
VAULT_TOKEN=dev-only-token
HF_TOKEN=${HF_TOKEN:-}
EOL
chmod 600 "${INSTALL_DIR}/.env"
echo -e "${GREEN}✓ Created .env file${NC}"

# Step 11: Make sure Docker network exists
echo -e "\n${BLUE}=== Step 11: Setting up Docker network ===${NC}"
docker network create sting_local 2>/dev/null || true
echo -e "${GREEN}✓ Docker network ready${NC}"

# Step 12: Create Docker volumes
echo -e "\n${BLUE}=== Step 12: Creating Docker volumes ===${NC}"
docker volume create config_data 2>/dev/null || true
docker volume create postgres_data 2>/dev/null || true
docker volume create vault_data 2>/dev/null || true
docker volume create vault_file 2>/dev/null || true
docker volume create vault_logs 2>/dev/null || true
docker volume create supertokens_logs 2>/dev/null || true
docker volume create sting_logs 2>/dev/null || true
docker volume create sting_certs 2>/dev/null || true
docker volume create llm_logs 2>/dev/null || true
echo -e "${GREEN}✓ Docker volumes ready${NC}"

echo -e "\n${GREEN}=== Fix completed successfully ===${NC}"
echo -e "${YELLOW}You can now try running:${NC}"
echo -e "  ./manage_sting.sh install"
echo ""
echo -e "${YELLOW}If you still have issues, try running:${NC}"
echo -e "  docker system prune -f"
echo -e "  docker volume prune -f"
echo -e "  ./manage_sting.sh install"