"""
Base Provider Abstract Class for LLM Providers

This module defines the interface that all LLM providers must implement.
Each provider (MiniMax, Ollama, OpenAI, Anthropic, etc.) extends BaseProvider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Types of LLM providers."""
    CLOUD = "cloud"      # Cloud-hosted APIs (OpenAI, MiniMax, Anthropic)
    LOCAL = "local"      # Locally running models (Ollama, LM Studio)
    HYBRID = "hybrid"    # Can be either (OpenAI-compatible endpoints)


class PrivacyLevel(Enum):
    """Privacy levels for data handling."""
    HIGH = "high"        # Data stays local, no external transmission
    MEDIUM = "medium"    # Data sent to trusted cloud with encryption
    LOW = "low"          # Data sent to third-party with minimal guarantees


@dataclass
class ProviderCapabilities:
    """Capabilities that a provider supports."""
    text_generation: bool = True
    chat_completion: bool = True
    embeddings: bool = False
    code_analysis: bool = False
    multi_modal: bool = False
    reasoning: bool = False
    streaming: bool = False
    function_calling: bool = False
    

@dataclass
class ProviderConfig:
    """Configuration for a provider instance."""
    id: str
    name: str
    description: str = ""
    provider_type: ProviderType = ProviderType.CLOUD
    privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM
    endpoint: str = ""
    api_key: str = ""
    default_model: str = ""
    max_tokens: int = 4096
    timeout: int = 300
    max_retries: int = 3
    enabled: bool = True
    is_primary: bool = False
    is_fallback: bool = False
    estimated_cost_per_token: float = 0.0
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Standardized result from any provider's generation."""
    response: str
    model: str
    provider: str
    done: bool = True
    tokens_generated: int = 0
    total_duration_ns: int = 0
    created_at: Optional[str] = None
    finish_reason: str = "stop"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama-compatible response format for backwards compatibility."""
        result = {
            "response": self.response,
            "model": self.model,
            "created_at": self.created_at or datetime.now().isoformat(),
            "done": self.done,
            "eval_count": self.tokens_generated,
            "total_duration": self.total_duration_ns,
            "provider": self.provider,
        }
        if self.fallback_used:
            result["fallback"] = True
            result["fallback_reason"] = self.fallback_reason
        return result


@dataclass 
class ProviderStatus:
    """Status information for a provider."""
    running: bool
    configured: bool
    error: Optional[str] = None
    models_count: int = 0
    endpoint: str = ""
    api_type: str = ""
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    is_healthy: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "configured": self.configured,
            "error": self.error,
            "models_count": self.models_count,
            "endpoint": self.endpoint,
            "api_type": self.api_type,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "is_healthy": self.is_healthy,
        }


class BaseProvider(ABC):
    """Abstract base class for all LLM providers.
    
    Each provider must implement:
    - is_configured(): Check if provider has valid configuration
    - check_status(): Get current status of the provider
    - generate(): Generate text completion
    - get_models(): List available models
    
    Optional overrides:
    - get_provider_info(): Return provider metadata
    - health_check(): Custom health check logic
    """
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self._consecutive_failures = 0
        self._last_error: Optional[str] = None
        self._last_success: Optional[datetime] = None
        
    @property
    def id(self) -> str:
        """Provider unique identifier."""
        return self.config.id
    
    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return self.config.name
    
    @property
    def is_healthy(self) -> bool:
        """Check if provider is considered healthy based on recent failures."""
        # Consider unhealthy after 5 consecutive failures
        return self._consecutive_failures < 5
    
    def record_success(self):
        """Record a successful operation."""
        self._consecutive_failures = 0
        self._last_error = None
        self._last_success = datetime.now()
        
    def record_failure(self, error: str):
        """Record a failed operation."""
        self._consecutive_failures += 1
        self._last_error = error
        logger.warning(f"🚨 {self.name} failure #{self._consecutive_failures}: {error}")
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured.
        
        Returns:
            True if provider has all required configuration
        """
        pass
    
    @abstractmethod
    async def check_status(self) -> ProviderStatus:
        """Check if the provider is accessible and operational.
        
        Returns:
            ProviderStatus with current state information
        """
        pass
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """Generate text completion.
        
        Args:
            prompt: The input prompt
            model: Model to use (defaults to provider's default_model)
            options: Generation options (temperature, max_tokens, etc.)
            
        Returns:
            GenerationResult with the generated text
        """
        pass
    
    @abstractmethod
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get list of available models.
        
        Returns:
            List of model information dictionaries
        """
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider metadata for API responses.
        
        Returns:
            Dictionary with provider information
        """
        return {
            "id": self.config.id,
            "name": self.config.name,
            "description": self.config.description,
            "type": self.config.provider_type.value,
            "privacyLevel": self.config.privacy_level.value,
            "defaultModel": self.config.default_model,
            "maxTokens": self.config.max_tokens,
            "endpoint": self.config.endpoint,
            "enabled": self.config.enabled,
            "isPrimary": self.config.is_primary,
            "isFallback": self.config.is_fallback,
            "estimatedCost": self.config.estimated_cost_per_token,
            "capabilities": {
                "textGeneration": self.config.capabilities.text_generation,
                "chatCompletion": self.config.capabilities.chat_completion,
                "embeddings": self.config.capabilities.embeddings,
                "codeAnalysis": self.config.capabilities.code_analysis,
                "multiModal": self.config.capabilities.multi_modal,
                "reasoning": self.config.capabilities.reasoning,
                "streaming": self.config.capabilities.streaming,
                "functionCalling": self.config.capabilities.function_calling,
            },
            "features": {
                "knowledgeSync": True,
                "agentTasks": self.config.capabilities.code_analysis,
            }
        }
    
    async def health_check(self) -> bool:
        """Perform a quick health check.
        
        Returns:
            True if provider is healthy
        """
        try:
            status = await self.check_status()
            return status.running and status.configured
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name})>"
