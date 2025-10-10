#!/bin/bash
# Comprehensive script to fix all service issues and restart the STING stack

set -e

echo "=== STING Service Repair Script ==="
echo "This script will:"
echo "1. Fix port conflicts"
echo "2. Fix the database healthcheck"
echo "3. Fix the LLM service configuration"
echo "4. Restart all services"
echo ""

# Step 1: Stop all containers first
echo "Stopping all existing containers..."
docker-compose down

# Step 2: Update ports to avoid conflicts
echo "Applying port fixes..."
./update-ports.sh

# Step 3: Fix the database healthcheck issue
echo "Ensuring database healthcheck is fixed..."
sed -i'.bak.dbfix2' 's/test: \["CMD", "pg_isready"\]/test: \["CMD", "pg_isready", "-U", "postgres"\]/g' docker-compose.yml

# Step 4: Apply LLM service fixes
echo "Applying LLM service fixes..."

# Check if server.py.fixed already exists, if not, create it
if [ ! -f "./llm_service/server.py.fixed" ]; then
  echo "Creating fixed server.py script..."
  cp ./llm_service/server.py ./llm_service/server.py.original
  
  # Find the appropriate import line and add BitsAndBytesConfig
  sed -i'.bak' 's/from transformers import AutoTokenizer, AutoModelForCausalLM/from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig/g' ./llm_service/server.py
  
  # Replace the deprecated load_in_8bit parameter with BitsAndBytesConfig
  cat > ./llm_service/server.py.fixed << 'EOF'
import os
import logging
import torch
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import uvicorn
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
MODEL_PATH = os.environ.get("MODEL_PATH", "/app/models/llama-3-8b")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "auto")  # cuda, cpu, or auto
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3")
QUANTIZATION = os.environ.get("QUANTIZATION", "none")  # int8, int4, or none
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "4096"))

app = FastAPI(title="STING LLM Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Message format
class Message(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    system_prompt: Optional[str] = None
    
class ChatResponse(BaseModel):
    model: str
    response: str
    usage: Dict[str, int]

# Load model on startup
@app.on_event("startup")
async def startup_event():
    global tokenizer, model
    
    logger.info(f"Starting LLM service with device_type={DEVICE_TYPE}, model={MODEL_NAME}, path={MODEL_PATH}")
    
    try:
        start_time = time.time()
        
        # Determine the device
        if DEVICE_TYPE == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = DEVICE_TYPE
            
        logger.info(f"Using device: {device}")
        
        # Configure quantization parameters using BitsAndBytesConfig (modern approach)
        if QUANTIZATION == "int4":
            logger.info("Using 4-bit quantization")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16
            )
        elif QUANTIZATION == "int8":
            logger.info("Using 8-bit quantization")
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )
        else:
            quantization_config = None
            logger.info("Using default precision")
        
        # Load tokenizer
        logger.info(f"Loading tokenizer from {MODEL_PATH}")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        
        # Load model
        logger.info(f"Loading model from {MODEL_PATH}")
        
        # Use the appropriate parameters based on quantization setting
        model_load_params = {
            "pretrained_model_name_or_path": MODEL_PATH,
            "device_map": device,
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
        }
        
        # Add quantization config if specified
        if quantization_config is not None:
            model_load_params["quantization_config"] = quantization_config
            
        model = AutoModelForCausalLM.from_pretrained(**model_load_params)
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Prepare the input
        messages = request.messages
        
        # Prepare system prompt if provided
        if request.system_prompt:
            messages = [Message(role="system", content=request.system_prompt)] + messages
            
        # Format conversation for the model
        conversation = []
        for msg in messages:
            if msg.role == "user":
                conversation.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                conversation.append({"role": "assistant", "content": msg.content})
            elif msg.role == "system":
                conversation.append({"role": "system", "content": msg.content})
        
        # Generate response
        input_tokens = tokenizer.apply_chat_template(
            conversation, 
            return_tensors="pt"
        )
        
        if torch.cuda.is_available():
            input_tokens = input_tokens.to("cuda")
            
        with torch.no_grad():
            outputs = model.generate(
                input_tokens,
                max_length=min(MAX_LENGTH, input_tokens.shape[1] + request.max_tokens),
                do_sample=True,
                temperature=request.temperature,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode the response
        response_text = tokenizer.decode(outputs[0][input_tokens.shape[1]:], skip_special_tokens=True)
        
        # Count tokens (rough estimation)
        input_token_count = input_tokens.shape[1]
        output_token_count = outputs.shape[1] - input_tokens.shape[1]
        
        return {
            "model": MODEL_NAME,
            "response": response_text,
            "usage": {
                "prompt_tokens": input_token_count,
                "completion_tokens": output_token_count,
                "total_tokens": input_token_count + output_token_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
        
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
EOF
fi

# Check if Dockerfile.gateway.fixed already exists, if not, create it
if [ ! -f "./llm_service/Dockerfile.gateway.fixed" ]; then
  echo "Creating fixed Dockerfile.gateway..."
  cp ./llm_service/Dockerfile.gateway ./llm_service/Dockerfile.gateway.original
  
  cat > ./llm_service/Dockerfile.gateway.fixed << 'EOF'
FROM python:3.10-slim

WORKDIR /app

COPY ./requirements.gateway.txt /app/requirements.gateway.txt

# Install dependencies with specific version constraints for critical packages
RUN pip install --no-cache-dir -r requirements.gateway.txt && \
    pip install --no-cache-dir --upgrade accelerate>=0.23.0 && \
    pip install --no-cache-dir --upgrade bitsandbytes>=0.41.1

# Copy application files
COPY ./gateway /app/gateway
COPY ./filtering /app/filtering
COPY ./chat /app/chat
COPY ./utils /app/utils
COPY ./server.py /app/server.py
COPY ./server.py.fixed /app/server.py.fixed

EXPOSE 8080

# Set environment variables for Python app
ENV PYTHONUNBUFFERED=1
ENV MODEL_NAME="llama3"

# Create log directory
RUN mkdir -p /var/log/llm-service

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:8080/health || exit 1

CMD ["python", "server.py.fixed"]
EOF
fi

# Step 5: Add the "ENV QUANTIZATION=none" to all model service sections
echo "Ensuring QUANTIZATION=none is set for all model services..."
grep -q 'QUANTIZATION=none' docker-compose.yml || sed -i'.bak.env' 's/- HF_TOKEN=\${HF_TOKEN:-dummy}/- HF_TOKEN=\${HF_TOKEN:-dummy}\n      - QUANTIZATION=none  # Disable quantization to avoid bitsandbytes issues/g' docker-compose.yml

# Step 6: Start the database first and make sure it's healthy
echo "Starting the database..."
docker-compose up -d db

# Wait for database to become healthy
echo "Waiting for database to become healthy..."
for i in {1..30}; do
  health_status=$(docker inspect --format='{{.State.Health.Status}}' sting-db-1 2>/dev/null || echo "container not found")
  if [ "$health_status" = "healthy" ]; then
    echo "Database container is now healthy!"
    break
  fi
  echo "Waiting for database to become healthy... (attempt $i/30)"
  sleep 5
done

if [ "$health_status" != "healthy" ]; then
  echo "ERROR: Database container failed to become healthy. Check the logs:"
  docker logs sting-db-1 2>&1 | tail -n 50
  exit 1
fi

# Step 7: Start other essential services
echo "Starting essential services: vault, dev, kratos..."
docker-compose up -d vault dev kratos

# Wait for essential services to become healthy
echo "Waiting for essential services to become healthy..."
for service in vault dev kratos; do
  container_name="sting-${service}-1"
  echo "Waiting for $service to become healthy..."
  
  for i in {1..30}; do
    health_status=$(docker inspect --format='{{.State.Health.Status}}' $container_name 2>/dev/null || echo "container not found")
    if [ "$health_status" = "healthy" ]; then
      echo "$service container is now healthy!"
      break
    fi
    echo "Waiting for $service to become healthy... (attempt $i/30)"
    sleep 5
  done
  
  if [ "$health_status" != "healthy" ]; then
    echo "WARNING: $service container failed to become healthy. Continuing anyway..."
  fi
done

# Step 8: Start the LLM services
echo "Starting LLM services..."
docker-compose up -d llama3-service phi3-service zephyr-service

# Step 9: Start the LLM Gateway and wait for it to become healthy
echo "Starting LLM Gateway..."
docker-compose up -d llm-gateway

# Wait for LLM Gateway to become healthy
echo "Waiting for LLM Gateway to become healthy..."
for i in {1..30}; do
  health_status=$(docker inspect --format='{{.State.Health.Status}}' sting-llm-gateway-1 2>/dev/null || echo "container not found")
  if [ "$health_status" = "healthy" ]; then
    echo "LLM Gateway container is now healthy!"
    break
  fi
  echo "Waiting for LLM Gateway to become healthy... (attempt $i/30)"
  sleep 5
done

if [ "$health_status" != "healthy" ]; then
  echo "WARNING: LLM Gateway container failed to become healthy. Check the logs:"
  docker logs sting-llm-gateway-1 2>&1 | tail -n 50
  echo "Continuing with the rest of the services anyway..."
fi

# Step 10: Start the remaining services
echo "Starting remaining services: app, frontend, mailslurper, chatbot..."
docker-compose up -d app frontend mailslurper chatbot

echo "All services have been started!"
echo "You can check their status with: docker-compose ps"
echo "And see the logs with: docker-compose logs -f [service_name]"

# Step 11: Verify the chatbot is working
echo "Checking if the chatbot service is healthy..."
chatbot_status=$(docker inspect --format='{{.State.Health.Status}}' sting-ce-chatbot 2>/dev/null || echo "container not found")

if [ "$chatbot_status" = "healthy" ]; then
  echo "SUCCESS: Chatbot service is healthy!"
  echo "You can test it with: curl -s http://localhost:8081/health"
else
  echo "WARNING: Chatbot service may not be fully healthy yet."
  echo "Check its status with: docker-compose logs chatbot"
fi

echo ""
echo "=== SERVICE STATUS SUMMARY ==="
docker-compose ps