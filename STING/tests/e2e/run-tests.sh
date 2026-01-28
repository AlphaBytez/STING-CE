#!/bin/bash
# run-tests.sh - Quick test runner for STING E2E tests

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   STING E2E Test Runner                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
STING_URL="${STING_URL:-https://CONFIGURE_YOUR_DOMAIN.local:8443}"
MAILPIT_URL="${MAILPIT_URL:-http://10.0.0.158:8025}"
TEST_EMAIL="${TEST_EMAIL:-admin@sting.local}"

echo -e "${BLUE}Configuration:${NC}"
echo "  STING URL:    $STING_URL"
echo "  Mailpit URL:  $MAILPIT_URL"
echo "  Test Email:   $TEST_EMAIL"
echo ""

# Check if node is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "   Please install Node.js from https://nodejs.org/"
    exit 1
fi

echo -e "${GREEN}✅ Node.js found: $(node --version)${NC}"

# Check if npm packages are installed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  Dependencies not installed${NC}"
    echo -e "${BLUE}Installing dependencies...${NC}"
    npm install
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

# Check if Playwright browsers are installed
if ! npx playwright --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Playwright not found${NC}"
    echo -e "${BLUE}Installing Playwright...${NC}"
    npm install -D @playwright/test
fi

# Install chromium browser if needed
echo -e "${BLUE}Checking Playwright browsers...${NC}"
npx playwright install chromium --with-deps
echo -e "${GREEN}✅ Playwright browsers ready${NC}"
echo ""

# Pre-flight checks
echo -e "${BLUE}Running pre-flight checks...${NC}"

# Check STING is accessible
echo -e "${BLUE}  → Checking STING accessibility...${NC}"
if curl -k -s -o /dev/null -w "%{http_code}" "$STING_URL/login" | grep -q "200\|302\|401"; then
    echo -e "${GREEN}    ✅ STING is accessible${NC}"
else
    echo -e "${RED}    ❌ STING is not accessible at $STING_URL${NC}"
    echo -e "${YELLOW}    Please start STING services first:${NC}"
    echo "      cd /opt/sting-ce"
    echo "      ./manage_sting.sh start"
    exit 1
fi

# Check Mailpit is accessible
echo -e "${BLUE}  → Checking Mailpit accessibility...${NC}"
if curl -s -o /dev/null -w "%{http_code}" "$MAILPIT_URL/api/v1/messages" | grep -q "200"; then
    echo -e "${GREEN}    ✅ Mailpit is accessible${NC}"
else
    echo -e "${RED}    ❌ Mailpit is not accessible at $MAILPIT_URL${NC}"
    echo -e "${YELLOW}    Please check Mailpit service and URL${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All pre-flight checks passed${NC}"
echo ""

# Parse command line arguments
TEST_MODE="${1:-normal}"

# Create test-results directory if it doesn't exist
mkdir -p test-results

case "$TEST_MODE" in
    "headed")
        echo -e "${BLUE}Running tests in HEADED mode (browser visible)...${NC}"
        npx playwright test --headed
        ;;
    "debug")
        echo -e "${BLUE}Running tests in DEBUG mode...${NC}"
        npx playwright test --debug
        ;;
    "ui")
        echo -e "${BLUE}Starting Playwright UI mode...${NC}"
        npx playwright test --ui
        ;;
    "specific")
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please specify a test name${NC}"
            echo "   Usage: $0 specific <test-name>"
            exit 1
        fi
        echo -e "${BLUE}Running specific test: $2${NC}"
        npx playwright test -g "$2"
        ;;
    "report")
        echo -e "${BLUE}Generating test report...${NC}"
        npx playwright show-report
        ;;
    *)
        echo -e "${BLUE}Running tests in NORMAL mode (headless)...${NC}"
        npx playwright test
        ;;
esac

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ ALL TESTS PASSED                         ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}View detailed report:${NC}"
    echo "  npm run test:report"
    echo ""
    echo -e "${BLUE}Screenshots saved to:${NC}"
    echo "  $SCRIPT_DIR/test-results/"
else
    echo -e "${RED}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ❌ TESTS FAILED                             ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  1. Check screenshots in: test-results/"
    echo "  2. View HTML report: npm run test:report"
    echo "  3. Run in headed mode: $0 headed"
    echo "  4. Debug mode: $0 debug"
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo "  • Hostname mismatch: Update STING_URL environment variable"
    echo "  • Email not received: Check Mailpit at $MAILPIT_URL"
    echo "  • UI changed: Update selectors in login-flow.spec.js"
fi

exit $TEST_EXIT_CODE
