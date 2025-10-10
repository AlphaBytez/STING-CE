#!/bin/bash
# Fix for the database password issue in STING

set -e

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

INSTALL_DIR=$(pwd)
ENV_DIR="${INSTALL_DIR}/env"
DB_ENV_FILE="${ENV_DIR}/db.env"
DOCKER_COMPOSE_FILE="docker-compose.yml"

echo -e "${BLUE}=== STING Database Password Fix ===${NC}"

# Step 1: Stop all services
echo -e "\n${BLUE}=== Step 1: Stopping all services ===${NC}"
./manage_sting.sh stop || true
docker rm -f $(docker ps -a -q --filter "name=sting-ce" 2>/dev/null) 2>/dev/null || true
echo -e "${GREEN}✓ All services stopped${NC}"

# Step 2: Create backup of docker-compose.yml
echo -e "\n${BLUE}=== Step 2: Creating backup of docker-compose.yml ===${NC}"
cp "$DOCKER_COMPOSE_FILE" "${DOCKER_COMPOSE_FILE}.bak.$(date +%Y%m%d%H%M%S)"
echo -e "${GREEN}✓ Backup created${NC}"

# Step 3: Check and fix db.env file
echo -e "\n${BLUE}=== Step 3: Checking and fixing db.env file ===${NC}"
if [ ! -f "$DB_ENV_FILE" ]; then
  echo -e "${YELLOW}Creating db.env file with default settings${NC}"
  mkdir -p "$ENV_DIR"
  cat > "$DB_ENV_FILE" << EOL
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
  chmod 600 "$DB_ENV_FILE"
  echo -e "${GREEN}✓ Created db.env with default settings${NC}"
else
  echo -e "${GREEN}✓ db.env file exists${NC}"
  
  # Check for password and fix if missing or empty
  if ! grep -q "POSTGRES_PASSWORD=" "$DB_ENV_FILE" || grep -q "POSTGRES_PASSWORD=$" "$DB_ENV_FILE"; then
    echo -e "${YELLOW}Adding or fixing POSTGRES_PASSWORD in db.env${NC}"
    if grep -q "POSTGRES_PASSWORD=" "$DB_ENV_FILE"; then
      sed -i '' 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=postgres/' "$DB_ENV_FILE"
    else
      echo "POSTGRES_PASSWORD=postgres" >> "$DB_ENV_FILE"
    fi
  fi
  
  # Check for POSTGRESQL_PASSWORD
  if ! grep -q "POSTGRESQL_PASSWORD=" "$DB_ENV_FILE" || grep -q "POSTGRESQL_PASSWORD=$" "$DB_ENV_FILE"; then
    echo -e "${YELLOW}Adding or fixing POSTGRESQL_PASSWORD in db.env${NC}"
    if grep -q "POSTGRESQL_PASSWORD=" "$DB_ENV_FILE"; then
      sed -i '' 's/POSTGRESQL_PASSWORD=.*/POSTGRESQL_PASSWORD=postgres/' "$DB_ENV_FILE"
    else
      echo "POSTGRESQL_PASSWORD=postgres" >> "$DB_ENV_FILE"
    fi
  fi
  
  # Ensure other PostgreSQL variables exist
  if ! grep -q "POSTGRESQL_USER=" "$DB_ENV_FILE"; then
    echo "POSTGRESQL_USER=postgres" >> "$DB_ENV_FILE"
  fi
  
  if ! grep -q "POSTGRESQL_DATABASE_NAME=" "$DB_ENV_FILE"; then
    echo "POSTGRESQL_DATABASE_NAME=sting_app" >> "$DB_ENV_FILE"
  fi
  
  if ! grep -q "POSTGRESQL_HOST=" "$DB_ENV_FILE"; then
    echo "POSTGRESQL_HOST=db" >> "$DB_ENV_FILE"
  fi
  
  if ! grep -q "POSTGRESQL_PORT=" "$DB_ENV_FILE"; then
    echo "POSTGRESQL_PORT=5432" >> "$DB_ENV_FILE"
  fi
  
  echo -e "${GREEN}✓ Updated db.env with required variables${NC}"
fi

# Step 4: Fix docker-compose.yml to use direct password value
echo -e "\n${BLUE}=== Step 4: Updating docker-compose.yml ===${NC}"

# Use sed to modify the docker-compose.yml file
# Update the db service to use direct password instead of variable
sed -i '' '/^  db:/,/networks:/s/POSTGRES_PASSWORD: \${POSTGRESQL_PASSWORD}/POSTGRES_PASSWORD: "postgres"/' "$DOCKER_COMPOSE_FILE"

# Update the kratos service to use direct password in DSN
sed -i '' '/^  kratos:/,/volumes:/s/DSN=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/DSN=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"

# Update the app service to use direct password
sed -i '' '/^  app:/,/volumes:/s/DATABASE_URL=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/DATABASE_URL=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"
sed -i '' '/^  app:/,/volumes:/s/SQLALCHEMY_DATABASE_URI=postgresql:\/\/postgres:\${POSTGRESQL_PASSWORD}@db/SQLALCHEMY_DATABASE_URI=postgresql:\/\/postgres:postgres@db/' "$DOCKER_COMPOSE_FILE"

echo -e "${GREEN}✓ Updated docker-compose.yml to use direct password${NC}"

# Step 5: Make sure directories and volumes exist
echo -e "\n${BLUE}=== Step 5: Ensuring directories and volumes exist ===${NC}"

# Create needed directories
mkdir -p "$ENV_DIR"
mkdir -p "${INSTALL_DIR}/conf/env"
mkdir -p "${INSTALL_DIR}/conf/kratos"

# Make sure Docker network exists
docker network create sting_local 2>/dev/null || true

# Make sure volumes exist
docker volume create config_data 2>/dev/null || true
docker volume create postgres_data 2>/dev/null || true
docker volume create vault_data 2>/dev/null || true
docker volume create vault_file 2>/dev/null || true
docker volume create vault_logs 2>/dev/null || true
docker volume create supertokens_logs 2>/dev/null || true
docker volume create sting_logs 2>/dev/null || true
docker volume create sting_certs 2>/dev/null || true
docker volume create llm_logs 2>/dev/null || true

echo -e "${GREEN}✓ All required directories and volumes exist${NC}"

# Step 6: Test the database directly
echo -e "\n${BLUE}=== Step 6: Testing database initialization ===${NC}"

# Create a minimal docker-compose file for testing database
cat > docker-compose-db-test.yml << EOL
services:
  db-test:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: sting_app
      POSTGRES_HOST_AUTH_METHOD: md5
    ports:
      - 5432:5432
    networks:
      - sting_local
    healthcheck:
      test: ["CMD", "pg_isready"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

networks:
  sting_local:
    external: true
EOL

# Run the test database
echo -e "${YELLOW}Starting test database container...${NC}"
docker-compose -f docker-compose-db-test.yml up -d

# Check if it's running
sleep 10
if docker ps | grep -q "db-test"; then
  echo -e "${GREEN}✓ Test database running successfully${NC}"
  docker-compose -f docker-compose-db-test.yml down
else
  echo -e "${RED}✗ Test database failed to start${NC}"
  docker-compose -f docker-compose-db-test.yml logs
  docker-compose -f docker-compose-db-test.yml down
  exit 1
fi

# Step 7: Create .env file with environment variables
echo -e "\n${BLUE}=== Step 7: Creating .env file for Docker Compose ===${NC}"
cat > .env << EOL
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
INSTALL_DIR=$(pwd)
EOL
chmod 600 .env
echo -e "${GREEN}✓ Created .env file${NC}"

echo -e "\n${GREEN}=== Database password fix completed ===${NC}"
echo -e "${YELLOW}Now try running:${NC}"
echo -e "  ./manage_sting.sh start"
echo -e "\n${YELLOW}If you still encounter issues, you can try:${NC}"
echo -e "  docker system prune -f"
echo -e "  docker volume rm postgres_data"
echo -e "  ./manage_sting.sh start"