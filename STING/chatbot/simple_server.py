from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import random
import time
import logging
import datetime
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple STING Chatbot")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample responses
SAMPLE_RESPONSES = [
    "I'm a simplified chatbot for testing. The actual LLM integration is being fixed!",
    "Hello! I'm a placeholder response while the LLM services are being configured.",
    "The STING platform is currently being updated to fix the LLM integration.",
    "This is a test response to verify the chatbot frontend integration.",
    "I'm Bee, your friendly assistant for STING, but I'm currently in maintenance mode.",
    "The development team is working on fixing the LLM integration. This is a placeholder response.",
    "Thank you for your message! The full AI capabilities will be available soon.",
    "I'm currently running in simulation mode while the language models are being configured.",
    "The chatbot API is working correctly, but the LLM backend is still being set up.",
    "I'm a simple test response to help verify the chatbot integration while LLM services are being fixed."
]

class ChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = "llama3"
    
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_used: List[str] = []
    processing_time: float
    filtered: bool = False
    filter_reason: Optional[str] = None
    timestamp: str

@app.get("/")
def root():
    """Get API information."""
    return {
        "service": "STING Chatbot Service",
        "version": "0.1.0",
        "endpoints": [
            {"path": "/chat/message", "method": "POST", "description": "Process a chat message"},
            {"path": "/chat/history", "method": "POST", "description": "Get conversation history"},
            {"path": "/chat/clear", "method": "POST", "description": "Clear conversation history"},
            {"path": "/health", "method": "GET", "description": "Health check"}
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server_running": True,
        "service_initialized": True,
        "error": None,
        "timestamp": str(time.time())
    }

@app.post("/chat/message")
async def chat(request: ChatRequest):
    """Process a chat message."""
    try:
        start_time = time.time()
        # Choose a random response
        response = random.choice(SAMPLE_RESPONSES)
        
        # Simulate processing time
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id or request.user_id,
            tools_used=[],
            processing_time=processing_time,
            filtered=False,
            filter_reason=None,
            timestamp=datetime.datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/history")
async def chat_history(request: Dict[str, Any]):
    """Get conversation history."""
    try:
        return {
            "history": [
                {"role": "system", "content": "You are Bee, a helpful assistant for the STING platform."},
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm a simplified chatbot for testing. The actual LLM integration is being fixed!"}
            ],
            "conversation_id": request.get("conversation_id", "test-convo")
        }
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/clear")
async def clear_history(request: Dict[str, Any]):
    """Clear conversation history."""
    try:
        return {
            "success": True,
            "message": "Chat history cleared",
            "conversation_id": request.get("conversation_id", "test-convo")
        }
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081, log_level="info")