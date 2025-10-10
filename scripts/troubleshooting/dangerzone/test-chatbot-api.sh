#!/bin/bash
# Test the STING chatbot API directly with curl commands

set -e
CHATBOT_URL="http://localhost:8081"
LLM_GATEWAY_URL="http://localhost:8080"

# Function to print section headers
print_header() {
    echo "======================================================"
    echo "  $1"
    echo "======================================================"
}

# Function to check if a service is running
check_service() {
    if curl -s -f "$1/health" > /dev/null; then
        echo "✅ Service at $1 is running"
        return 0
    else
        echo "❌ Service at $1 is not available"
        return 1
    fi
}

# Main script
clear
print_header "STING Chatbot API Test"

# Check if services are running
echo "Checking services..."
check_service $CHATBOT_URL || { echo "Chatbot service not available. Run './manage_sting.sh start chatbot' first."; exit 1; }
check_service $LLM_GATEWAY_URL || { echo "LLM Gateway not available. Run './manage_sting.sh start llm-gateway' first."; exit 1; }

# Test basic health endpoints
print_header "Testing Health Endpoints"
echo "Chatbot health:"
curl -s $CHATBOT_URL/health | jq .

echo "LLM Gateway health:"
curl -s $LLM_GATEWAY_URL/health | jq .

# Test chat API
print_header "Testing Chat API"

# Generate a unique user ID for testing
USER_ID="test-user-$(date +%s)"
echo "Using test user ID: $USER_ID"

# Define the test message
read -p "Enter a test message (or press Enter for default): " TEST_MSG
TEST_MSG=${TEST_MSG:-"What's the weather like today?"}

echo "Sending message: \"$TEST_MSG\""
curl -s -X POST $CHATBOT_URL/chat/message \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$TEST_MSG\", \"user_id\": \"$USER_ID\"}" | jq .

# Test conversation history
print_header "Testing Conversation History"
echo "Getting conversation history for $USER_ID:"
curl -s -X POST $CHATBOT_URL/chat/history \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$USER_ID\"}" | jq .

# Test direct gateway API
print_header "Testing LLM Gateway API Directly"

read -p "Would you like to test the LLM Gateway directly? (y/n): " TEST_GATEWAY
if [[ $TEST_GATEWAY == "y" ]]; then
    read -p "Enter a model to test (llama3, phi3, zephyr): " MODEL
    MODEL=${MODEL:-"llama3"}
    
    echo "Testing direct query to $MODEL model:"
    curl -s -X POST $LLM_GATEWAY_URL/generate \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$TEST_MSG\", \"model\": \"$MODEL\"}" | jq .
fi

print_header "Test Complete"
echo "For more testing options:"
echo "- Clear conversation: curl -X POST $CHATBOT_URL/chat/clear -H \"Content-Type: application/json\" -d '{\"user_id\": \"$USER_ID\"}'"
echo "- View logs: docker logs sting-ce-chatbot"
echo "- Gateway logs: docker logs sting-ce-llm-gateway"