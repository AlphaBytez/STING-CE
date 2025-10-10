#!/bin/bash
# Test script for loading and testing Llama 3 model

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if LLM service is running
log "Checking LLM service status..."
if ! ./sting-llm status; then
    log "Starting LLM service..."
    ./sting-llm start
    sleep 5
fi

# List current models
log "Current model status:"
./sting-llm models

# Load Llama 3
log "Loading Llama 3 model..."
time ./sting-llm load llama3

# Test Llama 3 with a simple request
log "Testing Llama 3 with a simple chat request..."
curl -X POST http://localhost:8086/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "message": "What is STING Assistant?",
    "max_tokens": 100
  }' | python3 -m json.tool

# Test task routing to see when Llama 3 would be selected
log "Testing task routing scenarios..."

echo -e "\n${YELLOW}1. Testing analysis task (should route to Llama 3):${NC}"
./sting-llm route "Can you analyze the pros and cons of using microservices architecture?"

echo -e "\n${YELLOW}2. Testing simple chat (should route to TinyLlama):${NC}"
./sting-llm route "Hello, how are you?"

echo -e "\n${YELLOW}3. Testing agent task (should route to DeepSeek or Llama 3):${NC}"
./sting-llm route "Search for information about quantum computing and summarize it"

# Show final model status
log "Final model status:"
./sting-llm models

# Optional: Test memory usage
log "Checking memory usage..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # On Mac, check memory pressure
    info "Memory pressure:"
    memory_pressure | grep "System-wide memory free percentage"
    info "Python process memory:"
    ps aux | grep -E "python.*server.py" | grep -v grep
fi

log "Llama 3 loading test complete!"