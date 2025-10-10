#!/bin/bash
# Test the chatbot with real responses by modifying the gateway's fallback behavior

set -e

# Directory of this script
SOURCE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SOURCE_DIR"

echo "🧪 Setting up test environment for real chatbot responses..."

# Create a temporary modified version of the gateway app
if [ ! -f ./llm_service/gateway/app.py.original ]; then
    echo "Creating backup of original gateway app..."
    cp ./llm_service/gateway/app.py ./llm_service/gateway/app.py.original
fi

# Modify the gateway app to prioritize real responses by increasing the timeout
# This will make the gateway spend more time trying to reach the model services
sed -i.bak 's/timeout=30.0/timeout=60.0/g' ./llm_service/gateway/app.py

echo "✅ Gateway modified to use longer timeout for model services"

# Restart the services to apply changes
echo "Restarting LLM services..."
./manage_sting.sh restart llm-gateway
./manage_sting.sh restart chatbot

echo "🔍 Testing chatbot API..."
sleep 5
curl -s http://localhost:8081/health | jq .

echo "🔍 Testing LLM Gateway..."
curl -s http://localhost:8080/health | jq .

# Test the gateway directly with a simple query
echo "🤖 Testing the gateway with a direct query..."
curl -s -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?", "model": "llama3"}' | jq .

echo "
🐝 Test setup complete! The chatbot should now try harder to use the real models.
   You can use the chat interface at: http://localhost:3000/dashboard/chat

   If you're still seeing mock responses, check these logs:
   - LLM Gateway: docker logs sting-ce-llm-gateway
   - Model Service: docker logs sting-ce-llama3-service
   - Chatbot: docker logs sting-ce-chatbot

   To restore the original gateway settings:
   ./manage_sting.sh restart llm-gateway
"