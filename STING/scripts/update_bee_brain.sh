#!/bin/bash
#
# Bee Brain Updater - Quick update script for STING Bee Brain
#
# Usage:
#   sudo ./update_bee_brain.sh
#
# Or via curl (1-liner):
#   curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE-Public/main/STING/scripts/update_bee_brain.sh | sudo bash
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# STING installation directory
INSTALL_DIR="${INSTALL_DIR:-/opt/sting-ce}"
EXTERNAL_AI_DIR="${INSTALL_DIR}/external_ai_service"
BEE_BRAINS_DIR="${EXTERNAL_AI_DIR}/bee_brains"
GENERATOR_SCRIPT="${EXTERNAL_AI_DIR}/bee_brain_generator.py"

echo -e "${BLUE}🐝 STING Bee Brain Updater${NC}"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo)${NC}"
    exit 1
fi

# Check if STING is installed
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: STING not found at $INSTALL_DIR${NC}"
    echo "Set INSTALL_DIR environment variable if installed elsewhere."
    exit 1
fi

# Read STING version
if [ -f "${INSTALL_DIR}/VERSION" ]; then
    STING_VERSION=$(cat "${INSTALL_DIR}/VERSION" | tr -d '[:space:]')
    echo -e "${GREEN}✓${NC} STING Version: ${STING_VERSION}"
else
    echo -e "${YELLOW}Warning: VERSION file not found, using 1.0.0${NC}"
    STING_VERSION="1.0.0"
fi

# Ensure bee_brains directory exists
mkdir -p "$BEE_BRAINS_DIR"

# Check if generator exists
if [ ! -f "$GENERATOR_SCRIPT" ]; then
    echo -e "${YELLOW}⚠ Bee Brain generator not found${NC}"
    echo "Downloading latest generator from GitHub..."

    REPO_URL="https://raw.githubusercontent.com/AlphaBytez/STING-CE-Public/main/STING/external_ai_service"

    # Download generator and manager
    curl -fsSL "${REPO_URL}/bee_brain_generator.py" -o "${GENERATOR_SCRIPT}"
    curl -fsSL "${REPO_URL}/bee_brain_manager.py" -o "${EXTERNAL_AI_DIR}/bee_brain_manager.py"

    echo -e "${GREEN}✓${NC} Downloaded bee_brain generator"
fi

# Check Python dependencies
echo ""
echo "Checking dependencies..."
if ! python3 -c "import packaging" 2>/dev/null; then
    echo -e "${YELLOW}Installing required Python packages...${NC}"
    pip3 install packaging -q
fi

echo -e "${GREEN}✓${NC} Dependencies OK"

# Generate/update bee_brain
echo ""
echo "Generating Bee Brain v${STING_VERSION}..."
echo ""

cd "$INSTALL_DIR"

if python3 "$GENERATOR_SCRIPT" --version "$STING_VERSION"; then
    echo ""
    echo -e "${GREEN}✓${NC} Bee Brain generated successfully"
else
    echo ""
    echo -e "${RED}✗ Bee Brain generation failed${NC}"
    exit 1
fi

# Reload external_ai service if running
echo ""
echo "Reloading Bee AI service..."

# Try API reload first
if curl -f -X POST http://localhost:5050/api/admin/bee-brain/reload -s > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Bee Brain reloaded via API"
elif command -v docker &> /dev/null; then
    # Fallback: restart external_ai container
    echo -e "${YELLOW}API not available, restarting container...${NC}"

    if docker ps --format '{{.Names}}' | grep -q 'external-ai\|external_ai'; then
        CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E 'external-ai|external_ai' | head -n1)
        docker restart "$CONTAINER_NAME" > /dev/null 2>&1
        echo -e "${GREEN}✓${NC} Bee AI container restarted"
    else
        echo -e "${YELLOW}⚠ External AI container not running${NC}"
        echo "Bee Brain will be loaded on next startup"
    fi
else
    echo -e "${YELLOW}⚠ Could not reload service automatically${NC}"
    echo "Please restart the external_ai service manually"
fi

# Show status
echo ""
echo -e "${GREEN}✅ Bee Brain Update Complete!${NC}"
echo ""
echo "📊 Status:"
ls -lh "${BEE_BRAINS_DIR}/bee_brain_v${STING_VERSION}.json" 2>/dev/null | awk '{print "   Size: " $5}'
echo "   Version: ${STING_VERSION}"
echo ""

# Show available versions
echo "📚 Available Bee Brain versions:"
ls -1 "${BEE_BRAINS_DIR}/" 2>/dev/null | grep "bee_brain_v.*\.json" | sed 's/bee_brain_v//g' | sed 's/.json//g' | awk '{print "   - " $0}' || echo "   None"

echo ""
echo -e "${BLUE}💡 Tip:${NC} Ask Bee AI to verify the update:"
echo '   "What version of Bee Brain are you using?"'
echo ""

# Check API status (non-blocking)
if curl -f -s http://localhost:5050/api/admin/bee-brain/status > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Bee AI API is responding"
    echo ""
    echo "Full status: curl http://localhost:5050/api/admin/bee-brain/status | jq"
fi

echo ""
echo "For more info: cat ${INSTALL_DIR}/docs/bee-brain.md"
echo ""
