"""
Conversation Summarization Service for Bee chatbot
Uses LLM to generate concise summaries of conversation segments
"""

import logging
import httpx
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import asyncio

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """
    Service for summarizing conversation segments using LLM.
    """
    
    def __init__(self, 
                 model: str = None,
                 max_summary_tokens: int = 200,
                 llm_endpoints: Optional[List[Dict[str, str]]] = None):
        """
        Initialize the conversation summarizer.
        
        Args:
            model: Model to use for summarization (defaults to config)
            max_summary_tokens: Maximum tokens for summary
            llm_endpoints: List of LLM endpoints to try
        """
        self.model = model or os.getenv('BEE_CONVERSATION_SUMMARY_MODEL', 'llama3.2:latest')
        self.max_summary_tokens = max_summary_tokens
        
        # LLM endpoints
        if llm_endpoints:
            self.llm_endpoints = llm_endpoints
        else:
            self.llm_endpoints = [
                {
                    "url": os.getenv('EXTERNAL_AI_URL', 'http://external-ai:8091'),
                    "name": "external-ai-ollama"
                },
                {
                    "url": os.getenv('NATIVE_LLM_URL', 'http://localhost:8086'),
                    "name": "native"
                },
                {
                    "url": os.getenv('LLM_GATEWAY_URL', 'http://llm-gateway:8080'),
                    "name": "docker"
                }
            ]
    
    async def summarize_messages(
        self,
        messages: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Summarize a list of messages into a concise summary.
        
        Args:
            messages: List of message dicts with role, content, timestamp
            context: Optional context about the conversation
            
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
        
        # Build prompt for summarization
        prompt = self._build_summarization_prompt(messages, context)
        
        # Get summary from LLM
        summary_response = await self._generate_summary(prompt)
        
        # Extract structured information
        summary_data = self._parse_summary_response(summary_response, messages)
        
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
        """
        for endpoint in self.llm_endpoints:
            try:
                logger.info(f"Trying summarization with {endpoint['name']} endpoint")
                
                async with httpx.AsyncClient() as client:
                    if endpoint['name'] == 'external-ai-ollama':
                        # Use Ollama-style API
                        response = await client.post(
                            f"{endpoint['url']}/api/generate",
                            json={
                                "model": self.model,
                                "prompt": prompt,
                                "stream": False,
                                "options": {
                                    "temperature": 0.7,
                                    "top_p": 0.9,
                                    "max_tokens": self.max_summary_tokens * 2  # Allow some overhead
                                }
                            },
                            timeout=60.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            return data.get('response', '')
                    
                    else:
                        # Legacy format
                        response = await client.post(
                            f"{endpoint['url']}/generate",
                            json={
                                "message": prompt,
                                "model": self.model,
                                "max_tokens": self.max_summary_tokens * 2,
                                "temperature": 0.7,
                                "top_p": 0.9
                            },
                            timeout=60.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            return data.get('text', data.get('response', ''))
                            
            except Exception as e:
                logger.error(f"Error with {endpoint['name']}: {str(e)}")
                continue
        
        # Fallback if all endpoints fail
        logger.warning("All LLM endpoints failed, using fallback summarization")
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