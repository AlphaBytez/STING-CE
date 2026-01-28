"""
Ollama/OpenAI-Compatible Provider Implementation

Supports Ollama, LM Studio, vLLM, and any OpenAI-compatible API endpoint.
This is typically used for local/private LLM deployments.
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
import aiohttp

from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    PrivacyLevel,
    ProviderCapabilities,
    ProviderStatus,
    GenerationResult,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Provider for Ollama and OpenAI-compatible local LLM endpoints.
    
    Supports:
    - Ollama (with OpenAI compatibility layer)
    - LM Studio
    - vLLM
    - Any OpenAI-compatible API
    """
    
    # Class-level cache for status and models (shared across instances)
    _status_cache: Optional[Dict] = None
    _status_cache_time: float = 0
    _models_cache: Optional[List] = None
    _models_cache_time: float = 0
    CACHE_TTL_SECONDS: int = 60  # Cache status/models for 60 seconds
    
    # Connection pool (shared across instances)
    _session: Optional[aiohttp.ClientSession] = None
    MAX_CONNECTIONS: int = 10
    MAX_CONNECTIONS_PER_HOST: int = 8
    
    def __init__(self, config: ProviderConfig):
        """Initialize Ollama provider."""
        super().__init__(config)
        # Ensure no trailing slash
        if self.config.endpoint:
            self.config.endpoint = self.config.endpoint.rstrip('/')
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session with connection pooling."""
        if cls._session is None or cls._session.closed:
            connector = aiohttp.TCPConnector(
                limit=cls.MAX_CONNECTIONS,
                limit_per_host=cls.MAX_CONNECTIONS_PER_HOST,
                enable_cleanup_closed=True,
            )
            timeout = aiohttp.ClientTimeout(total=300)
            cls._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
            logger.info(f"🔌 Created Ollama connection pool: max={cls.MAX_CONNECTIONS}")
        return cls._session
    
    @classmethod
    async def close_session(cls):
        """Close the shared session."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
            logger.info("🔌 Closed Ollama connection pool")
    
    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if cache is still valid."""
        return (time.time() - cache_time) < self.CACHE_TTL_SECONDS
    
    def is_configured(self) -> bool:
        """Check if Ollama endpoint is configured."""
        return bool(self.config.endpoint and self.config.endpoint.strip())
    
    async def check_status(self) -> ProviderStatus:
        """Check if the Ollama/OpenAI-compatible endpoint is accessible."""
        if not self.is_configured():
            return ProviderStatus(
                running=False,
                configured=False,
                error="Endpoint not configured"
            )
        
        # Return cached status if valid (cache both success AND failure to avoid repeated timeouts)
        if OllamaProvider._status_cache and self._is_cache_valid(OllamaProvider._status_cache_time):
            cached = OllamaProvider._status_cache
            return ProviderStatus(
                running=cached.get("running", False),
                configured=True,
                models_count=cached.get("models", 0),
                endpoint=cached.get("endpoint", self.config.endpoint),
                api_type=cached.get("api_type", "openai_compatible"),
                error=cached.get("error"),  # Include cached error
                consecutive_failures=self._consecutive_failures,
                last_error=self._last_error,
                is_healthy=self.is_healthy
            )
        
        try:
            session = await self.get_session()
            # Use shorter timeout (2s) to avoid blocking requests when Ollama isn't running
            timeout = aiohttp.ClientTimeout(total=2)
            
            async with session.get(
                f"{self.config.endpoint}/v1/models",
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("data", [])
                    
                    # Cache the successful result
                    OllamaProvider._status_cache = {
                        "running": True,
                        "models": len(models),
                        "endpoint": self.config.endpoint,
                        "api_type": "openai_compatible",
                        "error": None
                    }
                    OllamaProvider._status_cache_time = time.time()
                    
                    return ProviderStatus(
                        running=True,
                        configured=True,
                        models_count=len(models),
                        endpoint=self.config.endpoint,
                        api_type="openai_compatible",
                        consecutive_failures=self._consecutive_failures,
                        last_error=self._last_error,
                        is_healthy=self.is_healthy
                    )
                else:
                    error = f"HTTP {response.status}"
                    # Cache the failed result to avoid repeated checks
                    OllamaProvider._status_cache = {
                        "running": False,
                        "endpoint": self.config.endpoint,
                        "error": error
                    }
                    OllamaProvider._status_cache_time = time.time()
                    return ProviderStatus(
                        running=False,
                        configured=True,
                        error=error,
                        consecutive_failures=self._consecutive_failures,
                        last_error=error
                    )
        except Exception as e:
            error = str(e)
            # Cache the failed result to avoid repeated timeout waits
            OllamaProvider._status_cache = {
                "running": False,
                "endpoint": self.config.endpoint,
                "error": error
            }
            OllamaProvider._status_cache_time = time.time()
            logger.warning(f"Ollama status check failed (will retry in {self.CACHE_TTL_SECONDS}s): {error}")
            return ProviderStatus(
                running=False,
                configured=True,
                error=error,
                consecutive_failures=self._consecutive_failures,
                last_error=error
            )
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """Generate text using OpenAI-compatible chat/completions endpoint."""
        options = options or {}
        model = model or self.config.default_model
        
        max_tokens = options.get("num_predict", options.get("max_tokens", 2048))
        temperature = options.get("temperature", 0.7)
        
        # Set timeout for LLM generation (45 min for long reports)
        timeout_seconds = options.get("timeout", 2700)
        timeout = aiohttp.ClientTimeout(total=timeout_seconds, sock_read=None)
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        logger.info(f"📤 [Ollama] Sending to LLM: model={model}, max_tokens={max_tokens}")
        
        start_time = time.time()
        
        try:
            session = await self.get_session()
            async with session.post(
                f"{self.config.endpoint}/v1/chat/completions",
                json=payload,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    duration_ns = int((time.time() - start_time) * 1e9)
                    
                    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
                    
                    self.record_success()
                    logger.info(f"✅ [Ollama] Generation successful: {completion_tokens} tokens")
                    
                    return GenerationResult(
                        response=data["choices"][0]["message"]["content"],
                        model=data.get("model", model),
                        provider=self.id,
                        tokens_generated=completion_tokens,
                        total_duration_ns=duration_ns,
                        created_at=str(data.get("created", "")),
                        finish_reason=finish_reason,
                        raw_response=data
                    )
                else:
                    error_text = await response.text()
                    error = f"HTTP {response.status}: {error_text}"
                    self.record_failure(error)
                    raise Exception(error)
                    
        except asyncio.TimeoutError:
            error = "Request timeout"
            self.record_failure(error)
            raise Exception(error)
        except Exception as e:
            if not isinstance(e, Exception) or str(e) != str(self._last_error):
                self.record_failure(str(e))
            raise
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get list of available models from the endpoint."""
        if not self.is_configured():
            return []
        
        # Return cached models if valid
        if OllamaProvider._models_cache and self._is_cache_valid(OllamaProvider._models_cache_time):
            return OllamaProvider._models_cache
        
        try:
            session = await self.get_session()
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with session.get(
                f"{self.config.endpoint}/v1/models",
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    model_list = data.get("data", [])
                    
                    models = []
                    for model in model_list:
                        models.append({
                            "name": model.get("id"),
                            "modified_at": model.get("created", ""),
                            "size": 0,
                            "digest": "",
                            "details": {"format": "openai_compatible"}
                        })
                    
                    # Cache the result
                    OllamaProvider._models_cache = models
                    OllamaProvider._models_cache_time = time.time()
                    
                    logger.info(f"✅ [Ollama] Retrieved {len(models)} models")
                    return models
                else:
                    logger.warning(f"Failed to get models: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []


def create_ollama_provider(
    endpoint: str,
    default_model: str = "qwen2.5-14b-instruct",
    is_fallback: bool = True
) -> OllamaProvider:
    """Factory function to create an Ollama provider with common settings."""
    config = ProviderConfig(
        id="ollama",
        name="Ollama Local",
        description="Local Ollama/OpenAI-compatible deployment for maximum privacy",
        provider_type=ProviderType.LOCAL,
        privacy_level=PrivacyLevel.HIGH,
        endpoint=endpoint,
        default_model=default_model,
        max_tokens=32000,
        timeout=2700,
        is_fallback=is_fallback,
        estimated_cost_per_token=0.0,
        capabilities=ProviderCapabilities(
            text_generation=True,
            chat_completion=True,
            code_analysis=True,
            multi_modal=False,
            reasoning=False,
            streaming=True,
        )
    )
    return OllamaProvider(config)
