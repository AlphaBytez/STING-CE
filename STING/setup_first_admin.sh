#!/bin/bash
#
# STING Admin Setup Script
# This script sets up the first admin user for STING
#
# Usage: ./setup_first_admin.sh
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${BLUE}🐝 STING Admin Setup${NC}"
echo "=================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if services are running
echo -e "${YELLOW}Checking STING services...${NC}"
if ! curl -s -k https://localhost:4434/admin/health/ready > /dev/null 2>&1; then
    echo -e "${RED}❌ Kratos service is not running${NC}"
    echo -e "${YELLOW}Please start STING services first with: ./manage_sting.sh start${NC}"
    exit 1
fi

# Run the Python setup script
echo -e "${GREEN}Setting up admin user...${NC}"
python3 "${SCRIPT_DIR}/scripts/setup_admin_password.py"

exit $?