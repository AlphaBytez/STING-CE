#!/bin/bash
# Test script for --sync-only functionality

echo "🧪 Testing --sync-only functionality"
echo "===================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\n${BLUE}1. Checking current setup${NC}"
echo "Current directory: $(pwd)"
echo "Install directory: $HOME/.sting-ce"

echo -e "\n${BLUE}2. Checking if services are running${NC}"
if docker compose ps frontend 2>/dev/null | grep -q "Up"; then
    echo -e "${GREEN}✓ Frontend service is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend service not running - start with: ./manage_sting.sh start${NC}"
fi

echo -e "\n${BLUE}3. Making a small test change${NC}"
# Create a small test change in a comment
TEST_FILE="frontend/src/App.js"
if [ -f "$TEST_FILE" ]; then
    # Add a timestamp comment
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "// Test sync at $TIMESTAMP" >> "$TEST_FILE"
    echo -e "${GREEN}✓ Added test comment to $TEST_FILE${NC}"
else
    echo -e "${YELLOW}⚠ $TEST_FILE not found, skipping test change${NC}"
fi

echo -e "\n${BLUE}4. Testing sync-only update${NC}"
echo "Running: ./manage_sting.sh update frontend --sync-only"
echo "Watch for 'Sync-only mode' message..."
echo ""

# Run the update with sync-only
./manage_sting.sh update frontend --sync-only

echo -e "\n${BLUE}5. Verification${NC}"
echo "Check if the change was synced to install directory:"
if [ -f "$HOME/.sting-ce/$TEST_FILE" ]; then
    if grep -q "Test sync at" "$HOME/.sting-ce/$TEST_FILE"; then
        echo -e "${GREEN}✓ File was synced to install directory${NC}"
    else
        echo -e "${YELLOW}⚠ File exists but test comment not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ File not found in install directory${NC}"
fi

echo -e "\n${BLUE}6. Cleanup${NC}"
if [ -f "$TEST_FILE" ]; then
    # Remove the test comment
    sed -i '' '/Test sync at/d' "$TEST_FILE"
    echo -e "${GREEN}✓ Cleaned up test comment${NC}"
fi

echo -e "\n${GREEN}🎉 Test complete!${NC}"
echo "If you saw 'Sync-only mode' message and no Docker build, it worked!"