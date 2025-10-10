#!/bin/bash

# STING-CE Installation Status Checker
# This script helps verify the current installation state and provides guidance

echo "================================================"
echo "STING-CE Installation Status Check"
echo "================================================"
echo ""

# Detect platform
PLATFORM=$(uname)
echo "Platform: $PLATFORM"
echo ""

# Check Docker
echo "Docker Status:"
if command -v docker &> /dev/null; then
    echo "✓ Docker installed"
    if docker ps &> /dev/null; then
        echo "✓ Docker daemon running"
    else
        echo "✗ Docker daemon not running - start Docker Desktop"
    fi
else
    echo "✗ Docker not installed"
fi
echo ""

# Check running containers
echo "Running Services:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(sting|NAME)"
echo ""

# Check critical services with more flexible naming
echo "Service Health Checks:"

# Check postgres/db
if docker ps | grep -qE "sting.*db|sting.*postgres"; then
    echo "✓ postgres is running"
else
    echo "✗ postgres is not running"
fi

# Check other services
for service in kratos vault app frontend llm-gateway; do
    if docker ps | grep -q "sting.*${service}"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is not running"
    fi
done
echo ""

# Mac-specific checks
if [[ "$PLATFORM" == "Darwin" ]]; then
    echo "Mac-Specific Checks:"
    
    # Check native LLM service
    if pgrep -f "llm_service/server.py" > /dev/null; then
        echo "✓ Native LLM service is running"
    else
        echo "✗ Native LLM service is not running"
        
        # Check Python dependencies
        echo ""
        echo "Checking LLM dependencies:"
        if python3 -c "import torch" 2>/dev/null; then
            echo "✓ PyTorch installed"
        else
            echo "✗ PyTorch not installed"
            echo "  Run: pip3 install torch torchvision torchaudio"
        fi
        
        if python3 -c "import transformers" 2>/dev/null; then
            echo "✓ Transformers installed"
        else
            echo "✗ Transformers not installed"
            echo "  Run: pip3 install transformers accelerate"
        fi
    fi
    echo ""
fi

# Check frontend accessibility
echo "Frontend Accessibility:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|301\|302"; then
    echo "✓ Frontend accessible at http://localhost:3000"
else
    echo "✗ Frontend not accessible"
fi
echo ""

# Check LLM Gateway
echo "LLM Gateway Status:"
if [[ "$PLATFORM" == "Darwin" ]]; then
    # On Mac, check the native service port
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8085/health | grep -q "200"; then
        echo "✓ LLM Gateway healthy at http://localhost:8085"
    else
        echo "✗ LLM Gateway not responding"
        echo "  On Mac, ensure native LLM service is running:"
        echo "  ./sting-llm start"
    fi
else
    # On Linux, check the Docker service port
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health | grep -q "200"; then
        echo "✓ LLM Gateway healthy at http://localhost:8080"
    else
        echo "✗ LLM Gateway not responding"
    fi
fi
echo ""

# Provide next steps
echo "================================================"
echo "Next Steps:"
echo "================================================"

# Check if installation seems incomplete
incomplete=false

if ! docker ps | grep -q "sting.*app"; then
    incomplete=true
    echo "1. Complete the installation:"
    echo "   ./manage_sting.sh install"
    echo ""
fi

if [[ "$PLATFORM" == "Darwin" ]] && ! pgrep -f "llm_service/server.py" > /dev/null; then
    echo "2. Start the native LLM service:"
    echo "   ./sting-llm start"
    echo ""
fi

if ! docker ps | grep -q "sting.*frontend"; then
    echo "3. Start the frontend:"
    echo "   ./manage_sting.sh start"
    echo ""
fi

if [[ "$incomplete" == "false" ]]; then
    echo "✓ Installation appears complete!"
    echo ""
    echo "Access STING-CE at:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - API: http://localhost:5000"
    if [[ "$PLATFORM" == "Darwin" ]]; then
        echo "  - LLM Gateway: http://localhost:8085"
    fi
fi

echo ""
echo "For detailed logs, run:"
echo "  ./manage_sting.sh logs [service-name]"
echo ""
echo "To restart all services:"
echo "  ./manage_sting.sh restart"
echo ""