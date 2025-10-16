"""
Public Bee Service - Main FastAPI Application

This service provides public-facing chat API endpoints that allow organizations
to deploy custom chatbots powered by their Honey Jar knowledge bases.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import logging
import time
import uuid
from datetime import datetime, timezone
import requests
import json

# Database imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, PublicBot, PublicBotAPIKey, PublicBotUsage
from auth import get_public_bee_auth, PublicBeeAuth
from bot_manager import PublicBotManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PUBLIC_BEE_PORT = int(os.getenv('PUBLIC_BEE_PORT', '8092'))
PUBLIC_BEE_HOST = os.getenv('PUBLIC_BEE_HOST', '0.0.0.0')
POSTGRES_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@db:5432/sting_app')
EXTERNAL_AI_URL = os.getenv('EXTERNAL_AI_URL', 'http://external-ai:8091')
CHATBOT_URL = os.getenv('CHATBOT_URL', 'http://chatbot:8888')
KNOWLEDGE_SERVICE_URL = os.getenv('KNOWLEDGE_SERVICE_URL', 'http://knowledge:8090')

# Database setup
try:
    engine = create_engine(POSTGRES_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database connection established")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    # Continue without database for now
    engine = None
    SessionLocal = None

def get_db():
    """Database dependency"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class ChatMessage(BaseModel):
    message: str = Field(..., description="The user's message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    bot_id: str
    processing_time_ms: int
    tokens_used: int
    sources: List[Dict[str, Any]] = []
    timestamp: str

class BotInfo(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    enabled: bool

class ErrorResponse(BaseModel):
    error: str
    message: str
    code: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="Public Bee API",
    description="Public chatbot API powered by STING knowledge bases",
    version="1.0.0",
    docs_url="/docs" if os.getenv('DEBUG') else None,
    redoc_url="/redoc" if os.getenv('DEBUG') else None
)

# CORS middleware - restrictive by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # Will be configured per bot
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "public-bee",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/public/bots", response_model=List[BotInfo])
async def list_public_bots(db = Depends(get_db)):
    """List all public bots (no authentication required)"""
    try:
        manager = PublicBotManager(db)
        bots = db.query(PublicBot).filter(
            PublicBot.enabled == True,
            PublicBot.public == True
        ).all()
        
        return [bot.public_dict() for bot in bots]
        
    except Exception as e:
        logger.error(f"Error listing public bots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list public bots")

@app.get("/api/public/bots/{bot_id}", response_model=BotInfo)
async def get_bot_info(bot_id: str, db = Depends(get_db)):
    """Get public information about a bot"""
    try:
        bot = db.query(PublicBot).filter(
            PublicBot.id == bot_id,
            PublicBot.enabled == True
        ).first()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return bot.public_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bot information")

@app.post("/api/public/chat/{bot_id}/message", response_model=ChatResponse)
async def chat_with_bot(
    bot_id: str,
    message: ChatMessage,
    request: Request,
    db = Depends(get_db),
    auth_data: tuple = Depends(get_public_bee_auth)
):
    """Send a message to a public bot"""
    start_time = time.time()
    bot, api_key_record = auth_data
    
    try:
        # Generate conversation ID if not provided
        conversation_id = message.conversation_id or str(uuid.uuid4())
        
        # Get relevant knowledge from bot's honey jars
        manager = PublicBotManager(db)
        knowledge_context = manager.query_honey_jars(bot, message.message, max_results=5)
        
        # Prepare context for the AI
        context = {
            "bot_name": bot.display_name,
            "system_prompt": bot.system_prompt,
            "knowledge_context": knowledge_context,
            "conversation_id": conversation_id,
            "user_message": message.message
        }
        
        if message.context:
            context.update(message.context)
        
        # Call the AI service
        ai_response = await call_ai_service(context)
        
        # Calculate processing time and estimate tokens
        processing_time_ms = int((time.time() - start_time) * 1000)
        tokens_used = estimate_tokens(message.message + ai_response)
        
        # Log usage
        auth_handler = PublicBeeAuth(db)
        auth_handler.log_usage(
            bot=bot,
            api_key_record=api_key_record,
            request=request,
            conversation_id=conversation_id,
            tokens_used=tokens_used,
            response_time_ms=processing_time_ms
        )
        
        # Prepare sources from knowledge context
        sources = [
            {
                "title": result.get("metadata", {}).get("title", "Document"),
                "excerpt": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", ""),
                "score": result.get("score", 0),
                "honey_jar": result.get("honey_jar_name", "Knowledge Base")
            }
            for result in knowledge_context[:3]  # Include top 3 sources
        ]
        
        return ChatResponse(
            response=ai_response,
            conversation_id=conversation_id,
            bot_id=str(bot.id),
            processing_time_ms=processing_time_ms,
            tokens_used=tokens_used,
            sources=sources,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        
        # Log failed usage
        processing_time_ms = int((time.time() - start_time) * 1000)
        auth_handler = PublicBeeAuth(db)
        auth_handler.log_usage(
            bot=bot,
            api_key_record=api_key_record,
            request=request,
            conversation_id=message.conversation_id or "unknown",
            tokens_used=0,
            response_time_ms=processing_time_ms,
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(status_code=500, detail="Failed to process message")

async def call_ai_service(context: Dict[str, Any]) -> str:
    """Call the AI service to generate a response"""
    try:
        # Try External AI service first
        ai_payload = {
            "model": "phi3:mini",
            "messages": [
                {
                    "role": "system",
                    "content": context["system_prompt"]
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # Add knowledge context if available
        if context.get("knowledge_context"):
            knowledge_text = "\n".join([
                f"Source: {result.get('honey_jar_name', 'Knowledge Base')}\n{result.get('content', '')}"
                for result in context["knowledge_context"]
            ])
            ai_payload["messages"].append({
                "role": "system",
                "content": f"Relevant knowledge:\n{knowledge_text}"
            })
        
        # Add user message
        ai_payload["messages"].append({
            "role": "user",
            "content": context["user_message"]
        })
        
        # Call External AI service
        response = requests.post(
            f"{EXTERNAL_AI_URL}/v1/chat/completions",
            json=ai_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        # Fallback to chatbot service
        logger.warning(f"External AI failed ({response.status_code}), trying chatbot service")
        
        chatbot_payload = {
            "message": context["user_message"],
            "user_id": "public-bot",
            "session_id": context["conversation_id"],
            "context": {
                "system_prompt": context["system_prompt"],
                "knowledge": context.get("knowledge_context", [])
            }
        }
        
        chatbot_response = requests.post(
            f"{CHATBOT_URL}/chat",
            json=chatbot_payload,
            timeout=30
        )
        
        if chatbot_response.status_code == 200:
            result = chatbot_response.json()
            return result.get("response", "I'm sorry, I couldn't generate a response.")
        
        # Final fallback
        return "I'm sorry, I'm temporarily unavailable. Please try again later."
        
    except Exception as e:
        logger.error(f"Error calling AI service: {e}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again later."

def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    # Simple estimation: ~4 characters per token for English text
    return max(1, len(text) // 4)

# Admin endpoints (for managing bots - should be protected by STING auth)
@app.get("/api/admin/public-bots")
async def admin_list_bots(db = Depends(get_db)):
    """List all bots for admin interface"""
    # TODO: Add STING authentication check
    try:
        manager = PublicBotManager(db)
        bots = manager.list_bots(enabled_only=False)
        return [bot.to_dict() for bot in bots]
    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(status_code=500, detail="Failed to list bots")

@app.post("/api/admin/public-bots")
async def admin_create_bot(
    bot_data: dict,
    db = Depends(get_db)
):
    """Create a new public bot"""
    # TODO: Add STING authentication check
    try:
        manager = PublicBotManager(db)
        bot = manager.create_bot(**bot_data)
        return bot.to_dict()
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise HTTPException(status_code=500, detail="Failed to create bot")

# Initialize demo bot on startup
@app.on_event("startup")
async def startup_event():
    """Initialize demo data and configurations"""
    try:
        if SessionLocal:
            db = SessionLocal()
            try:
                manager = PublicBotManager(db)
                demo_bot = manager.create_demo_bot()
                logger.info(f"Demo bot ready: {demo_bot.display_name}")
            finally:
                db.close()
        else:
            logger.warning("Database not available - skipping demo bot creation")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=PUBLIC_BEE_HOST, port=PUBLIC_BEE_PORT)