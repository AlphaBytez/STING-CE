"""
Chat API endpoints for the STING LLM Gateway
Provides endpoints for conversation-based interactions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import time
import os

from ..chat.chat_service import STINGChatService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chat-api")

# Initialize router
router = APIRouter(prefix="/chat", tags=["chat"])

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    user_id: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_used: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time: float = 0.0
    filtered: bool = False
    filter_reason: Optional[str] = None
    timestamp: str

class ConversationHistoryRequest(BaseModel):
    user_id: str
    limit: Optional[int] = None

class ConversationClearRequest(BaseModel):
    user_id: str

# Global chat service instance
_chat_service = None

def get_chat_service():
    """Get or initialize the chat service singleton"""
    global _chat_service
    if _chat_service is None:
        # Load configuration
        with open("/app/conf/config.yml", "r") as f:
            import yaml
            config = yaml.safe_load(f)
        
        # Initialize chat service
        _chat_service = STINGChatService(config)
        logger.info("Chat service initialized")
    
    return _chat_service

@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest, chat_service: STINGChatService = Depends(get_chat_service)):
    """Process a chat message with conversation context"""
    start_time = time.time()
    
    try:
        # Process the message
        result = chat_service.process_message(
            user_id=request.user_id,
            message=request.message
        )
        
        # Add processing time if not already included
        if "processing_time" not in result:
            result["processing_time"] = time.time() - start_time
            
        return ChatResponse(**result)
        
    except Exception as e:
        logger.exception(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing error: {str(e)}"
        )

@router.post("/history", response_model=List[Dict[str, Any]])
async def get_conversation_history(
    request: ConversationHistoryRequest,
    chat_service: STINGChatService = Depends(get_chat_service)
):
    """Get conversation history for a user"""
    try:
        history = chat_service.get_conversation_history(
            user_id=request.user_id,
            limit=request.limit
        )
        return history
        
    except Exception as e:
        logger.exception(f"Error getting conversation history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation history: {str(e)}"
        )

@router.post("/clear")
async def clear_conversation(
    request: ConversationClearRequest,
    chat_service: STINGChatService = Depends(get_chat_service)
):
    """Clear conversation history for a user"""
    try:
        success = chat_service.clear_conversation(user_id=request.user_id)
        if success:
            return {"status": "success", "message": "Conversation cleared"}
        else:
            return {"status": "error", "message": "Conversation not found"}
            
    except Exception as e:
        logger.exception(f"Error clearing conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing conversation: {str(e)}"
        )

@router.get("/health")
async def health_check(chat_service: STINGChatService = Depends(get_chat_service)):
    """Health check endpoint for the chat service"""
    return {
        "status": "healthy",
        "tools_available": len(chat_service.tools),
        "timestamp": time.time()
    }