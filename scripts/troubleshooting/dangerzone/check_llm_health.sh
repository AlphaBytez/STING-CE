#!/bin/bash
# Post-installation health check script for STING LLM services
# Run this after installation completes to verify all models are loaded and working

# ANSI color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_ATTEMPTS=30
INTERVAL=10
GATEWAY_PORT=8080
GATEWAY_URL="http://localhost:${GATEWAY_PORT}"
MODEL_SERVICES=("llama3-service" "phi3-service" "zephyr-service" "llm-gateway")

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}     STING LLM Health Check         ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo

# Function to check if Docker is running
check_docker() {
  echo -e "${BLUE}Checking if Docker is running...${NC}"
  if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
  fi
  echo -e "${GREEN}Docker is running.${NC}"
  echo
}

# Function to check if Docker containers are running
check_containers() {
  echo -e "${BLUE}Checking LLM service containers...${NC}"
  local all_running=true
  
  for service in "${MODEL_SERVICES[@]}"; do
    container_id=$(docker ps | grep -w "${service}" | awk '{print $1}')
    if [ -z "$container_id" ]; then
      echo -e "${YELLOW}⚠️  ${service}: Not running${NC}"
      all_running=false
    else
      echo -e "${GREEN}✓ ${service}: Running (${container_id})${NC}"
    fi
  done
  
  if [ "$all_running" = false ]; then
    echo
    echo -e "${YELLOW}Some containers are not running. You may need to start them:${NC}"
    echo "./manage_sting.sh start llama3-service phi3-service zephyr-service llm-gateway"
    return 1
  fi
  
  echo -e "${GREEN}All expected containers are running.${NC}"
  echo
  return 0
}

# Function to check gateway health endpoint
check_gateway_health() {
  echo -e "${BLUE}Checking LLM Gateway health endpoint...${NC}"
  local attempt=1
  
  while [ $attempt -le $MAX_ATTEMPTS ]; do
    echo -e "Attempt $attempt/$MAX_ATTEMPTS..."
    
    if health_data=$(curl -s ${GATEWAY_URL}/health 2>/dev/null); then
      if echo "$health_data" | grep -q "healthy"; then
        echo -e "${GREEN}Gateway health endpoint is responding!${NC}"
        
        # Extract and display service status
        echo
        echo -e "${BLUE}Service status from gateway:${NC}"
        
        # Use grep and sed to extract the service status
        echo "$health_data" | grep -o '"services":{[^}]*}' | sed 's/"services"://g' | 
          sed 's/{//g' | sed 's/}//g' | sed 's/,/\'$'\n/g' | sed 's/"//g' | 
          while read line; do
            service=$(echo $line | cut -d: -f1)
            status=$(echo $line | cut -d: -f2)
            
            if [[ "$status" == "true" ]]; then
              echo -e "${GREEN}✓ $service: Healthy${NC}"
            else
              echo -e "${YELLOW}⚠️  $service: Not healthy${NC}"
            fi
          done
        
        echo
        return 0
      fi
    fi
    
    attempt=$((attempt + 1))
    sleep $INTERVAL
  done
  
  echo -e "${RED}Failed to connect to gateway health endpoint after $MAX_ATTEMPTS attempts.${NC}"
  echo "The LLM Gateway service may still be initializing or has failed to start."
  return 1
}

# Function to test the LLM models
test_models() {
  echo -e "${BLUE}Testing LLM models with a simple prompt...${NC}"
  echo
  
  # Simple test prompt
  test_prompt="What is the capital of France? Keep it short."
  
  # Test each model
  for model in "llama3" "phi3" "zephyr"; do
    echo -e "${BLUE}Testing $model...${NC}"
    
    # Prepare JSON payload
    json_payload="{\"message\":\"$test_prompt\",\"model\":\"$model\"}"
    
    # Send test request
    if response=$(curl -s -X POST ${GATEWAY_URL}/generate \
                      -H "Content-Type: application/json" \
                      -d "$json_payload" 2>/dev/null); then
      
      # Check for error response
      if echo "$response" | grep -q "error"; then
        echo -e "${RED}Error testing $model:${NC}"
        echo "$response" | jq -r .detail 2>/dev/null || echo "$response"
      else
        # Extract and display the model response
        model_response=$(echo "$response" | grep -o '"response":"[^"]*"' | sed 's/"response":"//g' | sed 's/"//g')
        model_used=$(echo "$response" | grep -o '"model":"[^"]*"' | sed 's/"model":"//g' | sed 's/"//g')
        
        # Truncate long responses for display
        if [ ${#model_response} -gt 100 ]; then
          model_response="${model_response:0:100}... (truncated)"
        fi
        
        echo -e "${GREEN}✓ Model responded:${NC} $model_response"
        echo -e "${BLUE}Model actually used:${NC} $model_used"
      fi
    else
      echo -e "${RED}Failed to connect to the $model service${NC}"
    fi
    
    echo
    sleep 2  # Small delay between tests
  done
}

# Function to check model loading status from logs
check_model_loading() {
  echo -e "${BLUE}Checking model loading status from logs...${NC}"
  
  for service in "llama3-service" "phi3-service" "zephyr-service"; do
    container_id=$(docker ps | grep -w "${service}" | awk '{print $1}')
    
    if [ -z "$container_id" ]; then
      echo -e "${YELLOW}⚠️  ${service}: Not running, can't check logs${NC}"
      continue
    fi
    
    echo -e "${BLUE}${service} logs:${NC}"
    
    # Get recent logs and check for successful model loading messages
    if docker logs --tail 50 "$container_id" 2>&1 | grep -q "Model loaded successfully"; then
      echo -e "${GREEN}✓ Model loaded successfully${NC}"
    else
      # Check if it's still loading
      if docker logs --tail 50 "$container_id" 2>&1 | grep -q "Loading model from"; then
        echo -e "${YELLOW}⚠️  Model is still loading...${NC}"
      else
        echo -e "${RED}⚠️  No clear indication of model loading status${NC}"
        echo -e "${YELLOW}Last few log entries:${NC}"
        docker logs --tail 5 "$container_id" 2>&1
      fi
    fi
    
    echo
  done
}

# Main function to run all checks
main() {
  # Run checks in sequence
  check_docker
  
  if check_containers; then
    check_gateway_health
    check_model_loading
    test_models
    
    echo -e "${BLUE}=====================================${NC}"
    echo -e "${GREEN}Health check completed!${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo
    echo -e "If you encountered any issues:"
    echo -e "1. Check container logs with: ${YELLOW}docker logs <container_id>${NC}"
    echo -e "2. Restart services with: ${YELLOW}./manage_sting.sh restart llama3-service phi3-service zephyr-service llm-gateway${NC}"
    echo -e "3. To see detailed service stats: ${YELLOW}curl http://localhost:8080/stats${NC}"
  else
    echo -e "${RED}Cannot complete all checks because some containers are not running.${NC}"
    echo -e "${YELLOW}Please start the required services first.${NC}"
  fi
}

# Run the main function
main