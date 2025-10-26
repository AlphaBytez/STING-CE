"""
Nectar Worker - Lightweight AI service for Nectar Bots
Handles public and private bot chat requests with optional Honey Jar context
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import asyncio

from honey_jar_cache import HoneyJarContextManager
from ollama_client import OllamaClient

# Import PII Serialization Middleware
import sys
sys.path.insert(0, '/app/app/middleware')
try:
    from pii_serialization import PIIMiddleware
except Exception as e:
    import logging
    logging.warning(f"Failed to load PII middleware: {e}")
    PIIMiddleware = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Nectar Worker",
    description="Lightweight AI service for Nectar Bots",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
STING_API_URL = os.getenv('STING_API_URL', 'http://app:5000')
STING_API_KEY = os.getenv('STING_API_KEY', '')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'phi3:mini')
KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '30m')  # Keep model in memory for 30 minutes

# Nectar bot limits
MAX_HONEY_JARS_PER_BOT = int(os.getenv('MAX_HONEY_JARS_PER_BOT', '3'))
MAX_CONTEXT_TOKENS = int(os.getenv('MAX_CONTEXT_TOKENS', '2000'))

# Initialize managers
honey_jar_manager = HoneyJarContextManager(
    sting_api_url=STING_API_URL,
    sting_api_key=STING_API_KEY,
    cache_size=100,
    ttl=300  # 5 minute cache
)

ollama_client = OllamaClient(
    base_url=OLLAMA_URL,
    default_model=DEFAULT_MODEL,
    keep_alive=KEEP_ALIVE
)

# Initialize PII Middleware
pii_middleware = None
if PIIMiddleware is not None:
    try:
        import yaml
        config_path = os.getenv("CONFIG_PATH", "/app/conf/config.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                pii_middleware = PIIMiddleware(config.get('security', {}))
                logger.info("PII middleware initialized successfully")
        else:
            logger.warning(f"Config file not found at {config_path}, PII middleware disabled")
    except Exception as e:
        logger.error(f"Failed to initialize PII middleware: {e}")
        logger.warning("PII protection will be disabled for this service")
else:
    logger.warning("PII middleware module not available, protection disabled")


# Request/Response Models
class NectarChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    bot_id: str = Field(..., description="Nectar Bot ID")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    user_id: Optional[str] = Field(None, description="User ID (for private bots)")
    user_email: Optional[str] = Field(None, description="User email (for private bots)")


class NectarChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    processing_time: float
    model_used: str
    honey_jars_used: List[str] = []
    handoff_triggered: bool = False
    handoff_reason: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    ollama_status: str
    model_loaded: bool
    timestamp: str


# Bot config cache (simple in-memory cache)
bot_config_cache = {}
BOT_CACHE_TTL = 300  # 5 minutes


async def fetch_bot_config(bot_id: str) -> Dict[str, Any]:
    """Fetch bot configuration from STING API with caching"""
    # Check cache
    if bot_id in bot_config_cache:
        cached = bot_config_cache[bot_id]
        if time.time() - cached['timestamp'] < BOT_CACHE_TTL:
            return cached['config']

    # Fetch from API
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(
                f"{STING_API_URL}/api/nectar-bots/internal/{bot_id}",
                headers={"Authorization": f"Bearer {STING_API_KEY}"},
                timeout=5.0
            )

            if response.status_code == 200:
                config = response.json()
                bot_config_cache[bot_id] = {
                    'config': config,
                    'timestamp': time.time()
                }
                return config
            else:
                logger.error(f"Failed to fetch bot config: {response.status_code}")
                raise HTTPException(status_code=404, detail="Bot not found")

        except httpx.RequestError as e:
            logger.error(f"Error fetching bot config: {e}")
            raise HTTPException(status_code=503, detail="Unable to fetch bot configuration")


async def check_handoff_keywords(message: str, bot_config: Dict) -> tuple[bool, Optional[str]]:
    """Check if message contains handoff keywords"""
    handoff_config = bot_config.get('handoff_config', {})
    if not handoff_config.get('enabled', False):
        return False, None

    keywords = handoff_config.get('keywords', [])
    message_lower = message.lower()

    for keyword in keywords:
        if keyword.lower() in message_lower:
            return True, f"keyword_detected:{keyword}"

    return False, None


async def save_conversation_message(
    conversation_id: str,
    bot_id: str,
    user_message: str,
    bot_response: str,
    user_id: Optional[str] = None
):
    """Save conversation message to STING database via API"""
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{STING_API_URL}/api/nectar-bots/internal/conversations/{conversation_id}/messages",
                headers={"X-API-Key": STING_API_KEY},
                json={
                    "bot_id": bot_id,
                    "user_id": user_id,
                    "user_message": user_message,
                    "bot_response": bot_response
                },
                timeout=5.0
            )
        except Exception as e:
            logger.warning(f"Failed to save conversation: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    # Check Ollama status
    ollama_status = "unknown"
    model_loaded = False

    try:
        ollama_healthy = await ollama_client.health_check()
        ollama_status = "healthy" if ollama_healthy else "unhealthy"

        # Check if default model is loaded
        if ollama_healthy:
            model_loaded = await ollama_client.is_model_loaded(DEFAULT_MODEL)
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        ollama_status = "error"

    return HealthResponse(
        status="healthy" if ollama_status == "healthy" else "degraded",
        service="nectar-worker",
        ollama_status=ollama_status,
        model_loaded=model_loaded,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/chat", response_model=NectarChatResponse)
async def chat(request: NectarChatRequest):
    """
    Process chat request for Nectar Bot

    Features:
    - Lightweight, optimized for speed
    - Optional Honey Jar context
    - Handoff detection
    - Conversation persistence
    """
    start_time = time.time()

    try:
        # Fetch bot configuration
        bot = await fetch_bot_config(request.bot_id)

        # Validate Honey Jar count
        honey_jar_ids = bot.get('honey_jar_ids', [])
        if len(honey_jar_ids) > MAX_HONEY_JARS_PER_BOT:
            honey_jar_ids = honey_jar_ids[:MAX_HONEY_JARS_PER_BOT]
            logger.warning(f"Bot {request.bot_id} has too many Honey Jars, limiting to {MAX_HONEY_JARS_PER_BOT}")

        # Check for handoff keywords
        handoff_triggered, handoff_reason = await check_handoff_keywords(request.message, bot)

        # Build context from Honey Jars if present
        honey_jar_context = ""
        jars_used = []

        if honey_jar_ids:
            logger.info(f"Loading context from {len(honey_jar_ids)} Honey Jars")

            for jar_id in honey_jar_ids:
                try:
                    jar_context = await honey_jar_manager.get_relevant_context(
                        jar_id=jar_id,
                        user_message=request.message,
                        limit=5,  # Top 5 relevant docs per jar
                        is_public=bot.get('is_public', False),
                        bot_owner_id=bot.get('owner_id')
                    )

                    if jar_context:
                        honey_jar_context += f"\n\n=== Knowledge Base Context ===\n{jar_context}\n"
                        jars_used.append(jar_id)

                except Exception as e:
                    logger.error(f"Failed to load Honey Jar {jar_id}: {e}")

        # Build system prompt
        system_prompt = bot.get('system_prompt', 'You are a helpful AI assistant.')

        # Add Honey Jar context to system prompt
        if honey_jar_context:
            system_prompt += f"\n\n{honey_jar_context}\n\nUse the above knowledge base to answer questions when relevant."

        # Trim system prompt if too long (rough token estimation)
        if len(system_prompt) > MAX_CONTEXT_TOKENS * 4:  # ~4 chars per token
            system_prompt = system_prompt[:MAX_CONTEXT_TOKENS * 4]
            logger.warning(f"System prompt truncated to {MAX_CONTEXT_TOKENS} tokens")

        # Select model
        model = bot.get('model') or DEFAULT_MODEL

        # PII Protection: Serialize message and system prompt before sending to LLM
        pii_context = {}
        serialized_message = request.message
        serialized_system_prompt = system_prompt

        if pii_middleware:
            try:
                # Serialize the user message
                serialized_message, pii_context = await pii_middleware.serialize_message(
                    message=request.message,
                    conversation_id=request.conversation_id or str(uuid4()),
                    user_id=request.user_id,
                    mode="external"  # Use external mode for Nectar bots
                )

                # Also serialize system prompt (which may contain Honey Jar context with PII)
                if honey_jar_context:
                    serialized_system_prompt, _ = await pii_middleware.serialize_message(
                        message=system_prompt,
                        conversation_id=request.conversation_id or str(uuid4()),
                        user_id=request.user_id,
                        mode="external"
                    )
            except Exception as e:
                logger.error(f"PII serialization failed: {e}")
                # Continue without serialization on error

        # Generate response with Ollama
        logger.info(f"Generating response with model: {model}")

        response_text = await ollama_client.generate(
            model=model,
            prompt=serialized_message,
            system=serialized_system_prompt
        )

        # PII Protection: Deserialize response to restore original values
        if pii_middleware and pii_context:
            try:
                response_text = await pii_middleware.deserialize_response(
                    response=response_text,
                    context=pii_context
                )
            except Exception as e:
                logger.error(f"PII deserialization failed: {e}")
                # Continue with serialized response on error

        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid4())

        # Save conversation asynchronously (don't wait)
        asyncio.create_task(
            save_conversation_message(
                conversation_id=conversation_id,
                bot_id=request.bot_id,
                user_message=request.message,
                bot_response=response_text,
                user_id=request.user_id
            )
        )

        processing_time = time.time() - start_time

        logger.info(f"Chat processed in {processing_time:.2f}s using model {model}")

        return NectarChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time=processing_time,
            model_used=model,
            honey_jars_used=jars_used,
            handoff_triggered=handoff_triggered,
            handoff_reason=handoff_reason
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9002,
        log_level="info"
    )
