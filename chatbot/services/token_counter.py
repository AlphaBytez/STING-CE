"""
Token counting service for Bee chatbot
Uses tiktoken for accurate token counting across different models
"""

import tiktoken
import logging
from typing import List, Dict, Optional, Union
import functools

logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Service for counting tokens in text using tiktoken.
    Supports multiple encoding models and caching for performance.
    """
    
    # Model to encoding mapping
    MODEL_ENCODINGS = {
        # OpenAI models
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "gpt-3.5": "cl100k_base",
        "text-davinci-003": "p50k_base",
        "text-davinci-002": "p50k_base",
        
        # For other models, we'll use a default encoding
        "default": "cl100k_base",  # Good general-purpose encoding
        
        # Llama models (approximate using cl100k_base)
        "llama": "cl100k_base",
        "llama2": "cl100k_base",
        "llama3": "cl100k_base",
        "llama3.2": "cl100k_base",
        
        # Other common models
        "phi": "cl100k_base",
        "phi3": "cl100k_base",
        "mistral": "cl100k_base",
        "zephyr": "cl100k_base"
    }
    
    def __init__(self, model: str = "default"):
        """
        Initialize token counter for a specific model.
        
        Args:
            model: Model name to use for encoding selection
        """
        self.model = model
        self._encoding = None
        self._encoding_name = None
        self._initialize_encoding()
        
    def _initialize_encoding(self):
        """Initialize the tiktoken encoding for the model."""
        try:
            # Try to get model-specific encoding
            if self.model in self.MODEL_ENCODINGS:
                encoding_name = self.MODEL_ENCODINGS[self.model]
            else:
                # Check if model starts with known prefix
                model_lower = self.model.lower()
                for prefix, encoding in self.MODEL_ENCODINGS.items():
                    if model_lower.startswith(prefix):
                        encoding_name = encoding
                        break
                else:
                    encoding_name = self.MODEL_ENCODINGS["default"]
            
            self._encoding_name = encoding_name
            self._encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"Initialized token counter with encoding: {encoding_name} for model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize encoding: {e}")
            # Fallback to cl100k_base
            self._encoding_name = "cl100k_base"
            self._encoding = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"Using fallback encoding: cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a single text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
            
        try:
            tokens = self._encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback to character-based estimation
            return self._estimate_tokens(text)
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Count tokens in a list of messages (conversation format).
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Dictionary with token counts by role and total
        """
        token_counts = {
            "total": 0,
            "by_role": {
                "system": 0,
                "user": 0,
                "assistant": 0,
                "tool": 0
            },
            "messages": []
        }
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Count tokens for this message
            # Note: Different models have different message formatting overhead
            # For GPT models, each message has ~4 tokens of overhead
            message_tokens = self.count_tokens(content)
            
            # Add message overhead based on model
            if self._encoding_name == "cl100k_base":
                # GPT-3.5/4 style: <|start|>role<|end|>content<|end|>
                message_tokens += 4
            else:
                # Conservative estimate for other models
                message_tokens += 3
            
            token_counts["total"] += message_tokens
            token_counts["by_role"][role] = token_counts["by_role"].get(role, 0) + message_tokens
            token_counts["messages"].append({
                "role": role,
                "tokens": message_tokens,
                "content_preview": content[:50] + "..." if len(content) > 50 else content
            })
        
        return token_counts
    
    def truncate_to_token_limit(
        self, 
        text: str, 
        max_tokens: int, 
        truncate_from: str = "end"
    ) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens allowed
            truncate_from: Where to truncate from ('start', 'end', 'middle')
            
        Returns:
            Truncated text
        """
        tokens = self._encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        if truncate_from == "start":
            truncated_tokens = tokens[-max_tokens:]
        elif truncate_from == "middle":
            # Keep start and end
            keep_start = max_tokens // 2
            keep_end = max_tokens - keep_start
            truncated_tokens = tokens[:keep_start] + tokens[-keep_end:]
        else:  # end
            truncated_tokens = tokens[:max_tokens]
        
        # Decode back to text
        try:
            return self._encoding.decode(truncated_tokens)
        except Exception as e:
            logger.error(f"Error decoding truncated tokens: {e}")
            # Fallback to character-based truncation
            return text[:max_tokens * 4]  # Rough estimate
    
    def fit_messages_to_limit(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int,
        preserve_system: bool = True,
        preserve_recent: int = 10
    ) -> List[Dict[str, str]]:
        """
        Fit messages within token limit while preserving important context.
        
        Args:
            messages: List of messages to fit
            max_tokens: Maximum token limit
            preserve_system: Whether to always keep system messages
            preserve_recent: Number of recent messages to try to preserve
            
        Returns:
            List of messages that fit within the limit
        """
        if not messages:
            return []
        
        # First, calculate tokens for each message
        message_tokens = []
        total_tokens = 0
        
        for msg in messages:
            tokens = self.count_tokens(msg.get("content", "")) + 4  # Message overhead
            message_tokens.append(tokens)
            total_tokens += tokens
        
        # If everything fits, return as-is
        if total_tokens <= max_tokens:
            return messages
        
        # Strategy: Keep system messages and most recent messages
        result = []
        used_tokens = 0
        
        # 1. Add system messages if requested
        if preserve_system:
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    if used_tokens + message_tokens[i] <= max_tokens:
                        result.append(msg)
                        used_tokens += message_tokens[i]
        
        # 2. Add recent messages (from the end)
        recent_messages = []
        recent_tokens = []
        
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("role") != "system" or not preserve_system:
                recent_messages.insert(0, msg)
                recent_tokens.insert(0, message_tokens[i])
                
                if len(recent_messages) >= preserve_recent:
                    break
        
        # 3. Add as many recent messages as will fit
        for i, msg in enumerate(recent_messages):
            if used_tokens + recent_tokens[i] <= max_tokens:
                result.append(msg)
                used_tokens += recent_tokens[i]
            else:
                # Try to add a truncated version of the last message
                remaining_tokens = max_tokens - used_tokens - 10  # Leave some buffer
                if remaining_tokens > 50:  # Only if we have reasonable space
                    truncated_content = self.truncate_to_token_limit(
                        msg.get("content", ""), 
                        remaining_tokens
                    )
                    result.append({
                        "role": msg.get("role"),
                        "content": truncated_content + "... [truncated]"
                    })
                break
        
        return result
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Fallback token estimation based on character count.
        Rough estimate: 1 token ≈ 4 characters for English text.
        """
        return len(text) // 4
    
    @functools.lru_cache(maxsize=1000)
    def cached_count_tokens(self, text: str) -> int:
        """
        Cached version of token counting for frequently repeated text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        return self.count_tokens(text)
    
    def get_model_context_limit(self) -> int:
        """
        Get the context window limit for the current model.
        
        Returns:
            Maximum number of tokens for the model
        """
        # Model context limits (approximate for non-OpenAI models)
        context_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "llama3": 8192,
            "llama3.2": 131072,  # 128k context
            "phi3": 4096,
            "mistral": 8192,
            "default": 4096
        }
        
        # Check exact model match first
        if self.model in context_limits:
            return context_limits[self.model]
        
        # Check model prefix
        model_lower = self.model.lower()
        for model_prefix, limit in context_limits.items():
            if model_lower.startswith(model_prefix):
                return limit
        
        return context_limits["default"]


# Singleton instance for default model
_default_counter = None


def get_token_counter(model: str = "default") -> TokenCounter:
    """
    Get a token counter instance for a specific model.
    
    Args:
        model: Model name
        
    Returns:
        TokenCounter instance
    """
    global _default_counter
    
    if model == "default" and _default_counter is not None:
        return _default_counter
    
    counter = TokenCounter(model)
    
    if model == "default":
        _default_counter = counter
    
    return counter