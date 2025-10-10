#!/bin/bash
# Apply the final fix to the LLM service

set -e

echo "Applying final fix to LLM Gateway..."

# Copy the final server.py file to the container
docker cp /Users/captain-wolf/Documents/GitHub/STING-CE/STING/llm_service/server.py.final sting-llm-gateway-1:/app/server.py.fixed

# Update docker-compose.yml to point to the fixed server
if ! grep -q "server.py.fixed" docker-compose.yml; then
  sed -i'.bak.server' 's/python server.py/python server.py.fixed/g' docker-compose.yml
fi

# Make sure QUANTIZATION=none is set in the environment
if ! grep -q "QUANTIZATION=none" docker-compose.yml; then
  sed -i'.bak.quant' 's/- HF_TOKEN=${HF_TOKEN:-dummy}/- HF_TOKEN=${HF_TOKEN:-dummy}\n      - QUANTIZATION=none  # Explicitly disable quantization/g' docker-compose.yml
fi

# Restart the LLM Gateway
echo "Restarting LLM Gateway with final fixes..."
docker-compose restart llm-gateway

echo "Waiting for LLM Gateway to become healthy..."
for i in {1..30}; do
  health_status=$(curl -s http://localhost:8086/health 2>/dev/null | grep -q "healthy" && echo "healthy" || echo "unhealthy")
  if [ "$health_status" = "healthy" ]; then
    echo "LLM Gateway is now healthy!"
    break
  fi
  echo "Waiting for LLM Gateway to become healthy... (attempt $i/30)"
  sleep 5
done

if [ "$health_status" != "healthy" ]; then
  echo "WARNING: LLM Gateway failed to become healthy. Check logs:"
  docker logs sting-llm-gateway-1 | tail -n 30
fi

# Restart the chatbot service too
echo "Restarting chatbot service..."
docker-compose restart chatbot

echo "Waiting for chatbot to become healthy..."
for i in {1..15}; do
  health_status=$(curl -s http://localhost:8081/health 2>/dev/null | grep -q "healthy" && echo "healthy" || echo "unhealthy")
  if [ "$health_status" = "healthy" ]; then
    echo "Chatbot service is now healthy!"
    break
  fi
  echo "Waiting for chatbot to become healthy... (attempt $i/15)"
  sleep 5
done

if [ "$health_status" != "healthy" ]; then
  echo "WARNING: Chatbot failed to become healthy. Check logs:"
  docker logs sting-ce-chatbot | tail -n 30
fi

echo "Fix applied! You can test the chatbot with:"
echo "curl -s -X POST -H \"Content-Type: application/json\" -d '{\"message\": \"Hello, how are you?\", \"user_id\": \"test-user\", \"conversation_id\": \"test-convo\"}' http://localhost:8081/chat/message"