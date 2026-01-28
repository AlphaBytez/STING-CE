"""
Conversation Summarization Service for Bee chatbot
Uses LLM to generate concise summaries of conversation segments.

Integrated with external_ai_service for direct LLM access and Redis caching.
"""

import logging
import os
import redis
import json
import hashlib
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """
    Service for summarizing conversation segments using LLM.

    Features:
    - Direct LLM inference (no HTTP calls when running in external-ai)
    - Redis caching for summaries (24h TTL)
    - Fallback to keyword extraction if LLM unavailable
    """

    # Redis key prefix for summary cache
    SUMMARY_CACHE_PREFIX = "bee:summary:"
    SUMMARY_CACHE_TTL = 86400  # 24 hours

    def __init__(self,
                 model: str = None,
                 max_summary_tokens: int = 200,
                 llm_generate_fn: Optional[Callable] = None,
                 redis_client: Optional[redis.Redis] = None):
        """
        Initialize the conversation summarizer.

        Args:
            model: Model to use for summarization (defaults to config)
            max_summary_tokens: Maximum tokens for summary
            llm_generate_fn: Direct LLM generation function (avoids HTTP)
            redis_client: Redis client for caching summaries
        """
        self.model = model or os.getenv('BEE_CONVERSATION_SUMMARY_MODEL', 'qwen2.5-14b-instruct')
        self.max_summary_tokens = max_summary_tokens
        self.llm_generate_fn = llm_generate_fn  # Set via set_llm_generator()

        # Initialize Redis for caching
        self.redis = redis_client
        if not self.redis:
            try:
                self.redis = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'redis'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self.redis.ping()
                logger.info("✅ ConversationSummarizer connected to Redis")
            except Exception as e:
                logger.warning(f"Redis not available for summary caching: {e}")
                self.redis = None

    def set_llm_generator(self, generate_fn: Callable):
        """Set the LLM generation function for direct inference."""
        self.llm_generate_fn = generate_fn
        logger.info("✅ LLM generator set for ConversationSummarizer")
    
    def _get_cache_key(self, conversation_id: str, message_count: int) -> str:
        """Generate cache key for a conversation summary."""
        return f"{self.SUMMARY_CACHE_PREFIX}{conversation_id}:{message_count}"

    def _get_cached_summary(self, conversation_id: str, message_count: int) -> Optional[Dict[str, Any]]:
        """Check if we have a cached summary for this conversation state."""
        if not self.redis:
            return None
        try:
            key = self._get_cache_key(conversation_id, message_count)
            cached = self.redis.get(key)
            if cached:
                logger.debug(f"📝 Cache hit for summary {conversation_id[:8]}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached summary: {e}")
        return None

    def _cache_summary(self, conversation_id: str, message_count: int, summary: Dict[str, Any]):
        """Cache a summary for later retrieval."""
        if not self.redis:
            return
        try:
            key = self._get_cache_key(conversation_id, message_count)
            self.redis.setex(key, self.SUMMARY_CACHE_TTL, json.dumps(summary))
            logger.debug(f"📝 Cached summary for {conversation_id[:8]}")
        except Exception as e:
            logger.warning(f"Failed to cache summary: {e}")

    async def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Summarize a list of messages into a concise summary.

        Args:
            messages: List of message dicts with role, content, timestamp
            context: Optional context about the conversation
            conversation_id: Optional ID for caching

        Returns:
            Dictionary with summary text and metadata
        """
        if not messages:
            return {
                "summary": "No messages to summarize",
                "message_count": 0,
                "topics": [],
                "entities": []
            }

        # Check cache first
        if conversation_id:
            cached = self._get_cached_summary(conversation_id, len(messages))
            if cached:
                return cached

        # Build prompt for summarization
        prompt = self._build_summarization_prompt(messages, context)

        # Get summary from LLM
        summary_response = await self._generate_summary(prompt)

        # Extract structured information
        summary_data = self._parse_summary_response(summary_response, messages)

        # Cache the result
        if conversation_id:
            self._cache_summary(conversation_id, len(messages), summary_data)

        return summary_data
    
    def _build_summarization_prompt(
        self,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a prompt for the LLM to summarize messages.
        """
        # Format messages for summarization
        conversation_text = ""
        for msg in messages:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # Truncate very long messages
            if len(content) > 500:
                content = content[:500] + "..."
            
            conversation_text += f"{role}: {content}\n"
        
        # Build the summarization prompt
        prompt = f"""You are a helpful assistant tasked with summarizing conversations.
Please provide a concise summary of the following conversation segment.

Instructions:
1. Create a brief summary (max {self.max_summary_tokens} tokens) capturing the main points
2. Identify key topics discussed
3. Extract important entities mentioned (names, places, technical terms)
4. Note any decisions made or action items
5. Preserve important context for future reference

Conversation to summarize:
{conversation_text}

Please provide the summary in the following JSON format:
{{
    "summary": "Brief summary of the conversation",
    "topics": ["topic1", "topic2"],
    "entities": ["entity1", "entity2"],
    "key_points": ["point1", "point2"],
    "action_items": ["action1", "action2"]
}}

Summary:"""
        
        return prompt
    
    async def _generate_summary(self, prompt: str) -> str:
        """
        Generate summary using LLM.

        Uses direct LLM function if available (when running in external-ai),
        otherwise falls back to HTTP endpoints or keyword extraction.
        """
        # Try direct LLM generation first (fastest, no HTTP overhead)
        if self.llm_generate_fn:
            try:
                logger.debug("Using direct LLM function for summarization")
                response = await self.llm_generate_fn(
                    prompt=prompt,
                    model=self.model,
                    max_tokens=self.max_summary_tokens * 2,
                    temperature=0.5  # Lower temp for more consistent summaries
                )
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Direct LLM generation failed: {e}")

        # Fallback: Use keyword-based extraction (no LLM needed)
        logger.info("Using fallback summarization (no LLM)")
        return self._fallback_summary(prompt)
    
    def _parse_summary_response(
        self,
        response: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse the LLM response into structured summary data.
        """
        # Try to parse as JSON first
        try:
            # Extract JSON from response if wrapped in other text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                summary_data = json.loads(json_str)
                
                # Ensure all required fields exist
                return {
                    "summary": summary_data.get("summary", "Conversation summary"),
                    "message_count": len(messages),
                    "topics": summary_data.get("topics", []),
                    "entities": summary_data.get("entities", []),
                    "key_points": summary_data.get("key_points", []),
                    "action_items": summary_data.get("action_items", []),
                    "start_timestamp": messages[0].get("timestamp") if messages else None,
                    "end_timestamp": messages[-1].get("timestamp") if messages else None
                }
        except Exception as e:
            logger.warning(f"Failed to parse JSON summary: {e}")
        
        # Fallback: Use response as plain text summary
        return {
            "summary": response[:self.max_summary_tokens] if response else "Conversation segment",
            "message_count": len(messages),
            "topics": self._extract_topics_fallback(messages),
            "entities": [],
            "key_points": [],
            "action_items": [],
            "start_timestamp": messages[0].get("timestamp") if messages else None,
            "end_timestamp": messages[-1].get("timestamp") if messages else None
        }
    
    def _fallback_summary(self, prompt: str) -> str:
        """
        Generate a basic summary without LLM.
        """
        # Extract conversation from prompt
        conv_start = prompt.find("Conversation to summarize:")
        conv_end = prompt.find("Please provide the summary")
        
        if conv_start > 0 and conv_end > conv_start:
            conversation = prompt[conv_start:conv_end].strip()
            lines = conversation.split('\n')[1:]  # Skip header
            
            # Count messages by role
            user_count = sum(1 for line in lines if line.startswith("User:"))
            assistant_count = sum(1 for line in lines if line.startswith("Assistant:"))
            
            # Extract first and last messages
            if lines:
                first_msg = lines[0][:100] if lines[0] else ""
                last_msg = lines[-1][:100] if lines[-1] else ""
                
                summary = f"Conversation with {user_count} user messages and {assistant_count} assistant responses. "
                summary += f"Started with: {first_msg}... "
                if len(lines) > 1:
                    summary += f"Ended with: {last_msg}..."
                
                return json.dumps({
                    "summary": summary,
                    "topics": ["general"],
                    "entities": [],
                    "key_points": [f"{user_count + assistant_count} total messages"],
                    "action_items": []
                })
        
        return json.dumps({
            "summary": "Conversation segment",
            "topics": [],
            "entities": [],
            "key_points": [],
            "action_items": []
        })
    
    def _extract_topics_fallback(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract basic topics from messages without LLM.
        """
        topics = set()
        
        # Simple keyword-based topic extraction
        topic_keywords = {
            "greeting": ["hello", "hi", "hey", "greetings"],
            "help": ["help", "assist", "support", "guide"],
            "technical": ["code", "error", "bug", "install", "setup"],
            "question": ["what", "how", "why", "when", "where"],
            "settings": ["config", "setting", "preference", "option"]
        }
        
        for msg in messages:
            content_lower = msg.get("content", "").lower()
            for topic, keywords in topic_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    topics.add(topic)
        
        return list(topics)[:5]  # Limit to 5 topics
    
    async def summarize_for_pruning(
        self,
        conversation_id: str,
        messages_to_prune: List[Dict[str, Any]],
        keep_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a summary specifically for conversation pruning.
        
        Args:
            conversation_id: ID of the conversation
            messages_to_prune: Messages that will be removed
            keep_messages: Messages that will be kept
            
        Returns:
            Summary data optimized for context preservation
        """
        # Add context about what's being kept
        context = {
            "pruning_reason": "token_limit",
            "messages_kept": len(keep_messages),
            "messages_pruned": len(messages_to_prune)
        }
        
        # Generate summary
        summary_data = await self.summarize_messages(messages_to_prune, context)
        
        # Add pruning-specific metadata
        summary_data["conversation_id"] = conversation_id
        summary_data["pruning_context"] = {
            "total_messages_before": len(messages_to_prune) + len(keep_messages),
            "messages_after": len(keep_messages),
            "messages_summarized": len(messages_to_prune)
        }
        
        return summary_data


# Singleton instance
_default_summarizer = None


def get_conversation_summarizer() -> ConversationSummarizer:
    """
    Get the default conversation summarizer instance.
    
    Returns:
        ConversationSummarizer instance
    """
    global _default_summarizer
    
    if _default_summarizer is None:
        _default_summarizer = ConversationSummarizer()
    
    return _default_summarizer