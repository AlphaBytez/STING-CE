"""
Database-backed Conversation Manager
Manages conversation state using PostgreSQL for persistence
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from .database_manager import DatabaseManager
from .enhanced_context_manager import EnhancedContextManager

# Import summarization service
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.conversation_summarizer import get_conversation_summarizer
# Note: token_counter removed - using simple character-based estimation instead

logger = logging.getLogger(__name__)


class ConversationManagerDB:
    """
    Database-backed conversation management for Bee.
    Provides persistent conversation storage and retrieval.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db = DatabaseManager()
        self.enhanced_context = EnhancedContextManager()
        
        self.max_history_length = config.get('max_history_length', 100)
        self.context_window = config.get('context_window', 10)
        self.conversation_timeout = config.get('conversation_timeout_hours', 24)
        
        # Cache for active conversations (reduces DB queries)
        self.conversation_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        self._cleanup_task = None
        self._initialized = False
        
        # Initialize services
        self.summarizer = get_conversation_summarizer()
        
        # Configuration for conversation management
        self.max_tokens = int(os.getenv('BEE_CONVERSATION_MAX_TOKENS', '4096'))
        self.max_messages = int(os.getenv('BEE_CONVERSATION_MAX_MESSAGES', '50'))
        self.token_buffer_percent = float(os.getenv('BEE_CONVERSATION_TOKEN_BUFFER_PERCENT', '20'))
        self.summarization_enabled = os.getenv('BEE_CONVERSATION_SUMMARIZATION_ENABLED', 'true').lower() == 'true'
        self.summarize_after_messages = int(os.getenv('BEE_CONVERSATION_SUMMARIZE_AFTER_MESSAGES', '20'))
        self.pruning_strategy = os.getenv('BEE_CONVERSATION_PRUNING_STRATEGY', 'sliding_window')
        self.keep_recent_messages = int(os.getenv('BEE_CONVERSATION_KEEP_RECENT_MESSAGES', '10'))

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Simple token estimation based on character count.
        Rough approximation: 1 token ≈ 4 characters.
        Returns dict with 'total' key for compatibility with old token_counter.
        """
        total_chars = sum(
            len(msg.get('content', '')) + len(msg.get('role', ''))
            for msg in messages
        )
        estimated_tokens = total_chars // 4
        return {'total': estimated_tokens}

    async def initialize(self):
        """
        Initialize database connection.
        """
        if not self._initialized:
            await self.db.initialize()
            self._initialized = True
            logger.info("ConversationManagerDB initialized with database")
    
    async def start_cleanup_task(self):
        """
        Start the cleanup task for old conversations.
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_conversations())
    
    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing conversation or create new one.
        """
        # Debug logging
        logger.info(f"get_or_create_conversation called with conversation_id='{conversation_id}', type={type(conversation_id)}, is_truthy={bool(conversation_id)}")
        
        # Ensure initialized
        if not self._initialized:
            await self.initialize()
        
        # Check cache first
        if conversation_id and conversation_id in self.conversation_cache:
            cached = self.conversation_cache[conversation_id]
            if cached['user_id'] == user_id:
                # Update activity
                await self.db.update_conversation_activity(conversation_id)
                return cached
        
        # Try to get from database
        if conversation_id:
            conversation = await self.db.get_conversation(conversation_id, user_id)
            if conversation:
                # Update cache
                self.conversation_cache[conversation_id] = conversation
                return conversation
        
        # Create new conversation
        conversation = await self.db.create_conversation(user_id)
        conversation_id = str(conversation['id'])
        
        # Initialize enhanced context for this conversation
        self.enhanced_context.process_message(
            conversation_id, 
            user_id, 
            "[New conversation started]"
        )
        
        # Cache it
        self.conversation_cache[conversation_id] = conversation
        
        logger.info(f"Created new conversation {conversation_id} for user {user_id}")
        return conversation
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to the conversation.
        """
        # Extract additional metadata
        sentiment = metadata.get('sentiment') if metadata else None
        tools_used = metadata.get('tools_used') if metadata else None
        
        # Store in database
        message = await self.db.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata,
            sentiment=sentiment,
            tools_used=tools_used
        )
        
        # Process with enhanced context if it's a user message
        if role == 'user':
            # Get user_id from conversation
            conversation = await self.db.get_conversation(conversation_id)
            if conversation:
                context_info = self.enhanced_context.process_message(
                    conversation_id,
                    conversation['user_id'],
                    content
                )
                
                # Store extracted entities
                for entity_type, values in context_info['entities'].items():
                    if values and isinstance(values, list):
                        for value in values:
                            await self.db.store_entity(
                                conversation_id,
                                str(message['id']),
                                entity_type,
                                str(value),
                                confidence=0.8
                            )
                
                # Store facts
                for fact in context_info['facts']:
                    await self.db.store_fact(
                        user_id=conversation['user_id'],
                        conversation_id=conversation_id,
                        fact_type=fact['type'],
                        subject=fact['subject'],
                        predicate=fact['predicate'],
                        object=fact['object'],
                        confidence=fact.get('confidence', 0.7)
                    )
        
        # Check if we need to prune the conversation
        await self.prune_and_summarize_conversation(conversation_id)
        
        return message
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from a conversation.
        """
        if limit is None:
            limit = self.context_window
        
        messages = await self.db.get_conversation_messages(conversation_id, limit)
        return messages
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get full conversation details.
        """
        conversation = await self.db.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        # Add messages
        messages = await self.db.get_conversation_messages(
            conversation_id, 
            self.max_history_length
        )
        conversation['messages'] = messages
        
        # Add context from enhanced manager
        enhanced_context = self.enhanced_context.get_conversation_context(
            conversation_id,
            user_id
        )
        conversation['enhanced_context'] = enhanced_context
        
        # Get summary
        summary = await self.db.get_conversation_summary(conversation_id)
        if summary:
            conversation['summary'] = summary
        
        return conversation

    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        Returns list of conversations with basic metadata.
        """
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id,
                    user_id,
                    bot_id,
                    title,
                    conversation_type,
                    status,
                    created_at,
                    updated_at,
                    last_message_at
                FROM conversations
                WHERE user_id = $1 AND status != 'deleted'
                ORDER BY last_message_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset
            )

            conversations = []
            for row in rows:
                # Get message count
                msg_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = $1",
                    row['id']
                )

                conversations.append({
                    'conversation_id': str(row['id']),
                    'user_id': row['user_id'],
                    'bot_id': row['bot_id'],
                    'title': row['title'] or f"Chat {str(row['id'])[:8]}",
                    'conversation_type': row['conversation_type'],
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat(),
                    'updated_at': row['updated_at'].isoformat(),
                    'last_message_at': row['last_message_at'].isoformat(),
                    'message_count': msg_count
                })

            return conversations

    async def clear_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Clear a conversation (mark as deleted).
        """
        conversation = await self.db.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        
        # Update status to deleted
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations 
                SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND user_id = $2
                """,
                uuid.UUID(conversation_id),
                user_id
            )
        
        # Clear from cache
        if conversation_id in self.conversation_cache:
            del self.conversation_cache[conversation_id]
        
        # Clear from enhanced context
        self.enhanced_context.clear_conversation_context(conversation_id)
        
        return True
    
    async def export_conversation(
        self,
        conversation_id: str,
        user_id: str,
        format: str = 'json'
    ) -> Optional[str]:
        """
        Export conversation in specified format.
        """
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        if format == 'json':
            # Convert UUID and datetime objects to strings
            def serialize(obj):
                if isinstance(obj, (uuid.UUID, datetime)):
                    return str(obj)
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            return json.dumps(conversation, indent=2, default=serialize)
        
        elif format == 'text':
            lines = [
                f"Conversation ID: {conversation_id}",
                f"User: {user_id}",
                f"Started: {conversation['started_at']}",
                f"Last Activity: {conversation['last_activity']}",
                "\n--- Messages ---\n"
            ]
            
            for msg in conversation.get('messages', []):
                timestamp = msg['timestamp']
                role = msg['role'].capitalize()
                content = msg['content']
                lines.append(f"[{timestamp}] {role}: {content}")
            
            if 'summary' in conversation:
                lines.append(f"\n--- Summary ---\n{conversation['summary']}")
            
            return "\n".join(lines)
        
        return None
    
    async def get_user_context(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get overall context for a user across all conversations.
        """
        # Get user preferences
        preferences = await self.db.get_user_preferences(user_id)
        
        # Get user facts
        facts = await self.db.get_user_facts(user_id, ['user_identity', 'preference'])
        
        # Get recent memories
        memories = await self.db.get_user_memories(user_id, limit=10)
        
        return {
            'preferences': preferences,
            'facts': facts,
            'memories': memories,
            'enhanced_context': self.enhanced_context.user_preferences.get(user_id, {})
        }
    
    async def prune_and_summarize_conversation(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Prune old messages from a conversation and create a summary.
        
        Args:
            conversation_id: ID of the conversation to prune
            
        Returns:
            Summary data if pruning occurred, None otherwise
        """
        if not self.summarization_enabled:
            return None
        
        # Get all messages for the conversation
        messages = await self.db.get_messages(conversation_id)
        
        if len(messages) <= self.summarize_after_messages:
            return None  # Not enough messages to prune
        
        # Calculate token usage (using simple estimation)
        messages_for_counting = [
            {"role": msg['role'], "content": msg['content']}
            for msg in messages
        ]
        token_info = self._estimate_tokens(messages_for_counting)
        total_tokens = token_info['total']
        
        # Check if we need to prune based on tokens or message count
        max_allowed_tokens = int(self.max_tokens * (1 - self.token_buffer_percent / 100))
        needs_pruning = (
            total_tokens > max_allowed_tokens or 
            len(messages) > self.max_messages
        )
        
        if not needs_pruning:
            return None
        
        # Determine which messages to keep and which to prune
        if self.pruning_strategy == "sliding_window":
            # Keep the most recent messages
            messages_to_keep = messages[-self.keep_recent_messages:]
            messages_to_prune = messages[:-self.keep_recent_messages]
        else:
            # For other strategies, implement as needed
            messages_to_keep = messages[-self.keep_recent_messages:]
            messages_to_prune = messages[:-self.keep_recent_messages]
        
        if not messages_to_prune:
            return None
        
        # Generate summary of pruned messages
        summary_data = await self.summarizer.summarize_for_pruning(
            conversation_id,
            messages_to_prune,
            messages_to_keep
        )
        
        # Store summary in database
        try:
            async with self.db.pool.acquire() as conn:
                summary_id = await conn.fetchval(
                    """
                    INSERT INTO conversation_summaries (
                        conversation_id, summary_text, token_count, 
                        message_count, start_timestamp, end_timestamp, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    uuid.UUID(conversation_id),
                    summary_data['summary'],
                    summary_data.get('message_count', len(messages_to_prune)),
                    len(messages_to_prune),
                    messages_to_prune[0]['timestamp'],
                    messages_to_prune[-1]['timestamp'],
                    json.dumps({
                        'topics': summary_data.get('topics', []),
                        'entities': summary_data.get('entities', []),
                        'key_points': summary_data.get('key_points', []),
                        'action_items': summary_data.get('action_items', [])
                    })
                )
                
                # Delete the pruned messages
                message_ids = [msg['id'] for msg in messages_to_prune]
                await conn.execute(
                    """
                    DELETE FROM messages 
                    WHERE id = ANY($1::uuid[])
                    """,
                    message_ids
                )
                
                # Update conversation token counts (using simple estimation)
                new_token_info = self._estimate_tokens([
                    {"role": msg['role'], "content": msg['content']}
                    for msg in messages_to_keep
                ])
                
                await conn.execute(
                    """
                    UPDATE conversations 
                    SET active_tokens = $1, total_tokens = total_tokens + $2
                    WHERE id = $3
                    """,
                    new_token_info['total'],
                    summary_data.get('message_count', 0),
                    uuid.UUID(conversation_id)
                )
                
                logger.info(f"Pruned {len(messages_to_prune)} messages from conversation {conversation_id}, created summary {summary_id}")
                
                return {
                    'summary_id': str(summary_id),
                    'messages_pruned': len(messages_to_prune),
                    'messages_kept': len(messages_to_keep),
                    'tokens_before': total_tokens,
                    'tokens_after': new_token_info['total'],
                    'summary': summary_data['summary']
                }
                
        except Exception as e:
            logger.error(f"Failed to prune conversation {conversation_id}: {e}")
            return None
    
    async def _cleanup_old_conversations(self):
        """
        Periodically clean up old conversations.
        """
        while True:
            try:
                # Wait 1 hour between cleanups
                await asyncio.sleep(3600)
                
                # Clean up conversations older than configured timeout
                deleted_count = await self.db.cleanup_old_conversations(
                    days_to_keep=self.conversation_timeout // 24
                )
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old conversations")
                
                # Clean cache
                current_time = datetime.now()
                expired_keys = [
                    key for key, conv in self.conversation_cache.items()
                    if (current_time - conv.get('last_activity', current_time)).seconds > self.cache_ttl
                ]
                
                for key in expired_keys:
                    del self.conversation_cache[key]
                
                if expired_keys:
                    logger.info(f"Cleared {len(expired_keys)} conversations from cache")
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def is_healthy(self) -> bool:
        """
        Check if the conversation manager is healthy.
        """
        return self._initialized and self.db.pool is not None
    
    async def close(self):
        """
        Clean up resources.
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        await self.db.close()