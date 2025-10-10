#!/bin/bash
# Script to update all ports in docker-compose.yml to avoid conflicts

set -e

# Create a backup
cp docker-compose.yml docker-compose.yml.original

# Update all ports
sed -i'.bak' \
    -e 's/8200:8200/8201:8200/g' \
    -e 's/8085:8080/8086:8080/g' \
    -e 's/5433:5432/5434:5432/g' \
    -e 's/1026:1025/1027:1025/g' \
    -e 's/4436:4436/4438:4436/g' \
    -e 's/4437:4437/4439:4437/g' \
    -e 's/4433:4433/4443:4433/g' \
    -e 's/4434:4434/4444:4434/g' \
    -e 's/\${FLASK_PORT:-5050}:5050/\${FLASK_PORT:-5051}:5050/g' \
    -e 's/REACT_APP_API_URL: "https:\/\/localhost:5050"/REACT_APP_API_URL: "https:\/\/localhost:5051"/g' \
    -e 's/REACT_APP_KRATOS_PUBLIC_URL: "https:\/\/localhost:4433"/REACT_APP_KRATOS_PUBLIC_URL: "https:\/\/localhost:4443"/g' \
    -e 's/test: \["CMD", "curl", "-f", "-k", "https:\/\/localhost:5050\/api\/auth\/health"\]/test: \["CMD", "curl", "-f", "-k", "https:\/\/localhost:5051\/api\/auth\/health"\]/g' \
    -e 's/\${REACT_PORT:-3001}:3000/\${REACT_PORT:-3002}:3000/g' \
    docker-compose.yml

echo "Updated all ports in docker-compose.yml to avoid conflicts."
echo "Original file saved as docker-compose.yml.original"