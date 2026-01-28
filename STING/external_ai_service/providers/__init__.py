"""
LLM Provider Registry and Unified Interface

This module provides:
- Provider registry for dynamic provider management
- Unified generate function with automatic fallback
- Provider configuration from environment/config files
"""

import os
import logging
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    PrivacyLevel,
    ProviderCapabilities,
    ProviderStatus,
    GenerationResult,
)
from .ollama import OllamaProvider, create_ollama_provider
from .minimax import MiniMaxProvider, create_minimax_provider

logger = logging.getLogger(__name__)

# Re-export for convenience
__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderConfig",
    "ProviderType",
    "PrivacyLevel",
    "ProviderCapabilities",
    "ProviderStatus",
    "GenerationResult",
    # Provider implementations
    "OllamaProvider",
    "MiniMaxProvider",
    # Factory functions
    "create_ollama_provider",
    "create_minimax_provider",
    # Registry
    "ProviderRegistry",
    "get_registry",
    # Unified interface
    "generate_with_fallback",
]


class ProviderRegistry:
    """Registry for managing LLM providers.
    
    Provides:
    - Provider registration and discovery
    - Primary/fallback provider management
    - Unified generation with automatic fallback
    - Status monitoring for all providers
    """
    
    _instance: Optional['ProviderRegistry'] = None
    
    def __init__(self):
        """Initialize the provider registry."""
        self._providers: Dict[str, BaseProvider] = {}
        self._primary_id: Optional[str] = None
        self._fallback_id: Optional[str] = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'ProviderRegistry':
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        cls._instance = None
    
    def register(self, provider: BaseProvider):
        """Register a provider.
        
        Args:
            provider: Provider instance to register
        """
        self._providers[provider.id] = provider
        logger.info(f"📌 Registered provider: {provider.name} (id={provider.id})")
        
        # Track primary/fallback
        if provider.config.is_primary:
            self._primary_id = provider.id
            logger.info(f"⭐ Set {provider.name} as primary provider")
        if provider.config.is_fallback:
            self._fallback_id = provider.id
            logger.info(f"🔄 Set {provider.name} as fallback provider")
    
    def get(self, provider_id: str) -> Optional[BaseProvider]:
        """Get a provider by ID."""
        return self._providers.get(provider_id)
    
    def get_primary(self) -> Optional[BaseProvider]:
        """Get the primary provider."""
        if self._primary_id:
            return self._providers.get(self._primary_id)
        # Fallback to first configured provider
        for provider in self._providers.values():
            if provider.is_configured():
                return provider
        return None
    
    def get_fallback(self) -> Optional[BaseProvider]:
        """Get the fallback provider."""
        if self._fallback_id:
            return self._providers.get(self._fallback_id)
        return None
    
    def list_providers(self) -> List[BaseProvider]:
        """Get all registered providers."""
        return list(self._providers.values())
    
    def get_all_info(self) -> List[Dict[str, Any]]:
        """Get info for all registered providers."""
        return [p.get_provider_info() for p in self._providers.values()]
    
    async def get_all_status(self) -> Dict[str, Any]:
        """Get status for all providers.
        
        Returns:
            Dictionary with provider statuses and overall health
        """
        statuses = {}
        primary_healthy = False
        fallback_available = False
        
        for provider_id, provider in self._providers.items():
            status = await provider.check_status()
            statuses[provider_id] = {
                "configured": status.configured,
                "status": {
                    "running": status.running,
                    "error": status.error,
                } if status.error else {
                    "running": status.running,
                    "models": status.models_count,
                    "endpoint": status.endpoint,
                    "api_type": status.api_type,
                },
                "failure_stats": {
                    "consecutive_failures": status.consecutive_failures,
                    "last_error": status.last_error,
                    "is_healthy": status.is_healthy,
                },
                "model": provider.config.default_model,
            }
            
            # Track health
            if provider_id == self._primary_id and status.running:
                primary_healthy = True
            if provider_id == self._fallback_id and status.running:
                fallback_available = True
        
        return {
            "status": "healthy" if (primary_healthy or fallback_available) else "unhealthy",
            "primary_provider": self._primary_id,
            "providers": statuses,
            "fallback_available": fallback_available,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        provider_id: Optional[str] = None,
        use_fallback: bool = True
    ) -> GenerationResult:
        """Generate text with automatic fallback.
        
        Args:
            prompt: The input prompt
            model: Model to use (optional, uses provider default)
            options: Generation options
            provider_id: Specific provider to use (optional)
            use_fallback: Whether to use fallback on failure
            
        Returns:
            GenerationResult with provider and fallback info
        """
        # Determine which provider to use
        if provider_id:
            provider = self.get(provider_id)
            if not provider:
                raise ValueError(f"Provider not found: {provider_id}")
        else:
            provider = self.get_primary()
            if not provider:
                raise ValueError("No primary provider configured")
        
        fallback = self.get_fallback() if use_fallback else None
        
        # If primary is MiniMax and has fallback support, use it
        if isinstance(provider, MiniMaxProvider) and fallback:
            return await provider.generate_with_fallback(
                prompt, model, options, fallback
            )
        
        # Otherwise try primary, then fallback
        try:
            return await provider.generate(prompt, model, options)
        except Exception as e:
            if use_fallback and fallback and fallback.id != provider.id:
                logger.warning(f"🔄 Primary failed, using fallback: {e}")
                result = await fallback.generate(prompt, None, options)
                result.fallback_used = True
                result.fallback_reason = str(e)
                return result
            raise
    
    async def close_all(self):
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, 'close_session'):
                await provider.close_session()
        logger.info("🔌 Closed all provider connections")


def get_registry() -> ProviderRegistry:
    """Get the global provider registry instance."""
    return ProviderRegistry.get_instance()


def initialize_providers_from_env() -> ProviderRegistry:
    """Initialize providers from environment variables.
    
    Environment variables used:
    - MINIMAX_API_KEY: MiniMax API key
    - MINIMAX_BASE_URL: MiniMax API base URL
    - MINIMAX_DEFAULT_MODEL: Default MiniMax model
    - OLLAMA_BASE_URL: Ollama/LM Studio endpoint
    - LLM_PRIMARY_PROVIDER: Which provider is primary (minimax/ollama)
    
    Returns:
        Configured ProviderRegistry
    """
    registry = get_registry()
    
    # Get configuration from environment
    minimax_api_key = os.getenv("MINIMAX_API_KEY", "")
    minimax_base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    minimax_model = os.getenv("MINIMAX_DEFAULT_MODEL", "MiniMax-Text-01")
    
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    primary_provider = os.getenv("LLM_PRIMARY_PROVIDER", "minimax")
    
    # Create and register MiniMax provider
    if minimax_api_key:
        minimax = create_minimax_provider(
            api_key=minimax_api_key,
            base_url=minimax_base_url,
            default_model=minimax_model,
            is_primary=(primary_provider == "minimax")
        )
        registry.register(minimax)
        logger.info(f"✅ MiniMax provider configured: {minimax_base_url}")
    else:
        logger.warning("⚠️ MiniMax API key not configured, skipping provider")
    
    # Create and register Ollama provider
    if ollama_base_url:
        ollama = create_ollama_provider(
            endpoint=ollama_base_url,
            default_model=os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5-14b-instruct"),
            is_fallback=True
        )
        # If MiniMax is not primary, make Ollama primary
        if primary_provider == "ollama":
            ollama.config.is_primary = True
            ollama.config.is_fallback = False
        registry.register(ollama)
        logger.info(f"✅ Ollama provider configured: {ollama_base_url}")
    
    registry._initialized = True
    logger.info(f"📋 Provider registry initialized: {len(registry._providers)} providers")
    
    return registry


async def generate_with_fallback(
    prompt: str,
    model: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    provider_id: Optional[str] = None
) -> GenerationResult:
    """Convenience function for generating text with fallback.
    
    Uses the global registry.
    
    Args:
        prompt: The input prompt
        model: Model to use (optional)
        options: Generation options
        provider_id: Specific provider to use (optional)
        
    Returns:
        GenerationResult
    """
    registry = get_registry()
    return await registry.generate(prompt, model, options, provider_id)


# Legacy compatibility - AI_PROVIDERS dict format
def get_legacy_providers_dict() -> Dict[str, Dict[str, Any]]:
    """Get providers in legacy AI_PROVIDERS dict format.
    
    For backwards compatibility with existing code.
    """
    registry = get_registry()
    providers = {}
    
    for provider in registry.list_providers():
        info = provider.get_provider_info()
        providers[provider.id] = {
            "id": info["id"],
            "name": info["name"],
            "description": info["description"],
            "capabilities": list(info.get("capabilities", {}).keys()),
            "privacyLevel": info["privacyLevel"],
            "estimatedCost": info["estimatedCost"],
            "maxTokens": info["maxTokens"],
            "type": info["type"],
            "defaultModel": info["defaultModel"],
            "endpoint": info["endpoint"],
            "features": info.get("features", {}),
        }
    
    return providers
