#!/bin/sh
# Simple script to update environment variables in the frontend

# Define default values
DEFAULT_API_URL="https://localhost:5050"
DEFAULT_KRATOS_URL="https://localhost:4433"
DEFAULT_MAILPIT_URL="http://localhost:8025"
DEFAULT_PUBLIC_URL="/"
DEFAULT_CHATBOT_URL="http://localhost:8081/chat"
DEFAULT_LLM_GATEWAY_URL="/api/llm"

# Create the env.js content with all needed variables
echo "window.env = {
  REACT_APP_API_URL: '${REACT_APP_API_URL:-$DEFAULT_API_URL}',
  REACT_APP_KRATOS_PUBLIC_URL: '${REACT_APP_KRATOS_PUBLIC_URL:-$DEFAULT_KRATOS_URL}',
  REACT_APP_MAILPIT_URL: '${REACT_APP_MAILPIT_URL:-$DEFAULT_MAILPIT_URL}',
  REACT_APP_CHATBOT_URL: '${REACT_APP_CHATBOT_URL:-$DEFAULT_CHATBOT_URL}',
  REACT_APP_LLM_GATEWAY_URL: '${REACT_APP_LLM_GATEWAY_URL:-$DEFAULT_LLM_GATEWAY_URL}',
  PUBLIC_URL: '${PUBLIC_URL:-$DEFAULT_PUBLIC_URL}',
  NODE_ENV: '${NODE_ENV:-development}',
  DEBUG: 'true'
};" > /usr/share/nginx/html/env.js

# No need for .env file in nginx container

echo "Updated environment variables in /usr/share/nginx/html/env.js"
echo "API URL: ${REACT_APP_API_URL:-$DEFAULT_API_URL}"
echo "Kratos URL: ${REACT_APP_KRATOS_PUBLIC_URL:-$DEFAULT_KRATOS_URL}"
echo "Mailpit URL: ${REACT_APP_MAILPIT_URL:-$DEFAULT_MAILPIT_URL}"
echo "Chatbot URL: ${REACT_APP_CHATBOT_URL:-$DEFAULT_CHATBOT_URL}"
echo "LLM Gateway URL: ${REACT_APP_LLM_GATEWAY_URL:-$DEFAULT_LLM_GATEWAY_URL}"
echo "Public URL: ${PUBLIC_URL:-$DEFAULT_PUBLIC_URL}"
echo "NODE_ENV: ${NODE_ENV:-development}"

