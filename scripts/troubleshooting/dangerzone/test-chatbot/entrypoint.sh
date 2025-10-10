#!/bin/bash
# Test Chatbot service entrypoint script - completely standalone
# No dependencies on other scripts or commands
set -e

# Make sure we don't try to source any non-existent files
# or run commands that aren't installed

echo "Starting TEST chatbot service..."
python --version 2>&1
echo "Current directory:"
pwd
echo "Directory contents:"
ls -la
echo "Python path: $PYTHONPATH"
echo "LLM Gateway URL: $LLM_GATEWAY_URL"

# Set PYTHONPATH to include the app directory
export PYTHONPATH="${PYTHONPATH}:/app"

# Create a fallback server for testing if needed
cat > /app/test_server.py << 'EOL'
#!/usr/bin/env python3
"""
Test Chatbot Server for STING platform
Simple implementation that always works regardless of LLM availability
"""

import os
import time
import datetime
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-chatbot")

# Create FastAPI app
app = FastAPI(title="TEST STING Chatbot Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory store for conversations
conversations = {}

class ChatRequest(BaseModel):
    message: str
    user_id: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_used: List[Dict[str, Any]] = []
    processing_time: float = 0.0
    filtered: bool = False
    filter_reason: Optional[str] = None
    timestamp: str

class ConversationHistoryRequest(BaseModel):
    user_id: str
    limit: Optional[int] = None

class ConversationClearRequest(BaseModel):
    user_id: str

@app.post("/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """Process a chat message with fallback response"""
    logger.info(f"Received message from {request.user_id}: {request.message}")
    
    # Track the message in our simple conversation store
    if request.user_id not in conversations:
        conversations[request.user_id] = []
    
    conversations[request.user_id].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    # Generate a response based on the message
    start_time = time.time()
    time.sleep(0.5)  # Simulate processing time
    
    # Simple pattern matching for responses
    message = request.message.lower()
    
    if "hello" in message or "hi" in message:
        response = "Hello! I'm TestBee, a simplified test version of the STING chatbot. How can I help you today?"
    elif "how are you" in message:
        response = "I'm functioning perfectly as a test chatbot. Thanks for asking!"
    elif "model" in message or "llm" in message:
        response = "I'm not using any actual LLM model. I'm a simple rule-based test chatbot designed to verify connectivity."
    elif "test" in message:
        response = "Yes, this is the test chatbot service. It's working correctly!"
    elif "what can you do" in message:
        response = "I can respond to basic queries to verify that the chatbot service is operational. I'm not using a real LLM model."
    elif "help" in message:
        response = "I'm a test chatbot that provides simple responses. Try saying 'hello', 'how are you', or asking about my capabilities."
    else:
        response = f"I received your message: '{request.message}'. This is a test response from the simplified chatbot service."
    
    # Track response
    conversations[request.user_id].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.datetime.now().isoformat()
    })
    
    processing_time = time.time() - start_time
    
    # Return formatted response
    return ChatResponse(
        response=response,
        conversation_id=request.user_id,
        tools_used=[],
        processing_time=processing_time,
        filtered=False,
        filter_reason=None,
        timestamp=datetime.datetime.now().isoformat()
    )

@app.post("/chat/history")
async def get_conversation_history(request: ConversationHistoryRequest):
    """Get conversation history for a user"""
    if request.user_id not in conversations:
        return []
    
    history = conversations[request.user_id]
    if request.limit:
        history = history[-request.limit:]
    
    return history

@app.post("/chat/clear")
async def clear_conversation(request: ConversationClearRequest):
    """Clear conversation history for a user"""
    if request.user_id in conversations:
        conversations[request.user_id] = []
        return {"status": "success", "message": "Conversation cleared"}
    
    return {"status": "success", "message": "No conversation found"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server_running": True,
        "service_initialized": True,
        "error": None,
        "timestamp": str(time.time())
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "TEST STING Chatbot Service",
        "version": "0.1.0",
        "endpoints": [
            {"path": "/chat/message", "method": "POST", "description": "Process a chat message"},
            {"path": "/chat/history", "method": "POST", "description": "Get conversation history"},
            {"path": "/chat/clear", "method": "POST", "description": "Clear conversation history"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8082))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting TEST STING Chatbot Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
EOL

echo "Starting test chatbot server..."
# Try to run the regular chatbot server first
if [ -f /app/chatbot/server.py ]; then
    echo "Found server.py at /app/chatbot/server.py - trying to run it"
    python -m chatbot.server || {
        echo "❌ Error running main chatbot server, falling back to test server"
        python /app/test_server.py
    }
else
    echo "⚠️ Regular chatbot server not found, using test server"
    python /app/test_server.py
fi