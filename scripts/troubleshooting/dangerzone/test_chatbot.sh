#!/bin/bash
# Quick Chatbot Test Script
# Tests LLM service health and basic chatbot functionality

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default ports
LLM_PORT=8085  # Native LLM service on macOS
CHATBOT_PORT=8888  # Bee chatbot service

if [[ "$(uname)" != "Darwin" ]]; then
    LLM_PORT=8086  # Docker LLM gateway on Linux
fi

echo "=== STING Chatbot Health Check ==="
echo

# Test 1: Check if LLM service is running
echo -n "1. Testing LLM service health (port $LLM_PORT)... "
if curl -s -f "http://localhost:${LLM_PORT}/health" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "   LLM service is not responding on port $LLM_PORT"
    echo "   Try: ./manage_sting.sh llm start"
    exit 1
fi

# Test 2: Check if LLM can generate responses
echo -n "2. Testing LLM generation capability... "
response=$(curl -s -X POST "http://localhost:${LLM_PORT}/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello", "max_tokens": 10}' 2>/dev/null || echo "ERROR")

if [[ "$response" != "ERROR" ]] && [[ "$response" =~ "text" || "$response" =~ "response" || "$response" =~ "usage" ]]; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    echo "   LLM service is not generating responses properly"
    echo "   Response: $response"
    exit 1
fi

# Test 3: Check if Bee chatbot service is running
echo -n "3. Testing Bee chatbot service (port $CHATBOT_PORT)... "
if curl -s -f "http://localhost:${CHATBOT_PORT}/health" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${YELLOW}WARNING${NC}"
    echo "   Bee chatbot service is not responding on port $CHATBOT_PORT"
    echo "   Check: docker ps | grep chatbot"
fi

# Test 4: Check if chatbot can respond
echo -n "4. Testing chatbot conversation capability... "
if curl -s -f "http://localhost:${CHATBOT_PORT}/health" >/dev/null 2>&1; then
    chat_response=$(curl -s -X POST "http://localhost:${CHATBOT_PORT}/chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "Hello", "user_id": "test"}' 2>/dev/null || echo "ERROR")
    
    if [[ "$chat_response" != "ERROR" ]] && [[ "$chat_response" =~ "response" ]]; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${YELLOW}PARTIAL${NC}"
        echo "   Chatbot service is running but may not be responding correctly"
    fi
else
    echo -e "${YELLOW}SKIPPED${NC} (chatbot service not running)"
fi

echo
echo "=== Service Status Summary ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(chatbot|llm|sting-ce-)" || true

echo
echo "=== Quick Test Commands ==="
echo "Test LLM directly:"
echo "curl -X POST http://localhost:${LLM_PORT}/generate -H 'Content-Type: application/json' -d '{\"prompt\": \"Hello world\", \"max_tokens\": 20}'"
echo
echo "Test chatbot:"
echo "curl -X POST http://localhost:${CHATBOT_PORT}/chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello\", \"user_id\": \"test\"}'"
echo
echo
echo "=== Diagnostic Information ==="
echo "LLM Models Directory: /Users/captain-wolf/Downloads/llm_models/"
ls -la /Users/captain-wolf/Downloads/llm_models/ 2>/dev/null || echo "Models directory is empty or missing"

echo
echo "=== Quick Fixes ==="
if ! curl -s http://localhost:8085/health | grep -q "healthy"; then
    echo "❌ LLM service not running - try: ./manage_sting.sh llm start"
elif ! ls /Users/captain-wolf/Downloads/llm_models/*/ >/dev/null 2>&1; then
    echo "❌ No models found - download models first:"
    echo "   ./manage_sting.sh download_models"
    echo "   Or use HuggingFace model names in config.yml instead of local paths"
else
    echo "✅ Basic setup looks good"
fi

echo
echo -e "${GREEN}Health check complete!${NC}"