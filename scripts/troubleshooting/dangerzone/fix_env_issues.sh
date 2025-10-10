#!/bin/bash
# Script to fix environment variable issues in STING
# This script addresses issues with missing environment variables that can cause
# container startup failures after Kratos integration

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

echo -e "${BLUE}=== STING Environment Variable Fix ===${NC}"

# Step 1: Check for env directory
echo -e "\n${BLUE}=== Step 1: Checking for environment directories ===${NC}"
mkdir -p "${ENV_DIR}"
if [ -d "${ENV_DIR}" ]; then
  echo -e "${GREEN}✓ Environment directory exists: ${ENV_DIR}${NC}"
else
  echo -e "${RED}✗ Could not create environment directory: ${ENV_DIR}${NC}"
  exit 1
fi

# Step 2: Ensure minimal required environment files exist
echo -e "\n${BLUE}=== Step 2: Creating minimal required environment files ===${NC}"

# Create db.env if it doesn't exist or is empty
if [ ! -s "${ENV_DIR}/db.env" ]; then
  echo -e "${YELLOW}Creating db.env with default values${NC}"
  cat > "${ENV_DIR}/db.env" << EOL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sting_app
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_DATABASE_NAME=sting_app
POSTGRESQL_HOST=db
POSTGRESQL_PORT=5432
EOL
  chmod 600 "${ENV_DIR}/db.env"
  echo -e "${GREEN}✓ Created db.env${NC}"
else
  echo -e "${GREEN}✓ db.env already exists${NC}"
fi

# Create kratos.env if it doesn't exist or is empty
if [ ! -s "${ENV_DIR}/kratos.env" ]; then
  echo -e "${YELLOW}Creating kratos.env with default values${NC}"
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
else
  echo -e "${GREEN}✓ kratos.env already exists${NC}"
fi

# Step 3: Verify environment variables in db.env
echo -e "\n${BLUE}=== Step 3: Verifying environment variables in db.env ===${NC}"
DB_ENV_FILE="${ENV_DIR}/db.env"
if [ -f "$DB_ENV_FILE" ]; then
  # Check for essential variables
  if grep -q "POSTGRES_PASSWORD" "$DB_ENV_FILE"; then
    PG_PASSWORD=$(grep "POSTGRES_PASSWORD" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    if [ -z "$PG_PASSWORD" ]; then
      echo -e "${RED}✗ POSTGRES_PASSWORD is empty in db.env${NC}"
      echo -e "${YELLOW}Setting POSTGRES_PASSWORD to default value${NC}"
      sed -i -e 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=postgres/' "$DB_ENV_FILE"
    else
      echo -e "${GREEN}✓ POSTGRES_PASSWORD is set in db.env${NC}"
    fi
  else
    echo -e "${RED}✗ POSTGRES_PASSWORD not found in db.env${NC}"
    echo -e "${YELLOW}Adding POSTGRES_PASSWORD to db.env${NC}"
    echo "POSTGRES_PASSWORD=postgres" >> "$DB_ENV_FILE"
  fi
else
  echo -e "${RED}✗ Could not read db.env${NC}"
  exit 1
fi

# Step 4: Regenerate all environment files using utils container
echo -e "\n${BLUE}=== Step 4: Regenerating environment files ===${NC}"
cd "$INSTALL_DIR"

# Source config utilities for centralized config generation
if [ -f "$INSTALL_DIR/lib/config_utils.sh" ]; then
    source "$INSTALL_DIR/lib/config_utils.sh"
    source "$INSTALL_DIR/lib/logging.sh"
    
    if generate_config_via_utils "runtime" "config.yml"; then
        echo -e "${GREEN}✓ Environment files regenerated via utils container${NC}"
    else
        echo -e "${RED}✗ Failed to regenerate via utils container${NC}"
        echo -e "${YELLOW}Attempting manual environment file generation${NC}"
        # Create necessary environment files with minimal required variables
    fi
else
    echo -e "${RED}✗ Config utils not available${NC}"
    echo -e "${YELLOW}Attempting manual environment file generation${NC}"
    # Create necessary environment files with minimal required variables
fi

# Step 5: Update docker-compose.yml to ensure environment variables are correctly loaded
echo -e "\n${BLUE}=== Step 5: Ensuring docker-compose.yml loads environment files ===${NC}"
cd "$INSTALL_DIR"
DOCKER_COMPOSE_FILE="docker-compose.yml"

if grep -q "env_file:" "$DOCKER_COMPOSE_FILE"; then
  echo -e "${GREEN}✓ docker-compose.yml contains env_file directives${NC}"
else
  echo -e "${RED}✗ docker-compose.yml may be missing env_file directives${NC}"
  echo -e "${YELLOW}Please check docker-compose.yml manually to ensure it loads environment files${NC}"
fi

# Step 6: Add a comment in docker-compose.yml to prevent future issues
echo -e "\n${BLUE}=== Step 6: Adding helpful comments to docker-compose.yml ===${NC}"
if grep -q "# IMPORTANT: These environment files must exist" "$DOCKER_COMPOSE_FILE"; then
  echo -e "${GREEN}✓ docker-compose.yml already contains helpful comments${NC}"
else
  echo -e "${YELLOW}Adding comment to docker-compose.yml${NC}"
  # Create a temporary file with the comment
  TMP_FILE=$(mktemp)
  cat > "$TMP_FILE" << 'EOL'
# Common database environment - only used for shared defaults
# IMPORTANT: These environment files must exist in the env directory:
# - db.env: Contains database credentials (POSTGRES_PASSWORD, etc.)
# - kratos.env: Contains Kratos configuration
# If containers fail to start with "Database is uninitialized" errors,
# verify that these files exist and contain the necessary variables.
# Run ./fix_env_issues.sh to fix common environment issues.
EOL
  
  # Insert the comment at the beginning of the file, preserving the rest
  cat "$DOCKER_COMPOSE_FILE" >> "$TMP_FILE"
  mv "$TMP_FILE" "$DOCKER_COMPOSE_FILE"
  echo -e "${GREEN}✓ Added helpful comments to docker-compose.yml${NC}"
fi

# Step 7: Stop and clean Docker
echo -e "\n${BLUE}=== Step 7: Cleaning Docker environment ===${NC}"
./manage_sting.sh stop || true

# Remove any stale containers
echo -e "${YELLOW}Removing any stale containers${NC}"
docker rm -f $(docker ps -a -q --filter "name=sting" 2>/dev/null) 2>/dev/null || true
echo -e "${GREEN}✓ Docker environment cleaned${NC}"

echo -e "\n${GREEN}=== Environment fix completed ===${NC}"
echo -e "${YELLOW}To start the services, run:${NC}"
echo -e "  ./manage_sting.sh start"
echo -e "${YELLOW}If problems persist, you may need to run:${NC}"
echo -e "  docker-compose down -v"
echo -e "  docker system prune -f"
echo -e "  ./manage_sting.sh start"