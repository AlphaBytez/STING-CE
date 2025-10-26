"""
Ollama Client for Nectar Worker
Handles communication with Ollama service for AI inference
"""

import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for Ollama API with model management and keep-alive support

    Features:
    - Automatic model loading
    - Keep-alive to maintain models in memory
    - Health checking
    - Streaming support (future)
    """

    def __init__(self, base_url: str, default_model: str = "llama3.2:latest", keep_alive: str = "30m"):
        """
        Initialize Ollama client

        Args:
            base_url: Ollama service URL (e.g., http://ollama:11434)
            default_model: Default model to use
            keep_alive: How long to keep model in memory (e.g., "30m", "1h", "-1" for forever)
        """
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self.keep_alive = keep_alive

        logger.info(f"Initialized OllamaClient: {base_url}, model={default_model}, keep_alive={keep_alive}")

    async def health_check(self) -> bool:
        """Check if LLM service is healthy (OpenAI-compatible API standard)"""
        try:
            async with httpx.AsyncClient() as client:
                # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
                response = await client.get(f"{self.base_url}/v1/models", timeout=5.0)
                if response.status_code == 200:
                    logger.debug("Health check passed via OpenAI-compatible API")
                    return True
                else:
                    logger.warning(f"LLM service health check failed: HTTP {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models (OpenAI-compatible API standard)"""
        try:
            async with httpx.AsyncClient() as client:
                # Use OpenAI-compatible API (LM Studio, vLLM, Ollama with OpenAI mode)
                response = await client.get(f"{self.base_url}/v1/models", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    # Convert OpenAI format to Ollama format for compatibility
                    models = []
                    for model in data.get("data", []):
                        models.append({
                            "name": model.get("id"),
                            "modified_at": model.get("created", ""),
                            "size": 0,
                            "digest": "",
                            "details": {"format": "openai_compatible"}
                        })
                    logger.debug(f"Retrieved {len(models)} models via OpenAI-compatible API")
                    return models
                else:
                    logger.error(f"Failed to list models: HTTP {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def is_model_loaded(self, model: str) -> bool:
        """Check if a specific model is loaded"""
        models = await self.list_models()
        model_names = [m.get("name", "") for m in models]
        return model in model_names

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response using LLM service (supports OpenAI-compatible and Ollama APIs)

        Args:
            prompt: User's input prompt
            model: Model to use (defaults to default_model)
            system: System prompt/context
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        model = model or self.default_model

        try:
            async with httpx.AsyncClient() as client:
                # Try OpenAI-compatible API first (LM Studio, vLLM, etc.)
                try:
                    import time
                    start_time = time.time()

                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})

                    openai_payload = {
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "temperature": temperature,
                        "max_tokens": max_tokens or 2048
                    }

                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=openai_payload,
                        timeout=60.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        generated_text = data["choices"][0]["message"]["content"]

                        # Calculate duration
                        total_duration = time.time() - start_time
                        logger.info(f"Generated {len(generated_text)} chars in {total_duration:.2f}s with {model} (OpenAI API)")
                        return generated_text
                    else:
                        logger.debug(f"OpenAI API returned {response.status_code}, falling back to Ollama")
                except Exception as e:
                    logger.debug(f"OpenAI-compatible API not available for generation: {e}")
                    pass  # Fall through to Ollama native API

                # Fall back to Ollama native API
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    }
                }

                # Add system prompt if provided
                if system:
                    payload["system"] = system

                # Add max tokens if provided
                if max_tokens:
                    payload["options"]["num_predict"] = max_tokens

                # Add keep_alive to maintain model in memory
                payload["keep_alive"] = self.keep_alive

                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    generated_text = data.get("response", "")

                    # Log model performance
                    total_duration = data.get("total_duration", 0) / 1e9  # Convert to seconds
                    logger.info(f"Generated {len(generated_text)} chars in {total_duration:.2f}s with {model} (Ollama API)")

                    return generated_text

                else:
                    error_text = response.text
                    logger.error(f"LLM generation failed ({response.status_code}): {error_text}")
                    raise Exception(f"LLM service returned {response.status_code}: {error_text}")

        except httpx.RequestError as e:
            logger.error(f"LLM request failed: {e}")
            raise Exception(f"Failed to communicate with LLM service: {str(e)}")

        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            raise

    async def preload_model(self, model: Optional[str] = None):
        """
        Preload model into memory by making a dummy request

        Args:
            model: Model to preload (defaults to default_model)
        """
        model = model or self.default_model

        try:
            logger.info(f"Preloading model: {model}")

            await self.generate(
                prompt="Hello",
                model=model,
                max_tokens=1
            )

            logger.info(f"Model {model} preloaded successfully")

        except Exception as e:
            logger.error(f"Failed to preload model {model}: {e}")
