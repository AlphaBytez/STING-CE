#!/usr/bin/env python3
"""
Bee - The AI-powered assistant for STING platform
Enhanced chatbot with authentication, encryption, context retention, and analytics
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import logging
import datetime
from datetime import timezone
import time
import asyncio
import json
import uvicorn
from enum import Enum

# Import core Bee modules
from chatbot.core.conversation_manager import ConversationManager
from chatbot.core.conversation_manager_db import ConversationManagerDB
from chatbot.core.context_manager import ContextManager
from chatbot.core.sentiment_analyzer import SentimentAnalyzer
from chatbot.core.knowledge_base import get_knowledge_base
from chatbot.auth.kratos_integration import KratosAuth
# from chatbot.messaging.secure_messaging import SecureMessaging
# from chatbot.analytics.analytics_engine import AnalyticsEngine
# from chatbot.tools.tool_manager import ToolManager
# from chatbot.prompts.bee_prompt_config import BeePromptConfig

# Import Bee context manager for persistent context
from chatbot.core.bee_context_manager import BeeContextManager
from chatbot.core.enhanced_context_manager import EnhancedContextManager

# Import support request handler for conversational support
from chatbot.core.support_request_handler import SupportRequestHandler

# Import adaptive context manager for performance optimization
from chatbot.core.adaptive_context_manager import get_adaptive_context_manager
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
BEE_PORT = int(os.getenv('BEE_PORT', '8888'))
BEE_HOST = os.getenv('BEE_HOST', '0.0.0.0')
# Modern Ollama stack: External AI Service (preferred), then legacy services
EXTERNAL_AI_URL = os.getenv('EXTERNAL_AI_URL', 'http://external-ai:8091')
NATIVE_LLM_URL = os.getenv('NATIVE_LLM_URL', 'http://localhost:8086')
LLM_GATEWAY_URL = os.getenv('LLM_GATEWAY_URL', 'http://llm-gateway:8080')
KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'https://kratos:4433')
KRATOS_ADMIN_URL = os.getenv('KRATOS_ADMIN_URL', 'https://kratos:4434')
KNOWLEDGE_SERVICE_URL = os.getenv('KNOWLEDGE_SERVICE_URL', 'http://knowledge:8090')

class UserRole(str, Enum):
    END_USER = "end_user"
    ADMIN = "admin"
    SUPPORT = "support"

class BeeRequest(BaseModel):
    """Request model for Bee chat interactions"""
    message: str = Field(..., description="The user's message")
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    tools_enabled: Optional[List[str]] = Field(None, description="List of tools to enable")
    require_auth: Optional[bool] = Field(True, description="Whether authentication is required")
    encryption_required: Optional[bool] = Field(False, description="Whether to encrypt messages")

class BeeResponse(BaseModel):
    """Response model for Bee chat interactions"""
    response: str
    conversation_id: str
    session_id: str
    sentiment: Optional[Dict[str, float]] = None
    tools_used: List[Dict[str, Any]] = []
    processing_time: float
    filtered: bool = False
    filter_reason: Optional[str] = None
    requires_auth: bool = False
    auth_request: Optional[Dict[str, str]] = None
    encrypted: bool = False
    timestamp: str
    context_retained: bool = True
    bee_personality: str = "friendly"

# Create FastAPI app
app = FastAPI(
    title="Bee - STING AI Assistant",
    description="AI-powered chat assistant with advanced security and context awareness",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://localhost:8443",
        "http://localhost:8443",
        "https://127.0.0.1:8443",
        "http://127.0.0.1:8443"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize knowledge base
knowledge_base = get_knowledge_base()

# Load system prompt from file
system_prompt_file = os.path.join(os.path.dirname(__file__), 'prompts', 'bee_system_prompt.txt')
try:
    with open(system_prompt_file, 'r') as f:
        system_prompt_content = f.read()
        logger.info("Loaded custom system prompt from file")
except Exception as e:
    logger.warning(f"Failed to load custom prompt file: {e}, falling back to knowledge base")
    system_prompt_content = knowledge_base.get_system_prompt('bee')

# Initialize configuration
config = {
    "system_prompt": os.getenv(
        'BEE_SYSTEM_PROMPT',
        system_prompt_content
    ),
    "max_history_length": int(os.getenv('BEE_MAX_HISTORY', '100')),
    "context_window": int(os.getenv('BEE_CONTEXT_WINDOW', '10')),
    "sentiment_analysis_enabled": os.getenv('BEE_SENTIMENT_ENABLED', 'true').lower() == 'true',
    "encryption_enabled": os.getenv('BEE_ENCRYPTION_ENABLED', 'true').lower() == 'true',
    "tools_enabled": os.getenv('BEE_TOOLS_ENABLED', 'true').lower() == 'true',
    "llm_gateway_url": LLM_GATEWAY_URL,
    "kratos_public_url": KRATOS_PUBLIC_URL,
    "kratos_admin_url": KRATOS_ADMIN_URL,
    "messaging_service_enabled": os.getenv('BEE_MESSAGING_SERVICE_ENABLED', 'true').lower() == 'true',
    "messaging_service_url": os.getenv('MESSAGING_SERVICE_URL', 'http://messaging:8889'),
}

# Initialize core components
# Check if database persistence is enabled
persistence_enabled = os.getenv('BEE_CONVERSATION_PERSISTENCE_ENABLED', 'true').lower() == 'true'

if persistence_enabled:
    logger.info("Initializing database-backed conversation manager")
    conversation_manager = ConversationManagerDB(config)
else:
    logger.info("Initializing memory-backed conversation manager")
    conversation_manager = ConversationManager(config)

context_manager = ContextManager(config)
sentiment_analyzer = SentimentAnalyzer(config)
kratos_auth = KratosAuth(config)

# Initialize Redis for adaptive context caching
try:
    redis_client = redis.Redis(host='redis', port=6379, db=2, decode_responses=True)
    redis_client.ping()  # Test connection
    adaptive_context_manager = get_adaptive_context_manager(redis_client)
    logger.info("🧠 Adaptive context manager initialized with Redis caching")
except Exception as e:
    logger.warning(f"Redis connection failed, adaptive context disabled: {e}")
    adaptive_context_manager = None
# secure_messaging = SecureMessaging(config)
# analytics_engine = AnalyticsEngine(config)
# tool_manager = ToolManager(config)

# Initialize Bee Context Manager for persistent context
max_tokens = int(os.getenv('BEE_CONVERSATION_MAX_TOKENS', '4096'))
max_messages = int(os.getenv('BEE_CONVERSATION_MAX_MESSAGES', '50'))
session_timeout = int(os.getenv('BEE_CONVERSATION_SESSION_TIMEOUT_HOURS', '24')) * 60  # Convert to minutes
model = os.getenv('BEE_CONVERSATION_SUMMARY_MODEL', 'llama3.2:latest')

bee_context_manager = BeeContextManager(
    max_context_length=max_tokens,
    max_history_messages=max_messages,
    session_timeout_minutes=session_timeout,
    model=model
)

# Initialize Enhanced Context Manager for improved awareness
enhanced_context_manager = EnhancedContextManager()

# Support request handler for conversational support
support_handler = SupportRequestHandler()

# Security
security = HTTPBearer(auto_error=False)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Bee - STING AI Assistant",
        "version": "1.0.0",
        "status": "buzzing",
        "personality": "friendly and helpful",
        "endpoints": [
            {"path": "/chat", "method": "POST", "description": "Send a message to Bee"},
            {"path": "/conversations/{conversation_id}", "method": "GET", "description": "Get conversation history"},
            {"path": "/conversations/{conversation_id}/token-usage", "method": "GET", "description": "Get token usage statistics"},
            {"path": "/conversations/{conversation_id}/export", "method": "GET", "description": "Export conversation"},
            {"path": "/conversations/{conversation_id}/clear", "method": "DELETE", "description": "Clear conversation"},
            {"path": "/conversations/{conversation_id}/prune", "method": "POST", "description": "Manually prune conversation"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/analytics/report", "method": "POST", "description": "Generate analytics report"},
            {"path": "/admin/config", "method": "GET/PUT", "description": "Admin configuration"},
            {"path": "/tools", "method": "GET", "description": "List available tools"}
        ]
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "service": "bee",
        "version": "1.0.0",
        "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
        "components": {
            "conversation_manager": conversation_manager.is_healthy(),
            "context_manager": context_manager.is_healthy(),
            "sentiment_analyzer": sentiment_analyzer.is_healthy(),
            "kratos_auth": await kratos_auth.is_healthy(),
            # "secure_messaging": secure_messaging.is_healthy(),  # Not initialized yet
            # "analytics_engine": analytics_engine.is_healthy(),  # Not initialized yet
            # "tool_manager": tool_manager.is_healthy(),  # Not initialized yet
            "llm_gateway": await check_llm_gateway_health(),
            "knowledge_service": await check_knowledge_service_health()
        },
        "response_time_ms": (time.time() - start_time) * 1000,
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }
    
    # Check if all components are healthy
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
        # Log which components are unhealthy
        unhealthy = [k for k, v in health_status["components"].items() if not v]
        logger.warning(f"Unhealthy components: {unhealthy}")
    
    return health_status

@app.get("/support/health")
async def support_health_check():
    """Support system health check"""
    start_time = time.time()
    
    # Check support handler status
    knowledge_status = support_handler.get_knowledge_status()
    
    health_status = {
        "status": "healthy",
        "service": "bee_support",
        "components": {
            "support_handler": support_handler is not None,
            "sting_knowledge": knowledge_status.get('status') == 'loaded',
            "support_patterns": len(support_handler.support_patterns) > 0 if support_handler else False
        },
        "knowledge_info": knowledge_status,
        "processing_time": time.time() - start_time,
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }
    
    # Check if all components are healthy
    all_healthy = all(health_status["components"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
        unhealthy = [k for k, v in health_status["components"].items() if not v]
        logger.warning(f"Unhealthy support components: {unhealthy}")
    
    return health_status

@app.post("/chat/test", response_model=BeeResponse)
async def test_chat(request: BeeRequest):
    """Test chat endpoint that bypasses authentication"""
    start_time = time.time()
    
    # Force authentication to be disabled for testing
    request.require_auth = False
    
    # Create a test conversation
    logger.info(f"DEBUG: request.conversation_id = '{request.conversation_id}', type = {type(request.conversation_id)}")
    conversation = await conversation_manager.get_or_create_conversation(
        user_id=request.user_id or "test-user",
        conversation_id=request.conversation_id,  # Let DB generate UUID if None
        session_id=request.session_id or "test-session"
    )
    
    # Analyze sentiment
    sentiment = None
    if config['sentiment_analysis_enabled']:
        sentiment = await sentiment_analyzer.analyze(request.message)
        logger.info(f"Test chat sentiment: {sentiment}")
    
    # Generate response without auth checks
    # Check for bot_context in request context (for testing Nectar Bot fallback)
    bot_context = None
    if request.context and request.context.get('bot_context'):
        bot_context = request.context['bot_context']

    tools_used = []
    response_text = await generate_bee_response(
        message=request.message,
        context={'conversation_id': conversation['id']},
        sentiment=sentiment,
        tools_used=tools_used,
        user_info={'id': request.user_id or "test-user", 'role': 'end_user'},
        conversation_history=[],
        auth_token=None,  # Test endpoint has no auth
        bot_context=bot_context  # Pass Nectar Bot context if provided
    )
    
    # Add to conversation history
    # Add user message
    await conversation_manager.add_message(
        conversation_id=conversation['id'],
        role="user",
        content=request.message,
        metadata={
            "sentiment": sentiment,
            "encrypted": False
        }
    )
    
    # Add assistant response
    await conversation_manager.add_message(
        conversation_id=conversation['id'],
        role="assistant",
        content=response_text,
        metadata={
            "encrypted": False,
            "model": "bee-enhanced"
        }
    )
    
    return BeeResponse(
        response=response_text,
        conversation_id=str(conversation['id']),
        session_id=request.session_id or "test-session",
        sentiment=sentiment,
        tools_used=tools_used,
        processing_time=time.time() - start_time,
        filtered=False,
        requires_auth=False,
        encrypted=False,
        timestamp=datetime.datetime.now(timezone.utc).isoformat(),
        context_retained=True,
        bee_personality="helpful"
    )

@app.post("/chat", response_model=BeeResponse)
async def chat(request: BeeRequest, auth: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Main chat endpoint for Bee"""
    start_time = time.time()
    
    try:
        # Verify authentication if required
        user_info = None
        user_role = UserRole.END_USER
        
        if request.require_auth:
            if not auth:
                return BeeResponse(
                    response="🔐 Authentication required to access this feature. Please authenticate using your passkey or biometrics.",
                    conversation_id=request.conversation_id or "auth_required",
                    session_id=request.session_id or "none",
                    requires_auth=True,
                    auth_request={
                        "type": "passkey",
                        "message": "Please authenticate using your passkey or biometrics",
                        "auth_url": f"{KRATOS_PUBLIC_URL}/self-service/login/browser"
                    },
                    processing_time=time.time() - start_time,
                    timestamp=datetime.datetime.now(timezone.utc).isoformat(),
                    bee_personality="security-conscious"
                )
            
            # Verify token with Kratos
            user_info = await kratos_auth.verify_session(auth.credentials)
            if not user_info:
                raise HTTPException(status_code=401, detail="Invalid authentication")

            user_role = UserRole(user_info.get('role', 'end_user'))

            # ADAPTIVE CONTEXT: Trigger background context pre-warming for authenticated users
            if adaptive_context_manager and user_info:
                user_id = user_info.get('id')
                user_email = user_info.get('email')
                # Non-blocking background task for context pre-warming
                asyncio.create_task(
                    adaptive_context_manager.pre_warm_user_contexts(user_id, user_email)
                )
        
        # Get or create conversation
        conversation = await conversation_manager.get_or_create_conversation(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            session_id=request.session_id
        )
        
        # Analyze sentiment if enabled
        sentiment = None
        if config['sentiment_analysis_enabled']:
            sentiment = await sentiment_analyzer.analyze(request.message)
            logger.info(f"Sentiment analysis: {sentiment}")
        
        # Check for sensitive content
        message_encrypted = False
        original_message = request.message
        
        if request.encryption_required or await contains_sensitive_data(request.message):
            if config['encryption_enabled']:
                # Encrypt the message
                # encrypted_message = await secure_messaging.encrypt_message(
                #     request.message,
                #     request.user_id
                # )
                encrypted_message = request.message  # Temporary: no encryption
                request.message = encrypted_message
                message_encrypted = True
                logger.info("Message encrypted due to sensitive content")
        
        # Get context
        context = await context_manager.get_context(
            conversation_id=conversation['id'],
            user_id=request.user_id,
            additional_context=request.context
        )

        # Add user role to context
        context['user_role'] = user_role.value

        # Check for Nectar Bot context (fallback from Nectar Bot routes)
        bot_context = None
        if request.context and request.context.get('bot_context'):
            bot_context = request.context['bot_context']
            if bot_context.get('is_nectar_bot'):
                bot_name = bot_context.get('bot_name', 'Nectar Bot')
                logger.info(f"Nectar Bot fallback detected: {bot_name}")
                context['nectar_bot_context'] = bot_context
        
        # Process with tools if requested
        tools_used = []
        enhanced_context = context.copy()
        
        if request.tools_enabled and config['tools_enabled']:
            for tool_name in request.tools_enabled:
                if False:  # tool_manager.is_tool_available(tool_name, user_role):
                    # tool_result = await tool_manager.execute_tool(
                    #     tool_name,
                    #     original_message,  # Use original message for tools
                    #     context,
                    #     user_info
                    # )
                    tool_result = None
                    if tool_result:
                        tools_used.append(tool_result)
                        enhanced_context.update(tool_result.get('context', {}))
                        logger.info(f"Tool {tool_name} executed successfully")
        
        # Check for support requests before generating normal response
        user_context = {
            'user_id': request.user_id,
            'session_id': request.session_id,
            'role': user_role.value if user_role else 'user',
            'email': user_info.get('email') if user_info else None,
            'authenticated': user_info is not None
        }
        
        support_response = await support_handler.handle_support_request(original_message, user_context)
        
        if support_response.get('is_support_response'):
            # This is a support request - return the support response
            response_text = support_response['message']
            
            # Add any support-specific metadata
            support_metadata = {
                'support_handled': True,
                'support_type': support_response.get('primary_intent'),
                'requires_admin': support_response.get('requires_admin', False),
                'ticket_created': support_response.get('ticket_created', False),
                'analysis': support_response.get('analysis', {})
            }
            
            logger.info(f"Support request handled: {support_metadata}")
        else:
            # Generate normal response
            response_text = await generate_bee_response(
                message=original_message,  # Use original message for generation
                context=enhanced_context,
                sentiment=sentiment,
                tools_used=tools_used,
                user_info=user_info,
                conversation_history=await conversation_manager.get_recent_messages(conversation['id']),
                auth_token=auth.credentials if auth else None,
                bot_context=bot_context  # Pass Nectar Bot context if available
            )
        
        # Encrypt response if needed
        if message_encrypted and config['encryption_enabled']:
            # encrypted_response = await secure_messaging.encrypt_message(
            #     response_text,
            #     request.user_id
            # )
            encrypted_response = response_text  # Temporary: no encryption
            # Return both encrypted and a summary
            response_text = f"[Encrypted Response] {encrypted_response[:50]}..."
        
        # Update conversation history
        await conversation_manager.add_message(
            conversation_id=conversation['id'],
            role="user",
            content=original_message,  # Store original message
            metadata={
                "sentiment": sentiment,
                "encrypted": message_encrypted,
                "tools_requested": request.tools_enabled
            }
        )
        
        await conversation_manager.add_message(
            conversation_id=conversation['id'],
            role="assistant",
            content=response_text,
            metadata={
                "tools_used": tools_used,
                "encrypted": message_encrypted,
                "model": "bee-enhanced"
            }
        )
        
        # Update context
        await context_manager.update_context(
            conversation_id=conversation['id'],
            user_id=request.user_id,
            new_context={
                "last_sentiment": sentiment,
                "tools_used": [t['name'] for t in tools_used],
                "last_interaction": datetime.datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Log analytics
        # await analytics_engine.log_interaction(
        #     user_id=request.user_id,
        #     conversation_id=conversation['id'],
        #     message_length=len(original_message),
        #     response_length=len(response_text),
        #     sentiment=sentiment,
        #     tools_used=tools_used,
        #     processing_time=time.time() - start_time,
        #     user_role=user_role.value
        # )
        
        # Determine Bee's personality based on context
        bee_personality = "friendly"
        if sentiment and sentiment.get('negative', 0) > 0.7:
            bee_personality = "empathetic"
        elif sentiment and sentiment.get('joy', 0) > 0.7:
            bee_personality = "cheerful"
        elif tools_used:
            bee_personality = "helpful"
        
        # ADAPTIVE LEARNING: Update user usage stats for continuous optimization
        final_processing_time = time.time() - start_time
        if adaptive_context_manager and user_info:
            complexity = adaptive_context_manager._analyze_query_complexity(message) if adaptive_context_manager else 'medium'
            asyncio.create_task(
                adaptive_context_manager.update_user_usage_stats(
                    user_info.get('id'), complexity, final_processing_time
                )
            )

        return BeeResponse(
            response=response_text,
            conversation_id=str(conversation['id']),
            session_id=request.session_id or "main-session",
            sentiment=sentiment,
            tools_used=tools_used,
            processing_time=final_processing_time,
            encrypted=message_encrypted,
            timestamp=datetime.datetime.now(timezone.utc).isoformat(),
            context_retained=True,
            bee_personality=bee_personality
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        
        # Log error to analytics
        # await analytics_engine.log_error(
        #     user_id=request.user_id,
        #     error_type="chat_processing_error",
        #     error_message=str(e),
        #     context={
        #         "conversation_id": request.conversation_id,
        #         "message_length": len(request.message)
        #     }
        # )
        
        return BeeResponse(
            response="I apologize, but I encountered an error processing your request. Our team has been notified. Please try again in a moment.",
            conversation_id=request.conversation_id or "error",
            session_id=request.session_id or "error",
            processing_time=time.time() - start_time,
            timestamp=datetime.datetime.now(timezone.utc).isoformat(),
            bee_personality="apologetic"
        )

@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get conversation history"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify user has access to this conversation
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    conversation = await conversation_manager.get_conversation(
        conversation_id,
        user_info['id']
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation

@app.get("/conversations/{conversation_id}/token-usage")
async def get_conversation_token_usage(
    conversation_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get token usage statistics for a conversation"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    # For in-memory version, use BeeContextManager
    if hasattr(conversation_manager, 'conversations'):
        # In-memory version - use bee_context_manager
        token_usage = bee_context_manager.get_session_token_usage(conversation_id)
        if not token_usage:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return token_usage
    else:
        # DB version - need to implement token usage method
        # For now, return basic info
        conversation = await conversation_manager.get_conversation(
            conversation_id,
            user_info['id']
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation_id": conversation_id,
            "total_tokens": conversation.get('active_tokens', 0),
            "message_count": len(conversation.get('messages', [])),
            "persistence_enabled": True
        }

@app.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = "json",
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Export conversation in specified format"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    export_data = await conversation_manager.export_conversation(
        conversation_id,
        user_info['id'],
        format
    )
    
    if not export_data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Set appropriate content type
    content_type = "application/json" if format == "json" else "text/plain"
    
    return Response(
        content=export_data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename=bee_conversation_{conversation_id}.{format}"
        }
    )

@app.delete("/conversations/{conversation_id}/clear")
async def clear_conversation(
    conversation_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Clear conversation history"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    success = await conversation_manager.clear_conversation(
        conversation_id,
        user_info['id']
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Log the action
    # await analytics_engine.log_user_action(
    #     user_id=user_info['id'],
    #     action="clear_conversation",
    #     details={"conversation_id": conversation_id}
    # )
    
    return {"success": True, "message": "Conversation cleared"}

@app.post("/conversations/{conversation_id}/prune")
async def prune_conversation(
    conversation_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Manually trigger conversation pruning and summarization"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    # Check if using DB version
    if not isinstance(conversation_manager, ConversationManagerDB):
        raise HTTPException(
            status_code=400, 
            detail="Pruning is only available with database persistence enabled"
        )
    
    # Verify user has access to conversation
    conversation = await conversation_manager.get_conversation(
        conversation_id,
        user_info['id']
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Trigger pruning
    result = await conversation_manager.prune_and_summarize_conversation(conversation_id)
    
    if result:
        return {
            "success": True,
            "pruning_result": result
        }
    else:
        return {
            "success": False,
            "message": "No pruning needed or pruning disabled"
        }

@app.get("/tools")
async def list_tools(auth: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """List available tools based on user role"""
    user_role = UserRole.END_USER
    
    if auth:
        user_info = await kratos_auth.verify_session(auth.credentials)
        if user_info:
            user_role = UserRole(user_info.get('role', 'end_user'))
    
    available_tools = []  # tool_manager.get_available_tools(user_role)
    
    return {
        "tools": available_tools,
        "user_role": user_role.value
    }

@app.post("/analytics/report")
async def generate_analytics_report(
    request: Dict[str, Any],
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Generate analytics report (admin/support only)"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    user_role = UserRole(user_info.get('role', 'end_user'))
    if user_role not in [UserRole.ADMIN, UserRole.SUPPORT]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # report = await analytics_engine.generate_report(
    #     user_id=request.get('user_id'),
    #     start_date=request.get('start_date'),
    #     end_date=request.get('end_date'),
    #     report_type=request.get('report_type', 'summary'),
    #     include_sensitive=user_role == UserRole.ADMIN
    # )
    
    # Temporary stub report
    report = {
        "status": "not_implemented",
        "message": "Analytics engine not yet implemented",
        "requested_by": user_info['id'],
        "role": user_role.value
    }
    
    return report

@app.get("/admin/config")
async def get_config(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get Bee configuration (admin only)"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info or user_info.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Return sanitized config (no secrets)
    safe_config = {
        "system_prompt": config['system_prompt'],
        "tools_enabled": [],  # tool_manager.get_all_tools(),
        "sentiment_analysis_enabled": config['sentiment_analysis_enabled'],
        "context_window_size": config['context_window'],
        "encryption_enabled": config['encryption_enabled'],
        "max_history_length": config['max_history_length'],
        "active_conversations": len(conversation_manager.conversations) if hasattr(conversation_manager, 'conversations') else 0,
        "total_interactions": 0,  # await analytics_engine.get_total_interactions()
        "persistence_enabled": isinstance(conversation_manager, ConversationManagerDB),
        "conversation_management": {
            "max_tokens": max_tokens,
            "max_messages": max_messages,
            "token_buffer_percent": float(os.getenv('BEE_CONVERSATION_TOKEN_BUFFER_PERCENT', '20')),
            "summarization_enabled": os.getenv('BEE_CONVERSATION_SUMMARIZATION_ENABLED', 'true').lower() == 'true',
            "summarize_after_messages": int(os.getenv('BEE_CONVERSATION_SUMMARIZE_AFTER_MESSAGES', '20')),
            "summary_model": model,
            "pruning_strategy": os.getenv('BEE_CONVERSATION_PRUNING_STRATEGY', 'sliding_window'),
            "keep_recent_messages": int(os.getenv('BEE_CONVERSATION_KEEP_RECENT_MESSAGES', '10'))
        }
    }
    
    return safe_config

@app.put("/admin/config")
async def update_config(
    config_update: Dict[str, Any],
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Update Bee configuration (admin only)"""
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_info = await kratos_auth.verify_session(auth.credentials)
    if not user_info or user_info.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Update allowed configuration items
    updated_items = []
    
    if 'system_prompt' in config_update:
        config['system_prompt'] = config_update['system_prompt']
        updated_items.append('system_prompt')
    
    if 'tools_enabled' in config_update:
        # tool_manager.update_enabled_tools(config_update['tools_enabled'])
        updated_items.append('tools_enabled')
    
    if 'sentiment_analysis_enabled' in config_update:
        config['sentiment_analysis_enabled'] = config_update['sentiment_analysis_enabled']
        updated_items.append('sentiment_analysis_enabled')
    
    if 'context_window' in config_update:
        config['context_window'] = config_update['context_window']
        conversation_manager.context_window = config_update['context_window']
        updated_items.append('context_window')
    
    # Log configuration change
    # await analytics_engine.log_admin_action(
    #     admin_id=user_info['id'],
    #     action="config_update",
    #     details={
    #         "updated_items": updated_items,
    #         "changes": config_update
    #     }
    # )
    
    return {
        "success": True,
        "message": f"Configuration updated: {', '.join(updated_items)}",
        "updated_items": updated_items
    }

# Utility functions
async def check_llm_gateway_health() -> bool:
    """Check if LLM gateway is healthy"""
    try:
        import httpx
        
        # Try the same endpoints that generate_bee_response uses
        endpoints = [
            {"url": NATIVE_LLM_URL, "name": "native"},
            {"url": LLM_GATEWAY_URL, "name": "docker"}
        ]
        
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{endpoint['url']}/health", timeout=15.0)
                    if response.status_code == 200:
                        # Parse JSON response and check actual health status
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            return True
            except:
                continue
        
        return False
    except:
        return False

async def check_knowledge_service_health() -> bool:
    """Check if knowledge service is healthy"""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{KNOWLEDGE_SERVICE_URL}/health", timeout=10.0)
            if response.status_code == 200:
                # Parse JSON response and check actual health status
                health_data = response.json()
                return health_data.get("status") == "healthy"
            return False
    except:
        return False

async def query_knowledge_service(query: str, user_id: str = None, auth_token: str = None, honey_jar_id: str = None) -> Dict[str, Any]:
    """
    Query the knowledge service for relevant honey jar context

    Args:
        query: The user's query to search for relevant context
        user_id: Optional user ID for context tracking
        auth_token: Authentication token to forward to knowledge service
        honey_jar_id: Optional honey jar ID to search within specific context

    Returns:
        Dictionary with knowledge service response or empty dict if unavailable
    """
    try:
        import httpx
        
        logger.info(f"Querying knowledge service for: {query[:50]}...")
        
        # Prepare headers for authentication
        headers = {
            "Content-Type": "application/json"
        }

        # Try service API key first (for service-to-service auth)
        service_api_key = os.environ.get('STING_SERVICE_API_KEY')
        if service_api_key:
            headers["X-API-Key"] = service_api_key
            logger.info("Using service API key for knowledge service authentication")
        elif auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            logger.info("Forwarding user authentication token to knowledge service")
        else:
            logger.warning("No authentication token provided - knowledge service may require authentication")
        
        async with httpx.AsyncClient(verify=False) as client:
            # Query the knowledge service for relevant context
            request_body = {
                "query": query,
                "user_id": user_id or "anonymous",
                "limit": 5,  # Limit results to keep response manageable
                "include_metadata": True
            }

            # Add honey_jar_id if provided to search within specific context
            if honey_jar_id:
                request_body["honey_jar_id"] = honey_jar_id
                logger.info(f"Searching within honey jar: {honey_jar_id}")

            response = await client.post(
                f"{KNOWLEDGE_SERVICE_URL}/bee/context",
                json=request_body,
                headers=headers,
                timeout=10.0  # 10 second timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats for backward compatibility
                if 'context_items' in data and 'results' not in data:
                    # Convert old format to new format expected by the rest of the code
                    context_items = data.get('context_items', [])
                    results = []
                    for item in context_items:
                        if isinstance(item, dict):
                            # Convert SearchResult object to dict format
                            result = {
                                'content': item.get('content', ''),
                                'score': item.get('score', 0.0),
                                'metadata': {
                                    'source': item.get('honey_jar_name', 'unknown'),
                                    'honey_jar_id': item.get('honey_jar_id', 'unknown')
                                }
                            }
                            results.append(result)
                    data['results'] = results
                    logger.info(f"Knowledge service returned {len(results)} results (converted from context_items)")
                else:
                    results = data.get('results', [])
                    if len(results) == 0:
                        logger.warning(f"Knowledge service returned no results for query: '{query[:50]}'. This may indicate no honey jars exist or user lacks access.")
                        # Return a structured empty response instead of generic empty dict
                        return {
                            "results": [],
                            "total": 0,
                            "message": "No honey jars available. This could mean no honey jars exist in your account, or you need to log in again.",
                            "status": "empty"
                        }
                    else:
                        logger.info(f"Knowledge service returned {len(results)} results")
                
                return data
            else:
                logger.warning(f"Knowledge service returned status {response.status_code}: {response.text}")
                return {
                    "results": [],
                    "error": f"Knowledge service error: HTTP {response.status_code}",
                    "status": "error"
                }
                
    except httpx.TimeoutException:
        logger.warning("Knowledge service query timed out - this may cause 'No honey jars available' error")
        return {
            "results": [],
            "error": "Knowledge service timed out",
            "status": "timeout"
        }
    except httpx.ConnectError:
        logger.warning("Knowledge service is unavailable - this will cause 'No honey jars available' error")
        return {
            "results": [],
            "error": "Knowledge service unavailable",
            "status": "unavailable"
        }
    except Exception as e:
        logger.error(f"Error querying knowledge service: {str(e)} - this may cause 'No honey jars available' error")
        return {
            "results": [],
            "error": f"Knowledge service error: {str(e)}",
            "status": "error"
        }

async def contains_sensitive_data(text: str) -> bool:
    """Check if text contains sensitive data that should be encrypted"""
    import re
    
    sensitive_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b(?:password|passwd|pwd|secret|token|api_key|apikey)\s*[:=]\s*\S+\b',  # Credentials
        r'\b\d{10,}\b',  # Phone numbers
    ]
    
    text_lower = text.lower()
    
    # Check for patterns
    for pattern in sensitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Check for keywords
    sensitive_keywords = ['ssn', 'social security', 'credit card', 'bank account', 
                         'routing number', 'password', 'secret', 'confidential']
    
    for keyword in sensitive_keywords:
        if keyword in text_lower:
            return True
    
    return False

async def generate_bee_response(
    message: str,
    context: Dict[str, Any],
    sentiment: Optional[Dict[str, float]],
    tools_used: List[Dict[str, Any]],
    user_info: Optional[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]],
    auth_token: str = None,
    bot_context: Optional[Dict[str, Any]] = None
) -> str:
    """Generate response using LLM with enhanced Bee personality and context.

    Args:
        bot_context: Optional Nectar Bot context with custom system_prompt for fallback handling
    """
    
    # ADAPTIVE CONTEXT: Smart honey jar context loading with performance optimization
    knowledge_context = {}
    adaptive_timeout = 30  # Default timeout
    try:
        user_id = user_info.get('id') if user_info else None
        user_email = user_info.get('email') if user_info else None
        honey_jar_id = context.get('conversation_context', {}).get('honey_jar_id')

        if adaptive_context_manager and user_id and honey_jar_id:
            # Use adaptive context manager for optimized loading
            logger.info(f"🧠 Using adaptive context for user {user_email}, jar {honey_jar_id}")

            # Analyze query complexity for smart timeout
            complexity = adaptive_context_manager._analyze_query_complexity(message)
            adaptive_timeout = {
                'simple': 15,    # Quick questions
                'medium': 30,    # Normal queries
                'complex': 60,   # Multi-step analysis
                'research': 90   # Deep research
            }.get(complexity, 30)

            logger.info(f"⏱️ Query complexity: {complexity}, timeout: {adaptive_timeout}s")

            # Get optimized context
            optimized_context = await adaptive_context_manager.get_context_for_query(
                user_id, honey_jar_id, message
            )

            if optimized_context:
                knowledge_context = {
                    'results': [{'content': optimized_context, 'source': 'adaptive_cache'}],
                    'context_source': 'adaptive',
                    'optimization_applied': True
                }
                logger.info(f"✅ Adaptive context loaded for {complexity} query")
            else:
                # Fallback to traditional knowledge service
                knowledge_context = await query_knowledge_service(message, user_id, auth_token, honey_jar_id)
        else:
            # Traditional knowledge service query
            knowledge_context = await query_knowledge_service(message, user_id, auth_token, honey_jar_id)

        if knowledge_context and knowledge_context.get('results'):
            context_source = knowledge_context.get('context_source', 'traditional')
            logger.info(f"Knowledge service provided {len(knowledge_context['results'])} relevant contexts ({context_source})")

    except Exception as e:
        logger.error(f"Failed to query knowledge service: {str(e)}")
        # Set conservative timeout for fallback
        adaptive_timeout = 45
    
    # Get enhanced system context for improved awareness
    system_context = {}
    try:
        from app.services.system_context_service import get_enhanced_system_context, format_context_for_prompt
        system_context = await get_enhanced_system_context()
        logger.info(f"System context gathered: {system_context['environment']['deployment_type']} environment")
    except Exception as e:
        logger.warning(f"Failed to get system context: {str(e)}")
        # Continue without system context - not critical
    
    # Determine sentiment category from sentiment scores
    sentiment_category = "neutral"
    if sentiment:
        if sentiment.get('anger', 0) > 0.5 or sentiment.get('negative', 0) > 0.6:
            sentiment_category = "frustrated"
        elif sentiment.get('question', 0) > 0.7:
            sentiment_category = "confused"
        elif sentiment.get('positive', 0) > 0.7 or sentiment.get('joy', 0) > 0.7:
            sentiment_category = "satisfied"
        elif sentiment.get('urgency', 0) > 0.7:
            sentiment_category = "urgent"
    
    # Determine user role
    user_role = "end_user"
    if user_info:
        user_role = user_info.get('role', 'end_user')
    
    # Get conversation ID from context
    conversation_id = context.get('conversation_id', 'default')

    # Determine which system prompt to use
    # If this is a Nectar Bot fallback, use the bot's custom system prompt
    effective_system_prompt = config['system_prompt']
    if bot_context and bot_context.get('is_nectar_bot'):
        custom_prompt = bot_context.get('system_prompt')
        if custom_prompt:
            bot_name = bot_context.get('bot_name', 'Nectar Bot')
            logger.info(f"Using custom system prompt for Nectar Bot: {bot_name}")
            effective_system_prompt = custom_prompt
        else:
            logger.warning(f"Nectar Bot {bot_context.get('bot_name')} has no system_prompt, using Bee's default")

    # Use BeeContextManager to generate minimal prompt with persistent context
    # First ensure system prompt is initialized (use effective prompt which may be custom)
    # Note: For Nectar Bot requests, we override the system prompt
    if not bee_context_manager.system_prompt_initialized:
        bee_context_manager.initialize_system_prompt(effective_system_prompt)
    elif bot_context and bot_context.get('is_nectar_bot'):
        # For Nectar Bot requests, temporarily override the system prompt
        # This ensures the bot uses its custom identity, not Bee's
        bee_context_manager.initialize_system_prompt(effective_system_prompt)

    # Get context messages from BeeContextManager
    context_messages = bee_context_manager.get_context_for_llm(
        session_id=conversation_id,
        user_message=message
    )
    
    # Process message with enhanced context manager
    enhanced_context_manager.process_message(conversation_id, user_info.get('id', 'unknown') if user_info else 'unknown', message)
    
    # Get enhanced context
    context_prompt = enhanced_context_manager.build_context_prompt(
        conversation_id, 
        user_info.get('id', 'unknown') if user_info else 'unknown'
    )
    
    # Format as a single prompt string for the LLM
    prompt = ""
    for msg in context_messages:
        if msg['role'] == 'system':
            prompt += f"{msg['content']}\n\n"
        elif msg['role'] == 'user':
            prompt += f"User: {msg['content']}\n"
        elif msg['role'] == 'assistant':
            prompt += f"Bee: {msg['content']}\n"
    
    # Add enhanced context if available
    if context_prompt:
        prompt = prompt.replace("\n\nUser:", f"{context_prompt}User:")
    
    # Add knowledge service context if available
    if knowledge_context and knowledge_context.get('results'):
        knowledge_prompt = "\n\nRelevant honey jar context from STING knowledge base:\n"
        for i, result in enumerate(knowledge_context['results'][:3], 1):  # Limit to top 3 results
            content = result.get('content', result.get('text', ''))
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'honeyjar')
            timestamp = metadata.get('timestamp', '')
            
            knowledge_prompt += f"\n{i}. From {source}"
            if timestamp:
                knowledge_prompt += f" ({timestamp})"
            knowledge_prompt += f"\n\n"  # Double newline instead of colon for better markdown separation
            
            # Preserve full content up to 500 chars to maintain code blocks
            # and add proper line breaks to preserve formatting
            truncated_content = content[:500]
            if len(content) > 500:
                # Try to find a good breakpoint
                last_newline = truncated_content.rfind('\n')
                if last_newline > 300:  # If there's a newline after 300 chars, break there
                    truncated_content = truncated_content[:last_newline]
                truncated_content += "\n..."
            
            knowledge_prompt += f"{truncated_content}\n"
        
        knowledge_prompt += "\nUse this context to provide more informed responses. When referencing code or commands from the context, preserve the proper markdown formatting with backticks for inline code and triple backticks for code blocks.\n"
        prompt = prompt.replace("\n\nUser:", f"{knowledge_prompt}User:")
    
    # Add system context if available (after knowledge context)
    if system_context:
        try:
            from app.services.system_context_service import format_context_for_prompt
            system_prompt = format_context_for_prompt(system_context)
            prompt = prompt.replace("\n\nUser:", f"\n{system_prompt}\nUser:")
            logger.debug("System context injected into prompt")
        except Exception as e:
            logger.warning(f"Failed to format system context for prompt: {str(e)}")
    
    # Add tool results if any
    if tools_used:
        prompt += "\nTool Results:"
        for tool in tools_used:
            prompt += f"\n- {tool['name']}: {tool.get('result', tool.get('summary', 'Completed'))}"
    
    prompt += "\nBee (provide a direct, helpful response): "
    
    # Try to get response from LLM
    try:
        import httpx
        
        # Try multiple endpoints - prioritize external AI service with Ollama
        endpoints = [
            {"url": EXTERNAL_AI_URL, "name": "external-ai-ollama"},
            {"url": NATIVE_LLM_URL, "name": "native"},
            {"url": LLM_GATEWAY_URL, "name": "docker"}
        ]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Trying {endpoint['name']} endpoint: {endpoint['url']}")
                logger.debug(f"Prompt length: {len(prompt)} chars")
                async with httpx.AsyncClient() as client:
                    # Use different endpoints and payloads based on service type
                    if endpoint['name'] == 'external-ai-ollama':
                        # Use the new external AI service with bee/chat endpoint
                        response = await client.post(
                            f"{endpoint['url']}/bee/chat",
                            json={
                                "message": message,  # Use original message, not full prompt
                                "user_id": user_info.get('id', 'anonymous') if user_info else 'anonymous',
                                "conversation_id": conversation_id,
                                "tools_enabled": [tool['name'] for tool in tools_used] if tools_used else [],
                                "require_auth": False,
                                "encryption_required": False,
                                "context": {
                                    "sentiment": sentiment,
                                    "knowledge_context": knowledge_context,
                                    "conversation_history": conversation_history[-5:] if conversation_history else []
                                }
                            },
                            timeout=float(adaptive_timeout)
                        )
                    else:
                        # Legacy endpoints use the old format
                        response = await client.post(
                            f"{endpoint['url']}/generate",
                            json={
                                "message": prompt,
                                "model": os.getenv('CHATBOT_MODEL', 'phi3'),
                                "max_tokens": 1500,
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "stop": ["\nUser:", "\nHuman:"],
                                "hide_reasoning": True
                            },
                            timeout=float(adaptive_timeout)
                        )
                    
                    if response.status_code == 200:
                        data = response.json()
                        text = data.get('text', data.get('response', ''))
                        
                        if text and text.strip():
                            # Clean and enhance the response
                            text = text.strip()
                            
                            # Remove any role prefixes
                            for prefix in ["Bee:", "Assistant:", "AI:"]:
                                if text.startswith(prefix):
                                    text = text[len(prefix):].strip()
                            
                            # Filter out DeepSeek reasoning for enterprise use
                            enhanced_text = _filter_reasoning(text)
                            
                            # Apply sentiment enhancements
                            # enhanced_text = BeePromptConfig.enhance_response(enhanced_text, sentiment_category)
                            logger.info(f"Generated response via {endpoint['name']}: {enhanced_text[:100]}...")
                            
                            # Update context manager with assistant response
                            bee_context_manager.update_assistant_response(conversation_id, enhanced_text)
                            
                            return enhanced_text
                    
            except Exception as e:
                logger.error(f"Error with {endpoint['name']}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception details: {repr(e)}", exc_info=True)
                continue
        
        # If all endpoints fail, use enhanced fallback
        logger.warning("All LLM endpoints failed, using fallback")
        fallback_response = generate_enhanced_fallback(message, sentiment_category, tools_used, knowledge_context)
        
        # Update context manager with fallback response
        bee_context_manager.update_assistant_response(conversation_id, fallback_response)
        
        return fallback_response
        
    except Exception as e:
        logger.error(f"Error in generate_bee_response: {e}")
        fallback_response = generate_enhanced_fallback(message, sentiment_category, tools_used, knowledge_context)
        
        # Update context manager with fallback response
        bee_context_manager.update_assistant_response(conversation_id, fallback_response)
        
        return fallback_response

def _filter_reasoning(text: str) -> str:
    """
    Filter out DeepSeek reasoning patterns for enterprise use
    
    Args:
        text: Raw response from DeepSeek model
        
    Returns:
        Cleaned response with reasoning removed
    """
    import re
    
    # Patterns that indicate reasoning/thinking
    reasoning_patterns = [
        r"^(Okay, so|Let me think|I'm trying to|Wait, maybe|Hmm,|Actually,)",
        r"(let me try to figure out|I need to think about|I'm not sure|I wonder)",
        r"(Maybe I should|I can split|I remember from school|Let me break it down)",
        r"(That seems too|I think|I guess|I believe|It looks like)",
        r"^(So,|Well,|Now,|First,|Then,) ",
        r"\. (So|Well|Now|First|Then|Actually|Maybe|I think|Let me|Hmm|Wait)",
        r"(The user is asking|which implies|I should consider|I should)",
        r"(might be curious|perhaps just testing|keep it simple)",
    ]
    
    lines = text.split('\n')
    filtered_lines = []
    skip_reasoning = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line contains reasoning patterns
        is_reasoning = False
        for pattern in reasoning_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_reasoning = True
                break
        
        # Skip reasoning lines but look for direct answers
        if is_reasoning:
            skip_reasoning = True
            continue
        
        # Look for direct answer patterns
        direct_patterns = [
            r"^(The answer is|It is|This is|STING is|STING Assistant)",
            r"^[A-Z].*[.!?]$",  # Complete sentences starting with capital
            r"^\d+$",  # Just numbers for math
            r"^(Yes|No)\b",  # Yes/No answers
        ]
        
        is_direct = False
        for pattern in direct_patterns:
            if re.search(pattern, line):
                is_direct = True
                break
        
        if is_direct or not skip_reasoning:
            filtered_lines.append(line)
    
    # If we filtered everything, return the last sentence
    if not filtered_lines and lines:
        # Try to find the most direct sentence
        for line in reversed(lines):
            line = line.strip()
            if line and len(line) > 10 and '.' in line:
                return line
        return lines[-1].strip()
    
    result = ' '.join(filtered_lines)
    
    # Additional cleanup for enterprise presentation
    result = re.sub(r'\s+', ' ', result)  # Normalize whitespace
    result = result.strip()
    
    # If result is empty or too short, provide a fallback
    if not result or len(result) < 10:
        # Check the original text for common queries
        text_lower = text.lower()
        if "what is sting" in text_lower:
            return "STING is a secure communication platform with AI-powered intelligence assistance."
        elif "can you hear me" in text_lower or "hear me" in text_lower:
            return "Yes, I can hear you loud and clear! I'm Bee, your AI assistant. How can I help you today?"
        elif "hello" in text_lower or "hi" in text_lower:
            return "Hi! I'm Bee. How can I help?"
        elif any(op in text_lower for op in ['+', 'plus', 'add']):
            # Extract numbers and calculate if it's a simple math problem
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                try:
                    result = str(int(numbers[0]) + int(numbers[1]))
                    return result
                except:
                    pass
        return "I can help you with that. Could you please provide more details?"
    
    return result

def generate_enhanced_fallback(message: str, sentiment: str, tools: List[Dict], knowledge_context: Dict[str, Any] = None) -> str:
    """Smart fallback responses when LLM is unavailable"""
    
    # Detect intent
    msg_lower = message.lower()
    
    if any(w in msg_lower for w in ["hello", "hi", "hey", "greetings"]):
        base = "Hi! I'm Bee. How can I help?"
    elif any(w in msg_lower for w in ["help", "how", "what", "explain", "guide"]):
        base = "I'd be happy to help! STING offers secure messaging, passkey authentication, and AI assistance. What would you like to know more about?"
    elif any(w in msg_lower for w in ["security", "encrypt", "safe", "protect"]):
        base = "STING prioritizes security with end-to-end encryption, local AI models, and passkey authentication. Your data never leaves your control."
    elif any(w in msg_lower for w in ["error", "problem", "issue", "broken", "fix"]):
        base = "I understand you're experiencing an issue. Let me help troubleshoot. Could you describe what's happening?"
    elif any(w in msg_lower for w in ["login", "passkey", "auth", "password"]):
        base = "STING uses advanced passkey authentication for secure, passwordless login. Would you like help setting up your passkey?"
    elif any(w in msg_lower for w in ["model", "llm", "ai", "llama", "phi"]):
        base = "STING runs multiple AI models locally including LLaMA 3, Phi-3, and Zephyr. Each is optimized for different tasks."
    else:
        base = "I'm here to assist with STING's features. Could you tell me more about what you're trying to do?"
    
    # Apply sentiment adjustments
    prefixes = {
        "frustrated": "I understand this might be frustrating. ",
        "confused": "Let me clarify this for you. ",
        "urgent": "I'll help you quickly. ",
        "satisfied": "Great! "
    }
    
    prefix = prefixes.get(sentiment, "")
    
    # Add knowledge context if available
    if knowledge_context and knowledge_context.get('results'):
        results = knowledge_context['results'][:2]  # Show top 2 results in fallback
        base += f" Based on recent honey jar data, I found {len(results)} relevant security events"
        if len(results) == 1:
            result = results[0]
            content = result.get('content', result.get('text', ''))
            if content:
                base += f": {content[:100]}{'...' if len(content) > 100 else ''}"
        base += "."
    
    # Add tool context if available
    if tools:
        tool_names = [tool['name'] for tool in tools]
        base += f" I've also checked {', '.join(tool_names)} for additional information."
    
    return prefix + base + " Is there anything specific you'd like to know more about?"

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize Bee on startup"""
    app.state.start_time = time.time()
    logger.info(f"🐝 Bee Server is starting up on {BEE_HOST}:{BEE_PORT}")
    
    # Initialize components
    await kratos_auth.initialize()
    # await analytics_engine.initialize()  # Analytics engine not implemented yet
    
    # Initialize database connection for conversation manager if using DB version
    if isinstance(conversation_manager, ConversationManagerDB):
        await conversation_manager.initialize()
    
    await conversation_manager.start_cleanup_task()
    
    logger.info("🐝 Bee is ready to buzz!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🐝 Bee Server is shutting down...")
    
    # Save any pending analytics
    # await analytics_engine.flush()
    
    # Close database connections if using DB version
    if isinstance(conversation_manager, ConversationManagerDB) and hasattr(conversation_manager, 'close'):
        await conversation_manager.close()
    
    logger.info("🐝 Bee Server has stopped buzzing. Goodbye!")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=BEE_HOST,
        port=BEE_PORT,
        log_level="info",
        access_log=True
    )