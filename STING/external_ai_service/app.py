#!/usr/bin/env python3
"""
STING External AI Service
Bridge between frontend and AI providers with unified LLM interface
"""

import os
import logging
import asyncio
import aiohttp
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import Queue Manager
from llm_queue_manager import LLMQueueManager, QueuedRequest, RequestStatus, UserRole

# Import Bee Context Manager for enhanced chat capabilities
from bee_context_manager import BeeContextManager

# Import Provider Registry and providers
from providers import (
    ProviderRegistry,
    get_registry,
    initialize_providers_from_env,
    generate_with_fallback as provider_generate,
    get_legacy_providers_dict,
    OllamaProvider,
    MiniMaxProvider,
    GenerationResult,
)

# Configure logging first (before PII import that may fail)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import PII Serialization Middleware
import sys
# Add middleware directory to path to avoid app.py vs app package conflict
sys.path.insert(0, '/app/app/middleware')
try:
    from pii_serialization import PIIMiddleware, EnhancedDeserializer, ImprovedCacheManager, ModeDetector, PIIAnalytics, get_analytics_instance
except Exception as e:
    logger.warning(f"Failed to load PII middleware: {e}")
    PIIMiddleware = None
    EnhancedDeserializer = None
    ImprovedCacheManager = None
    ModeDetector = None
    PIIAnalytics = None
    get_analytics_instance = None

# Get CORS origins from environment or use defaults
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else [
    "https://localhost:8443",
    "http://localhost:8443",
    "https://127.0.0.1:8443",
    "http://127.0.0.1:8443",
    "http://localhost",
    "https://localhost",
    "http://host.docker.internal:8443",
    "https://host.docker.internal:8443"
]

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SERVICE_PORT = int(os.getenv("EXTERNAL_AI_PORT", "8091"))
SERVICE_HOST = os.getenv("EXTERNAL_AI_HOST", "0.0.0.0")

# MiniMax Configuration (Primary LLM with Ollama fallback)
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_DEFAULT_MODEL = os.getenv("MINIMAX_DEFAULT_MODEL", "MiniMax-Text-01")
LLM_PRIMARY_PROVIDER = os.getenv("LLM_PRIMARY_PROVIDER", "minimax")  # minimax or ollama

app = FastAPI(
    title="STING External AI Service",
    description="Bridge service for AI providers including Ollama",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ReportRequest(BaseModel):
    templateId: str
    provider: str
    privacyLevel: str
    dataSources: List[str]
    requiredFields: Dict[str, Any]
    authenticatedAt: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    user_role: Optional[str] = "worker"
    async_mode: Optional[bool] = True  # Default to async for reports

class OllamaGenerateRequest(BaseModel):
    model: str
    prompt: str
    options: Optional[Dict[str, Any]] = {}

class KnowledgeSyncRequest(BaseModel):
    data: Dict[str, Any]
    targetProvider: str = "ollama"
    syncType: str = "incremental"

class EmbeddingRequest(BaseModel):
    documents: List[str]
    provider: str = "ollama"
    model: str = "nomic-embed-text"

class BeeChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None
    tools_enabled: List[str] = []
    require_auth: bool = False
    encryption_required: bool = False
    context: Optional[Dict[str, Any]] = None
    user_role: Optional[str] = "worker"  # Default role if not specified
    async_mode: Optional[bool] = False  # Whether to use queue or direct processing
    honey_jar_id: Optional[str] = None  # ID of honey jar to use for context


# =============================================================================
# PROVIDER REGISTRY INITIALIZATION
# Initializes LLM providers from environment configuration
# =============================================================================

# Initialize provider registry from environment variables
provider_registry = initialize_providers_from_env()

# Legacy AI_PROVIDERS dict for backwards compatibility
# This is now dynamically generated from the registry
def get_ai_providers() -> Dict[str, Any]:
    """Get AI_PROVIDERS dict, dynamically from registry with static fallbacks."""
    providers = get_legacy_providers_dict()
    
    # Add static entries for providers not yet implemented
    if "openai" not in providers:
        providers["openai"] = {
            "id": "openai",
            "name": "OpenAI GPT-4",
            "description": "Advanced language model for comprehensive analysis",
            "capabilities": ["text-analysis", "summarization", "insights", "recommendations"],
            "privacyLevel": "medium",
            "estimatedCost": 0.03,
            "maxTokens": 128000,
            "type": "cloud"
        }
    if "claude" not in providers:
        providers["claude"] = {
            "id": "claude",
            "name": "Anthropic Claude",
            "description": "Constitutional AI for safe and helpful analysis",
            "capabilities": ["text-analysis", "summarization", "code-review", "research"],
            "privacyLevel": "medium",
            "estimatedCost": 0.025,
            "maxTokens": 200000,
            "type": "cloud"
        }
    return providers

# Create static reference for backwards compatibility
AI_PROVIDERS = get_ai_providers()


class LLMConnectionPool:
    """Manages a pool of HTTP connections for parallel LLM inference.

    Benefits:
    - Reuses TCP connections (avoids handshake overhead)
    - Limits concurrent connections to prevent overwhelming the LLM
    - Enables true parallel inference when LM Studio has n_parallel > 1
    """

    _instance = None
    _session: Optional[aiohttp.ClientSession] = None
    _lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None

    # Connection pool settings optimized for parallel LLM inference
    MAX_CONNECTIONS = 10  # Max simultaneous connections to LLM
    MAX_CONNECTIONS_PER_HOST = 8  # Should match LM Studio's n_parallel
    KEEPALIVE_TIMEOUT = 30  # Keep connections warm for 30 seconds

    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create the shared aiohttp session with connection pooling."""
        if cls._session is None or cls._session.closed:
            # Configure connection pool
            connector = aiohttp.TCPConnector(
                limit=cls.MAX_CONNECTIONS,
                limit_per_host=cls.MAX_CONNECTIONS_PER_HOST,
                keepalive_timeout=cls.KEEPALIVE_TIMEOUT,
                enable_cleanup_closed=True,
                force_close=False,  # Reuse connections
            )

            # Default timeout - individual requests can override
            timeout = aiohttp.ClientTimeout(
                total=None,  # No total timeout (LLM can be slow)
                connect=10,  # 10s to establish connection
                sock_read=None,  # No read timeout (streaming)
            )

            cls._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
            logger.info(f"🔌 Created LLM connection pool: max={cls.MAX_CONNECTIONS}, per_host={cls.MAX_CONNECTIONS_PER_HOST}")

        return cls._session

    @classmethod
    async def close(cls):
        """Close the connection pool gracefully."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
            logger.info("🔌 Closed LLM connection pool")

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if cls._session and cls._session.connector:
            connector = cls._session.connector
            return {
                "pool_size": connector.limit,
                "per_host_limit": connector.limit_per_host,
                "active_connections": len(connector._acquired),
                "available_connections": connector.limit - len(connector._acquired),
            }
        return {"status": "not_initialized"}


class OllamaClient:
    """Client for interacting with Ollama API with caching and connection pooling."""

    # Class-level cache for status and models (shared across instances)
    _status_cache = None
    _status_cache_time = 0
    _models_cache = None
    _models_cache_time = 0
    CACHE_TTL_SECONDS = 60  # Cache status/models for 60 seconds

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        # Remove trailing slash to prevent double slashes in URLs
        self.base_url = base_url.rstrip('/')

    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if cache is still valid"""
        import time
        return (time.time() - cache_time) < self.CACHE_TTL_SECONDS

    async def check_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Check if LLM service is running (OpenAI-compatible API standard)

        Uses caching to avoid repeated HTTP calls on every request.
        Cache TTL: 60 seconds (configurable via CACHE_TTL_SECONDS)
        """
        import time

        # Return cached status if valid
        if not force_refresh and OllamaClient._status_cache and self._is_cache_valid(OllamaClient._status_cache_time):
            logger.debug(f"⚡ Using cached LLM status (age: {int(time.time() - OllamaClient._status_cache_time)}s)")
            return OllamaClient._status_cache

        try:
            # Use connection pool instead of creating new session
            session = await LLMConnectionPool.get_session()
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout for health check
            # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
            async with session.get(f"{self.base_url}/v1/models", timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("data", [])
                    logger.debug(f"Connected via OpenAI-compatible API: {len(models)} models available")
                    result = {
                        "running": True,
                        "models": len(models),
                        "endpoint": self.base_url,
                        "api_type": "openai_compatible"
                    }
                    # Cache the result
                    OllamaClient._status_cache = result
                    OllamaClient._status_cache_time = time.time()
                    return result
                else:
                    logger.warning(f"LLM service returned status {response.status}")
                    # Don't cache failures
                    return {"running": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"Failed to check LLM service status: {e}")
            # Don't cache failures
            return {"running": False, "error": str(e)}

    async def get_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get available models (OpenAI-compatible API standard)

        Uses caching to avoid repeated HTTP calls on every request.
        Cache TTL: 60 seconds (configurable via CACHE_TTL_SECONDS)
        """
        import time

        # Return cached models if valid
        if not force_refresh and OllamaClient._models_cache is not None and self._is_cache_valid(OllamaClient._models_cache_time):
            logger.debug(f"⚡ Using cached models list (age: {int(time.time() - OllamaClient._models_cache_time)}s)")
            return OllamaClient._models_cache

        logger.info(f"🔍 Fetching models from {self.base_url}/v1/models")
        try:
            # Use connection pool instead of creating new session
            session = await LLMConnectionPool.get_session()
            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout for model list
            # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
            async with session.get(f"{self.base_url}/v1/models", timeout=timeout) as response:
                logger.info(f"📡 Got response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"📦 Response data keys: {data.keys()}")
                    # Convert OpenAI format to Ollama-like format for compatibility
                    models = []
                    for model in data.get("data", []):
                        models.append({
                            "name": model.get("id"),
                            "modified_at": model.get("created", ""),
                            "size": 0,  # Not provided by OpenAI API
                            "digest": "",
                            "details": {"format": "openai_compatible"}
                        })
                    logger.info(f"✅ Retrieved {len(models)} models via OpenAI-compatible API")
                    # Cache the result
                    OllamaClient._models_cache = models
                    OllamaClient._models_cache_time = time.time()
                    return models
                else:
                    logger.warning(f"❌ Failed to get models: HTTP {response.status}")
                    return []  # Return empty list instead of raising exception
        except HTTPException:
            raise  # Re-raise HTTPException for API endpoints
        except Exception as e:
            logger.error(f"❌ Exception in get_models: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []  # Return empty list for startup robustness

    async def get_status_and_models(self) -> tuple:
        """Get both status and models in a single call (optimized)

        Since check_status and get_models both call /v1/models, this combines them
        to avoid duplicate HTTP requests.
        """
        import time

        # If both caches are valid, return from cache
        if (OllamaClient._status_cache and OllamaClient._models_cache is not None and
            self._is_cache_valid(OllamaClient._status_cache_time) and
            self._is_cache_valid(OllamaClient._models_cache_time)):
            logger.debug("⚡ Using cached status and models")
            return OllamaClient._status_cache, OllamaClient._models_cache

        # Make a single request and populate both caches
        logger.info(f"🔍 Fetching status and models from {self.base_url}/v1/models")
        try:
            # Use connection pool instead of creating new session
            session = await LLMConnectionPool.get_session()
            timeout = aiohttp.ClientTimeout(total=10)
            async with session.get(f"{self.base_url}/v1/models", timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    model_list = data.get("data", [])

                    # Build status result
                    status = {
                        "running": True,
                        "models": len(model_list),
                        "endpoint": self.base_url,
                        "api_type": "openai_compatible"
                    }

                    # Build models list
                    models = []
                    for model in model_list:
                        models.append({
                            "name": model.get("id"),
                            "modified_at": model.get("created", ""),
                            "size": 0,
                            "digest": "",
                            "details": {"format": "openai_compatible"}
                        })

                    # Cache both
                    OllamaClient._status_cache = status
                    OllamaClient._status_cache_time = time.time()
                    OllamaClient._models_cache = models
                    OllamaClient._models_cache_time = time.time()

                    logger.info(f"✅ Retrieved status and {len(models)} models in single call")
                    return status, models
                else:
                    logger.warning(f"❌ Failed to get status/models: HTTP {response.status}")
                    return {"running": False, "error": f"HTTP {response.status}"}, []
        except Exception as e:
            logger.error(f"❌ Exception in get_status_and_models: {e}")
            return {"running": False, "error": str(e)}, []
    
    async def generate(self, model: str, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate text using OpenAI-compatible API only (/v1/chat/completions).

        Uses connection pooling for efficient parallel inference when LM Studio
        has n_parallel > 1 configured.
        """
        try:
            import time
            start_time = time.time()

            max_tokens_value = options.get("num_predict", 2048) if options else 2048

            # Set timeout for LLM generation
            # Conservative timeout for long-form report generation (up to 16K tokens)
            # At ~10 tokens/sec, 16K tokens ≈ 27 minutes. Set to 45 min for safety.
            timeout_seconds = 2700  # 45 minutes - reports are queued, so longer timeout is acceptable
            # Set total timeout but sock_read=None for non-streaming responses
            # In non-streaming mode, LM Studio doesn't send data until fully generated
            # so sock_read needs to be unlimited (None) to avoid timeout during generation
            timeout = aiohttp.ClientTimeout(total=timeout_seconds, sock_read=None)

            openai_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": options.get("temperature", 0.7) if options else 0.7,
                "max_tokens": max_tokens_value
            }
            logger.info(f"📤 Sending to LLM: max_tokens={max_tokens_value}, model={model}, timeout={timeout_seconds}s")

            # Use connection pool for parallel inference support
            session = await LLMConnectionPool.get_session()
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=openai_payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Calculate duration since OpenAI API doesn't provide it
                    duration_ns = int((time.time() - start_time) * 1e9)

                    # Convert OpenAI format to Ollama format for compatibility
                    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason", "unknown")
                    logger.info(f"✅ OpenAI-compatible API successful for model {model}")
                    logger.info(f"📊 Token usage: completion={completion_tokens}, requested_max={max_tokens_value}, finish_reason={finish_reason}")
                    return {
                        "response": data["choices"][0]["message"]["content"],
                        "model": data.get("model", model),
                        "created_at": data.get("created", ""),
                        "done": True,
                        "eval_count": completion_tokens,
                        "total_duration": duration_ns
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ OpenAI API returned status {response.status}: {error_text}")
                    raise HTTPException(status_code=response.status, detail=f"LLM API error: {error_text}")
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            logger.error(f"Failed to generate: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


class MiniMaxClient:
    """Client for interacting with MiniMax API with fallback support.
    
    Uses OpenAI-compatible API format for /v1/chat/completions endpoint.
    Implements automatic fallback to Ollama with logging for alerting.
    """
    
    def __init__(self, base_url: str = MINIMAX_BASE_URL, api_key: str = MINIMAX_API_KEY):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._last_error = None
        self._consecutive_failures = 0
    
    def is_configured(self) -> bool:
        """Check if MiniMax API key is configured"""
        return bool(self.api_key and self.api_key.strip())
    
    async def check_status(self) -> Dict[str, Any]:
        """Check if MiniMax API is accessible"""
        if not self.is_configured():
            return {"running": False, "error": "MiniMax API key not configured"}
        
        try:
            session = await LLMConnectionPool.get_session()
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            async with session.get(f"{self.base_url}/models", headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "running": True,
                        "models": len(data.get("data", [])),
                        "endpoint": self.base_url,
                        "api_type": "minimax"
                    }
                else:
                    return {"running": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"MiniMax status check failed: {e}")
            return {"running": False, "error": str(e)}
    
    async def generate(self, model: str, prompt: str, options: Dict[str, Any] = None, 
                       fallback_client: 'OllamaClient' = None) -> Dict[str, Any]:
        """Generate text using MiniMax API with automatic Ollama fallback.
        
        Args:
            model: Model name to use (e.g., 'MiniMax-Text-01')
            prompt: The prompt to send
            options: Generation options (temperature, max_tokens, etc.)
            fallback_client: OllamaClient instance to use if MiniMax fails
            
        Returns:
            Generation result dict (Ollama-compatible format)
        """
        import time
        
        # Check if MiniMax is configured
        if not self.is_configured():
            logger.warning("🔄 MiniMax not configured, falling back to Ollama")
            if fallback_client:
                return await self._fallback_to_ollama(fallback_client, model, prompt, options, "not_configured")
            raise HTTPException(status_code=503, detail="MiniMax not configured and no fallback available")
        
        start_time = time.time()
        max_tokens_value = options.get("num_predict", 4096) if options else 4096
        
        # MiniMax API uses OpenAI-compatible format
        payload = {
            "model": model or MINIMAX_DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": options.get("temperature", 0.7) if options else 0.7,
            "max_tokens": max_tokens_value
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout for complex tasks
            session = await LLMConnectionPool.get_session()
            
            logger.info(f"📤 Sending to MiniMax: model={payload['model']}, max_tokens={max_tokens_value}")
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    duration_ns = int((time.time() - start_time) * 1e9)
                    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    
                    # Reset failure counter on success
                    self._consecutive_failures = 0
                    self._last_error = None
                    
                    logger.info(f"✅ MiniMax API successful: {completion_tokens} tokens generated")
                    
                    # Return in Ollama-compatible format
                    return {
                        "response": data["choices"][0]["message"]["content"],
                        "model": data.get("model", model),
                        "created_at": data.get("created", ""),
                        "done": True,
                        "eval_count": completion_tokens,
                        "total_duration": duration_ns,
                        "provider": "minimax"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ MiniMax API error {response.status}: {error_text}")
                    self._consecutive_failures += 1
                    self._last_error = f"HTTP {response.status}: {error_text}"
                    
                    # Log for alerting
                    logger.warning(f"🚨 ALERT: MiniMax failure #{self._consecutive_failures}: {self._last_error}")
                    
                    if fallback_client:
                        return await self._fallback_to_ollama(fallback_client, model, prompt, options, self._last_error)
                    raise HTTPException(status_code=response.status, detail=f"MiniMax API error: {error_text}")
                    
        except aiohttp.ClientError as e:
            self._consecutive_failures += 1
            self._last_error = str(e)
            logger.error(f"❌ MiniMax connection error: {e}")
            logger.warning(f"🚨 ALERT: MiniMax connection failure #{self._consecutive_failures}: {e}")
            
            if fallback_client:
                return await self._fallback_to_ollama(fallback_client, model, prompt, options, str(e))
            raise HTTPException(status_code=503, detail=f"MiniMax connection error: {e}")
        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            self._last_error = "Request timeout"
            logger.error("❌ MiniMax request timeout")
            logger.warning(f"🚨 ALERT: MiniMax timeout failure #{self._consecutive_failures}")
            
            if fallback_client:
                return await self._fallback_to_ollama(fallback_client, model, prompt, options, "timeout")
            raise HTTPException(status_code=504, detail="MiniMax request timeout")
        except Exception as e:
            self._consecutive_failures += 1
            self._last_error = str(e)
            logger.error(f"❌ MiniMax unexpected error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.warning(f"🚨 ALERT: MiniMax unexpected failure #{self._consecutive_failures}: {e}")
            
            if fallback_client:
                return await self._fallback_to_ollama(fallback_client, model, prompt, options, str(e))
            raise HTTPException(status_code=500, detail=f"MiniMax error: {e}")
    
    async def _fallback_to_ollama(self, ollama_client: 'OllamaClient', model: str, 
                                   prompt: str, options: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Fall back to Ollama when MiniMax fails.
        
        Logs the fallback event for alerting purposes.
        """
        logger.warning(f"🔄 FALLBACK: Switching to Ollama due to MiniMax failure: {reason}")
        
        # Log structured data for alerting systems
        fallback_event = {
            "event": "llm_fallback",
            "from_provider": "minimax",
            "to_provider": "ollama",
            "reason": reason,
            "consecutive_failures": self._consecutive_failures,
            "timestamp": datetime.now().isoformat()
        }
        logger.warning(f"📊 FALLBACK_EVENT: {json.dumps(fallback_event)}")
        
        try:
            # Use Ollama's default model for fallback
            fallback_model = AI_PROVIDERS["ollama"]["defaultModel"]
            result = await ollama_client.generate(fallback_model, prompt, options)
            result["provider"] = "ollama"
            result["fallback"] = True
            result["fallback_reason"] = reason
            logger.info(f"✅ Ollama fallback successful")
            return result
        except Exception as e:
            logger.error(f"❌ Ollama fallback also failed: {e}")
            raise HTTPException(status_code=503, detail=f"Both MiniMax and Ollama failed. MiniMax: {reason}, Ollama: {e}")
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get failure statistics for monitoring/alerting"""
        return {
            "consecutive_failures": self._consecutive_failures,
            "last_error": self._last_error,
            "is_healthy": self._consecutive_failures == 0
        }


# =============================================================================
# LEGACY CLIENT ALIASES (for backwards compatibility)
# These wrap the new provider system for existing code
# =============================================================================

class OllamaClientLegacy:
    """Legacy wrapper for OllamaProvider to maintain backwards compatibility."""
    
    def __init__(self):
        self._provider = provider_registry.get("ollama")
    
    async def check_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        if not self._provider:
            return {"running": False, "error": "Provider not configured"}
        status = await self._provider.check_status()
        return status.to_dict() if hasattr(status, 'to_dict') else {
            "running": status.running,
            "models": status.models_count,
            "endpoint": status.endpoint,
            "api_type": status.api_type
        }
    
    async def get_models(self) -> List[Dict[str, Any]]:
        if not self._provider:
            return []
        return await self._provider.get_models()
    
    async def generate(self, model: str, prompt: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self._provider:
            raise HTTPException(status_code=503, detail="Ollama provider not configured")
        result = await self._provider.generate(prompt, model, options)
        return result.to_ollama_format()
    
    async def get_status_and_models(self) -> tuple:
        """Get both status and models in a single call (optimized)."""
        if not self._provider:
            return {"running": False, "error": "Provider not configured"}, []
        status = await self.check_status()
        models = await self.get_models()
        return status, models


class MiniMaxClientLegacy:
    """Legacy wrapper for MiniMaxProvider to maintain backwards compatibility."""
    
    def __init__(self):
        self._provider = provider_registry.get("minimax")
        self._fallback = provider_registry.get("ollama")
    
    def is_configured(self) -> bool:
        return self._provider is not None and self._provider.is_configured()
    
    async def check_status(self) -> Dict[str, Any]:
        if not self._provider:
            return {"running": False, "error": "not_configured"}
        status = await self._provider.check_status()
        return {
            "running": status.running,
            "error": status.error
        }
    
    async def generate(self, model: str, prompt: str, options: Dict[str, Any] = None,
                       fallback_client: 'OllamaClientLegacy' = None) -> Dict[str, Any]:
        if not self._provider:
            if self._fallback:
                result = await self._fallback.generate(prompt, None, options)
                result_dict = result.to_ollama_format()
                result_dict["fallback"] = True
                result_dict["fallback_reason"] = "minimax_not_configured"
                return result_dict
            raise HTTPException(status_code=503, detail="No LLM provider available")
        
        result = await self._provider.generate_with_fallback(prompt, model, options, self._fallback)
        return result.to_ollama_format()
    
    def get_failure_stats(self) -> Dict[str, Any]:
        if not self._provider:
            return {"consecutive_failures": 0, "last_error": None, "is_healthy": False}
        return {
            "consecutive_failures": self._provider._consecutive_failures,
            "last_error": self._provider._last_error,
            "is_healthy": self._provider.is_healthy
        }


# Initialize legacy client wrappers for backwards compatibility
ollama_client = OllamaClientLegacy()
minimax_client = MiniMaxClientLegacy()

# Initialize Queue Manager
queue_manager = LLMQueueManager()

# Initialize Bee Context Manager
bee_context_manager = BeeContextManager()


# =============================================================================
# UNIFIED LLM GENERATION FUNCTION
# Routes through provider registry with automatic fallback
# =============================================================================

async def generate_with_fallback(prompt: str, model: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Unified LLM generation with automatic fallback.
    
    Uses the provider registry to route to primary LLM with automatic fallback.
    Logs all fallback events for alerting.
    
    Args:
        prompt: The prompt to send to the LLM
        model: Model override (uses default for each provider if not specified)
        options: Generation options (temperature, max_tokens, etc.)
        
    Returns:
        Generation result dict in Ollama-compatible format
    """
    try:
        result = await provider_registry.generate(prompt, model, options)
        return result.to_ollama_format()
    except Exception as e:
        logger.error(f"❌ generate_with_fallback failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


def get_primary_provider_info() -> tuple:
    """Get primary LLM provider info for PII mode detection.
    
    Returns:
        Tuple of (provider_name, endpoint_url, is_cloud_provider)
        - provider_name: 'minimax', 'ollama', etc.
        - endpoint_url: The actual API endpoint URL
        - is_cloud_provider: True if cloud API (should use full PII protection)
    """
    try:
        primary = provider_registry.get_primary()
        if primary:
            from providers.base import DeploymentType
            provider_name = primary.id
            endpoint_url = getattr(primary.config, 'base_url', OLLAMA_BASE_URL)
            is_cloud = primary.deployment_type == DeploymentType.CLOUD
            logger.debug(f"Primary provider: {provider_name}, cloud={is_cloud}, url={endpoint_url}")
            return provider_name, endpoint_url, is_cloud
    except Exception as e:
        logger.warning(f"Could not determine primary provider: {e}")
    
    # Fallback to env var config
    if LLM_PRIMARY_PROVIDER == "minimax" and MINIMAX_API_KEY:
        return "minimax", MINIMAX_BASE_URL, True  # MiniMax is always cloud
    return "ollama", OLLAMA_BASE_URL, False


# =============================================================================
# OPTIMIZED RESPONSE CLEANUP
# Pre-compiled regex patterns for faster response cleaning (avoids re-compilation)
# =============================================================================
import re

# Pre-compile all cleanup patterns at module load time (runs once)
_CLEANUP_PATTERNS = {
    # Think tags and reasoning - most common, check first
    'think_tags': re.compile(r'<think>.*?</think>\s*', re.DOTALL),
    'orphan_think': re.compile(r'</?think>\s*', re.DOTALL),
    'explanation': re.compile(r'\n\s*Explanation:.*', re.DOTALL),
    'reasoning': re.compile(r'\n\s*Reasoning:.*', re.DOTALL),

    # Model echo patterns
    'user_bee_echo': re.compile(r'^User:\s*.*?\n\nBee:\s*', re.DOTALL | re.MULTILINE),
    'user_label': re.compile(r'^User:\s*', re.MULTILINE),
    'bee_label': re.compile(r'^Bee:\s*', re.MULTILINE),

    # Punctuation cleanup
    'leading_punct': re.compile(r'^\s*[,)}\]]\s*', re.MULTILINE),
    'lone_punct': re.compile(r'\n\s*[,)}\]]\s*\n'),
    'punct_spacing': re.compile(r'\s+([,)}\]])\s+'),

    # LaTeX cleanup
    'boxed': re.compile(r'\\boxed\{([^}]*)\}'),
    'text_cmd': re.compile(r'\\text\{([^}]*)\}'),
    'display_math': re.compile(r'\$\$[^$]*\$\$'),
    'inline_math': re.compile(r'\$[^$]*\$'),
    'latex_cmd': re.compile(r'\\[a-zA-Z]+\{[^}]*\}'),
    'final_answer': re.compile(r'Final Answer[:\s]*', re.IGNORECASE),
}


def clean_llm_response(raw_response: str) -> str:
    """Clean LLM response using pre-compiled regex patterns.

    Performance: Uses pre-compiled patterns and early-exit checks to minimize
    unnecessary regex operations. Typical cleanup: 5-20ms (vs 50-500ms sequential).

    Args:
        raw_response: Raw text from LLM

    Returns:
        Cleaned response text
    """
    if not raw_response:
        return ""

    response = raw_response

    # Quick check: if no problematic patterns exist, skip most cleanup
    has_think = '<think' in response or '</think' in response
    has_labels = 'User:' in response or 'Bee:' in response
    has_latex = '\\' in response or '$' in response
    has_reasoning = 'Explanation:' in response or 'Reasoning:' in response

    # Think tags cleanup (most common for reasoning models)
    if has_think:
        response = _CLEANUP_PATTERNS['think_tags'].sub('', response)
        response = _CLEANUP_PATTERNS['orphan_think'].sub('', response)

    # Reasoning section cleanup
    if has_reasoning:
        response = _CLEANUP_PATTERNS['explanation'].sub('', response)
        response = _CLEANUP_PATTERNS['reasoning'].sub('', response)

    # Model echo cleanup
    if has_labels:
        response = _CLEANUP_PATTERNS['user_bee_echo'].sub('', response)
        response = _CLEANUP_PATTERNS['user_label'].sub('', response)
        response = _CLEANUP_PATTERNS['bee_label'].sub('', response)

    # LaTeX cleanup (only if backslash or $ present)
    if has_latex:
        response = _CLEANUP_PATTERNS['boxed'].sub(r'\1', response)
        response = _CLEANUP_PATTERNS['text_cmd'].sub(r'\1', response)
        response = _CLEANUP_PATTERNS['display_math'].sub('', response)
        response = _CLEANUP_PATTERNS['inline_math'].sub('', response)
        response = _CLEANUP_PATTERNS['latex_cmd'].sub('', response)
        response = _CLEANUP_PATTERNS['final_answer'].sub('', response)

    # Punctuation cleanup (always run, but fast)
    response = _CLEANUP_PATTERNS['leading_punct'].sub('', response)
    response = _CLEANUP_PATTERNS['lone_punct'].sub('\n', response)
    response = _CLEANUP_PATTERNS['punct_spacing'].sub(r'\1 ', response)

    return response.strip()


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEWBEE UNIFIED QUALITY ASSURANCE
# Combines: Requirements validation + PII safety checks + Content quality
# Replaces legacy QE Bee - this is the single source of truth for report QA
# ═══════════════════════════════════════════════════════════════════════════════

# PII Token Pattern - detect unresolved PII tokens that should have been replaced
# Pattern matches tokens like [PII_NAME_1a2b3c], [PII_EMAIL_abc123], etc.
PII_TOKEN_PATTERN = re.compile(r'\[PII_[A-Z_]+_[a-f0-9]+\]')

# Minimum content lengths for validation
MIN_REPORT_LENGTH = 500   # Reports should be substantial
MIN_RESPONSE_LENGTH = 50  # Chat responses can be shorter

# Hallucination detection patterns
HALLUCINATION_PATTERNS = {
    # Repetitive character sequences (like f5f5f5f5f5...)
    'repetitive_chars': re.compile(r'(.{2,4})\1{10,}'),
    # Repetitive hex-like patterns
    'repetitive_hex': re.compile(r'([0-9a-f]{2})\1{8,}', re.IGNORECASE),
    # Fake SHA/hash patterns (too many repeated chars)
    'fake_hash': re.compile(r'sha=([a-f0-9])\1{15,}', re.IGNORECASE),
    # Broken URLs with garbage
    'garbage_url': re.compile(r'https?://[^\s\)]+[a-f0-9]{50,}', re.IGNORECASE),
    # Duplicate section headers (same header appearing multiple times)
    'duplicate_headers': re.compile(r'^(#{1,6}\s+.+)$', re.MULTILINE),
}


def check_hallucinations(content: str) -> Dict[str, Any]:
    """
    Detect common LLM hallucination patterns in generated content.
    
    Catches:
    - Repetitive character garbage (f5f5f5f5f5...)
    - Fake/malformed URLs with garbage data
    - Duplicate sections (same heading appearing twice)
    - Overly long URLs with repetitive patterns
    
    Returns:
        Dict with: passed, code, message, severity, details
    """
    issues = []
    details = {}
    
    # 1. Check for repetitive character sequences
    repetitive_matches = HALLUCINATION_PATTERNS['repetitive_chars'].findall(content)
    if repetitive_matches:
        # Filter to actual problems (not legitimate patterns like "====")
        real_issues = [m for m in repetitive_matches if m not in ('==', '--', '  ', '..', '──', '═')]
        if real_issues:
            issues.append(f"Repetitive garbage pattern detected: '{real_issues[0]}' repeated")
            details['repetitive_patterns'] = real_issues[:5]
    
    # 2. Check for fake hash/SHA patterns
    fake_hash_matches = HALLUCINATION_PATTERNS['fake_hash'].findall(content)
    if fake_hash_matches:
        issues.append(f"Fake/invalid hash detected with repeated character '{fake_hash_matches[0]}'")
        details['fake_hashes'] = len(fake_hash_matches)
    
    # 3. Check for garbage URLs (very long with repetitive hex)
    garbage_urls = HALLUCINATION_PATTERNS['garbage_url'].findall(content)
    if garbage_urls:
        issues.append(f"Malformed URL with garbage data detected ({len(garbage_urls)} found)")
        details['garbage_urls'] = len(garbage_urls)
    
    # 4. Check for duplicate section headers
    headers = HALLUCINATION_PATTERNS['duplicate_headers'].findall(content)
    if headers:
        # Normalize headers and check for duplicates
        normalized = [h.strip().lower() for h in headers]
        seen = {}
        duplicates = []
        for h in normalized:
            if h in seen:
                seen[h] += 1
                if seen[h] == 2:  # Only add on first duplicate
                    duplicates.append(h)
            else:
                seen[h] = 1
        
        if duplicates:
            issues.append(f"Duplicate section headers found: {duplicates[:3]}")
            details['duplicate_headers'] = duplicates
    
    # 5. Check for URLs that are suspiciously long (often hallucinated)
    long_url_pattern = re.compile(r'https?://[^\s\)\]]{200,}')
    long_urls = long_url_pattern.findall(content)
    if long_urls:
        issues.append(f"Suspiciously long URL detected ({len(long_urls[0])} chars)")
        details['long_urls'] = len(long_urls)
    
    # 6. Check for markdown link syntax errors (common hallucination)
    broken_links = re.findall(r'\[[^\]]+\]\([^\)]*\n[^\)]*\)', content)
    if broken_links:
        issues.append(f"Broken markdown links spanning multiple lines ({len(broken_links)} found)")
        details['broken_links'] = len(broken_links)
    
    # 7. Check for likely fabricated doctor/professional names with detailed fake bios
    # Pattern: "Dr. [First] [Last]" followed by detailed credentials within ~500 chars
    fabricated_bio_pattern = re.compile(
        r'Dr\.\s+([A-Z][a-z]+)\s+([A-Z][a-z]+).{0,300}'
        r'(completed (his|her|their) (medical degree|residency|fellowship)|'
        r'board-certified|received (his|her|their) medical degree|'
        r'specializes in|has extensive experience)',
        re.IGNORECASE | re.DOTALL
    )
    fabricated_bios = fabricated_bio_pattern.findall(content)
    
    # Common hallucinated names - these exact patterns appear frequently in LLM fabrications
    KNOWN_FAKE_NAMES = {
        ('emily', 'carter'), ('michael', 'thompson'), ('sarah', 'nguyen'),
        ('john', 'smith'), ('jennifer', 'williams'), ('david', 'johnson'),
        ('james', 'anderson'), ('lisa', 'brown'), ('robert', 'taylor'),
        ('maria', 'garcia'), ('william', 'martinez'), ('patricia', 'chen'),
        ('elizabeth', 'wilson'), ('richard', 'moore'), ('susan', 'lee'),
        ('joseph', 'harris'), ('margaret', 'clark'), ('thomas', 'lewis'),
        ('nancy', 'walker'), ('christopher', 'hall'), ('karen', 'allen'),
        ('daniel', 'young'), ('helen', 'king'), ('matthew', 'wright'),
    }
    
    # Check for known fake name patterns
    found_fake_names = []
    for match in fabricated_bios:
        first_name = match[0].lower() if match[0] else ''
        last_name = match[1].lower() if match[1] else ''
        if (first_name, last_name) in KNOWN_FAKE_NAMES:
            found_fake_names.append(f"Dr. {match[0]} {match[1]}")
    
    if found_fake_names:
        issues.append(f"Likely fabricated person names detected: {', '.join(found_fake_names[:3])}")
        details['fabricated_names'] = found_fake_names
    
    # Also flag if there are many detailed doctor bios (3+) without source attribution
    # This is a strong indicator of hallucination
    if len(fabricated_bios) >= 3:
        # Check if content has source references nearby
        has_source_refs = bool(re.search(r'(Source:|Reference:|According to|per )', content, re.IGNORECASE))
        if not has_source_refs:
            issues.append(f"Multiple detailed professional biographies ({len(fabricated_bios)}) without source attribution - likely fabricated")
            details['unsourced_bios'] = len(fabricated_bios)
    
    if issues:
        return {
            'check': 'hallucination_detection',
            'passed': False,
            'code': 'HALLUCINATION_DETECTED',
            'message': f"Content quality issues: {'; '.join(issues[:3])}",
            'severity': 'error',
            'details': details
        }
    
    return {
        'check': 'hallucination_detection',
        'passed': True,
        'code': 'CONTENT_CLEAN',
        'message': 'No hallucination patterns detected',
        'severity': 'info'
    }


def check_reference_relevance(content: str, original_request: str) -> Dict[str, Any]:
    """
    Check if references in the content are relevant to the original request.
    
    Detects when search returned irrelevant results (e.g., high schools when 
    asking about hospitals) and flags the report as having mismatched sources.
    
    Returns:
        Dict with: passed, code, message, severity, details
    """
    import re
    
    # Extract key entities from the original request
    request_lower = original_request.lower()
    
    # Extract likely organization types from request
    request_entities = []
    org_type_patterns = [
        (r'\b(hospital|medical center|clinic|healthcare)\b', 'healthcare'),
        (r'\b(university|college|school of|institute)\b', 'education'),
        (r'\b(company|corporation|inc\.|llc|enterprise)\b', 'business'),
        (r'\b(law firm|attorney|legal)\b', 'legal'),
        (r'\b(bank|financial|investment)\b', 'financial'),
    ]
    
    expected_org_type = None
    for pattern, org_type in org_type_patterns:
        if re.search(pattern, request_lower):
            expected_org_type = org_type
            break
    
    # Extract capitalized organization names from request
    org_names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', original_request)
    request_entities.extend([name.lower() for name in org_names])
    
    # Extract key topic words from request
    topic_words = []
    for word in original_request.split():
        word_clean = re.sub(r'[^\w]', '', word.lower())
        if len(word_clean) > 4 and word_clean not in ['about', 'report', 'write', 'create', 'generate']:
            topic_words.append(word_clean)
    
    # Find the References section in the content
    ref_section_match = re.search(
        r'(?:References|Sources|Bibliography|Works Cited)[:\s]*\n(.*?)(?:\n\n|\Z)',
        content,
        re.IGNORECASE | re.DOTALL
    )
    
    if not ref_section_match:
        # No references section - can't check relevance
        return {
            'check': 'reference_relevance',
            'passed': True,
            'code': 'NO_REFERENCES',
            'message': 'No references section found to validate',
            'severity': 'info'
        }
    
    references_text = ref_section_match.group(1).lower()
    
    # Check for obviously mismatched references
    mismatches = []
    is_major_mismatch = False
    
    # Check if expected organization type is present in references
    if expected_org_type == 'healthcare':
        # References should have healthcare terms, not school terms
        healthcare_terms = ['hospital', 'medical', 'health', 'clinic', 'doctor', 'physician', 'patient', 'cardio', 'surgery']
        school_terms = ['high school', 'middle school', 'elementary', 'football', 'basketball', 'maxpreps', 'varsity', 'athletics', 'school district', 'school boundaries']
        
        has_healthcare = any(term in references_text for term in healthcare_terms)
        has_school = any(term in references_text for term in school_terms)
        
        if has_school and not has_healthcare:
            mismatches.append(f"References contain SCHOOL/SPORTS content but request was about HEALTHCARE")
            is_major_mismatch = True  # This is a critical mismatch
        elif has_school:
            mismatches.append(f"References may be contaminated with school/sports content")
    
    # Additional healthcare check - look for specific patterns
    if expected_org_type == 'healthcare' and 'doctor' in request_lower or 'cardiac' in request_lower:
        # User asked about doctors - check if we have medical content
        medical_indicators = ['md', 'physician', 'cardiologist', 'surgeon', 'specialist', 'board certified', 'medical degree']
        has_medical_content = any(ind in references_text for ind in medical_indicators)
        has_school_content = 'school' in references_text or 'football' in references_text or 'maxpreps' in references_text
        
        if has_school_content and not has_medical_content:
            mismatches.append("Asked about doctors/medical staff but references are about schools")
            is_major_mismatch = True
    
    # Check if key organization name appears in references
    if org_names:
        main_org = org_names[0].lower()
        # Check if the full org name (not just part of it) appears in context
        if main_org not in references_text:
            # Check if at least the significant parts appear
            org_parts = main_org.split()
            if len(org_parts) >= 2:
                # For "Northside Hospital Atlanta", check if "hospital" context exists
                significant_parts = [p for p in org_parts if len(p) > 4]
                matching_parts = [p for p in significant_parts if p in references_text]
                if len(matching_parts) < len(significant_parts) // 2:
                    mismatches.append(f"Organization '{org_names[0]}' not found in references")
    
    if mismatches:
        return {
            'check': 'reference_relevance',
            'passed': False,
            'code': 'MAJOR_MISMATCH' if is_major_mismatch else 'REFERENCE_MISMATCH',
            'message': f"References don't match request: {'; '.join(mismatches)}",
            'severity': 'error',
            'details': {
                'expected_type': expected_org_type,
                'mismatches': mismatches,
                'org_names_sought': org_names,
                'is_major_mismatch': is_major_mismatch
            }
        }
    
    return {
        'check': 'reference_relevance',
        'passed': True,
        'code': 'REFERENCES_RELEVANT',
        'message': 'References appear relevant to the request',
        'severity': 'info'
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SMART REPORT GATING SYSTEM
# Evaluates context quality before generating reports to:
# 1. Conserve expensive LLM resources
# 2. Prevent low-quality reports from vague requests
# 3. Guide users to provide better context
# ═══════════════════════════════════════════════════════════════════════════════

def assess_report_readiness(
    user_message: str,
    honey_jar_id: str = None,
    honey_jar_context: str = None,
    web_search_results: list = None,
    conversation_history: list = None
) -> Dict[str, Any]:
    """
    Score the available context to determine if we have enough information
    to generate a high-quality report.
    
    Scoring factors:
    - Honey Jar attached: +40 points (user has relevant documents)
    - Specific entity named: +20 points (e.g., "Northside Hospital" vs "a hospital")
    - Web search quality results: +15 points (found authoritative sources)
    - Clear scope/timeframe: +10 points (e.g., "in 2025", "for healthcare")
    - Actionable request: +10 points (e.g., "implementation plan" vs "tell me about")
    - Prior conversation context: +5 points (continuing a discussion)
    
    Thresholds:
    - >= 50: Generate immediately (high confidence)
    - 30-49: Offer to proceed with suggestions (medium confidence)
    - < 30: Ask clarifying questions (low confidence)
    
    Returns:
        Dict with: score, confidence_level, can_proceed, suggestions, clarifying_questions
    """
    import re
    
    score = 0
    factors = []
    suggestions = []
    clarifying_questions = []
    
    msg_lower = user_message.lower()
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 1: Honey Jar attached (+40 points)
    # ═══════════════════════════════════════════════════════════════════
    if honey_jar_id and honey_jar_context and len(honey_jar_context) > 100:
        score += 40
        factors.append(("honey_jar_attached", 40, "Relevant Honey Jar documents available"))
    elif honey_jar_id:
        score += 20
        factors.append(("honey_jar_attached_light", 20, "Honey Jar attached but limited content"))
        suggestions.append("Consider adding more documents to your Honey Jar for richer context")
    else:
        clarifying_questions.append("Would you like to attach a Honey Jar with relevant documents?")
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 2: Specific entity named (+20 points)
    # ═══════════════════════════════════════════════════════════════════
    # Look for capitalized proper nouns (organizations, people, places)
    proper_nouns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', user_message)
    # Also check for quoted entities
    quoted_entities = re.findall(r'"([^"]+)"', user_message)
    
    has_specific_entity = len(proper_nouns) > 0 or len(quoted_entities) > 0
    
    # Check for vague language that suggests no specific entity
    vague_indicators = ['a company', 'an organization', 'some hospital', 'any business', 
                       'generic', 'general', 'typical', 'example of']
    is_vague = any(v in msg_lower for v in vague_indicators)
    
    if has_specific_entity and not is_vague:
        score += 20
        entity_example = proper_nouns[0] if proper_nouns else quoted_entities[0]
        factors.append(("specific_entity", 20, f"Specific entity identified: {entity_example}"))
    elif has_specific_entity:
        score += 10
        factors.append(("partial_entity", 10, "Entity mentioned but request seems generic"))
    else:
        clarifying_questions.append("Is there a specific organization, company, or topic you'd like me to focus on?")
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 3: Web search quality (+15 points)
    # ═══════════════════════════════════════════════════════════════════
    if web_search_results:
        # Count authoritative sources
        authoritative_domains = ['.gov', '.edu', '.org', 'wikipedia', 'official']
        quality_sources = 0
        total_content_length = 0
        
        for result in web_search_results[:5]:
            url = result.get('url', '').lower()
            content = result.get('content', '')
            total_content_length += len(content)
            
            if any(domain in url for domain in authoritative_domains):
                quality_sources += 1
        
        if quality_sources >= 2 and total_content_length > 5000:
            score += 15
            factors.append(("web_search_quality", 15, f"Found {quality_sources} authoritative sources"))
        elif total_content_length > 2000:
            score += 8
            factors.append(("web_search_partial", 8, "Web search returned some relevant content"))
        else:
            suggestions.append("Web search found limited results - consider being more specific")
    else:
        # No web search yet - this is OK, just note it
        factors.append(("no_web_search", 0, "Web search not yet performed"))
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 4: Clear scope/timeframe (+10 points)
    # ═══════════════════════════════════════════════════════════════════
    # Check for year mentions
    has_year = bool(re.search(r'\b(202[0-9]|203[0-9]|last year|this year|current)\b', msg_lower))
    
    # Check for industry/domain specification
    industry_keywords = ['healthcare', 'financial', 'legal', 'technology', 'manufacturing',
                        'retail', 'education', 'government', 'nonprofit', 'startup']
    has_industry = any(ind in msg_lower for ind in industry_keywords)
    
    # Check for geographic scope
    has_geography = bool(re.search(r'\b(atlanta|new york|california|usa|europe|global|local)\b', msg_lower, re.IGNORECASE))
    
    scope_points = 0
    scope_details = []
    if has_year:
        scope_points += 4
        scope_details.append("timeframe")
    if has_industry:
        scope_points += 4
        scope_details.append("industry")
    if has_geography:
        scope_points += 2
        scope_details.append("geography")
    
    if scope_points > 0:
        score += min(scope_points, 10)
        factors.append(("clear_scope", scope_points, f"Clear scope: {', '.join(scope_details)}"))
    else:
        clarifying_questions.append("What industry or domain is this report for?")
        if not has_year:
            clarifying_questions.append("Is there a specific timeframe or date range to focus on?")
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 5: Actionable request (+10 points)
    # ═══════════════════════════════════════════════════════════════════
    actionable_keywords = ['implement', 'plan', 'strategy', 'recommend', 'evaluate',
                          'compare', 'analyze', 'assess', 'proposal', 'roadmap',
                          'decision', 'choose', 'select', 'budget', 'roi']
    
    # Generic/weak request indicators
    weak_indicators = ['tell me about', 'what is', 'explain', 'describe', 'overview',
                      'information on', 'learn about']
    
    is_actionable = any(kw in msg_lower for kw in actionable_keywords)
    is_weak = any(w in msg_lower for w in weak_indicators) and not is_actionable
    
    if is_actionable:
        score += 10
        factors.append(("actionable_request", 10, "Clear actionable goal identified"))
    elif is_weak:
        score += 3
        factors.append(("general_inquiry", 3, "General inquiry - could be more specific"))
        suggestions.append("For a more actionable report, specify what decision or goal this supports")
    
    # ═══════════════════════════════════════════════════════════════════
    # FACTOR 6: Conversation context (+5 points)
    # ═══════════════════════════════════════════════════════════════════
    if conversation_history and len(conversation_history) > 0:
        score += 5
        factors.append(("conversation_context", 5, f"Building on {len(conversation_history)} prior messages"))
    
    # ═══════════════════════════════════════════════════════════════════
    # DETERMINE CONFIDENCE LEVEL AND DECISION
    # ═══════════════════════════════════════════════════════════════════
    if score >= 50:
        confidence_level = "high"
        can_proceed = True
        recommendation = "Sufficient context available - generating report"
    elif score >= 30:
        confidence_level = "medium"
        can_proceed = True
        recommendation = "Moderate context - report will be generated but may benefit from more specifics"
    else:
        confidence_level = "low"
        can_proceed = False
        recommendation = "Insufficient context - requesting clarification before generating report"
    
    # Limit clarifying questions to top 3 most important
    clarifying_questions = clarifying_questions[:3]
    
    logger.info(f"📊 Report Readiness Assessment: score={score}, confidence={confidence_level}, can_proceed={can_proceed}")
    for factor_name, points, desc in factors:
        logger.debug(f"  - {factor_name}: +{points} ({desc})")
    
    return {
        'score': score,
        'max_score': 100,
        'confidence_level': confidence_level,
        'can_proceed': can_proceed,
        'recommendation': recommendation,
        'factors': factors,
        'suggestions': suggestions,
        'clarifying_questions': clarifying_questions
    }


def generate_clarification_response(assessment: Dict[str, Any], original_message: str) -> str:
    """
    Generate a friendly response asking the user for more context before proceeding.
    
    Args:
        assessment: The report readiness assessment dict
        original_message: The user's original request
        
    Returns:
        A helpful message with clarifying questions
    """
    score = assessment['score']
    questions = assessment.get('clarifying_questions', [])
    suggestions = assessment.get('suggestions', [])
    
    # Build a friendly response
    response_parts = []
    
    # Opening
    response_parts.append("I'd be happy to generate a comprehensive report for you! To make sure I create something really useful, could you help me with a few details?\n")
    
    # Add clarifying questions
    if questions:
        response_parts.append("**A few quick questions:**")
        for i, q in enumerate(questions, 1):
            response_parts.append(f"{i}. {q}")
        response_parts.append("")
    
    # Add suggestions if any
    if suggestions:
        response_parts.append("**Tips for a better report:**")
        for s in suggestions:
            response_parts.append(f"• {s}")
        response_parts.append("")
    
    # Offer to proceed anyway
    response_parts.append("*Or if you'd like me to proceed with what I have, just say \"generate report anyway\" and I'll do my best!*")
    
    return "\n".join(response_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# URL INJECTION POST-PROCESSOR
# LLMs often ignore instructions to include URLs in References sections.
# This post-processor automatically injects URLs from web search results into
# the References section of generated reports.
# ═══════════════════════════════════════════════════════════════════════════════

# Pattern to extract URLs from the prompt context (from bee_context_manager formatting)
WEB_SOURCE_PATTERN = re.compile(
    r'--- SOURCE \d+ ---\s*\nTITLE:\s*(.+?)\nURL TO COPY:\s*(https?://[^\s\n]+)',
    re.IGNORECASE | re.MULTILINE
)

def extract_web_sources_from_prompt(prompt: str) -> Dict[str, str]:
    """
    Extract web source title->URL mappings from the enhanced prompt.
    The bee_context_manager formats sources with clear markers we can parse.
    
    Returns:
        Dict mapping normalized titles to their URLs
    """
    sources = {}
    matches = WEB_SOURCE_PATTERN.findall(prompt)
    for title, url in matches:
        # Normalize title for fuzzy matching
        normalized_title = title.strip().lower()
        # Also store cleaned version without special chars
        clean_title = re.sub(r'[^\w\s]', '', normalized_title)
        sources[normalized_title] = url.strip()
        sources[clean_title] = url.strip()
        # Store first few significant words for partial matching
        words = clean_title.split()
        if len(words) >= 3:
            sources[' '.join(words[:3])] = url.strip()
            sources[' '.join(words[:4])] = url.strip() if len(words) >= 4 else url.strip()
    return sources


def inject_urls_into_references(response: str, prompt: str) -> str:
    """
    Post-process a report to inject missing URLs into the References section.
    
    LLMs often include source titles but forget the actual URLs despite explicit
    instructions. This function:
    1. Extracts web source URLs from the prompt context
    2. Finds the References section in the response
    3. If no References section with URLs exists, APPENDS one from web sources
    
    Args:
        response: The generated report content
        prompt: The enhanced prompt that contained the web sources
        
    Returns:
        Response with URLs injected into References section
    """
    # Extract available URLs from prompt
    sources = extract_web_sources_from_prompt(prompt)
    if not sources:
        logger.info("📎 URL Injection: No web sources found in prompt")
        return response
    
    # Get unique URLs (sources dict has multiple keys pointing to same URL)
    unique_urls = {}
    for title, url in sources.items():
        if url not in unique_urls.values():
            # Use the longest title as the display name
            existing_title = [k for k, v in unique_urls.items() if v == url]
            if not existing_title or len(title) > len(existing_title[0]):
                # Remove shorter keys for this URL
                unique_urls = {k: v for k, v in unique_urls.items() if v != url}
                unique_urls[title] = url
    
    logger.info(f"📎 URL Injection: Found {len(unique_urls)} unique web sources")
    
    # Find ALL References/Sources sections (there might be duplicates from LLM)
    # Match patterns like "## References", "## References & Sources", "### Sources", etc.
    refs_pattern = re.compile(
        r'(#{1,3}\s*(?:References?(?:\s*[&]\s*Sources?)?|Sources?|Works?\s+Cited|Bibliography|Citations?|Further\s+Reading)\s*:?\s*\n)',
        re.IGNORECASE
    )
    
    # Find all matches
    all_matches = list(refs_pattern.finditer(response))
    
    if all_matches:
        # Use the FIRST reference section, remove any duplicates
        match = all_matches[0]
        
        # Found a References section - check if IT SPECIFICALLY has URLs
        refs_start = match.end()
        
        # Find the end of this section (next heading or end of document)
        # But also check if there's another reference section after this one
        if len(all_matches) > 1:
            # There are duplicate reference sections - we'll replace from first to after the last
            last_match = all_matches[-1]
            next_section_after_last = re.search(r'\n#{1,3}\s+(?!References|Sources)[A-Z]', response[last_match.end():])
            if next_section_after_last:
                refs_end = last_match.end() + next_section_after_last.start()
            else:
                refs_end = len(response)
            logger.info(f"📎 URL Injection: Found {len(all_matches)} reference sections - will consolidate")
        else:
            next_section = re.search(r'\n#{1,3}\s+[A-Z]', response[refs_start:])
            refs_end = refs_start + next_section.start() if next_section else len(response)
        
        refs_section = response[refs_start:refs_end]
        
        # Only check for URLs in the References section, not the whole response
        refs_urls = re.findall(r'https?://[^\s\)\]]+', refs_section)
        logger.info(f"📎 URL Injection: References section has {len(refs_urls)} URLs")
        
        if len(refs_urls) >= 2 and len(all_matches) == 1:
            logger.info(f"📎 URL Injection: References section already has {len(refs_urls)} URLs")
            return response
        
        # References section exists but has no/few URLs OR there are duplicates - replace everything
        logger.info(f"📎 URL Injection: {'Multiple sections found' if len(all_matches) > 1 else f'Only {len(refs_urls)} URLs'} - replacing")
        
        # Build new references section (reusing the original heading style)
        new_refs = []
        for title, url in list(unique_urls.items())[:5]:  # Max 5 sources
            # Clean up the title
            clean_title = title.strip().title() if len(title) < 100 else title[:100].strip().title() + "..."
            new_refs.append(f"- [{clean_title}]({url})")
        
        new_refs_section = '\n'.join(new_refs) + '\n'
        # Keep the original heading from first match, replace everything after with our refs
        response = response[:refs_start] + new_refs_section + response[refs_end:].lstrip()
        logger.info(f"📎 URL Injection: Replaced/consolidated References with {len(new_refs)} linked sources")
        
    else:
        # No References section found - append one
        logger.info("📎 URL Injection: No References section found - appending one")
        
        new_refs = ["\n\n## References\n"]
        for title, url in list(unique_urls.items())[:5]:  # Max 5 sources
            clean_title = title.strip().title() if len(title) < 100 else title[:100].strip().title() + "..."
            ref_line = f"- [{clean_title}]({url})"
            new_refs.append(ref_line)
            logger.info(f"📎 Adding reference: {ref_line[:100]}...")
        
        refs_text = '\n'.join(new_refs) + '\n'
        logger.info(f"📎 Full references section:\n{refs_text}")
        response = response.rstrip() + refs_text
        logger.info(f"📎 URL Injection: Appended References section with {len(new_refs)-1} sources")
    
    return response


def check_pii_tokens(content: str) -> Dict[str, Any]:
    """
    Check for unresolved PII tokens in content.
    
    PII tokens like [PII_NAME_1a2b3c] should be replaced with actual values
    during deserialization. If they remain, something went wrong.
    
    Returns:
        Dict with: passed, code, message, details
    """
    matches = PII_TOKEN_PATTERN.findall(content)
    
    if matches:
        unique_tokens = list(set(matches))
        return {
            'check': 'pii_validation',
            'passed': False,
            'code': 'PII_TOKENS_REMAINING',
            'message': f"Found {len(matches)} unresolved PII token(s): {', '.join(unique_tokens[:5])}{'...' if len(unique_tokens) > 5 else ''}",
            'severity': 'critical',
            'details': {
                'token_count': len(matches),
                'unique_tokens': unique_tokens[:10],
                'sample_positions': [content.find(t) for t in unique_tokens[:3]]
            }
        }
    
    return {
        'check': 'pii_validation',
        'passed': True,
        'code': 'PII_CLEAN',
        'message': 'No unresolved PII tokens found',
        'severity': 'info'
    }


def check_content_completeness(content: str, content_type: str = 'report') -> Dict[str, Any]:
    """
    Check if content appears complete (not truncated or too short).
    
    Args:
        content: The content to check
        content_type: 'report' or 'response' for different thresholds
        
    Returns:
        Dict with: passed, code, message, severity, details
    """
    min_length = MIN_REPORT_LENGTH if content_type == 'report' else MIN_RESPONSE_LENGTH
    content_stripped = content.strip()
    
    # Check minimum length
    if len(content_stripped) < min_length:
        return {
            'check': 'completeness',
            'passed': False,
            'code': 'OUTPUT_EMPTY' if len(content_stripped) < 10 else 'OUTPUT_TRUNCATED',
            'message': f"Content too short ({len(content_stripped)} chars, minimum {min_length})",
            'severity': 'error',
            'details': {'content_length': len(content_stripped), 'min_required': min_length}
        }
    
    # Check for truncation indicators
    truncation_indicators = [
        content_stripped.endswith('...') and not content_stripped.endswith('....'),
        content_stripped.endswith('…'),
        # Check if ends mid-sentence (no proper ending punctuation)
        len(content) > 100 and not any(content_stripped.endswith(p) for p in ['.', '!', '?', ':', '"', "'", ')', ']', '`'])
    ]
    
    if any(truncation_indicators):
        return {
            'check': 'completeness',
            'passed': True,  # Warning, not hard failure
            'severity': 'warning',
            'code': 'POSSIBLY_TRUNCATED',
            'message': 'Content may be truncated (ends abruptly)',
            'details': {'ending': content[-50:] if len(content) > 50 else content}
        }
    
    return {
        'check': 'completeness',
        'passed': True,
        'code': 'COMPLETE',
        'message': 'Content appears complete',
        'severity': 'info',
        'details': {'content_length': len(content_stripped)}
    }


def extract_requirements_from_request(original_request: str) -> Dict[str, Any]:
    """
    Extract explicit and implicit requirements from the original user request.
    
    This helps ReviewBee understand what the user actually asked for,
    so it can validate the output against the ORIGINAL ASK.
    """
    requirements = {
        'word_count': None,
        'sections_requested': [],
        'topics_mentioned': [],
        'format_hints': [],
        'tone_hints': [],
        'explicit_asks': []
    }
    
    text_lower = original_request.lower()
    
    # Extract word count requirements
    import re
    word_patterns = [
        r'(\d+)\s*(?:word|words)',
        r'(?:at least|minimum|around|about)\s*(\d+)',
        r'(\d+)\s*(?:character|char)',
    ]
    for pattern in word_patterns:
        match = re.search(pattern, text_lower)
        if match:
            requirements['word_count'] = int(match.group(1))
            break
    
    # Extract section hints
    section_keywords = ['executive summary', 'introduction', 'conclusion', 'recommendations', 
                        'analysis', 'findings', 'methodology', 'overview', 'details', 'summary']
    for keyword in section_keywords:
        if keyword in text_lower:
            requirements['sections_requested'].append(keyword)
    
    # Extract format hints
    format_keywords = {
        'bullet': 'bullet points',
        'numbered': 'numbered list', 
        'table': 'table format',
        'markdown': 'markdown',
        'detailed': 'detailed analysis',
        'brief': 'brief summary',
        'comprehensive': 'comprehensive coverage'
    }
    for key, hint in format_keywords.items():
        if key in text_lower:
            requirements['format_hints'].append(hint)
    
    # Extract tone hints
    tone_keywords = {
        'formal': 'formal tone',
        'professional': 'professional tone',
        'technical': 'technical language',
        'simple': 'simple language',
        'executive': 'executive-level'
    }
    for key, hint in tone_keywords.items():
        if key in text_lower:
            requirements['tone_hints'].append(hint)
    
    # Extract explicit questions/asks (sentences ending with ?)
    questions = re.findall(r'[^.!?]*\?', original_request)
    requirements['explicit_asks'] = [q.strip() for q in questions if len(q.strip()) > 10][:5]
    
    return requirements


def validate_revision_quality(original: str, revised: str, check_pii: bool = True) -> Dict[str, Any]:
    """
    Validate that a revision is actually an improvement, not a degradation.
    
    Unified QA gate that checks:
    - PII tokens (critical - must not have unresolved tokens)
    - Length ratio (revision shouldn't be drastically shorter)
    - Character encoding (no unexpected unicode/CJK characters)
    - Structure preservation (headings, sections)
    - Content completeness (not truncated)
    """
    validation = {
        'is_valid': True,
        'rejection_reasons': [],
        'warnings': [],
        'metrics': {},
        'checks': []
    }
    
    # PII Token Check (CRITICAL - unresolved tokens are a security issue)
    if check_pii:
        pii_result = check_pii_tokens(revised)
        validation['checks'].append(pii_result)
        validation['metrics']['pii_tokens_found'] = pii_result['details'].get('token_count', 0) if not pii_result['passed'] else 0
        
        if not pii_result['passed']:
            validation['is_valid'] = False
            validation['rejection_reasons'].append(f"SECURITY: {pii_result['message']}")
    
    # Hallucination Check (NEW - catches garbage patterns, duplicate sections, broken URLs)
    hallucination_result = check_hallucinations(revised)
    validation['checks'].append(hallucination_result)
    validation['metrics']['hallucination_issues'] = len(hallucination_result.get('details', {}))
    
    if not hallucination_result['passed']:
        validation['is_valid'] = False
        validation['rejection_reasons'].append(f"QUALITY: {hallucination_result['message']}")
        logger.warning(f"🐝 ReviewBee: Hallucination detected - {hallucination_result['message']}")
    
    # Content Completeness Check
    completeness_result = check_content_completeness(revised, 'report')
    validation['checks'].append(completeness_result)
    validation['metrics']['content_length'] = len(revised.strip())
    
    if not completeness_result['passed']:
        validation['is_valid'] = False
        validation['rejection_reasons'].append(completeness_result['message'])
    elif completeness_result.get('severity') == 'warning':
        validation['warnings'].append(completeness_result['message'])
    
    # Length check - revision shouldn't lose more than 30% of content
    original_len = len(original)
    revised_len = len(revised)
    length_ratio = revised_len / original_len if original_len > 0 else 0
    validation['metrics']['length_ratio'] = length_ratio
    
    if length_ratio < 0.7:
        validation['is_valid'] = False
        validation['rejection_reasons'].append(f"Revision too short: {length_ratio:.1%} of original")
    
    # Character encoding check - flag unexpected CJK/Arabic/etc.
    # Check for unexpected script characters (CJK, Arabic, Hebrew, etc.)
    unexpected_scripts = re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u0600-\u06ff\u0590-\u05ff]', revised)
    original_scripts = re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u0600-\u06ff\u0590-\u05ff]', original)
    
    # Only flag if revision has MORE unexpected characters than original
    if len(unexpected_scripts) > len(original_scripts) + 5:
        validation['is_valid'] = False
        validation['rejection_reasons'].append(f"Revision contains {len(unexpected_scripts)} unexpected characters")
    
    validation['metrics']['unexpected_chars'] = len(unexpected_scripts)
    
    # Structure check - count markdown headers
    original_headers = len(re.findall(r'^#{1,6}\s', original, re.MULTILINE))
    revised_headers = len(re.findall(r'^#{1,6}\s', revised, re.MULTILINE))
    validation['metrics']['original_headers'] = original_headers
    validation['metrics']['revised_headers'] = revised_headers
    
    # If original had headers but revision lost most of them, flag it
    if original_headers > 2 and revised_headers < original_headers * 0.5:
        validation['is_valid'] = False
        validation['rejection_reasons'].append(f"Lost document structure: {original_headers} → {revised_headers} headers")
    
    return validation


async def run_review_bee_critic(
    report_content: str,
    original_prompt: str,
    critic_model: str = "microsoft/phi-4-mini-reasoning",
    pii_context: Dict[str, Any] = None,
    user_message: str = None
) -> Dict[str, Any]:
    """
    Run ReviewBee critic analysis on a generated report.
    
    ReviewBee's core purpose is to compare the FINAL OUTPUT against the ORIGINAL ASK.
    It doesn't need all context - just enough to enforce strict, clear requirements.
    
    Architecture:
    1. Extract requirements from original request (word count, sections, explicit asks)
    2. Compare report against those specific requirements
    3. Check grammar, structure, and professional quality
    4. Generate a structured TASK LIST for the regenerating model
    5. Return actionable feedback for improvement
    
    Args:
        report_content: The generated report text to analyze
        original_prompt: The full prompt used to generate the report
        critic_model: The lightweight model to use for critique (default: microsoft/phi-4-mini-reasoning)
        pii_context: Optional PII context for awareness during critique
        user_message: The original user message/request (if available separately)
        
    Returns:
        Dict containing:
        - score: Overall quality score (0.0-1.0)
        - requirements_met: Which requirements from original ask were satisfied
        - task_list: Structured list of tasks for regeneration
        - revision_feedback: Formatted feedback for regeneration prompt
        - pii_check: PII token validation result
        - completeness_check: Content completeness check result
    """
    # Initialize result structure
    result = {
        'score': 1.0,
        'findings': [],
        'task_list': [],
        'revision_feedback': '',
        'pii_check': None,
        'completeness_check': None,
        'safety_passed': True,
        'quality_passed': True
    }
    
    if not report_content or len(report_content) < 100:
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SAFETY CHECKS (Run first - these are critical)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # 1. PII Token Check - CRITICAL
    # Check if there are unresolved PII tokens that should have been replaced
    # Only check if pii_context indicates PII was expected (otherwise tokens are intentional)
    pii_result = check_pii_tokens(report_content)
    result['pii_check'] = pii_result
    result['findings'].append(pii_result)
    
    # If PII context says we SHOULD have resolved tokens but we still have them, fail
    if not pii_result['passed']:
        if pii_context and pii_context.get('pii_count', 0) == 0:
            # No PII was expected, but we found tokens - this is a problem
            result['safety_passed'] = False
            logger.warning(f"🐝 ReviewBee SECURITY: Found unresolved PII tokens: {pii_result['message']}")
    
    # 2. Completeness Check
    completeness_result = check_content_completeness(report_content, 'report')
    result['completeness_check'] = completeness_result
    result['findings'].append(completeness_result)
    
    if not completeness_result['passed']:
        result['quality_passed'] = False
        logger.warning(f"🐝 ReviewBee: Content completeness failed: {completeness_result['message']}")
    
    # 3. Hallucination Detection - STRICT MODE
    # Check for garbage patterns, duplicate sections, broken URLs, FABRICATED NAMES
    hallucination_result = check_hallucinations(report_content)
    result['hallucination_check'] = hallucination_result
    result['findings'].append(hallucination_result)
    
    if not hallucination_result['passed']:
        details = hallucination_result.get('details', {})
        
        # CRITICAL: Fabricated names = automatic rejection
        if 'fabricated_names' in details or 'unsourced_bios' in details:
            result['quality_passed'] = False
            result['safety_passed'] = False  # Treat fabrication as safety issue
            result['score'] = 0.0  # Complete rejection
            result['rejected'] = True
            result['rejection_reason'] = "FABRICATED_CONTENT"
            result['task_list'].append("⛔ CRITICAL: Report contains fabricated person names/biographies")
            result['task_list'].append("REJECT: Do not output invented names - acknowledge information was not found")
            if 'fabricated_names' in details:
                result['task_list'].append(f"Fabricated names detected: {details['fabricated_names']}")
            logger.error(f"🐝 ReviewBee REJECTED: Fabricated names detected - {details.get('fabricated_names', details.get('unsourced_bios', 'unknown'))}")
        else:
            # Other hallucinations (garbage text, broken links) - quality failure only
            result['quality_passed'] = False
            result['score'] = min(result['score'], 0.4)
            for key, value in details.items():
                if key == 'duplicate_headers':
                    result['task_list'].append(f"Remove duplicate section headers: {value[:2]}")
                elif key == 'garbage_urls' or key == 'long_urls':
                    result['task_list'].append("Fix or remove malformed/garbage URLs in references")
                elif key == 'repetitive_patterns':
                    result['task_list'].append(f"Remove repetitive garbage text patterns")
                elif key == 'broken_links':
                    result['task_list'].append("Fix broken markdown links that span multiple lines")
            logger.warning(f"🐝 ReviewBee: Hallucination detected - {hallucination_result['message']}")
    
    # 4. Reference Relevance Check - STRICT MODE
    # Check if references actually match the topic (catches search returning wrong results)
    reference_result = check_reference_relevance(report_content, user_message or original_prompt)
    result['reference_check'] = reference_result
    result['findings'].append(reference_result)
    
    if not reference_result['passed']:
        details = reference_result.get('details', {})
        mismatch_count = len(details.get('mismatches', []))
        
        # If majority of references are mismatched, reject the report
        if mismatch_count >= 3 or reference_result.get('code') == 'MAJOR_MISMATCH':
            result['quality_passed'] = False
            result['safety_passed'] = False
            result['score'] = 0.0
            result['rejected'] = True
            result['rejection_reason'] = "IRRELEVANT_SOURCES"
            result['task_list'].append("⛔ CRITICAL: Web search returned completely wrong results")
            result['task_list'].append(f"User asked about: {details.get('expected_type', 'unknown')}")
            result['task_list'].append(f"Sources are about: {details.get('mismatches', ['unknown'])[:3]}")
            result['task_list'].append("REJECT: Cannot generate accurate report with wrong sources")
            logger.error(f"🐝 ReviewBee REJECTED: Sources don't match query - expected {details.get('expected_type')}, got {details.get('mismatches', [])[:3]}")
        else:
            result['quality_passed'] = False
            result['score'] = min(result['score'], 0.3)
            result['task_list'].append("CRITICAL: References don't match the topic - web search returned wrong results")
            result['task_list'].append("Either find correct sources or explicitly state the information was not available")
            logger.warning(f"🐝 ReviewBee: Reference mismatch - {reference_result['message']}")
    
    # 5. Claim Verification Check - NEW
    # Re-search specific claims (names, statistics) to catch fabrications
    try:
        claim_result = await verify_claims_with_search(report_content, user_message or original_prompt)
        result['claim_verification'] = claim_result
        
        if not claim_result.get('verified', True):
            # Don't fail outright, but add warnings
            result['warnings'] = result.get('warnings', []) + claim_result.get('warnings', [])
            result['score'] = min(result['score'], 0.6)  # Reduce score for unverified claims
            
            for warning in claim_result.get('warnings', []):
                result['task_list'].append(f"WARNING: {warning}")
            
            logger.warning(f"🐝 ReviewBee: Claim verification issues - {claim_result.get('warnings', [])}")
    except Exception as e:
        logger.debug(f"Claim verification skipped: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REQUIREMENTS ANALYSIS (LLM-powered)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Extract what the user actually asked for
    request_text = user_message or original_prompt
    requirements = extract_requirements_from_request(request_text)
    
    # Build PII awareness note
    pii_note = ""
    if pii_context and pii_context.get('pii_count', 0) > 0:
        pii_note = "\n\nIMPORTANT: Tokens like [PII_NAME_1], [PII_EMAIL_1] are INTENTIONAL privacy protections. Do NOT flag these as issues."
    
    # Build requirements context for the critic
    req_context = []
    if requirements['word_count']:
        req_context.append(f"- Requested length: approximately {requirements['word_count']} words")
    if requirements['sections_requested']:
        req_context.append(f"- Requested sections: {', '.join(requirements['sections_requested'])}")
    if requirements['format_hints']:
        req_context.append(f"- Format requirements: {', '.join(requirements['format_hints'])}")
    if requirements['explicit_asks']:
        req_context.append(f"- Questions to answer: {len(requirements['explicit_asks'])} explicit questions")
    
    requirements_text = '\n'.join(req_context) if req_context else "No explicit requirements detected"
    
    # Truncate content for critic (keep it focused)
    report_preview = report_content[:6000]
    request_preview = request_text[:1500]
    
    critic_prompt = f"""You are ReviewBee 🐝 - a strict quality reviewer for generated reports.

YOUR CORE MISSION: Compare the GENERATED REPORT against the ORIGINAL USER REQUEST.
Verify the report actually delivers what the user asked for.

═══════════════════════════════════════════════════════════════
ORIGINAL USER REQUEST:
═══════════════════════════════════════════════════════════════
{request_preview}

═══════════════════════════════════════════════════════════════
EXTRACTED REQUIREMENTS:
═══════════════════════════════════════════════════════════════
{requirements_text}

═══════════════════════════════════════════════════════════════
GENERATED REPORT TO REVIEW:
═══════════════════════════════════════════════════════════════
{report_preview}
{pii_note}

═══════════════════════════════════════════════════════════════
YOUR REVIEW CHECKLIST:
═══════════════════════════════════════════════════════════════

1. **REQUIREMENTS FULFILLMENT** (Most Important!)
   - Does the report answer what was actually asked?
   - Are all explicit questions addressed?
   - Does it cover the requested topics/scope?

2. **COMPLETENESS**
   - Any gaps or missing information?
   - Are conclusions supported by the content?

3. **STRUCTURE & ORGANIZATION**
   - Clear sections and flow?
   - Appropriate headers and formatting?

4. **GRAMMAR & CLARITY**
   - Spelling, grammar, punctuation errors?
   - Clear, professional language?

5. **ACCURACY & TRUTH**
   - Any inconsistencies or contradictions?
   - Claims that seem unsupported?

═══════════════════════════════════════════════════════════════
RESPOND IN THIS EXACT FORMAT:
═══════════════════════════════════════════════════════════════

REQUIREMENTS_MET: [YES/PARTIAL/NO]
SCORE: [0.0-1.0 where 1.0 means fully meets requirements]

GAPS:
- [What's missing from the original request]

ISSUES:
- [Grammar, structure, or clarity problems]

TASK_LIST:
1. [Specific task to fix gap/issue #1]
2. [Specific task to fix gap/issue #2]
3. [Specific task to fix gap/issue #3]

If the report fully addresses the request with no issues, respond:
REQUIREMENTS_MET: YES
SCORE: 0.95
GAPS: None
ISSUES: None
TASK_LIST: None"""

    try:
        # Call the critic model
        critic_options = {
            'num_predict': 1200,  # Enough for detailed review
            'temperature': 0.2,   # Very deterministic for analysis
        }
        
        llm_result = await generate_with_fallback(critic_prompt, critic_model, critic_options)
        critique_text = llm_result.get("response", "")
        
        # Parse the structured critique response
        score = 0.85  # Default if parsing fails
        requirements_met = "PARTIAL"
        gaps = []
        issues = []
        task_list = []
        
        lines = critique_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('REQUIREMENTS_MET:'):
                requirements_met = line.replace('REQUIREMENTS_MET:', '').strip().upper()
                if requirements_met not in ['YES', 'PARTIAL', 'NO']:
                    requirements_met = 'PARTIAL'
                    
            elif line.startswith('SCORE:'):
                try:
                    score_str = line.replace('SCORE:', '').strip()
                    # Handle formats like "0.7" or "0.7/1.0" or "7/10"
                    if '/' in score_str:
                        parts = score_str.split('/')
                        score = float(parts[0]) / float(parts[1])
                    else:
                        score = float(score_str.split()[0])  # Take first number
                    score = max(0.0, min(1.0, score))
                except:
                    pass
                    
            elif line.startswith('GAPS:'):
                current_section = 'gaps'
            elif line.startswith('ISSUES:'):
                current_section = 'issues'
            elif line.startswith('TASK_LIST:'):
                current_section = 'tasks'
            elif current_section and line.startswith(('-', '•')):
                item = line.lstrip('-•').strip()
                if item and len(item) > 3 and item.lower() != 'none':
                    if current_section == 'gaps':
                        gaps.append(item)
                    elif current_section == 'issues':
                        issues.append(item)
            elif current_section == 'tasks' and line and line[0].isdigit():
                # Parse numbered task items like "1. Task description"
                import re
                task_match = re.match(r'^\d+[\.\)]\s*(.+)', line)
                if task_match:
                    task = task_match.group(1).strip()
                    if task and task.lower() != 'none':
                        task_list.append(task)
        
        # Generate structured revision feedback with task list
        revision_feedback = ""
        if task_list or gaps or issues:
            feedback_parts = ["**REVIEWER FEEDBACK - Please address the following:**\n"]
            
            if requirements_met != 'YES':
                feedback_parts.append(f"⚠️ Requirements fulfillment: {requirements_met}\n")
            
            if gaps:
                feedback_parts.append("**Missing from original request:**")
                for g in gaps[:3]:
                    feedback_parts.append(f"  → {g}")
                feedback_parts.append("")
            
            if issues:
                feedback_parts.append("**Issues to fix:**")
                for i in issues[:3]:
                    feedback_parts.append(f"  → {i}")
                feedback_parts.append("")
            
            if task_list:
                feedback_parts.append("**Your task list:**")
                for idx, task in enumerate(task_list[:5], 1):
                    feedback_parts.append(f"  {idx}. {task}")
            
            feedback_parts.append("")
            feedback_parts.append("**IMPORTANT: Generate ONLY the revised report content. Do NOT include any meta-commentary, acknowledgment of feedback, or explanation of what you changed. The output should be a clean, polished report ready for the reader.**")
            
            revision_feedback = '\n'.join(feedback_parts)
        
        # Update result with LLM analysis
        result['score'] = score
        result['requirements_met'] = requirements_met
        result['gaps'] = gaps
        result['issues'] = issues
        result['task_list'] = task_list
        result['findings'] = result['findings'] + gaps + issues  # Combine with safety checks
        result['revision_feedback'] = revision_feedback
        result['extracted_requirements'] = requirements
        result['raw_critique'] = critique_text[:800]  # For debugging
        
        # Determine overall quality pass/fail
        if requirements_met == 'NO' or score < 0.5:
            result['quality_passed'] = False
        
        logger.info(f"🐝 ReviewBee: score={score:.2f}, req_met={requirements_met}, gaps={len(gaps)}, tasks={len(task_list)}, safety={result['safety_passed']}, quality={result['quality_passed']}")
        
        return result
        
    except Exception as e:
        logger.error(f"🐝 ReviewBee critic error: {e}")
        result['error'] = str(e)
        return result  # Return with safety checks still included


async def verify_claims_with_search(
    report_content: str,
    original_request: str,
    web_search_provider = None
) -> Dict[str, Any]:
    """
    Post-generation verification: Re-search key claims from the report.
    
    This catches when the LLM invents specific facts (names, dates, statistics)
    that aren't supported by actual web sources.
    
    Args:
        report_content: The generated report text
        original_request: The original user request
        web_search_provider: Optional WebSearchProvider instance
        
    Returns:
        Dict with verification results
    """
    result = {
        'verified': True,
        'claims_checked': 0,
        'claims_verified': 0,
        'unverified_claims': [],
        'warnings': []
    }
    
    # Only run if web search is available
    if web_search_provider is None:
        try:
            from web_search_provider import get_web_search_provider
            web_search_provider = get_web_search_provider()
        except:
            return result
    
    if not web_search_provider or not web_search_provider.enabled:
        return result
    
    try:
        # Extract potential claims to verify
        # Focus on: specific names, specific numbers/statistics, specific dates
        claims_to_verify = []
        
        # Pattern 1: Names (Dr. X, Mr. Y, CEO John Smith, etc.)
        name_patterns = [
            r'\b(Dr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'\b(CEO|CFO|Director|President|Chairman)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(MD|PhD|Jr\.|Sr\.)',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, report_content)
            for match in matches:
                if isinstance(match, tuple):
                    name = ' '.join(match).strip()
                else:
                    name = match.strip()
                if len(name) > 5 and name not in claims_to_verify:
                    claims_to_verify.append(('name', name))
        
        # Pattern 2: Specific statistics with percentages
        stat_pattern = r'(\d{1,3}(?:\.\d+)?%\s+(?:of|increase|decrease|growth|decline))'
        stats = re.findall(stat_pattern, report_content)
        for stat in stats[:3]:  # Limit to 3 stats
            claims_to_verify.append(('statistic', stat))
        
        # Limit total claims to check (performance)
        claims_to_verify = claims_to_verify[:5]
        result['claims_checked'] = len(claims_to_verify)
        
        if not claims_to_verify:
            return result
        
        # Extract organization context from request
        org_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        organizations = re.findall(org_pattern, original_request)
        org_context = organizations[0] if organizations else ''
        
        # Verify each claim
        for claim_type, claim in claims_to_verify:
            try:
                # Build verification query
                if claim_type == 'name' and org_context:
                    verify_query = f'"{claim}" {org_context}'
                else:
                    verify_query = f'"{claim}"'
                
                # Quick search (don't fetch full content)
                search_results = await web_search_provider.search(verify_query, max_results=3)
                
                # Check if claim appears in any results
                found = False
                claim_lower = claim.lower()
                for r in search_results:
                    title = r.get('title', '').lower()
                    snippet = r.get('snippet', '').lower()
                    if claim_lower in title or claim_lower in snippet:
                        found = True
                        break
                
                if found:
                    result['claims_verified'] += 1
                else:
                    result['unverified_claims'].append({
                        'type': claim_type,
                        'claim': claim,
                        'search_query': verify_query
                    })
                    
            except Exception as e:
                logger.debug(f"Error verifying claim '{claim}': {e}")
        
        # Determine if verification failed
        if result['claims_checked'] > 0:
            verification_rate = result['claims_verified'] / result['claims_checked']
            if verification_rate < 0.5:
                result['verified'] = False
                result['warnings'].append(
                    f"Only {result['claims_verified']}/{result['claims_checked']} specific claims could be verified"
                )
                
            # Add specific warnings for unverified names
            name_claims = [c for c in result['unverified_claims'] if c['type'] == 'name']
            if name_claims:
                names = [c['claim'] for c in name_claims]
                result['warnings'].append(
                    f"Could not verify these names: {', '.join(names[:3])}"
                )
        
        logger.info(f"🔍 Claim verification: {result['claims_verified']}/{result['claims_checked']} verified")
        
    except Exception as e:
        logger.error(f"Error in claim verification: {e}")
    
    return result


async def send_review_bee_webhook(
    review_result: Dict[str, Any],
    target_type: str = 'report',
    target_id: str = None,
    webhook_url: str = None
) -> bool:
    """
    Send ReviewBee results to configured webhook endpoint.
    
    This allows external systems to be notified of review results,
    enabling integrations with:
    - Alert systems (notify on critical failures)
    - Analytics dashboards
    - CI/CD pipelines
    - Audit logging systems
    
    Args:
        review_result: The result from run_review_bee_critic()
        target_type: 'report' or 'response'
        target_id: Identifier for the reviewed content
        webhook_url: Optional override for webhook URL
        
    Returns:
        True if webhook was sent successfully, False otherwise
    """
    # Get webhook URL from config or parameter
    configured_url = llm_config.get('review_bee_webhook_url', webhook_url)
    
    if not configured_url:
        # No webhook configured - this is normal, not an error
        return True
    
    try:
        payload = {
            'event_type': 'review_bee.review_complete',
            'timestamp': datetime.utcnow().isoformat(),
            'target_type': target_type,
            'target_id': target_id,
            'review_result': {
                'score': review_result.get('score', 1.0),
                'safety_passed': review_result.get('safety_passed', True),
                'quality_passed': review_result.get('quality_passed', True),
                'requirements_met': review_result.get('requirements_met', 'UNKNOWN'),
                'pii_check': review_result.get('pii_check', {}).get('code', 'NOT_RUN'),
                'task_count': len(review_result.get('task_list', [])),
                'gap_count': len(review_result.get('gaps', [])),
                'issue_count': len(review_result.get('issues', []))
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                configured_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False  # Allow self-signed certs
            ) as response:
                if response.status == 200:
                    logger.info(f"🐝 ReviewBee webhook sent successfully to {configured_url}")
                    return True
                else:
                    logger.warning(f"🐝 ReviewBee webhook returned status {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"🐝 ReviewBee webhook error: {e}")
        return False


# Initialize PII Middleware (basic initialization, enhanced components added in startup_event)
pii_middleware = None
mode_detector = None
pii_analytics = None  # PII analytics instance
app_config = None  # Store config for startup event
llm_config = {}   # Store LLM configuration (max_tokens, temperature, etc.)
if PIIMiddleware is not None:
    try:
        import yaml
        config_path = os.getenv("CONFIG_PATH", "/app/conf/config.yml")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                app_config = yaml.safe_load(f)
                security_config = app_config.get('security', {})
                pii_middleware = PIIMiddleware(security_config)

                # Load LLM configuration for Bee chat
                conversation_config = security_config.get('conversation', {})
                llm_config.update({
                    'max_tokens': conversation_config.get('max_tokens', 4096),
                    'temperature': conversation_config.get('temperature', 0.7),
                })
                logger.info(f"LLM config loaded: max_tokens={llm_config['max_tokens']}, temperature={llm_config['temperature']}")

                # Load report generation configuration
                llm_service_config = app_config.get('llm_service', {})
                report_gen_config = llm_service_config.get('report_generation', {})
                llm_config.update({
                    'report_model': report_gen_config.get('model', 'qwen2.5-14b-instruct'),
                    'report_fallback_model': report_gen_config.get('fallback_model', 'qwen2.5-14b-instruct'),
                    'report_max_tokens': report_gen_config.get('max_tokens', 8192),
                    'report_min_output_tokens': report_gen_config.get('min_output_tokens', 4500),
                })
                logger.info(f"Report generation config loaded: model={llm_config['report_model']}, max_tokens={llm_config['report_max_tokens']}")

                # Load ReviewBee configuration (Critic-Revise pattern for report improvement)
                review_bee_config = llm_service_config.get('review_bee', {})
                critic_config = review_bee_config.get('critic', {})
                llm_config.update({
                    'review_bee_enabled': review_bee_config.get('enabled', False),
                    'review_bee_mode': review_bee_config.get('mode', 'critique_only'),
                    'review_bee_critic_model': critic_config.get('model', 'microsoft/phi-4-mini-reasoning'),
                    'review_bee_critic_fallback': critic_config.get('fallback_model', 'qwen2.5-14b-instruct'),
                    'review_bee_critic_timeout': critic_config.get('timeout_seconds', 30),
                    'review_bee_max_iterations': review_bee_config.get('max_iterations', 1),
                    'review_bee_improvement_threshold': review_bee_config.get('revision_threshold', 0.75),
                    'review_bee_include_pii_context': review_bee_config.get('include_pii_context', True),
                })
                if llm_config['review_bee_enabled']:
                    logger.info(f"ReviewBee enabled: mode={llm_config['review_bee_mode']}, critic_model={llm_config['review_bee_critic_model']}")

                # Initialize mode detector for intelligent PII protection mode selection
                if ModeDetector is not None:
                    pii_config = security_config.get('message_pii_protection', {})
                    mode_detector = ModeDetector(pii_config)
                    logger.info("PII mode detector initialized (auto-detection enabled)")

                # Initialize PII analytics
                if get_analytics_instance is not None:
                    pii_analytics = get_analytics_instance()
                    logger.info("PII analytics initialized")

                logger.info("PII middleware initialized (will upgrade to enhanced mode in startup)")
        else:
            logger.warning(f"Config file not found at {config_path}, PII middleware disabled")
    except Exception as e:
        logger.error(f"Failed to initialize PII middleware: {e}")
        logger.warning("PII protection will be disabled for this service")
else:
    logger.warning("PII middleware module not available, protection disabled")

# Worker task handle
worker_task = None

# Global flag for indexing status (threading.Event for async-safe status)
is_indexing = threading.Event()

@app.get("/health")
async def health_check():
    """Health check endpoint that remains responsive during indexing"""
    if is_indexing.is_set():
        # During indexing, return a special status but still respond
        return {
            "status": "healthy",
            "service": "external-ai",
            "indexing": True,
            "timestamp": datetime.now().isoformat()
        }
    return {
        "status": "healthy",
        "service": "external-ai",
        "indexing": False,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/llm/status")
async def llm_status():
    """Get status of all LLM providers including MiniMax and Ollama.
    
    Returns health status, failure stats, and current primary provider configuration.
    Use this endpoint for monitoring and alerting integration.
    """
    # Get status from all registered providers (returns complete status structure)
    return await provider_registry.get_all_status()


@app.get("/api/pii/diagnostics")
async def pii_diagnostics():
    """
    PII Protection System Health and Diagnostics Endpoint

    Returns comprehensive diagnostics about the PII protection system including:
    - Cache performance metrics (hit rate, misses, errors)
    - Redis connection status
    - System health score
    - Operational recommendations

    This endpoint is critical for enterprise audit compliance and monitoring.
    """
    if not pii_middleware:
        return {
            "status": "disabled",
            "message": "PII protection middleware not loaded",
            "timestamp": datetime.now().isoformat()
        }

    # Check if enhanced deserializer is available
    if isinstance(getattr(pii_middleware, 'deserializer', None), EnhancedDeserializer):
        # Get comprehensive diagnostics from enhanced components
        deserializer = pii_middleware.deserializer
        cache_manager = pii_middleware.cache_manager

        # Get cache diagnostics
        if hasattr(cache_manager, 'get_diagnostics'):
            cache_diagnostics = cache_manager.get_diagnostics()
            cache_stats = cache_diagnostics.get('cache_stats', {})

            # Calculate health metrics
            total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            if total_requests > 0:
                hit_rate = cache_stats.get('hits', 0) / total_requests
                health_score = "healthy" if hit_rate > 0.8 else "degraded" if hit_rate > 0.5 else "unhealthy"
            else:
                hit_rate = 0
                health_score = "no_data"

            # Generate recommendations
            recommendations = []
            if cache_stats.get('misses', 0) > cache_stats.get('hits', 0):
                recommendations.append("High cache miss rate - consider increasing TTL in config.yml (current: 300s)")
            if cache_stats.get('errors', 0) > 10:
                recommendations.append("Redis connection issues detected - check Redis connectivity and logs")
            if cache_stats.get('fallback_used', 0) > 100:
                recommendations.append("Heavy fallback usage - Redis may be unavailable or overloaded")
            if cache_diagnostics.get('local_cache_size', 0) > 1000:
                recommendations.append("Large local cache - consider increasing Redis stability")

            # Get mode detection info
            mode_detection_info = None
            if mode_detector:
                # Get actual primary provider info for accurate detection
                provider_name, provider_url, is_cloud = get_primary_provider_info()
                detected_mode, mode_config = mode_detector.detect_mode(
                    endpoint_url=provider_url,
                    provider=provider_name,
                    context="chat",
                    is_cloud_provider=is_cloud
                )
                mode_detection_info = {
                    "enabled": mode_detector.auto_detection_config.get('enabled', False),
                    "primary_provider": provider_name,
                    "is_cloud_provider": is_cloud,
                    "current_endpoint": provider_url,
                    "detected_mode": detected_mode,
                    "protection_level": mode_config.get('protection_level', 'unknown'),
                    "mode_enabled": mode_config.get('enabled', False),
                    "protected_pii_types": mode_config.get('pii_types', []),
                    "detection_method": "cloud_provider" if is_cloud else ("auto_detected" if mode_detector.auto_detection_config.get('enabled') else "manual_config"),
                    "fallback_mode": mode_detector.auto_detection_config.get('fallback_mode', 'external'),
                    "trusted_networks": mode_detector.auto_detection_config.get('trusted_networks', []),
                    "request_overrides_enabled": mode_detector.override_config.get('enabled', False)
                }

            return {
                "status": health_score,
                "hit_rate": round(hit_rate, 3),
                "cache_diagnostics": cache_diagnostics,
                "deserializer_diagnostics": deserializer.diagnostics,
                "mode_detection": mode_detection_info,
                "recommendations": recommendations,
                "enhanced_mode": True,
                "features": {
                    "position_tracking": True,
                    "visual_indicators": True,
                    "fallback_cache": True,
                    "diagnostics": True,
                    "intelligent_mode_detection": mode_detector is not None
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Enhanced deserializer but no full diagnostics
            return {
                "status": "enhanced_basic",
                "message": "Enhanced deserializer active but cache diagnostics unavailable",
                "deserializer_diagnostics": deserializer.diagnostics,
                "enhanced_mode": True,
                "timestamp": datetime.now().isoformat()
            }
    else:
        # Basic middleware without enhanced features
        return {
            "status": "basic",
            "message": "Basic PII middleware active (no position tracking or visual indicators)",
            "enhanced_mode": False,
            "features": {
                "position_tracking": False,
                "visual_indicators": False,
                "fallback_cache": False,
                "diagnostics": False
            },
            "recommendation": "Restart service to enable enhanced PII features with visual indicators",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/pii/analytics")
async def get_pii_analytics():
    """
    Get comprehensive PII protection analytics.
    
    Returns real-time metrics including:
    - Total operations (serializations/deserializations)
    - PII items protected
    - Cache hit rates
    - Protection mode distribution
    - PII type distribution
    - Provider usage
    - Recent events
    """
    if not pii_analytics:
        return {
            "status": "unavailable",
            "message": "PII analytics not initialized",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        analytics = await pii_analytics.get_analytics()
        return {
            "status": "ok",
            **analytics
        }
    except Exception as e:
        logger.error(f"Failed to get PII analytics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/pii/analytics/summary")
async def get_pii_analytics_summary():
    """
    Get quick summary statistics for PII protection dashboard.
    
    Returns lightweight stats suitable for dashboard widgets:
    - Total PII items protected
    - Operations count
    - Cache hit rate
    - Primary protection mode
    - Top PII types
    - Health status
    """
    if not pii_analytics:
        return {
            "status": "unavailable",
            "message": "PII analytics not initialized"
        }
    
    try:
        summary = await pii_analytics.get_summary_stats()
        return {
            "status": "ok",
            **summary
        }
    except Exception as e:
        logger.error(f"Failed to get PII analytics summary: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/providers")
async def get_providers():
    """Get available AI providers"""
    return list(AI_PROVIDERS.values())

@app.get("/ollama/status")
async def get_ollama_status():
    """Check Ollama status"""
    return await ollama_client.check_status()

@app.get("/ollama/models")
async def get_ollama_models():
    """Get available Ollama models"""
    return await ollama_client.get_models()

@app.post("/ollama/generate")
async def ollama_generate(request: OllamaGenerateRequest):
    """Generate text using Ollama"""
    return await ollama_client.generate(request.model, request.prompt, request.options)

@app.post("/reports/generate")
async def generate_report(request: ReportRequest):
    """Generate AI-powered report"""
    try:
        # If async mode, enqueue the request
        if request.async_mode:
            request_id = await queue_manager.enqueue_request(
                user_id=request.user_id,
                user_role=request.user_role,
                request_type="report",
                payload={
                    "templateId": request.templateId,
                    "provider": request.provider,
                    "privacyLevel": request.privacyLevel,
                    "dataSources": request.dataSources,
                    "requiredFields": request.requiredFields
                },
                priority_boost=2  # Reports get priority boost
            )
            
            return {
                "request_id": request_id,
                "status": "queued",
                "message": "Report generation queued",
                "check_status_url": f"/queue/status/{request_id}"
            }
        
        # Synchronous mode - process immediately
        # For now, route all reports to Ollama if provider is ollama
        if request.provider == "ollama":
            # Check if Ollama is available
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # Get available models
            models = await ollama_client.get_models()
            if not models:
                raise HTTPException(status_code=503, detail="No Ollama models available")
            
            # Use the configured default model or fall back to first available
            default_model = AI_PROVIDERS["ollama"]["defaultModel"]
            available_models = [m["name"] for m in models]
            
            if default_model not in available_models:
                logger.warning(f"Default model '{default_model}' not found. Available models: {available_models}")
                if available_models:
                    model_name = available_models[0]
                    logger.info(f"Using fallback model: {model_name}")
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"No models available. Please install a model using: 'ollama pull {default_model}'"
                    )
            else:
                model_name = default_model
            
            # Create report prompt based on template
            prompt = f"""
Generate a comprehensive report for template: {request.templateId}

Data Sources: {', '.join(request.dataSources)}
Privacy Level: {request.privacyLevel}
Required Fields: {json.dumps(request.requiredFields, indent=2)}

Please provide:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Recommendations
5. Conclusion

Format the response as a structured report.
"""
            
            # Generate report using primary LLM with fallback
            result = await generate_with_fallback(prompt, model_name)
            
            return {
                "reportId": f"report_{int(datetime.now().timestamp())}",
                "status": "completed",
                "provider": result.get("provider", request.provider),
                "model": result.get("model", model_name),
                "content": result.get("response", ""),
                "generatedAt": datetime.now().isoformat(),
                "privacyLevel": request.privacyLevel,
                "tokensUsed": result.get("eval_count", 0),
                "processingTime": result.get('total_duration', 0) / 1e9
            }
        else:
            # For other providers, return a placeholder response
            return {
                "reportId": f"report_{int(datetime.now().timestamp())}",
                "status": "pending",
                "provider": request.provider,
                "message": f"Report generation with {request.provider} is not yet implemented",
                "estimatedCompletion": "5-10 minutes"
            }
            
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT USAGE TRACKING ENDPOINT
# Provides visibility into conversation context window usage
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/bee/context-usage/{conversation_id}")
async def get_context_usage(
    conversation_id: str,
    user_id: str = Query(..., description="User ID for the conversation"),
    include_honey_jar: bool = Query(False, description="Include honey jar context in calculation"),
    honey_jar_id: str = Query(None, description="Honey jar ID if include_honey_jar is True")
):
    """
    Get context window usage statistics for a conversation.
    
    Returns detailed information about how much of the available context
    window is being used, along with warnings and suggestions.
    
    Use this to:
    - Display a progress bar showing context usage
    - Warn users when approaching limits
    - Suggest starting a new conversation
    """
    try:
        usage = await bee_context_manager.get_context_usage(
            conversation_id=conversation_id,
            user_id=user_id,
            include_honey_jar=include_honey_jar,
            honey_jar_id=honey_jar_id
        )
        return {
            "status": "ok",
            **usage
        }
    except Exception as e:
        logger.error(f"Failed to get context usage: {e}")
        return {
            "status": "error",
            "error": str(e),
            "conversation_id": conversation_id
        }


@app.post("/bee/chat")
async def bee_chat(request: BeeChatRequest):
    """Unified Bee chat endpoint that can handle both conversations and report generation"""
    try:
        # Debug: Log incoming user_id to trace persistence issue
        logger.info(f"🐝 Bee chat request - user_id: {request.user_id}, conversation_id: {request.conversation_id}")
        
        # If async mode, enqueue the request
        if request.async_mode:
            request_id = await queue_manager.enqueue_request(
                user_id=request.user_id,
                user_role=request.user_role,
                request_type="chat",
                payload={
                    "message": request.message,
                    "conversation_id": request.conversation_id,
                    "tools_enabled": request.tools_enabled,
                    "context": request.context,
                    "encryption_required": request.encryption_required
                }
            )
            
            return {
                "request_id": request_id,
                "status": "queued",
                "message": "Request queued for processing",
                "check_status_url": f"/queue/status/{request_id}"
            }
        
        # Synchronous mode - process immediately
        # Use the provider registry to check what's available (supports MiniMax primary with Ollama fallback)
        provider_status = await provider_registry.get_all_status()
        if provider_status.get("status") != "healthy":
            # No providers available
            raise HTTPException(status_code=503, detail="No LLM providers available")
        
        # Get primary provider info for model selection
        primary = provider_registry.get_primary()
        if not primary:
            raise HTTPException(status_code=503, detail="No primary LLM provider configured")
        
        # Get the default model from the primary provider
        model_name = primary.config.default_model
        logger.info(f"Using primary provider: {primary.name} with model: {model_name}")
        
        # Detect if user is asking for a report
        # Check context first (explicit report generation from report worker)
        is_report_request = request.context and request.context.get('generation_mode') == 'report'

        # If not explicitly set in context, check keywords in message
        if not is_report_request:
            msg_lower = request.message.lower()
            # Use regex patterns to be more flexible with articles (a, an, the)
            import re
            report_patterns = [
                r'generate\s+(?:a\s+)?(?:comprehensive\s+)?report',
                r'create\s+(?:a\s+)?(?:detailed\s+)?report',
                r'write\s+(?:a\s+)?(?:comprehensive\s+)?report',
                r'report\s+on\b',
                r'analyze\s+and\s+report',
                r'summary\s+report',
                r'detailed\s+analysis',
                r'word\s+analysis',
                r'word\s+report',
                r'comprehensive\s+report',
                r'(?:prepare|draft|produce)\s+(?:a\s+)?report'
            ]
            is_report_request = any(re.search(pattern, msg_lower) for pattern in report_patterns)

        if is_report_request:
            logger.info(f"📊 Report request detected for message: {request.message[:50]}...")
            # ═══════════════════════════════════════════════════════════════════
            # SMART REPORT GATING: Check if we have enough context
            # ═══════════════════════════════════════════════════════════════════
            # Skip gating if this is from report worker (already validated) or forced
            skip_gating = (
                (request.context and request.context.get('generation_mode') == 'report') or
                (request.context and request.context.get('skip_gating', False)) or
                'generate report anyway' in request.message.lower() or
                'proceed anyway' in request.message.lower()
            )
            
            if not skip_gating:
                # Get honey jar context if available
                honey_jar_context = None
                if request.honey_jar_id:
                    try:
                        honey_jar_context = await bee_context_manager.get_honey_jar_context(
                            request.honey_jar_id,
                            request.message,
                            max_chunks=3
                        )
                    except Exception as e:
                        logger.warning(f"Could not fetch honey jar context for gating: {e}")
                
                # Perform readiness assessment
                assessment = assess_report_readiness(
                    user_message=request.message,
                    honey_jar_id=request.honey_jar_id,
                    honey_jar_context=honey_jar_context,
                    web_search_results=None,  # We'll check this after lightweight assessment
                    conversation_history=None  # Could add conversation context here
                )
                
                logger.info(f"📊 Report Gating: score={assessment['score']}, confidence={assessment['confidence_level']}")
                
                # If low confidence, return clarification request instead of generating
                if not assessment['can_proceed']:
                    clarification_response = generate_clarification_response(assessment, request.message)
                    return {
                        "response": clarification_response,
                        "conversation_id": request.conversation_id,
                        "timestamp": datetime.now().isoformat(),
                        "tools_used": [],
                        "processing_time": 0.1,
                        "report_generated": False,
                        "gating_result": {
                            "score": assessment['score'],
                            "confidence": assessment['confidence_level'],
                            "action": "clarification_requested",
                            "factors": [f[0] for f in assessment['factors']]
                        },
                        "pii_protection": {
                            "protection_active": False,
                            "items_protected": 0
                        }
                    }
            
            # Override model for report generation - use model from config (user-editable in config.yml)
            # The provider registry handles fallback automatically, so we just log the preference
            report_model = llm_config.get('report_model', model_name)
            logger.info(f"🔄 Report request detected, preferred model: {report_model} (primary: {model_name})")
            # Note: The actual model used depends on what the provider supports
            # generate_with_fallback will use the appropriate model

            # PII Protection: Serialize ONLY the user message BEFORE building enhanced prompt
            # For reports, this is critical - the report template is static and pre-vetted
            pii_context = {}
            protection_mode = "external"  # Default fallback
            user_message = request.message  # Original user message

            if pii_middleware:
                try:
                    # Intelligent mode detection based on actual primary provider
                    if mode_detector:
                        provider_name, provider_url, is_cloud = get_primary_provider_info()
                        protection_mode, mode_config = mode_detector.detect_mode(
                            endpoint_url=provider_url,
                            provider=provider_name,
                            context="report",  # Report context uses selective protection
                            user_role=request.user_role or "user",
                            is_cloud_provider=is_cloud
                        )
                        logger.info(f"PII protection mode for report: {protection_mode} (provider: {provider_name}, cloud: {is_cloud}, level: {mode_config.get('protection_level')})")

                    # Only serialize the user's message, not the entire report prompt
                    serialized_message, pii_context = await pii_middleware.serialize_message(
                        message=request.message,  # Only user message
                        conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                        user_id=request.user_id,
                        mode=protection_mode
                    )
                    pii_context['protection_mode'] = protection_mode
                    user_message = serialized_message
                    logger.debug(f"PII serialized report request ({len(request.message)} chars -> {len(serialized_message)} chars)")
                    
                    # Record analytics for serialization
                    if pii_analytics and pii_context.get('pii_count', 0) > 0:
                        await pii_analytics.record_serialization(
                            conversation_id=pii_context.get('conversation_id', ''),
                            user_id=request.user_id,
                            mode=protection_mode,
                            pii_count=pii_context.get('pii_count', 0),
                            pii_types=pii_context.get('pii_types', []),
                            provider=provider_name,
                            is_cloud_provider=is_cloud
                        )
                except Exception as e:
                    logger.error(f"PII serialization failed: {e}")
                    # Continue with original message on error

            # Check if web search should be skipped (for internal/system calls like title generation)
            skip_web_search = request.context.get('skip_web_search', False) if request.context else False

            # Handle as report generation with enhanced context
            # Force web search for reports since they benefit from external research
            # Use original message for web search, serialized message for LLM prompt
            enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
                user_message,  # PII-serialized message for LLM
                request.user_id,
                conversation_id=request.conversation_id,
                conversation_history=None,
                honey_jar_id=request.honey_jar_id,
                skip_web_search=skip_web_search,
                force_web_search=True,  # Reports benefit from external research
                original_message=request.message  # Original message for web search queries
            )

            # Detect report type from user's request to provide appropriate guidance
            user_msg_lower = user_message.lower()

            # Detect use case / business scenario requests
            is_use_case_request = any(kw in user_msg_lower for kw in [
                'use case', 'use-case', 'usecase', 'how can', 'how would', 'how could',
                'business scenario', 'real world', 'real-world', 'practical example',
                'application', 'implement', 'deploy', 'leverage', 'utilize'
            ])

            # Detect comparison/evaluation requests
            is_comparison_request = any(kw in user_msg_lower for kw in [
                'compare', 'versus', 'vs', 'difference', 'better', 'pros and cons',
                'advantages', 'disadvantages', 'alternative'
            ])

            # Detect summary/overview requests
            is_summary_request = any(kw in user_msg_lower for kw in [
                'summary', 'overview', 'summarize', 'brief', 'quick', 'tldr', 'highlights'
            ])

            # Build appropriate report prompt based on request type
            
            # Universal instructions - prepended to ALL report types
            universal_report_instructions = """
**CRITICAL PLATFORM IDENTITY NOTICE**:
STING is a **knowledge management and AI document analysis platform**. It is:
- A secure document repository system (Honey Jars store DOCUMENTS)
- An AI-powered search and Q&A system for your uploaded documents
- A report generation platform that analyzes YOUR documents

STING is **NOT**:
- A cybersecurity honeypot or deception technology
- A threat detection or intrusion detection system  
- A security monitoring or incident response platform
- Related to cybersecurity "honeypots" that trap attackers

When searching the web, ignore any results about cybersecurity "honeypots" or "deception technology" - those are NOT about STING. The term "Honey Jar" in STING refers to document repositories for knowledge management.

**CRITICAL ANTI-HALLUCINATION RULES - MANDATORY COMPLIANCE REQUIRED**:

⛔ **ABSOLUTE PROHIBITION ON FABRICATED NAMES** ⛔
If the user asks about specific people (doctors, staff, executives, etc.) at a real organization, and your web search results DO NOT contain those exact names, you MUST:
- State clearly: "I was unable to find the names of specific [doctors/staff/etc.] at [organization] in my search results."
- NEVER generate names like "Dr. Emily Carter", "Dr. Michael Thompson", "Dr. Sarah Nguyen" or ANY other invented names
- NEVER fabricate credentials (medical degrees, residencies, fellowships, board certifications)
- NEVER invent biographies or career histories
- Instead, recommend: "For accurate staff information, please visit [organization]'s official website or call their main number."

🚫 **SPECIFIC PROHIBITIONS**:
1. **NO INVENTED PERSON NAMES** - Do not write "Dr. [Name]", "[Name], MD", or any person's name unless it appears VERBATIM in your web search results
2. **NO FABRICATED CREDENTIALS** - Do not mention specific universities, hospitals, fellowships, or certifications unless from your sources
3. **NO MADE-UP STATISTICS** - Do not invent percentages, patient counts, success rates, or financial figures
4. **NO FICTIONAL QUOTES** - Do not create quotes attributed to people
5. **NO IMAGINARY AWARDS/HONORS** - Do not invent accolades or recognitions

✅ **WHAT YOU CAN DO**:
- Provide GENERAL information about the topic (e.g., "Cardiac catheterization is a diagnostic procedure...")
- Describe the TYPES of specialists typically involved (e.g., "Interventional cardiologists typically perform...")
- Explain procedures, equipment, and general practices
- Cite information that IS in your web search results
- Recommend how users can find the specific information they need

📋 **SOURCE VERIFICATION CHECKLIST** (Apply before including ANY factual claim):
□ Is this specific name/fact in my web search results? If NO → Do not include
□ Am I inventing details to make the response sound complete? If YES → Stop and acknowledge the gap
□ Could this be verified by checking the source? If NO → It's likely fabricated

When information is unavailable, respond like this:
"While I can provide general information about [topic], I was unable to find specific details about [what user asked] in my search results. For accurate, up-to-date information about staff/doctors/specifics at [organization], I recommend visiting their official website at [URL if known] or contacting them directly."
"""
            
            if is_use_case_request:
                report_prompt = f"""{enhanced_prompt}

{universal_report_instructions}

You are generating a **business use case and practical applications report**. Create original, realistic scenarios that demonstrate practical value.

CRITICAL: Focus your use cases and examples SPECIFICALLY on the topic the user asked about. Do NOT diverge into unrelated industries or domains. If the user asks about SCADA/ICS security, focus on industrial control systems, power grids, and critical infrastructure - NOT healthcare or finance.

GUIDELINES:

1. **Stay on topic** - All examples and use cases must directly relate to what the user asked about. Extract the core subject from their query and build all scenarios around it.

2. **Be honest about metrics** - Avoid inventing specific percentages or dollar figures. Use qualitative descriptions ("significantly reduces", "streamlines") or realistic ranges ("could reduce from hours to minutes"). Only cite specific numbers if from documentation.

3. **Be specific and vivid** - Include realistic organization types, actual job titles, concrete daily tasks, and specific pain points relevant to the user's topic.

4. **Ground in actual platform capabilities**:
   - Honey Jars: Secure, encrypted document repositories for organizing sensitive knowledge
   - Bee AI assistant: Intelligent document Q&A that answers questions from your uploaded documents
   - PII detection: Automatic detection and protection of personally identifiable information
   - End-to-end encryption: Data protection in transit and at rest
   - Multi-factor authentication: Passkeys, TOTP for secure access
   - Comprehensive audit logging: Track who accessed what and when
   - Report generation: AI-powered analysis and report creation from your knowledge base
   
   **IMPORTANT**: STING is a secure knowledge management and AI document analysis platform. It is NOT a cybersecurity honeypot, threat detection system, or deception technology platform.

5. **Include real-world context** - If the user mentions a timeframe (e.g., "2024-2025 threats"), you MUST include specific, realistic examples of actual or plausible incidents, vulnerabilities, or attack vectors from that period. Name specific threat types, protocols, or attack techniques relevant to the domain.

6. **Honor explicit requests** - If the user asks for a deployment architecture, technical diagram description, or specific deliverable, you MUST include it. Scan the user's prompt for keywords like "architecture", "deployment", "diagram", "cite sources", "references" and fulfill those requests.

REQUIRED STRUCTURE:

## Executive Summary
2-3 paragraphs: What problems does this solve for the specific domain/topic? Who benefits most? Why does it matter? Include brief mention of current challenges and context.

## Background & Context
Describe 3-5 key challenges or trends relevant to the user's topic. Include:
- Current industry challenges and pain points
- Recent developments or emerging trends (use realistic examples from the timeframe if specified)
- Why traditional approaches are insufficient

## Use Cases & Applications
Create 3-5 detailed use cases that are ALL within the SAME domain/industry the user specified. 

**CRITICAL**: Do NOT diverge into unrelated industries. If the user asks about a specific topic or domain, create 3-5 DIFFERENT use cases within that exact domain - NOT generic industry sections like "Healthcare", "Financial Services", "Legal", etc. Those are separate industries and should NEVER appear unless specifically requested.

Each use case should include:
- **The Challenge**: What specific problems exist in this context?
- **The Solution**: How does STING address these? Be specific about which features help (Honey Jars for knowledge organization, Bee AI for intelligent search and analysis, secure document management, etc.).
- **Who Uses It**: Describe relevant user personas and their workflows.
- **Real-World Scenario**: Walk through a specific realistic situation showing how knowledge management and AI-assisted analysis helps.

## Proposed Deployment Architecture
If the user requests an architecture or deployment plan, include:
- **Architecture Overview**: Describe the logical layout (e.g., "Three-tier architecture with...")
- **Component Placement**: Where STING components sit (frontend, backend services, knowledge service, AI services)
- **Data Flow**: How documents flow through ingestion, processing, and retrieval
- **Security Boundaries**: How data remains secure within the deployment
- **Integration Points**: How STING integrates with existing infrastructure (SSO, document sources, etc.)

If no architecture was requested, you may include a brief "Deployment Considerations" subsection instead.

## Implementation Considerations
Practical guidance for organizations in this specific domain:
- Prerequisites and infrastructure requirements
- Pilot program recommendations
- Key success factors for this type of use case
- Scaling considerations

## References & Sources
**MANDATORY - DO NOT SKIP**: You MUST include a References section with REAL, CLICKABLE URLs.

Look at the "Web Research Sources" section in your context above. Each source has a URL line like:
URL: https://example.com/article

COPY those exact URLs into your references like this:
1. [Source Title](https://exact-url-from-context.com/path)
2. [Another Source](https://another-real-url.com/article)

**DO NOT**:
- List titles without URLs
- Make up fake URLs
- Use placeholder text
- Skip the References section

**STRICT RULES**:
1. DO NOT list generic industry categories (Healthcare, Financial Services, Legal, Manufacturing) as separate sections UNLESS the user explicitly asked for a multi-industry comparison.
2. Keep ALL content focused on the user's SINGLE requested topic.
3. If the user explicitly requests something (architecture, citations, specific word count), you MUST deliver it.
4. ALWAYS cite your sources in the References section - this is mandatory for professional reports.

**CRITICAL - URLs**: Look at the "Web Research Sources" section above. COPY the actual URLs provided there (they start with http:// or https://) and use them in your References. Do NOT make up URLs or use placeholder text - use the EXACT URLs from the sources provided.

Begin the report now.
"""
            elif is_comparison_request:
                report_prompt = f"""{enhanced_prompt}

{universal_report_instructions}

You are generating a **comparison and evaluation report**. Provide objective, balanced analysis.

REQUIRED STRUCTURE:

## Executive Summary
Key comparison findings and recommendations (2-3 paragraphs).

## Detailed Comparison

### Feature-by-Feature Analysis
Create a comprehensive comparison covering capabilities, limitations, and trade-offs.

### Strengths
What does each option do well? Be specific with examples.

### Limitations
What are the weaknesses or gaps? Be honest and balanced.

### Best Fit Scenarios
When would you choose each option? What use cases favor each?

## Decision Framework
Help the reader decide which option fits their specific needs.

## Recommendations
Clear, actionable recommendations based on different user scenarios.

## References & Sources
**MANDATORY - DO NOT SKIP**: Include REAL URLs from the Web Research Sources in your context.
Format: [Source Title](https://exact-url-from-context.com)
DO NOT list titles without URLs. COPY the actual URLs provided above.

**CRITICAL - URLs**: Look at the "Web Research Sources" section above. COPY the actual URLs provided there (they start with http:// or https://) and use them in your References. Do NOT make up URLs or use placeholder text - use the EXACT URLs from the sources provided.

Begin the report now.
"""
            elif is_summary_request:
                report_prompt = f"""{enhanced_prompt}

{universal_report_instructions}

You are generating a **concise executive summary report**. Focus on clarity and actionable insights.

REQUIRED STRUCTURE:

## Executive Summary
The most important points in 3-4 paragraphs. What does a busy executive need to know?

## Key Highlights
Bulleted list of the 5-7 most critical points.

## Quick Reference
- **What it is**: One-sentence description
- **Key benefits**: Top 3 benefits
- **Best for**: Who should use this
- **Getting started**: First step to take

## Detailed Breakdown
Expand on each key area with specifics, but keep it focused and scannable.

## Action Items
What should the reader do next? Be specific and prioritized.

## Sources
**MANDATORY**: Include REAL URLs from the Web Research Sources in your context.
Format: [Source Title](https://exact-url-from-context.com)
DO NOT list titles without URLs. COPY the actual URLs provided in your context.

**CRITICAL - URLs**: Look at the "Web Research Sources" section above. COPY the actual URLs provided there (they start with http:// or https://) and use them in your Sources. Do NOT make up URLs or use placeholder text - use the EXACT URLs from the sources provided.

Begin the report now.
"""
            else:
                # Default comprehensive technical report
                report_prompt = f"""{enhanced_prompt}

{universal_report_instructions}

You are generating a professional enterprise report. This MUST be a comprehensive, detailed document.

CRITICAL REQUIREMENTS:
1. Minimum length: 3500-5000 words
2. Each major section MUST contain 4-6 substantial paragraphs with specific details
3. DO NOT use LaTeX notation - write in plain professional prose
4. Provide concrete examples and practical applications throughout
5. **SYNTHESIZE information** - don't just summarize, provide insights and actionable guidance

REQUIRED STRUCTURE:

## Executive Summary (400-600 words)
- Comprehensive overview of the analysis
- Key findings with specific observations
- Critical implications and business impact
- High-level recommendations

## Detailed Analysis (1500-2000 words)
- In-depth examination with specific details
- Practical applications and real-world scenarios
- Security and compliance considerations
- Performance and scalability insights
- Integration possibilities

## Recommendations (800-1200 words)
- Specific, actionable next steps
- Best practices with concrete examples
- Implementation guidance
- Success metrics

## Conclusion (400-600 words)
- Summary of key findings
- Strategic implications
- Future considerations
- Prioritized action items

## References & Sources
**MANDATORY - DO NOT SKIP**: You MUST include REAL, CLICKABLE URLs from your context.

Look at the "Web Research Sources" section above. Each source shows:
**[Source N]** Title
URL: https://actual-url.com/path

COPY those URLs into your references:
1. [Source Title](https://exact-url-from-context.com)
2. [Another Title](https://another-url-from-context.com)

**DO NOT** list titles without URLs or make up fake URLs.

**CRITICAL - URLs**: COPY the actual URLs from the Web Research Sources section above. Use the EXACT URLs provided - do not paraphrase or abbreviate them.

FORMATTING: Use markdown headers (##). Write in clear, professional prose. NO LaTeX formatting.

Begin the report now.
"""

            # Log detected report type
            report_type = "use_case" if is_use_case_request else "comparison" if is_comparison_request else "summary" if is_summary_request else "technical"
            logger.info(f"📊 Report type detected: {report_type} (use_case={is_use_case_request}, comparison={is_comparison_request}, summary={is_summary_request})")

            # Prepare LLM options with higher max_tokens for comprehensive reports
            # Use slightly higher temperature for use case reports to encourage creativity
            base_temp = llm_config.get('temperature', 0.7)
            report_temp = 0.8 if is_use_case_request else base_temp  # More creative for use cases

            report_llm_options = {
                'num_predict': llm_config.get('report_max_tokens', 8192),  # Higher limit for detailed reports
                'temperature': report_temp,
            }
            logger.info(f"🔍 Report generation: num_predict={report_llm_options['num_predict']}, model={model_name}, type={report_type}")

            result = await generate_with_fallback(report_prompt, model_name, report_llm_options)

            # Clean response using optimized pre-compiled patterns
            raw_response = result.get("response", "")
            clean_response = clean_llm_response(raw_response)

            # ReviewBee: Critic-Revise pattern for report improvement
            # Core mission: Compare FINAL OUTPUT against ORIGINAL ASK
            # Small model critiques with structured task list, powerful model regenerates
            review_bee_metadata = None
            if llm_config.get('review_bee_enabled', False):
                try:
                    logger.info("🐝 ReviewBee: Starting critic-revise cycle...")
                    critic_model = llm_config.get('review_bee_critic_model', 'microsoft/phi-4-mini-reasoning')
                    review_mode = llm_config.get('review_bee_mode', 'critique_only')
                    improvement_threshold = llm_config.get('review_bee_improvement_threshold', 0.7)
                    
                    # Run critic analysis - pass BOTH the report prompt AND original user message
                    # This allows ReviewBee to compare output against what user ACTUALLY asked for
                    critique_result = await run_review_bee_critic(
                        report_content=clean_response,
                        original_prompt=report_prompt,
                        critic_model=critic_model,
                        pii_context=pii_context,
                        user_message=request.message  # The original user ask
                    )
                    
                    # STRICT MODE: Reject reports with fabricated content or wrong sources
                    if critique_result.get('rejected', False):
                        rejection_reason = critique_result.get('rejection_reason', 'QUALITY_FAILURE')
                        task_list = critique_result.get('task_list', [])
                        logger.error(f"🐝 ReviewBee HARD REJECT: {rejection_reason}")
                        logger.error(f"🐝 Tasks: {task_list[:5]}")
                        
                        # Return a rejection response instead of fabricated content
                        rejection_messages = {
                            'FABRICATED_CONTENT': "I was unable to find verified information about the specific people/staff you asked about. The search results did not contain the details needed to answer your question accurately. To get accurate information about staff at this organization, I recommend visiting their official website or contacting them directly.",
                            'IRRELEVANT_SOURCES': "My web search returned results that don't match your query (for example, results about schools when you asked about a hospital). I cannot generate an accurate report without relevant sources. Please try rephrasing your query or verify the organization name.",
                            'QUALITY_FAILURE': "The generated report did not meet quality standards and contained potentially inaccurate information. Please try your request again with more specific details."
                        }
                        
                        return {
                            "response": rejection_messages.get(rejection_reason, rejection_messages['QUALITY_FAILURE']),
                            "type": "report_rejected",
                            "metadata": {
                                "model": model_name,
                                "provider": result.get("provider", "unknown"),
                                "rejection_reason": rejection_reason,
                                "review_bee": {
                                    'rejected': True,
                                    'reason': rejection_reason,
                                    'issues': task_list[:5]
                                }
                            }
                        }
                    
                    review_bee_metadata = {
                        'enabled': True,
                        'critic_model': critic_model,
                        'mode': review_mode,
                        'critique_score': critique_result.get('score', 0),
                        'requirements_met': critique_result.get('requirements_met', 'UNKNOWN'),
                        'gaps_count': len(critique_result.get('gaps', [])),
                        'task_list_count': len(critique_result.get('task_list', [])),
                        'findings_count': len(critique_result.get('findings', [])),
                        'revision_applied': False
                    }
                    
                    # If critique found issues and score is below threshold, regenerate
                    if review_mode == 'critique_and_revise' and critique_result.get('task_list'):
                        critique_score = critique_result.get('score', 1.0)
                        requirements_met = critique_result.get('requirements_met', 'YES')
                        
                        # Trigger revision if score below threshold OR requirements not fully met
                        should_revise = critique_score < improvement_threshold or requirements_met == 'NO'
                        
                        if should_revise:
                            logger.info(f"🐝 ReviewBee: Score {critique_score:.2f}, requirements={requirements_met} - regenerating...")
                            
                            # Generate revision feedback with structured task list
                            revision_feedback = critique_result.get('revision_feedback', '')
                            if revision_feedback:
                                enhanced_prompt = f"{report_prompt}\n\n---\n\n{revision_feedback}"
                                
                                # Regenerate with enhanced prompt
                                revision_result = await generate_with_fallback(enhanced_prompt, model_name, report_llm_options)
                                revised_response = clean_llm_response(revision_result.get("response", ""))
                                
                                # QUALITY VALIDATION: Don't accept revisions that are worse
                                validation = validate_revision_quality(clean_response, revised_response)
                                
                                if validation['is_valid']:
                                    # Log comparison for validation
                                    logger.info(f"🐝 ReviewBee COMPARISON:")
                                    logger.info(f"   ORIGINAL ({len(clean_response)} chars): {clean_response[:200]}...")
                                    logger.info(f"   REVISED  ({len(revised_response)} chars): {revised_response[:200]}...")
                                    
                                    clean_response = revised_response
                                    review_bee_metadata['revision_applied'] = True
                                    review_bee_metadata['original_length'] = len(raw_response)
                                    review_bee_metadata['revised_length'] = len(revised_response)
                                    review_bee_metadata['quality_metrics'] = validation['metrics']
                                    logger.info(f"🐝 ReviewBee: Revision applied (validated), {len(raw_response)} → {len(revised_response)} chars")
                                else:
                                    # Revision failed quality checks - keep original
                                    review_bee_metadata['revision_rejected'] = True
                                    review_bee_metadata['rejection_reasons'] = validation['rejection_reasons']
                                    review_bee_metadata['quality_metrics'] = validation['metrics']
                                    logger.warning(f"🐝 ReviewBee: Revision REJECTED - {validation['rejection_reasons']}")
                        else:
                            logger.info(f"🐝 ReviewBee: Score {critique_score:.2f} meets threshold, requirements={requirements_met}")
                    else:
                        logger.info(f"🐝 ReviewBee: Critique-only mode or no tasks, skipping revision")
                        
                except Exception as e:
                    logger.error(f"🐝 ReviewBee error: {e}")
                    review_bee_metadata = {
                        'enabled': True,
                        'error': str(e),
                        'revision_applied': False
                    }

            # PII Protection: Deserialize response with enhanced metadata for visual indicators
            pii_protected_metadata = None
            if pii_middleware and pii_context:
                try:
                    # Try enhanced deserialization with metadata
                    if hasattr(pii_middleware, 'deserialize_response_with_metadata'):
                        clean_response, deser_metadata = await pii_middleware.deserialize_response_with_metadata(
                            response=clean_response,
                            context=pii_context,
                            enable_diagnostics=True,
                            track_positions=True
                        )

                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': deser_metadata.get('tokens_replaced', 0),
                            'protection_quality': 'complete' if deser_metadata.get('tokens_missed', 0) == 0 else 'partial',
                            'pii_annotations': deser_metadata.get('pii_metadata', [])
                        }
                        
                        # Record deserialization analytics (report context)
                        if pii_analytics:
                            await pii_analytics.record_deserialization(
                                conversation_id=pii_context.get('conversation_id', ''),
                                tokens_found=deser_metadata.get('tokens_found', 0),
                                tokens_replaced=deser_metadata.get('tokens_replaced', 0),
                                tokens_missed=deser_metadata.get('tokens_missed', 0)
                            )
                    else:
                        # Fallback to basic deserialization
                        clean_response = await pii_middleware.deserialize_response(
                            response=clean_response,
                            context=pii_context
                        )
                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': pii_context.get('pii_count', 0),
                            'protection_quality': 'unknown',
                            'pii_annotations': []
                        }
                except Exception as e:
                    logger.error(f"PII deserialization failed: {e}")
                    pii_protected_metadata = {
                        'protection_active': True,
                        'protection_quality': 'failed',
                        'error': str(e)
                    }

            # URL Injection: Post-process to add missing URLs to References section
            # LLMs often ignore instructions to include URLs, so we inject them from the prompt
            try:
                before_len = len(clean_response)
                clean_response = inject_urls_into_references(clean_response, report_prompt)
                after_len = len(clean_response)
                logger.info(f"📎 URL Injection complete: {before_len} → {after_len} chars (+{after_len - before_len})")
                # Log the last 500 chars to verify references are there
                logger.info(f"📎 Response tail (last 500 chars): ...{clean_response[-500:]}")
            except Exception as e:
                logger.warning(f"📎 URL injection failed (non-fatal): {e}")

            return {
                "response": clean_response.strip(),
                "conversation_id": request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                "timestamp": datetime.now().isoformat(),
                "bee_personality": "professional_analyst",
                "tools_used": ["report_generator"],
                "processing_time": result.get('total_duration', 0) / 1e9,
                "report_generated": True,
                "report_metadata": {
                    "type": "conversational_report",
                    "model": model_name,
                    "tokens_used": result.get("eval_count", 0),
                    "privacy_level": "high" if not request.encryption_required else "maximum"
                },
                "pii_protection": pii_protected_metadata,  # PII metadata for frontend visual indicators
                "review_bee": review_bee_metadata  # ReviewBee critic-revise metadata (None if disabled)
            }
        else:
            # Handle as regular conversation
            # Check if this is a Nectar Bot request with custom system prompt
            bot_context = request.context.get('bot_context') if request.context else None
            nectar_bot_system_prompt = None
            if bot_context and bot_context.get('is_nectar_bot'):
                nectar_bot_system_prompt = bot_context.get('system_prompt')
                logger.info(f"Using Nectar Bot system prompt for bot: {bot_context.get('bot_name')}")

            # PII Protection: Serialize ONLY the user message BEFORE building enhanced prompt
            # This is critical for performance - system prompt and honey jar data are pre-vetted
            # Only user input needs PII protection
            pii_context = {}
            protection_mode = "external"  # Default fallback
            user_message = request.message  # Original user message

            if pii_middleware:
                try:
                    # Intelligent mode detection based on actual primary provider
                    if mode_detector:
                        provider_name, provider_url, is_cloud = get_primary_provider_info()
                        protection_mode, mode_config = mode_detector.detect_mode(
                            endpoint_url=provider_url,
                            provider=provider_name,
                            context="chat",  # Chat context
                            user_role=request.user_role or "user",
                            is_cloud_provider=is_cloud
                        )
                        logger.info(f"PII protection mode for chat: {protection_mode} (provider: {provider_name}, cloud: {is_cloud}, level: {mode_config.get('protection_level')})")

                    # Only serialize the user's message, not the entire enhanced prompt
                    # System prompt, honey jar data, and conversation history are pre-vetted
                    serialized_message, pii_context = await pii_middleware.serialize_message(
                        message=request.message,  # Only user message, NOT enhanced_prompt
                        conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                        user_id=request.user_id,
                        mode=protection_mode
                    )
                    pii_context['protection_mode'] = protection_mode
                    user_message = serialized_message  # Use serialized version
                    logger.debug(f"PII serialized user message ({len(request.message)} chars -> {len(serialized_message)} chars)")
                    
                    # Record analytics for serialization
                    if pii_analytics and pii_context.get('pii_count', 0) > 0:
                        await pii_analytics.record_serialization(
                            conversation_id=pii_context.get('conversation_id', ''),
                            user_id=request.user_id,
                            mode=protection_mode,
                            pii_count=pii_context.get('pii_count', 0),
                            pii_types=pii_context.get('pii_types', []),
                            provider=provider_name,
                            is_cloud_provider=is_cloud
                        )
                except Exception as e:
                    logger.error(f"PII serialization failed: {e}")
                    # Continue with original message on error

            # Generate conversation_id once for both user and assistant messages
            # This ensures new conversations have a consistent ID from the start
            conversation_id = request.conversation_id or f"conv_{int(datetime.now().timestamp())}"

            # Check if web search should be skipped (for internal/system calls like title generation)
            skip_web_search = request.context.get('skip_web_search', False) if request.context else False

            # Use the BeeContextManager to build enhanced prompt with honey jar context AND conversation history
            # Uses the PII-serialized user message for LLM, but original message for web search
            enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
                user_message,  # PII-serialized message for LLM prompt
                request.user_id,
                conversation_id=conversation_id,  # Pass conversation_id to load history from Redis
                conversation_history=None,  # Will be loaded from Redis automatically
                honey_jar_id=request.honey_jar_id,
                custom_system_prompt=nectar_bot_system_prompt,  # Pass custom prompt for Nectar Bots
                skip_web_search=skip_web_search,
                original_message=request.message  # Original message for web search queries
            )

            # Save user message to conversation history (use ORIGINAL message, not serialized)
            await bee_context_manager.save_message_to_history(
                conversation_id=conversation_id,
                user_id=request.user_id,
                role="user",
                content=request.message  # Save original, not serialized
            )

            # Prepare LLM options with max_tokens from config
            llm_options = {
                'num_predict': llm_config.get('max_tokens', 4096),
                'temperature': llm_config.get('temperature', 0.7),
            }

            result = await generate_with_fallback(enhanced_prompt, model_name, llm_options)

            # Clean response using optimized pre-compiled patterns
            raw_response = result.get("response", "")
            clean_response = clean_llm_response(raw_response)

            # PII Protection: Deserialize response with enhanced metadata for visual indicators
            pii_protected_metadata = None
            if pii_middleware and pii_context:
                try:
                    # Try enhanced deserialization with metadata
                    if hasattr(pii_middleware, 'deserialize_response_with_metadata'):
                        clean_response, deser_metadata = await pii_middleware.deserialize_response_with_metadata(
                            response=clean_response,
                            context=pii_context,
                            enable_diagnostics=True,
                            track_positions=True
                        )

                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': deser_metadata.get('tokens_replaced', 0),
                            'protection_quality': 'complete' if deser_metadata.get('tokens_missed', 0) == 0 else 'partial',
                            'pii_annotations': deser_metadata.get('pii_metadata', [])
                        }
                        
                        # Record deserialization analytics (chat context)
                        if pii_analytics:
                            await pii_analytics.record_deserialization(
                                conversation_id=pii_context.get('conversation_id', ''),
                                tokens_found=deser_metadata.get('tokens_found', 0),
                                tokens_replaced=deser_metadata.get('tokens_replaced', 0),
                                tokens_missed=deser_metadata.get('tokens_missed', 0)
                            )
                    else:
                        # Fallback to basic deserialization
                        clean_response = await pii_middleware.deserialize_response(
                            response=clean_response,
                            context=pii_context
                        )
                        pii_protected_metadata = {
                            'protection_active': True,
                            'protection_mode': pii_context.get('protection_mode', 'external'),
                            'items_protected': pii_context.get('pii_count', 0),
                            'protection_quality': 'unknown',
                            'pii_annotations': []
                        }
                except Exception as e:
                    logger.error(f"PII deserialization failed: {e}")
                    pii_protected_metadata = {
                        'protection_active': True,
                        'protection_quality': 'failed',
                        'error': str(e)
                    }

            # Save assistant response to conversation history
            # conversation_id is already defined at the start of the request
            await bee_context_manager.save_message_to_history(
                conversation_id=conversation_id,
                user_id=request.user_id,
                role="assistant",
                content=clean_response.strip()
            )

            # Calculate context usage for this conversation
            context_usage = None
            context_warning = None
            try:
                context_usage = await bee_context_manager.get_context_usage(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    include_honey_jar=bool(request.honey_jar_id),
                    honey_jar_id=request.honey_jar_id
                )
                # Generate warning message if needed
                context_warning = bee_context_manager.generate_context_warning_message(context_usage)
            except Exception as e:
                logger.warning(f"Could not calculate context usage: {e}")

            return {
                "response": clean_response.strip(),
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "tools_used": request.tools_enabled,
                "processing_time": result.get('total_duration', 0) / 1e9,
                "report_generated": False,
                "pii_protection": pii_protected_metadata,  # PII metadata for frontend visual indicators
                "context_usage": {
                    "percentage": context_usage.get("usage_percentage", 0) if context_usage else 0,
                    "status": context_usage.get("status", "unknown") if context_usage else "unknown",
                    "messages_count": context_usage.get("messages_count", 0) if context_usage else 0,
                    "summary": context_usage.get("summary", "") if context_usage else "",
                    "warnings": context_usage.get("warnings", []) if context_usage else [],
                    "suggestions": context_usage.get("suggestions", []) if context_usage else []
                } if context_usage else None,
                "context_warning": context_warning  # Inline warning message if critical
            }
            
    except Exception as e:
        logger.error(f"Failed to process Bee chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# User Conversation History Endpoints
# ============================================================================

@app.get("/users/{user_id}/conversations")
async def get_user_conversations(user_id: str, limit: int = 50, offset: int = 0):
    """Get all conversations for a user from PostgreSQL store"""
    try:
        if not bee_context_manager:
            raise HTTPException(status_code=503, detail="Bee context manager not available")
        
        # Ensure conversation store is initialized
        await bee_context_manager._ensure_conversation_store()
        
        if not bee_context_manager.conversation_store:
            raise HTTPException(status_code=503, detail="Conversation store not available")
        
        conversations = await bee_context_manager.conversation_store.list_conversations(
            user_id=user_id,
            status="active",
            limit=limit
        )
        
        # Map 'id' to 'conversation_id' for frontend compatibility
        formatted_conversations = []
        for conv in conversations:
            formatted_conversations.append({
                "conversation_id": conv.get("id"),
                "id": conv.get("id"),  # Keep both for compatibility
                "title": conv.get("title"),
                "conversation_type": conv.get("conversation_type"),
                "status": conv.get("status"),
                "is_pinned": conv.get("is_pinned"),
                "created_at": conv.get("created_at"),
                "last_message_at": conv.get("last_message_at"),
                "message_count": conv.get("message_count", 0),
            })
        
        logger.info(f"📚 Retrieved {len(formatted_conversations)} conversations for user {user_id[:8]}...")
        
        return {
            "conversations": formatted_conversations,
            "count": len(formatted_conversations),
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Failed to get user conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, limit: int = 100, offset: int = 0):
    """Get messages from a specific conversation"""
    try:
        if not bee_context_manager:
            raise HTTPException(status_code=503, detail="Bee context manager not available")
        
        # Ensure conversation store is initialized
        await bee_context_manager._ensure_conversation_store()
        
        if not bee_context_manager.conversation_store:
            raise HTTPException(status_code=503, detail="Conversation store not available")
        
        messages = await bee_context_manager.conversation_store.get_messages(
            conversation_id=conversation_id,
            limit=limit
        )
        
        # Map to expected format for frontend
        # Frontend expects: id, content, sender, timestamp, message_type
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            # Map 'role' to 'sender' for frontend compatibility
            sender = "bee" if role == "assistant" else "user"
            
            formatted_messages.append({
                "id": msg.get("id"),
                "role": role,
                "sender": sender,  # Frontend expects 'sender' not 'role'
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp"),
                "message_type": msg.get("message_type", "text"),  # Frontend expects this
                "metadata": msg.get("metadata", {})
            })
        
        logger.info(f"📜 Retrieved {len(formatted_messages)} messages for conversation {conversation_id[:8]}...")
        
        return {
            "messages": formatted_messages,
            "conversation_id": conversation_id,
            "count": len(formatted_messages)
        }
    except Exception as e:
        logger.error(f"Failed to get conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/sync")
async def sync_knowledge(request: KnowledgeSyncRequest):
    """Sync knowledge base with local AI"""
    try:
        if request.targetProvider == "ollama":
            # Check Ollama status
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # Simulate knowledge sync process
            data_size = len(json.dumps(request.data))
            
            # In a real implementation, this would:
            # 1. Process the knowledge data
            # 2. Create embeddings using Ollama
            # 3. Store in vector database
            # 4. Update knowledge base
            
            return {
                "syncId": f"sync_{int(datetime.now().timestamp())}",
                "status": "completed",
                "targetProvider": request.targetProvider,
                "syncType": request.syncType,
                "dataSize": f"{data_size / 1024:.2f} KB",
                "documentsProcessed": len(request.data.get("honeyJars", [])) + len(request.data.get("reports", [])),
                "processingTime": "2.3 seconds",
                "completedAt": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {request.targetProvider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to sync knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for documents"""
    try:
        if request.provider == "ollama":
            # Check Ollama status
            status = await ollama_client.check_status()
            if not status.get("running"):
                raise HTTPException(status_code=503, detail="Ollama service is not available")
            
            # In a real implementation, this would use Ollama's embedding model
            # For now, return mock embeddings
            embeddings = []
            for i, doc in enumerate(request.documents):
                embeddings.append({
                    "document": doc[:100] + "..." if len(doc) > 100 else doc,
                    "embedding": [0.1] * 384,  # Mock 384-dimensional embedding
                    "index": i
                })
            
            return {
                "embeddings": embeddings,
                "model": request.model,
                "dimensions": 384,
                "processingTime": f"{len(request.documents) * 0.1:.1f} seconds",
                "provider": request.provider
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {request.provider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to create embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status/{request_id}")
async def get_queue_status(request_id: str):
    """Get status of a queued request"""
    status = await queue_manager.get_request_status(request_id)
    
    if status:
        return status
    else:
        raise HTTPException(status_code=404, detail="Request not found")

@app.get("/queue/stats")
async def get_queue_stats():
    """Get overall queue statistics"""
    return await queue_manager.get_queue_stats()

@app.post("/queue/cancel/{request_id}")
async def cancel_request(request_id: str):
    """Cancel a queued request"""
    success = await queue_manager.cancel_request(request_id)
    
    if success:
        return {"message": f"Request {request_id} cancelled"}
    else:
        raise HTTPException(status_code=404, detail="Request not found or already processing")

@app.post("/admin/index-knowledge")
async def trigger_indexing():
    """Manually trigger knowledge indexing (admin endpoint)"""
    try:
        if not bee_context_manager.knowledge_indexer or not bee_context_manager.knowledge_indexer.enabled:
            raise HTTPException(status_code=503, detail="ChromaDB not available")

        # Get current stats
        stats = bee_context_manager.knowledge_indexer.get_stats()
        current_count = stats.get('document_count', 0)

        # Clear existing collection
        if current_count > 0:
            logger.info(f"Clearing existing {current_count} documents...")
            bee_context_manager.knowledge_indexer.clear_collection()

        # Load brain knowledge
        brain_knowledge = await bee_context_manager.load_brain_knowledge()

        # Trigger background indexing
        asyncio.create_task(index_knowledge_background(brain_knowledge))

        return {
            "status": "indexing_started",
            "message": "Knowledge indexing started in background",
            "previous_count": current_count,
            "check_status_url": "/admin/index-status"
        }

    except Exception as e:
        logger.error(f"Failed to trigger indexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/index-status")
async def get_index_status():
    """Get current indexing status"""
    try:
        if not bee_context_manager.knowledge_indexer or not bee_context_manager.knowledge_indexer.enabled:
            return {
                "status": "disabled",
                "message": "ChromaDB not available"
            }

        stats = bee_context_manager.knowledge_indexer.get_stats()

        return {
            "status": "active" if stats.get('document_count', 0) > 0 else "empty",
            "document_count": stats.get('document_count', 0),
            "collection_name": stats.get('collection_name'),
            "semantic_search_enabled": stats.get('document_count', 0) > 0
        }

    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge/search")
async def search_knowledge(request: Dict[str, Any]):
    """Search knowledge base"""
    try:
        query = request.get("query", "")
        provider = request.get("provider", "ollama")
        limit = request.get("limit", 10)
        
        if provider == "ollama":
            # Mock search results
            results = [
                {
                    "content": f"Knowledge about {query} from honey jar data",
                    "score": 0.95,
                    "source": "honey_jar_1"
                },
                {
                    "content": f"Related information on {query} patterns",
                    "score": 0.87,
                    "source": "report_analysis"
                },
                {
                    "content": f"Historical data regarding {query} trends",
                    "score": 0.82,
                    "source": "historical_logs"
                }
            ]
            
            return {
                "query": query,
                "results": results[:limit],
                "totalResults": len(results),
                "searchTime": "0.234 seconds",
                "provider": provider,
                "knowledgeBaseVersion": "1.2.3"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
            
    except Exception as e:
        logger.error(f"Failed to search knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Queue worker logic
async def process_queue_worker():
    """Background worker to process queued requests"""
    logger.info("Starting queue worker...")
    
    while True:
        try:
            # Get next request from queue
            request = await queue_manager.get_next_request()
            
            if request:
                logger.info(f"Processing request {request.request_id} of type {request.request_type}")
                
                try:
                    # Route to appropriate handler based on request type
                    if request.request_type == "chat":
                        result = await process_chat_request(request)
                    elif request.request_type == "report":
                        result = await process_report_request(request)
                    elif request.request_type == "embedding":
                        result = await process_embedding_request(request)
                    else:
                        raise Exception(f"Unknown request type: {request.request_type}")
                    
                    # Mark as complete
                    await queue_manager.mark_request_complete(request, result)
                    
                except Exception as e:
                    logger.error(f"Error processing request {request.request_id}: {e}")
                    
                    # Retry logic
                    if request.retry_count < 3:
                        request.retry_count += 1
                        await queue_manager.enqueue_request(
                            request.user_id,
                            request.user_role,
                            request.request_type,
                            request.payload,
                            priority_boost=1  # Boost priority for retries
                        )
                        logger.info(f"Requeued request {request.request_id} (retry {request.retry_count})")
                    else:
                        await queue_manager.mark_request_complete(request, None, str(e))
            else:
                # No requests in queue, wait a bit
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Queue worker error: {e}")
            await asyncio.sleep(1)  # Back off on error

async def process_chat_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process a chat request"""
    payload = request.payload
    message = payload.get("message", "")
    
    # Check if this is a report request
    report_keywords = ["generate report", "create report", "report on", "analyze", "summary report", "detailed analysis"]
    is_report_request = any(keyword in message.lower() for keyword in report_keywords)
    
    if is_report_request:
        # Handle as report with enhanced formatting
        report_prompt = f"""{message}

Since this is a report request, please generate a comprehensive report that includes:

1. **Executive Summary**
   - Brief overview of the analysis
   - Key findings at a glance

2. **Detailed Analysis**
   - In-depth examination of the topic
   - Data points and insights
   - Technical details where relevant

3. **Recommendations**
   - Actionable next steps
   - Best practices
   - Risk mitigation strategies

4. **Conclusion**
   - Summary of key takeaways
   - Future considerations

Format the response as a structured report with clear sections and professional tone.
Include relevant security considerations where applicable.
"""
        # Get available models and use the appropriate one
        models = await ollama_client.get_models()
        if not models:
            raise HTTPException(status_code=503, detail="No Ollama models available")
        
        default_model = AI_PROVIDERS["ollama"]["defaultModel"]
        available_models = [m["name"] for m in models]
        
        if default_model not in available_models:
            model = available_models[0]
            logger.warning(f"Default model '{default_model}' not found, using {model}")
        else:
            model = default_model
            
        result = await generate_with_fallback(report_prompt, model)
        
        return {
            "response": result.get("response", ""),
            "conversation_id": payload.get("conversation_id") or f"conv_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "bee_personality": "professional_analyst",
            "tools_used": ["report_generator"],
            "processing_time": result.get('total_duration', 0) / 1e9,
            "report_generated": True,
            "report_metadata": {
                "type": "conversational_report",
                "model": result.get("model", model),
                "provider": result.get("provider", "ollama"),
                "tokens_used": result.get("eval_count", 0),
                "privacy_level": "high" if not payload.get("encryption_required") else "maximum"
            }
        }
    else:
        # Handle as regular conversation using BeeContextManager for enhanced context
        enhanced_prompt = await bee_context_manager.build_enhanced_prompt(
            payload.get("message", ""),
            payload.get("user_id", "anonymous"),
            conversation_history=None,  # Could pass history if available
            honey_jar_id=payload.get("honey_jar_id")
        )
        
        # Get available models and use the appropriate one
        models = await ollama_client.get_models()
        if not models:
            raise HTTPException(status_code=503, detail="No Ollama models available")
        
        default_model = AI_PROVIDERS["ollama"]["defaultModel"]
        available_models = [m["name"] for m in models]
        
        if default_model not in available_models:
            model = available_models[0]
            logger.warning(f"Default model '{default_model}' not found, using {model}")
        else:
            model = default_model
            
        result = await generate_with_fallback(enhanced_prompt, model)
        
        return {
            "response": result.get("response", ""),
            "conversation_id": payload.get("conversation_id") or f"conv_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "tools_used": payload.get("tools_enabled", []),
            "processing_time": result.get('total_duration', 0) / 1e9,  # Return numeric value, not string
            "report_generated": False,
            "provider": result.get("provider", "ollama")
        }

async def process_report_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process a report generation request"""
    payload = request.payload
    
    # Similar to existing report generation logic
    prompt = f"""CRITICAL INSTRUCTION: Generate an EXTREMELY comprehensive, detailed report. This is a professional-grade analytical document that must be thorough and exhaustive. DO NOT write a brief summary - this requires substantial depth and analysis.

REPORT REQUIREMENTS:
- Template: {payload.get('templateId')}
- Data Sources: {', '.join(payload.get('dataSources', []))}
- Privacy Level: {payload.get('privacyLevel')}
- Required Fields: {json.dumps(payload.get('requiredFields', {}), indent=2)}

MANDATORY SECTIONS (Each section must be detailed and comprehensive):

1. EXECUTIVE SUMMARY (minimum 500 words)
   - Provide a thorough overview covering all key aspects
   - Include context, scope, and high-level findings
   - Summarize critical insights and recommendations
   - DO NOT make this brief - it should be substantial

2. DETAILED FINDINGS (minimum 2000 words)
   - Present comprehensive analysis of all data sources
   - Include specific examples, metrics, and observations
   - Break down findings by category with detailed subsections
   - Provide context and interpretation for each finding
   - Include quantitative and qualitative analysis

3. IN-DEPTH TECHNICAL ANALYSIS (minimum 2000 words)
   - Conduct thorough examination of technical aspects
   - Analyze patterns, trends, and correlations
   - Discuss methodology and analytical approaches
   - Present detailed evidence supporting conclusions
   - Include comparative analysis where relevant

4. COMPREHENSIVE RECOMMENDATIONS (minimum 1500 words)
   - Provide detailed, actionable recommendations
   - Explain rationale and expected outcomes for each
   - Include implementation considerations and priorities
   - Discuss potential challenges and mitigation strategies
   - Present both short-term and long-term recommendations

5. RISK ASSESSMENT & CONSIDERATIONS (minimum 1000 words)
   - Analyze potential risks and vulnerabilities
   - Evaluate likelihood and impact of identified risks
   - Discuss compliance and regulatory considerations
   - Provide risk mitigation strategies

6. CONCLUSION & NEXT STEPS (minimum 500 words)
   - Synthesize key points from the entire analysis
   - Provide clear, actionable next steps
   - Include timeline and resource considerations
   - Summarize critical takeaways

WRITING REQUIREMENTS:
- Write in a professional, analytical tone
- Use specific examples and concrete details throughout
- Include relevant technical terminology appropriately
- Structure with clear headings and subheadings
- Ensure logical flow between sections
- Maintain depth and substance in every section
- DO NOT stop writing until all sections are thoroughly covered
- Target total length: 10,000+ words for comprehensive coverage

BEGIN COMPREHENSIVE REPORT:
"""
    
    # Get available models and use the appropriate one
    models = await ollama_client.get_models()
    if not models:
        raise HTTPException(status_code=503, detail="No Ollama models available")

    # Use report-specific model from config
    report_model = llm_config.get('report_model', AI_PROVIDERS["ollama"]["defaultModel"])
    report_fallback = llm_config.get('report_fallback_model', AI_PROVIDERS["ollama"]["defaultModel"])
    available_models = [m["name"] for m in models]

    # Try report model first, then fallback, then first available
    if report_model in available_models:
        model = report_model
        logger.info(f"Using configured report model: {model}")
    elif report_fallback in available_models:
        model = report_fallback
        logger.warning(f"Report model '{report_model}' not found, using fallback: {model}")
    else:
        model = available_models[0]
        logger.warning(f"Neither report model '{report_model}' nor fallback found, using: {model}")

    # Prepare options with report-specific max_tokens
    report_max_tokens = llm_config.get('report_max_tokens', 8192)
    options = {
        "num_predict": report_max_tokens,
        "temperature": 0.7
    }
    logger.info(f"Report generation: model={model}, max_tokens={report_max_tokens}")

    result = await generate_with_fallback(prompt, model, options)
    
    return {
        "reportId": f"report_{request.request_id}",
        "content": result.get("response", ""),
        "model": result.get("model", model),
        "provider": result.get("provider", "ollama"),
        "tokensUsed": result.get("eval_count", 0),
        "processingTime": result.get('total_duration', 0) / 1e9
    }

async def process_embedding_request(request: QueuedRequest) -> Dict[str, Any]:
    """Process an embedding request"""
    # Placeholder for embedding logic
    return {
        "embeddings": [],
        "model": "nomic-embed-text",
        "dimensions": 384
    }

async def index_knowledge_background(brain_knowledge: str):
    """Background task to index knowledge in ChromaDB without blocking startup"""
    try:
        is_indexing.set()  # Mark indexing as in progress
        logger.info("🔄 Background indexing started...")

        # Delay to ensure service is fully started
        await asyncio.sleep(5)

        # Index brain knowledge with progress updates
        if brain_knowledge:
            logger.info(f"📖 Indexing brain knowledge ({len(brain_knowledge)} chars)...")
            logger.info("⏳ This may take 30-60 seconds for embedding generation...")

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                bee_context_manager.knowledge_indexer.index_brain_knowledge,
                brain_knowledge
            )

            if success:
                logger.info("✅ Brain knowledge indexed successfully")
            else:
                logger.error("❌ Failed to index brain knowledge")

            # Small delay between brain and docs indexing
            await asyncio.sleep(2)

        # Index documentation
        from pathlib import Path
        docs_path = Path(__file__).parent.parent / "docs"
        if docs_path.exists():
            logger.info("📚 Indexing documentation...")
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                bee_context_manager.knowledge_indexer.index_documentation,
                docs_path
            )
            if success:
                logger.info("✅ Documentation indexed successfully")
            else:
                logger.warning("⚠️  Documentation indexing incomplete")

        # Show final stats
        stats = bee_context_manager.knowledge_indexer.get_stats()
        logger.info(f"🎉 Indexing complete! {stats.get('document_count', 0)} document chunks indexed")

    except Exception as e:
        logger.error(f"Background indexing failed: {e}", exc_info=True)
    finally:
        is_indexing.clear()  # Clear indexing flag when done

async def pii_cache_cleanup_task(cache_manager):
    """
    Background task to maintain PII cache health.
    Runs cleanup every 5 minutes to remove expired entries.
    """
    logger.info("🧹 PII cache cleanup task started")
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes (matches config cleanup interval)
            await cache_manager.cleanup_expired()
            logger.debug("PII cache cleanup completed")
        except asyncio.CancelledError:
            logger.info("PII cache cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"PII cache cleanup error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global worker_task, pii_middleware

    # Initialize queue manager
    await queue_manager.initialize()

    # Upgrade PII middleware to enhanced mode with async components
    if pii_middleware and EnhancedDeserializer and ImprovedCacheManager and app_config:
        try:
            # Get Redis configuration from config
            redis_db = app_config.get('security', {}).get('message_pii_protection', {}).get('serialization', {}).get('redis_db', 3)
            redis_url = f"redis://redis:6379/{redis_db}"

            # Initialize improved cache manager with async connection
            improved_cache = ImprovedCacheManager(redis_url=redis_url)
            await improved_cache.connect()

            # Replace with enhanced deserializer
            pii_middleware.deserializer = EnhancedDeserializer(improved_cache)
            pii_middleware.cache_manager = improved_cache

            logger.info("✨ Enhanced PII middleware activated: position tracking + visual indicators enabled")

            # Start background cache cleanup task
            asyncio.create_task(pii_cache_cleanup_task(improved_cache))
        except Exception as enhance_error:
            logger.warning(f"Failed to upgrade to enhanced PII components: {enhance_error}")
            logger.info("Continuing with basic PII middleware")

    # Initialize Bee Context Manager and load brain knowledge
    logger.info("Loading Bee Brain knowledge into memory...")
    brain_knowledge = await bee_context_manager.load_brain_knowledge()
    if brain_knowledge:
        logger.info(f"✅ Bee Brain loaded successfully: {len(brain_knowledge)} characters")
    else:
        logger.warning("⚠️ Bee Brain knowledge not loaded - using fallback mode")

    # Start queue worker
    worker_task = asyncio.create_task(process_queue_worker())

    # ChromaDB semantic search - start auto-indexer for brain files
    if bee_context_manager.knowledge_indexer and bee_context_manager.knowledge_indexer.enabled:
        try:
            stats = bee_context_manager.knowledge_indexer.get_stats()
            doc_count = stats.get('document_count', 0)
            logger.info(f"📊 ChromaDB status: {doc_count} document chunks indexed")

            # Start the brain auto-indexer (watches for brain file changes)
            try:
                from knowledge_indexer import start_auto_indexer
                await start_auto_indexer()
                logger.info("🔄 Brain auto-indexer started (will detect brain file changes)")
            except Exception as auto_idx_err:
                logger.warning(f"Failed to start brain auto-indexer: {auto_idx_err}")
                if doc_count == 0:
                    logger.warning("📚 ChromaDB not indexed. Use POST /admin/index-knowledge to index manually.")
        except Exception as e:
            logger.warning(f"ChromaDB check failed: {e}. Using keyword fallback.")

    logger.info("External AI Service started successfully with Bee Brain system")
    
    # Check Ollama models on startup
    try:
        models = await ollama_client.get_models()
        if models:
            model_names = [m["name"] for m in models]
            logger.info(f"Available Ollama models: {model_names}")
            
            # Check if default model is available
            default_model = AI_PROVIDERS["ollama"]["defaultModel"]
            if default_model not in model_names:
                logger.warning(f"⚠️  Default model '{default_model}' not found!")
                logger.warning(f"📌 To install it, run: ollama pull {default_model.split(':')[0]}")
                logger.info(f"🔄 Will use fallback model: {model_names[0] if model_names else 'none'}")
        else:
            logger.error("❌ No Ollama models found!")
            logger.error("📌 Please install at least one model:")
            logger.error("   - For general use: ollama pull llama3.3")
            logger.error("   - For code tasks: ollama pull deepseek-coder-v2")
            logger.error("   - For smaller model: ollama pull phi3")
    except Exception as e:
        logger.error(f"⚠️  Could not check Ollama models: {e}")
        logger.error("📌 Make sure Ollama is running: ollama serve")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global worker_task

    # Cancel worker task
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    # Close queue manager
    await queue_manager.close()

    # Close LLM connection pool
    await LLMConnectionPool.close()

    logger.info("External AI Service shut down")

if __name__ == "__main__":
    logger.info(f"Starting STING External AI Service on {SERVICE_HOST}:{SERVICE_PORT}")
    logger.info(f"Ollama endpoint: {OLLAMA_BASE_URL}")
    
    uvicorn.run(
        app,
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        log_level="info"
    )