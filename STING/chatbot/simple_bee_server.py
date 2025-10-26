#!/usr/bin/env python3
"""
Simple Bee Server - A simplified version of the Bee AI assistant
Provides the endpoints needed by BeeChat UI without complex dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import random
import time
import logging
import datetime
import uvicorn
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple Bee Assistant")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample responses for Bee
BEE_RESPONSES = [
    "🐝 Hi! I'm Bee. How can I help?",
    "🐝 I'm here to help! The full AI capabilities are being configured, but I can still assist you.",
    "🐝 Great question! Let me help you with that. The STING platform is continuously improving.",
    "🐝 I understand what you're looking for. While my full capabilities are being set up, I'm here to help!",
    "🐝 Thanks for using STING! I'm Bee, and I'm buzzing with excitement to assist you.",
    "🐝 That's an interesting request! The development team is working on enhancing my abilities.",
    "🐝 I'm processing your request. The STING platform offers many features to explore!",
    "🐝 Let me help you navigate STING. What specific feature are you interested in?",
    "🐝 I'm learning and growing every day! Your feedback helps make STING better.",
    "🐝 Welcome to STING! I'm Bee, your AI companion. How may I assist you today?"
]

# Personality traits
PERSONALITIES = ["friendly", "helpful", "cheerful", "professional", "curious", "empathetic"]

class BeeRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None
    tools_enabled: Optional[List[str]] = []
    require_auth: Optional[bool] = False
    encryption_required: Optional[bool] = False

class BeeResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    sentiment: Optional[Dict[str, float]] = None
    tools_used: List[Dict[str, Any]] = []
    bee_personality: str
    encrypted: bool = False
    processing_time: float

@app.get("/")
def root():
    """Get API information."""
    return {
        "service": "Bee - STING AI Assistant",
        "version": "1.0.0-simple",
        "status": "buzzing",
        "endpoints": [
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/chat", "method": "POST", "description": "Chat with Bee"}
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "bee",
        "version": "1.0.0-simple",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/chat")
async def chat(request: BeeRequest):
    """Process a chat message."""
    try:
        start_time = time.time()
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"bee_{request.user_id}_{int(time.time())}"
        
        # Choose a random response
        response = random.choice(BEE_RESPONSES)
        
        # Add personalization based on message
        if "help" in request.message.lower():
            response += " I see you need help. What specific task can I assist you with?"
        elif "hello" in request.message.lower() or "hi" in request.message.lower():
            response = "🐝 Hello there! I'm Bee, your friendly STING assistant. It's great to meet you!"
        elif "thank" in request.message.lower():
            response = "🐝 You're very welcome! It's my pleasure to help. Is there anything else you need?"
        
        # Simulate sentiment analysis
        sentiment = {
            "positive": random.uniform(0.6, 0.9),
            "neutral": random.uniform(0.1, 0.3),
            "negative": random.uniform(0.0, 0.1)
        }
        
        # Simulate tool usage if requested
        tools_used = []
        if request.tools_enabled:
            for tool in request.tools_enabled[:2]:  # Use up to 2 tools
                tools_used.append({
                    "name": tool,
                    "status": "success",
                    "result": f"Completed {tool} operation"
                })
                response += f" I've used the {tool} tool to help with your request."
        
        # Choose personality
        personality = random.choice(PERSONALITIES)
        
        processing_time = time.time() - start_time
        
        return BeeResponse(
            response=response,
            conversation_id=conversation_id,
            timestamp=datetime.datetime.now().isoformat(),
            sentiment=sentiment,
            tools_used=tools_used,
            bee_personality=personality,
            encrypted=request.encryption_required,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv('BEE_PORT', '8888'))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")