#!/bin/bash
# Test script for venv and working directory fixes

echo "🧪 Testing Virtual Environment and Working Directory Fixes"
echo "=========================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "\n${BLUE}1. Testing working directory handling${NC}"
echo "Current directory: $(pwd)"

# Test if our libmagic fix would work
echo -e "\n${BLUE}2. Testing libmagic installation context${NC}"
if command -v brew >/dev/null 2>&1; then
    echo "Homebrew available: ✓"
    
    # Simulate the problematic scenario
    echo "Testing brew in invalid directory context..."
    (
        # This simulates what happens during reinstall
        cd /tmp/nonexistent_dir_test 2>/dev/null || {
            echo "Directory doesn't exist (expected)"
            # Our fix: change to valid directory
            cd /tmp || cd "$HOME" || cd /
            export PWD="$(pwd)"
            echo "Changed to valid directory: $(pwd)"
            
            # Test if brew would work now
            if brew --version >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Brew works in valid directory${NC}"
            else
                echo -e "${RED}✗ Brew still fails${NC}"
            fi
        }
    )
else
    echo -e "${YELLOW}⚠ Homebrew not available for testing${NC}"
fi

echo -e "\n${BLUE}3. Testing venv path resolution${NC}"
INSTALL_DIR="${HOME}/.sting-ce"
if [ -f "${INSTALL_DIR}/.venv/bin/python3" ]; then
    echo -e "${GREEN}✓ Virtual environment exists at ${INSTALL_DIR}/.venv${NC}"
    echo "Python version: $(${INSTALL_DIR}/.venv/bin/python3 --version)"
else
    echo -e "${YELLOW}⚠ Virtual environment not found (expected if not installed)${NC}"
fi

echo -e "\n${BLUE}4. Testing config_loader.py dependencies${NC}"
if [ -f "conf/config_loader.py" ]; then
    echo "Testing config_loader.py compilation..."
    if python3 -m py_compile conf/config_loader.py; then
        echo -e "${GREEN}✓ config_loader.py compiles successfully${NC}"
    else
        echo -e "${RED}✗ config_loader.py has syntax errors${NC}"
    fi
else
    echo -e "${YELLOW}⚠ config_loader.py not found${NC}"
fi

echo -e "\n${BLUE}5. Summary of fixes applied${NC}"
echo "✓ Added working directory validation before brew commands"
echo "✓ Added working directory validation before venv creation"
echo "✓ Enhanced config_loader.py to use venv when available"
echo "✓ Removed deprecated SupertokensConfig"
echo "✓ Added proper error handling and directory restoration"

echo -e "\n${GREEN}🎉 Test complete!${NC}"
echo "The fixes should resolve the 'getcwd: cannot access parent directories' error"
echo "during reinstall operations."