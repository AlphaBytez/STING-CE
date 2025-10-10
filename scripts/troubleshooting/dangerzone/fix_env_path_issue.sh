#!/bin/bash
# Script to fix environment path inconsistencies in STING
# This script addresses issues with mismatched environment file paths in docker-compose.yml

set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

INSTALL_DIR=$(pwd)
ENV_DIR="${INSTALL_DIR}/env"
CONF_ENV_DIR="${INSTALL_DIR}/conf/env"

echo -e "${BLUE}=== STING Environment Path Fix ===${NC}"

# Step 1: Check for environment directories
echo -e "\n${BLUE}=== Step 1: Checking for environment directories ===${NC}"
mkdir -p "${ENV_DIR}"
mkdir -p "${CONF_ENV_DIR}"

if [ -d "${ENV_DIR}" ]; then
  echo -e "${GREEN}✓ Environment directory exists: ${ENV_DIR}${NC}"
else
  echo -e "${RED}✗ Could not create environment directory: ${ENV_DIR}${NC}"
  exit 1
fi

if [ -d "${CONF_ENV_DIR}" ]; then
  echo -e "${GREEN}✓ Config environment directory exists: ${CONF_ENV_DIR}${NC}"
else
  echo -e "${RED}✗ Could not create config environment directory: ${CONF_ENV_DIR}${NC}"
  exit 1
fi

# Step 2: Copy LLM model env files to both locations for redundancy
echo -e "\n${BLUE}=== Step 2: Syncing environment files between env/ and conf/env/ ===${NC}"

# First, list all env files in the env directory
ENV_FILES=($(ls -1 ${ENV_DIR}/*.env 2>/dev/null))
CONF_ENV_FILES=($(ls -1 ${CONF_ENV_DIR}/*.env 2>/dev/null))

# Copy env files to conf/env
echo -e "${YELLOW}Copying env files from ${ENV_DIR} to ${CONF_ENV_DIR}${NC}"
for file in "${ENV_FILES[@]}"; do
  filename=$(basename "$file")
  
  # Check if we need to copy core files (only copy LLM files to avoid conflicts)
  if [[ "$filename" == llama3.env || "$filename" == phi3.env || "$filename" == zephyr.env || "$filename" == llm-gateway.env ]]; then
    cp -v "$file" "${CONF_ENV_DIR}/"
    chmod 600 "${CONF_ENV_DIR}/$filename"
    echo -e "${GREEN}✓ Copied $filename to ${CONF_ENV_DIR}${NC}"
  fi
done

# Copy conf/env files to env
echo -e "${YELLOW}Copying env files from ${CONF_ENV_DIR} to ${ENV_DIR}${NC}"
for file in "${CONF_ENV_FILES[@]}"; do
  filename=$(basename "$file")
  cp -v "$file" "${ENV_DIR}/"
  chmod 600 "${ENV_DIR}/$filename"
  echo -e "${GREEN}✓ Copied $filename to ${ENV_DIR}${NC}"
done

# Step 3: Fix the db.env file to ensure it has POSTGRESQL_ prefix variables
echo -e "\n${BLUE}=== Step 3: Ensuring DB environment file has consistent variable names ===${NC}"
DB_ENV_FILE="${ENV_DIR}/db.env"

if [ -f "$DB_ENV_FILE" ]; then
  echo -e "${YELLOW}Checking DB environment file: $DB_ENV_FILE${NC}"
  
  # Check if we need to add POSTGRESQL_ prefixed variables
  if ! grep -q "POSTGRESQL_PASSWORD" "$DB_ENV_FILE"; then
    echo -e "${YELLOW}Adding POSTGRESQL_ prefixed variables to db.env${NC}"
    # Append variables if they don't exist
    PG_PASSWORD=$(grep "POSTGRES_PASSWORD" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    PG_USER=$(grep "POSTGRES_USER" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    PG_DB=$(grep "POSTGRES_DB" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    PG_HOST=$(grep "POSTGRES_HOST" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    PG_PORT=$(grep "POSTGRES_PORT" "$DB_ENV_FILE" | cut -d'=' -f2- | tr -d "\"' ")
    
    # Add the variables
    echo "POSTGRESQL_PASSWORD=$PG_PASSWORD" >> "$DB_ENV_FILE"
    echo "POSTGRESQL_USER=$PG_USER" >> "$DB_ENV_FILE"
    echo "POSTGRESQL_DATABASE_NAME=$PG_DB" >> "$DB_ENV_FILE"
    echo "POSTGRESQL_HOST=$PG_HOST" >> "$DB_ENV_FILE"
    echo "POSTGRESQL_PORT=$PG_PORT" >> "$DB_ENV_FILE"
    
    echo -e "${GREEN}✓ Added POSTGRESQL_ prefixed variables to db.env${NC}"
  else
    echo -e "${GREEN}✓ POSTGRESQL_ prefixed variables already exist in db.env${NC}"
  fi
else
  echo -e "${RED}✗ db.env file not found${NC}"
  exit 1
fi

# Step 4: Create a backup of docker-compose.yml
echo -e "\n${BLUE}=== Step 4: Creating backup of docker-compose.yml ===${NC}"
DOCKER_COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE_BACKUP="docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)"

if [ -f "$DOCKER_COMPOSE_FILE" ]; then
  cp "$DOCKER_COMPOSE_FILE" "$DOCKER_COMPOSE_BACKUP"
  echo -e "${GREEN}✓ Created backup: $DOCKER_COMPOSE_BACKUP${NC}"
else
  echo -e "${RED}✗ docker-compose.yml not found${NC}"
  exit 1
fi

# Step 5: Fix Docker Compose file to ensure consistent environment paths
echo -e "\n${BLUE}=== Step 5: Updating docker-compose.yml to ensure consistent environment paths ===${NC}"

# Modify LLM service paths to use env/ instead of conf/env/
sed -i '' -e 's|${INSTALL_DIR}/conf/env/llm-gateway.env|${INSTALL_DIR}/env/llm-gateway.env|g' "$DOCKER_COMPOSE_FILE"
sed -i '' -e 's|${INSTALL_DIR}/conf/env/llama3.env|${INSTALL_DIR}/env/llama3.env|g' "$DOCKER_COMPOSE_FILE"
sed -i '' -e 's|${INSTALL_DIR}/conf/env/phi3.env|${INSTALL_DIR}/env/phi3.env|g' "$DOCKER_COMPOSE_FILE"
sed -i '' -e 's|${INSTALL_DIR}/conf/env/zephyr.env|${INSTALL_DIR}/env/zephyr.env|g' "$DOCKER_COMPOSE_FILE"

echo -e "${GREEN}✓ Updated environment file paths in docker-compose.yml${NC}"

# Step 6: Fix POSTGRES_PASSWORD in the db service
echo -e "\n${BLUE}=== Step 6: Ensuring PostgreSQL password is properly set ===${NC}"

# Check if the POSTGRES_PASSWORD environment variable is correctly set in the db service
if grep -q "POSTGRES_PASSWORD: \${POSTGRESQL_PASSWORD}" "$DOCKER_COMPOSE_FILE"; then
  echo -e "${GREEN}✓ POSTGRES_PASSWORD is correctly set in docker-compose.yml${NC}"
else
  # Update the db service to use the password from the db.env file
  PG_PASSWORD=$(grep "POSTGRES_PASSWORD" "$DB_ENV_FILE" | cut -d'=' -f2-)
  # This sed is more complex to target just the db service section
  sed -i '' -e '/^  db:/,/^  [a-z]/ s/POSTGRES_PASSWORD:.*/POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}/g' "$DOCKER_COMPOSE_FILE"
  echo -e "${GREEN}✓ Fixed POSTGRES_PASSWORD in docker-compose.yml${NC}"
fi

# Step 7: Stop and clean Docker
echo -e "\n${BLUE}=== Step 7: Cleaning Docker environment ===${NC}"
./manage_sting.sh stop || true

# Remove any stale containers
echo -e "${YELLOW}Removing any stale containers${NC}"
docker rm -f $(docker ps -a -q --filter "name=sting-ce" 2>/dev/null) 2>/dev/null || true
echo -e "${GREEN}✓ Docker environment cleaned${NC}"

echo -e "\n${GREEN}=== Environment path fix completed ===${NC}"
echo -e "${YELLOW}To start the installation, run:${NC}"
echo -e "  ./manage_sting.sh install"
echo -e "${YELLOW}If problems persist, you may need to run:${NC}"
echo -e "  docker-compose down -v"
echo -e "  docker system prune -f"
echo -e "  ./manage_sting.sh install"