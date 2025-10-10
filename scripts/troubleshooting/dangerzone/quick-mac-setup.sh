#!/bin/bash

# Quick Mac Setup for STING-CE
# This script ensures all Mac-specific requirements are met

set -e

echo "================================================"
echo "STING-CE Quick Mac Setup"
echo "================================================"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to install Python packages
install_python_deps() {
    echo "Installing Python dependencies for native LLM service..."
    
    # Check if pip3 exists
    if ! command_exists pip3; then
        echo "Error: pip3 not found. Please install Python 3 first."
        exit 1
    fi
    
    # Install required packages
    echo "Installing PyTorch with MPS support..."
    pip3 install torch torchvision torchaudio
    
    echo "Installing transformers and accelerate..."
    pip3 install transformers accelerate
    
    echo "Installing additional dependencies..."
    pip3 install flask flask-cors numpy
    
    echo "✓ Python dependencies installed"
}

# Check if running on Mac
if [[ "$(uname)" != "Darwin" ]]; then
    echo "This script is for macOS only. Detected: $(uname)"
    exit 1
fi

# Step 1: Ensure Docker is running
echo "Checking Docker..."
if ! docker ps &> /dev/null; then
    echo "Docker is not running. Please start Docker Desktop and run this script again."
    exit 1
fi
echo "✓ Docker is running"
echo ""

# Step 2: Check Python dependencies
echo "Checking Python dependencies..."
deps_needed=false

if ! python3 -c "import torch" 2>/dev/null; then
    echo "✗ PyTorch not installed"
    deps_needed=true
else
    echo "✓ PyTorch installed"
fi

if ! python3 -c "import transformers" 2>/dev/null; then
    echo "✗ Transformers not installed"
    deps_needed=true
else
    echo "✓ Transformers installed"
fi

if [ "$deps_needed" = true ]; then
    echo ""
    read -p "Install missing Python dependencies? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_python_deps
    else
        echo "Skipping Python dependency installation."
        echo "You can install manually with:"
        echo "  pip3 install torch torchvision torchaudio transformers accelerate flask flask-cors"
    fi
fi
echo ""

# Step 3: Start core services
echo "Starting core Docker services..."
cd "$(dirname "$0")"

# Use the Mac-specific compose file
export COMPOSE_PROJECT_NAME="sting-ce"
docker compose -f docker-compose.yml -f docker-compose.mac.yml up -d postgres vault kratos app frontend llm-gateway

echo "Waiting for services to initialize..."
sleep 10

# Step 4: Start native LLM service
echo ""
echo "Starting native LLM service..."
if [ -f "./sting-llm" ]; then
    ./sting-llm start
    echo "✓ Native LLM service started"
else
    echo "✗ sting-llm script not found"
    echo "You can start it manually with:"
    echo "  cd llm_service && python3 server.py"
fi

# Step 5: Verify installation
echo ""
echo "================================================"
echo "Verifying Installation"
echo "================================================"
echo ""

# Wait a bit for services to be ready
sleep 5

# Check services
./check-installation-status.sh

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "If all services show as running, you can access STING-CE at:"
echo "  http://localhost:3000"
echo ""
echo "If you encounter issues:"
echo "1. Check logs: ./manage_sting.sh logs [service-name]"
echo "2. Restart services: ./manage_sting.sh restart"
echo "3. Check installation status: ./check-installation-status.sh"
echo ""