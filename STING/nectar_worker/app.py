"""
Nectar Worker Service - Lightweight LLM service for Nectar Bots

This service provides dedicated, lightweight LLM responses for Nectar Bots without
the overhead of the full Bee Chat system (no Bee Brain, no doc search, etc.)

Features:
- LLM-agnostic (supports Ollama, OpenAI, Anthropic, etc.)
- Bot-specific system prompts
- Optional honey jar context loading
- Redis-based conversation history
- Rate limiting by IP/user/bot
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import aiohttp
import redis.asyncio as redis
import json
import os
import re
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def strip_model_artifacts(response: str) -> str:
    """
    Strip model-specific artifacts from LLM responses.

    Some reasoning models include artifacts that shouldn't be shown to users:
    - <think>...</think> tags (DeepSeek, Phi-4 chain-of-thought)
    - \\boxed{...} LaTeX wrappers (Phi-4 math formatting)
    """
    if not response:
        return response

    # Remove <think>...</think> blocks (including multiline)
    cleaned = re.sub(r'<think>.*?</think>\s*', '', response, flags=re.DOTALL)

    # Also handle unclosed <think> tags (model might have been cut off)
    cleaned = re.sub(r'<think>.*$', '', cleaned, flags=re.DOTALL)

    # Remove \boxed{...} completely - it's usually a duplicate of the answer
    # Phi-4 outputs: "Answer here\n\n\boxed{Answer here}"
    cleaned = re.sub(r'\\boxed\{[^}]*\}', '', cleaned)

    # Remove duplicate consecutive paragraphs (model sometimes repeats itself)
    lines = cleaned.strip().split('\n\n')
    if len(lines) >= 2:
        # Check if last paragraph is duplicate or near-duplicate of earlier content
        seen = set()
        unique_lines = []
        for line in lines:
            normalized = line.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_lines.append(line)
        cleaned = '\n\n'.join(unique_lines)

    return cleaned.strip()


# Initialize FastAPI
app = FastAPI(title="Nectar Worker Service", version="1.0.0")

# Configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "2"))  # Separate DB for nectar worker
CONVERSATION_TTL = int(os.getenv("CONVERSATION_TTL", "3600"))  # 1 hour default

# LLM Configuration (LLM-agnostic)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama, openai, anthropic, etc.
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://host.docker.internal:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")  # For OpenAI, Anthropic, etc.

# Redis connection
redis_client = None

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_id: str
    user_email: str = "user@example.com"
    bot_id: str
    bot_context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str
    confidence_score: Optional[float] = None

# Startup/Shutdown Events
@app.on_event("startup")
async def startup():
    """Initialize Redis connection on startup"""
    global redis_client
    try:
        redis_client = await redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        await redis_client.ping()
        logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT} (DB {REDIS_DB})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        raise

    logger.info(f"🤖 Nectar Worker started - LLM Provider: {LLM_PROVIDER}, Model: {LLM_MODEL}")

@app.on_event("shutdown")
async def shutdown():
    """Close Redis connection on shutdown"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if redis_client:
            await redis_client.ping()
        return {
            "status": "healthy",
            "service": "nectar-worker",
            "llm_provider": LLM_PROVIDER,
            "llm_model": LLM_MODEL,
            "redis_connected": redis_client is not None
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Helper Functions
async def get_conversation_history(conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """Retrieve conversation history from Redis"""
    try:
        history_key = f"nectar:conversation:{conversation_id}"
        history_json = await redis_client.lrange(history_key, -limit, -1)
        return [json.loads(msg) for msg in history_json]
    except Exception as e:
        logger.warning(f"Failed to load conversation history: {e}")
        return []

async def save_message(conversation_id: str, role: str, content: str):
    """Save message to conversation history in Redis"""
    try:
        history_key = f"nectar:conversation:{conversation_id}"
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await redis_client.rpush(history_key, json.dumps(message))
        await redis_client.expire(history_key, CONVERSATION_TTL)
    except Exception as e:
        logger.error(f"Failed to save message: {e}")

async def call_llm(system_prompt: str, user_message: str, conversation_history: List[Dict] = None) -> str:
    """
    LLM-agnostic function to call any LLM provider
    
    Supports:
    - Ollama (local)
    - OpenAI
    - Anthropic
    - Any OpenAI-compatible endpoint
    """
    
    # Build messages array
    messages = []
    
    # Add system prompt
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    # Call appropriate LLM based on provider
    if LLM_PROVIDER == "ollama":
        response = await call_ollama(messages)
    elif LLM_PROVIDER == "openai":
        response = await call_openai(messages)
    elif LLM_PROVIDER == "anthropic":
        response = await call_anthropic(messages)
    else:
        # Default: Try OpenAI-compatible endpoint
        response = await call_openai_compatible(messages)

    # Strip model artifacts (<think> tags, \boxed{}, etc.)
    return strip_model_artifacts(response)

async def call_ollama(messages: List[Dict]) -> str:
    """Call Ollama LLM"""
    try:
        # Combine system and user messages for Ollama
        prompt = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLM_ENDPOINT}/api/generate",
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "")
                else:
                    error_text = await response.text()
                    raise Exception(f"Ollama returned {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise

async def call_openai_compatible(messages: List[Dict]) -> str:
    """Call OpenAI or OpenAI-compatible endpoint"""
    try:
        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{LLM_ENDPOINT}/v1/chat/completions",
                headers=headers,
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"LLM returned {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

async def call_openai(messages: List[Dict]) -> str:
    """Alias for OpenAI-compatible (same implementation)"""
    return await call_openai_compatible(messages)

async def call_anthropic(messages: List[Dict]) -> str:
    """Call Anthropic Claude API"""
    try:
        # Anthropic uses different format - system is separate
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        conversation_msgs = [m for m in messages if m["role"] != "system"]
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": LLM_MODEL or "claude-3-sonnet-20240229",
                    "system": system_msg,
                    "messages": conversation_msgs,
                    "max_tokens": 2000
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["content"][0]["text"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Anthropic returned {response.status}: {error_text}")
    except Exception as e:
        logger.error(f"Anthropic call failed: {e}")
        raise

# Main Chat Endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for Nectar Bots
    
    This is a lightweight endpoint that:
    1. Loads bot context (system prompt, honey jars)
    2. Retrieves conversation history
    3. Calls LLM directly (no Bee Brain overhead)
    4. Saves conversation to Redis
    """
    try:
        # Extract bot context
        bot_context = request.bot_context or {}
        system_prompt = bot_context.get("system_prompt", "You are a helpful AI assistant.")
        bot_name = bot_context.get("bot_name", "Assistant")

        # Prepend bot identity to system prompt to override model's default name
        # This prevents models like Phi from introducing themselves by their model name
        identity_prefix = f"Your name is {bot_name}. Never refer to yourself as Phi, Claude, GPT, or any other AI model name. "
        system_prompt = identity_prefix + system_prompt

        logger.info(f"💬 Chat request for bot: {bot_name} (ID: {request.bot_id})")

        # Load conversation history
        history = await get_conversation_history(request.conversation_id, limit=10)

        # Call LLM
        response_text = await call_llm(
            system_prompt=system_prompt,
            user_message=request.message,
            conversation_history=history
        )
        
        # Save messages to history
        await save_message(request.conversation_id, "user", request.message)
        await save_message(request.conversation_id, "assistant", response_text)
        
        return ChatResponse(
            response=response_text,
            conversation_id=request.conversation_id,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
