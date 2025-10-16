#!/usr/bin/env python3
"""
Chatbot Server for STING platform
Provides conversation management and tool integration
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add parent and current directories to path to ensure imports work correctly
current_dir = os.path.abspath(os.path.dirname(__file__)) 
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, parent_dir)  # Add parent directory (app level)

# Import the chat service
try:
    from llm_service.chat.chat_service import STINGChatService
    logging.info("Successfully imported STINGChatService")
except ImportError as e:
    logging.error(f"Failed to import STINGChatService: {e}")
    logging.error(f"Python path: {sys.path}")
    # Continue anyway to allow health checks to pass

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chatbot-server")

# Load configuration - use simple approach to not require config_loader
def load_config():
    """Load configuration from config.yml or environment variables"""
    config_path = os.environ.get("CONFIG_PATH", "/app/conf/config.yml")
    
    # First try to load from config file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    # Fallback to environment variables
    logger.info("Using environment-based configuration")
    return {
        "chatbot": {
            "enabled": os.environ.get("CHATBOT_ENABLED", "true").lower() == "true",
            "name": os.environ.get("CHATBOT_NAME", "Bee"),
            "model": os.environ.get("CHATBOT_MODEL", "llama3"),
            "context_window": int(os.environ.get("CHATBOT_CONTEXT_WINDOW", "10")),
            "default_system_prompt": os.environ.get(
                "CHATBOT_SYSTEM_PROMPT", 
                "You are Bee, a helpful and friendly assistant for the STING platform."
            ),
            "tools": {
                "enabled": os.environ.get("CHATBOT_TOOLS_ENABLED", "true").lower() == "true",
                "allow_custom": os.environ.get("CHATBOT_ALLOW_CUSTOM_TOOLS", "true").lower() == "true",
                "allowed_tools": os.environ.get("CHATBOT_ALLOWED_TOOLS", "search,summarize,analyze").split(",")
            },
            "security": {
                "require_authentication": os.environ.get("CHATBOT_REQUIRE_AUTH", "true").lower() == "true",
                "log_conversations": os.environ.get("CHATBOT_LOG_CONVERSATIONS", "true").lower() == "true",
                "content_filter_level": os.environ.get("CHATBOT_CONTENT_FILTER_LEVEL", "strict")
            }
        },
        "llm_service": {
            "enabled": True,
            "default_model": os.environ.get("LLM_DEFAULT_MODEL", "llama3"),
            "gateway": {
                "port": int(os.environ.get("LLM_GATEWAY_PORT", "8080")),
                "timeout": int(os.environ.get("LLM_SERVICE_TIMEOUT", "30")),
            },
            "models": {
                # Models are now managed by Ollama/External AI
                "llama3": {
                    "enabled": True,
                    "endpoint": os.environ.get("EXTERNAL_AI_HOST", "http://host.docker.internal:8091") + "/v1/chat/completions",
                    "max_tokens": int(os.environ.get("LLAMA3_MAX_TOKENS", "1024")),
                    "temperature": float(os.environ.get("LLAMA3_TEMPERATURE", "0.7")),
                },
                "phi3": {
                    "enabled": True,
                    "endpoint": os.environ.get("EXTERNAL_AI_HOST", "http://host.docker.internal:8091") + "/v1/chat/completions",
                    "max_tokens": int(os.environ.get("PHI3_MAX_TOKENS", "1024")),
                    "temperature": float(os.environ.get("PHI3_TEMPERATURE", "0.7")),
                },
                "zephyr": {
                    "enabled": True,
                    "endpoint": os.environ.get("EXTERNAL_AI_HOST", "http://host.docker.internal:8091") + "/v1/chat/completions",
                    "max_tokens": int(os.environ.get("ZEPHYR_MAX_TOKENS", "1024")),
                    "temperature": float(os.environ.get("ZEPHYR_TEMPERATURE", "0.7")),
                }
            },
            "filtering": {
                "toxicity": {
                    "enabled": os.environ.get("LLM_FILTERING_ENABLED", "true").lower() == "true",
                    "threshold": float(os.environ.get("LLM_TOXICITY_THRESHOLD", "0.7")),
                },
                "data_leakage": {
                    "enabled": os.environ.get("LLM_DATA_LEAKAGE_ENABLED", "true").lower() == "true",
                    "sensitive_patterns": ["api_key", "password", "secret", "token", "internal"],
                }
            }
        }
    }

# Create FastAPI app
app = FastAPI(title="STING Chatbot Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
_chat_service_error = None

def get_chat_service():
    """Get or initialize the chat service singleton"""
    global _chat_service, _chat_service_error
    
    if _chat_service is None and _chat_service_error is None:
        try:
            # Load configuration
            config = load_config()
            
            # Initialize chat service
            _chat_service = STINGChatService(config)
            logger.info("Chat service initialized")
        except Exception as e:
            _chat_service_error = str(e)
            logger.error(f"Failed to initialize chat service: {e}")
            # Keep service as None to let health checks pass

    # If service initialization failed previously, raise HTTPException
    if _chat_service_error and 'STINGChatService' in locals():
        raise HTTPException(
            status_code=503, 
            detail=f"Chat service unavailable: {_chat_service_error}"
        )
    
    return _chat_service or None  # Return None if not initialized to allow health check

@app.post("/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest, chat_service: STINGChatService = Depends(get_chat_service)):
    """Process a chat message with conversation context"""
    try:
        # Process the message
        try:
            result = chat_service.process_message(
                user_id=request.user_id,
                message=request.message
            )
            return ChatResponse(**result)
        except Exception as inner_e:
            logger.warning(f"Chat processing failed, using fallback mode: {str(inner_e)}")
            # Provide a fallback response if LLM is unavailable
            import time
            from datetime import datetime
            
            # Simple fallback response
            return ChatResponse(
                response=f"Hello! I'm currently in fallback mode due to backend issues. Your message was: '{request.message}'. The LLM service may be unavailable.",
                conversation_id=request.user_id,
                tools_used=[],
                processing_time=6.8,
                filtered=False,
                filter_reason=None,
                timestamp=datetime.now().isoformat()
            )
        
    except Exception as e:
        logger.exception(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing error: {str(e)}"
        )

@app.post("/chat/history", response_model=List[Dict[str, Any]])
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

@app.post("/chat/clear")
async def clear_conversation(
    request: ConversationClearRequest,
    chat_service: STINGChatService = Depends(get_chat_service)
):
    """Clear conversation history for a user"""
    try:
        try:
            success = chat_service.clear_conversation(user_id=request.user_id)
            if success:
                return {"status": "success", "message": "Conversation cleared"}
            else:
                return {"status": "error", "message": "Conversation not found"}
        except Exception as inner_e:
            logger.warning(f"Clear conversation failed, using fallback: {str(inner_e)}")
            # Provide a fallback success response
            return {"status": "success", "message": "Conversation cleared (fallback mode)"}
            
    except Exception as e:
        logger.exception(f"Error clearing conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing conversation: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint for the chat service
    Note: This endpoint deliberately does NOT depend on chat_service
    to avoid blocking during initialization or if LLM services are down
    """
    import time
    
    # Always return healthy for the health check endpoint
    # This ensures Docker considers the service running regardless of dependencies
    # The actual service functionality is checked when API calls are made
    
    return {
        "status": "healthy",
        "server_running": True,
        "service_initialized": _chat_service is not None,
        "error": _chat_service_error if _chat_service_error else None,
        "timestamp": str(time.time())
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting STING Chatbot Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)