#!/bin/bash

echo "=== STING-CE Mac Setup Checker ==="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check platform
if [[ "$(uname)" == "Darwin" ]]; then
    echo -e "${GREEN}✓${NC} Running on macOS"
    
    # Check for Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        echo -e "${GREEN}✓${NC} Apple Silicon detected (M1/M2/M3)"
    else
        echo -e "${YELLOW}!${NC} Intel Mac detected - MPS not available"
    fi
else
    echo -e "${RED}✗${NC} Not running on macOS"
    exit 0
fi

echo
echo "Checking Python and PyTorch..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
else
    echo -e "${RED}✗${NC} Python 3 not found"
fi

# Check PyTorch and MPS
python3 -c "
import sys
try:
    import torch
    print(f'${GREEN}✓${NC} PyTorch {torch.__version__} installed')
    if torch.backends.mps.is_available():
        print(f'${GREEN}✓${NC} MPS (Metal Performance Shaders) available!')
        print(f'  Device will use GPU acceleration')
    else:
        print(f'${YELLOW}!${NC} MPS not available - will use CPU')
except ImportError:
    print(f'${RED}✗${NC} PyTorch not installed')
    print(f'  Install with: pip3 install torch torchvision')
" 2>/dev/null || echo -e "${RED}✗${NC} Could not check PyTorch"

echo
echo "Checking Docker setup..."

# Check for docker-compose.mac.yml
if [ -f "docker-compose.mac.yml" ]; then
    echo -e "${GREEN}✓${NC} Mac-specific Docker compose file found"
else
    echo -e "${RED}✗${NC} docker-compose.mac.yml not found"
fi

# Check if native LLM service is running
if lsof -Pi :8085 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Native LLM service is running on port 8085"
    
    # Try health check
    if curl -sf http://localhost:8085/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Native LLM service is healthy"
    else
        echo -e "${YELLOW}!${NC} Native LLM service not responding to health checks"
    fi
else
    echo -e "${YELLOW}!${NC} Native LLM service not running on port 8085"
fi

echo
echo "Checking model location..."

# Check for models
MODEL_DIR="$HOME/Downloads/llm_models"
if [ -d "$MODEL_DIR/llama-3-8b" ]; then
    echo -e "${GREEN}✓${NC} Llama 3 model found at $MODEL_DIR"
else
    echo -e "${YELLOW}!${NC} Llama 3 model not found at $MODEL_DIR"
    echo "  Models will be downloaded on first use"
fi

echo
echo "=== Summary ==="

# Final recommendation
if [[ "$(uname -m)" == "arm64" ]] && command -v python3 &> /dev/null; then
    echo -e "${GREEN}Your Mac is ready for GPU-accelerated LLM inference!${NC}"
    echo
    echo "To start STING-CE with native LLM support:"
    echo "  ./manage_sting.sh install"
    echo
    echo "To manage the LLM service:"
    echo "  ./sting-llm status"
else
    echo -e "${YELLOW}Some requirements are missing for optimal performance${NC}"
fi