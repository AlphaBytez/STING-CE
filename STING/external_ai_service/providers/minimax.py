"""
MiniMax Provider Implementation

MiniMax AI cloud provider with OpenAI-compatible API.
Includes automatic fallback support to other providers.
"""

import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
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

if TYPE_CHECKING:
    from .ollama import OllamaProvider

logger = logging.getLogger(__name__)


class MiniMaxProvider(BaseProvider):
    """Provider for MiniMax AI cloud API.
    
    Uses OpenAI-compatible API format (/v1/chat/completions).
    Supports automatic fallback to other providers when unavailable.
    """
    
    # Connection pool (shared across instances)
    _session: Optional[aiohttp.ClientSession] = None
    MAX_CONNECTIONS: int = 10
    MAX_CONNECTIONS_PER_HOST: int = 8
    
    # Status cache (shared across instances) - avoid repeated API calls for status checks
    _status_cache: Optional[Dict[str, Any]] = None
    _status_cache_time: float = 0
    CACHE_TTL_SECONDS: int = 60  # Cache status for 60 seconds
    
    def __init__(self, config: ProviderConfig):
        """Initialize MiniMax provider."""
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
            logger.info(f"🔌 Created MiniMax connection pool: max={cls.MAX_CONNECTIONS}")
        return cls._session
    
    @classmethod
    async def close_session(cls):
        """Close the shared session."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
            logger.info("🔌 Closed MiniMax connection pool")
    
    def _is_cache_valid(self, cache_time: float) -> bool:
        """Check if cache is still valid."""
        return (time.time() - cache_time) < self.CACHE_TTL_SECONDS
    
    def is_configured(self) -> bool:
        """Check if MiniMax API key is configured."""
        return bool(
            self.config.api_key and 
            self.config.api_key.strip() and
            self.config.endpoint
        )
    
    async def check_status(self) -> ProviderStatus:
        """Check if MiniMax API is accessible.
        
        Uses cached status to avoid repeated API calls. If API key is configured,
        we assume it's running (actual generation will fail fast if there's an issue).
        """
        if not self.is_configured():
            return ProviderStatus(
                running=False,
                configured=False,
                error="MiniMax API key not configured"
            )
        
        # Return cached status if valid (avoids API call on every request)
        if MiniMaxProvider._status_cache and self._is_cache_valid(MiniMaxProvider._status_cache_time):
            cached = MiniMaxProvider._status_cache
            return ProviderStatus(
                running=cached.get("running", False),
                configured=True,
                models_count=cached.get("models", 1),
                endpoint=cached.get("endpoint", self.config.endpoint),
                api_type=cached.get("api_type", "minimax"),
                error=cached.get("error"),
                consecutive_failures=self._consecutive_failures,
                last_error=self._last_error,
                is_healthy=self.is_healthy
            )
        
        # For MiniMax, if API key is configured, assume it's running
        # Actual generation will fail fast if there's an issue
        # This avoids a wasteful API call just for status check
        MiniMaxProvider._status_cache = {
            "running": True,
            "models": 1,
            "endpoint": self.config.endpoint,
            "api_type": "minimax",
            "error": None
        }
        MiniMaxProvider._status_cache_time = time.time()
        
        return ProviderStatus(
            running=True,
            configured=True,
            models_count=1,
            endpoint=self.config.endpoint,
            api_type="minimax",
            consecutive_failures=self._consecutive_failures,
            last_error=self._last_error,
            is_healthy=self.is_healthy
        )
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """Generate text using MiniMax API."""
        if not self.is_configured():
            raise Exception("MiniMax not configured")
        
        options = options or {}
        
        # For MiniMax, always use our configured model unless explicitly a MiniMax model
        # This handles fallback scenarios where an Ollama model name might be passed
        if model and model.lower().startswith("minimax"):
            effective_model = model
        else:
            effective_model = self.config.default_model
            if model and model != effective_model:
                logger.debug(f"🔄 Overriding model '{model}' with MiniMax default: {effective_model}")
        
        max_tokens = options.get("num_predict", options.get("max_tokens", 4096))
        temperature = options.get("temperature", 0.7)
        timeout_seconds = options.get("timeout", 300)
        
        payload = {
            "model": effective_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📤 [MiniMax] Sending: model={effective_model}, max_tokens={max_tokens}")
        
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            session = await self.get_session()
            
            async with session.post(
                f"{self.config.endpoint}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    duration_ns = int((time.time() - start_time) * 1e9)
                    
                    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
                    
                    self.record_success()
                    logger.info(f"✅ [MiniMax] Generation successful: {completion_tokens} tokens")
                    
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
        except aiohttp.ClientError as e:
            error = f"Connection error: {e}"
            self.record_failure(error)
            raise Exception(error)
        except Exception as e:
            if str(e) != str(self._last_error):
                self.record_failure(str(e))
            raise
    
    async def generate_with_fallback(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        fallback_provider: Optional['OllamaProvider'] = None
    ) -> GenerationResult:
        """Generate with automatic fallback to another provider.
        
        Args:
            prompt: The input prompt
            model: Model to use
            options: Generation options
            fallback_provider: Provider to use if MiniMax fails
            
        Returns:
            GenerationResult with provider and fallback info
        """
        # Check if MiniMax is configured
        if not self.is_configured():
            logger.warning("🔄 MiniMax not configured, falling back immediately")
            if fallback_provider:
                return await self._execute_fallback(
                    fallback_provider, prompt, options, "not_configured"
                )
            raise Exception("MiniMax not configured and no fallback available")
        
        try:
            return await self.generate(prompt, model, options)
        except Exception as e:
            error_reason = str(e)
            logger.warning(f"🔄 MiniMax failed, attempting fallback: {error_reason}")
            
            # Log structured event for alerting
            self._log_fallback_event(error_reason)
            
            if fallback_provider:
                return await self._execute_fallback(
                    fallback_provider, prompt, options, error_reason
                )
            raise
    
    async def _execute_fallback(
        self,
        fallback_provider: 'OllamaProvider',
        prompt: str,
        options: Optional[Dict[str, Any]],
        reason: str
    ) -> GenerationResult:
        """Execute fallback to another provider."""
        logger.warning(f"🔄 FALLBACK: Switching to {fallback_provider.name}")
        
        try:
            result = await fallback_provider.generate(prompt, None, options)
            result.fallback_used = True
            result.fallback_reason = reason
            logger.info(f"✅ Fallback to {fallback_provider.name} successful")
            return result
        except Exception as e:
            logger.error(f"❌ Fallback also failed: {e}")
            raise Exception(
                f"Both MiniMax and {fallback_provider.name} failed. "
                f"MiniMax: {reason}, {fallback_provider.name}: {e}"
            )
    
    def _log_fallback_event(self, reason: str):
        """Log structured fallback event for alerting systems."""
        event = {
            "event": "llm_fallback",
            "from_provider": self.id,
            "to_provider": "fallback",
            "reason": reason,
            "consecutive_failures": self._consecutive_failures,
            "timestamp": datetime.now().isoformat()
        }
        logger.warning(f"📊 FALLBACK_EVENT: {json.dumps(event)}")
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get list of available MiniMax models."""
        if not self.is_configured():
            return []
        
        try:
            session = await self.get_session()
            timeout = aiohttp.ClientTimeout(total=10)
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            async with session.get(
                f"{self.config.endpoint}/models",
                headers=headers,
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
                            "details": {"format": "minimax"}
                        })
                    
                    logger.info(f"✅ [MiniMax] Retrieved {len(models)} models")
                    return models
                else:
                    logger.warning(f"Failed to get MiniMax models: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Failed to get MiniMax models: {e}")
            return []


def create_minimax_provider(
    api_key: str,
    base_url: str = "https://api.minimax.io/v1",
    default_model: str = "MiniMax-Text-01",
    is_primary: bool = True
) -> MiniMaxProvider:
    """Factory function to create a MiniMax provider with common settings."""
    config = ProviderConfig(
        id="minimax",
        name="MiniMax",
        description="MiniMax AI - Cloud LLM with advanced reasoning capabilities",
        provider_type=ProviderType.CLOUD,
        privacy_level=PrivacyLevel.MEDIUM,
        endpoint=base_url,
        api_key=api_key,
        default_model=default_model,
        max_tokens=1048576,
        timeout=300,
        is_primary=is_primary,
        estimated_cost_per_token=0.00001,
        capabilities=ProviderCapabilities(
            text_generation=True,
            chat_completion=True,
            code_analysis=True,
            multi_modal=True,
            reasoning=True,
            streaming=True,
            function_calling=True,
        )
    )
    return MiniMaxProvider(config)
