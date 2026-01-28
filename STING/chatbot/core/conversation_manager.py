import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversation state and history for Bee
    Provides context retention and conversation continuity
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conversations = {}  # In-memory storage (will be replaced with DB)
        self.max_history_length = config.get('max_history_length', 100)
        self.context_window = config.get('context_window', 10)
        self.conversation_timeout = config.get('conversation_timeout_hours', 24)
        
        # Cleanup task will be started when event loop is available
        self._cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the cleanup task - call this after event loop is running"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_conversations())
    
    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing conversation or create new one"""
        
        # Try to find existing conversation
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
            # Verify user has access
            if conversation['user_id'] == user_id:
                conversation['last_activity'] = datetime.now()
                return conversation
            else:
                logger.warning(f"User {user_id} tried to access conversation {conversation_id} owned by {conversation['user_id']}")
        
        # Look for recent conversation by user_id if no conversation_id provided
        if not conversation_id:
            for conv_id, conv in self.conversations.items():
                if (conv['user_id'] == user_id and 
                    datetime.now() - conv['last_activity'] < timedelta(hours=1)):
                    conv['last_activity'] = datetime.now()
                    return conv
        
        # Create new conversation
        new_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        
        conversation = {
            'id': new_id,
            'user_id': user_id,
            'session_id': session_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'messages': [],
            'context': {
                'user_preferences': {},
                'conversation_topics': [],
                'entities_mentioned': []
            },
            'metadata': {
                'message_count': 0,
                'tool_usage': {},
                'sentiment_history': [],
                'interaction_quality': []
            }
        }
        
        self.conversations[new_id] = conversation
        logger.info(f"Created new conversation {new_id} for user {user_id}")
        
        return conversation
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add message to conversation history with metadata"""
        if conversation_id not in self.conversations:
            logger.error(f"Conversation {conversation_id} not found")
            return False
        
        conversation = self.conversations[conversation_id]
        
        message = {
            'id': f"msg_{uuid.uuid4().hex[:12]}",
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        conversation['messages'].append(message)
        conversation['last_activity'] = datetime.now()
        conversation['metadata']['message_count'] += 1
        
        # Update conversation analytics
        if metadata:
            # Track tool usage
            if 'tools_used' in metadata:
                for tool in metadata['tools_used']:
                    tool_name = tool.get('name', 'unknown')
                    if tool_name not in conversation['metadata']['tool_usage']:
                        conversation['metadata']['tool_usage'][tool_name] = 0
                    conversation['metadata']['tool_usage'][tool_name] += 1
            
            # Track sentiment over time
            if 'sentiment' in metadata:
                conversation['metadata']['sentiment_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'sentiment': metadata['sentiment'],
                    'message_id': message['id']
                })
                
                # Keep only last 50 sentiment records
                if len(conversation['metadata']['sentiment_history']) > 50:
                    conversation['metadata']['sentiment_history'] = \
                        conversation['metadata']['sentiment_history'][-50:]
        
        # Extract and update conversation topics
        if role == 'user':
            await self._extract_topics(content, conversation)
        
        # Trim history if too long
        if len(conversation['messages']) > self.max_history_length:
            # Keep system messages and recent messages
            system_messages = [m for m in conversation['messages'][:10] if m['role'] == 'system']
            recent_messages = conversation['messages'][-self.max_history_length:]
            conversation['messages'] = system_messages + recent_messages
        
        return True
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation if user has access"""
        if conversation_id not in self.conversations:
            return None
        
        conversation = self.conversations[conversation_id]
        
        # Verify user has access
        if conversation['user_id'] != user_id:
            logger.warning(f"User {user_id} attempted to access conversation {conversation_id}")
            return None
        
        return conversation
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get recent messages from conversation for context"""
        if conversation_id not in self.conversations:
            return []
        
        messages = self.conversations[conversation_id]['messages']
        count = count or self.context_window
        
        return messages[-count:] if len(messages) > count else messages
    
    async def get_conversation_summary(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        if conversation_id not in self.conversations:
            return {}
        
        conv = self.conversations[conversation_id]
        
        # Calculate conversation metrics
        total_messages = len(conv['messages'])
        user_messages = sum(1 for m in conv['messages'] if m['role'] == 'user')
        assistant_messages = sum(1 for m in conv['messages'] if m['role'] == 'assistant')
        
        # Get average sentiment
        sentiment_scores = conv['metadata']['sentiment_history']
        avg_sentiment = {}
        if sentiment_scores:
            sentiment_keys = set()
            for score in sentiment_scores:
                sentiment_keys.update(score['sentiment'].keys())
            
            for key in sentiment_keys:
                values = [s['sentiment'].get(key, 0) for s in sentiment_scores]
                avg_sentiment[key] = sum(values) / len(values)
        
        return {
            'conversation_id': conversation_id,
            'duration': (conv['last_activity'] - conv['created_at']).total_seconds(),
            'message_count': total_messages,
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'topics': conv['context'].get('conversation_topics', []),
            'tools_used': list(conv['metadata']['tool_usage'].keys()),
            'average_sentiment': avg_sentiment,
            'last_activity': conv['last_activity'].isoformat()
        }
    
    async def clear_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Clear conversation history while maintaining structure"""
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        
        # Keep conversation structure but clear messages and reset metadata
        conversation['messages'] = []
        conversation['context'] = {
            'user_preferences': conversation['context'].get('user_preferences', {}),
            'conversation_topics': [],
            'entities_mentioned': []
        }
        conversation['metadata']['message_count'] = 0
        conversation['metadata']['tool_usage'] = {}
        conversation['metadata']['sentiment_history'] = []
        conversation['last_activity'] = datetime.now()
        
        logger.info(f"Cleared conversation {conversation_id}")
        return True
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Completely delete a conversation"""
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        
        del self.conversations[conversation_id]
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 10,
        include_summary: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        user_conversations = []
        
        for conv_id, conv in self.conversations.items():
            if conv['user_id'] == user_id:
                if include_summary:
                    summary = await self.get_conversation_summary(conv_id)
                    user_conversations.append(summary)
                else:
                    # Return basic info only
                    basic_info = {
                        'id': conv['id'],
                        'created_at': conv['created_at'].isoformat(),
                        'last_activity': conv['last_activity'].isoformat(),
                        'message_count': conv['metadata']['message_count']
                    }
                    user_conversations.append(basic_info)
        
        # Sort by last activity
        user_conversations.sort(key=lambda x: x.get('last_activity', ''), reverse=True)
        
        return user_conversations[:limit]
    
    async def export_conversation(
        self,
        conversation_id: str,
        user_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """Export conversation in specified format"""
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None
        
        if format == "json":
            # Create exportable version (convert datetime objects)
            export_data = {
                'conversation_id': conversation['id'],
                'user_id': conversation['user_id'],
                'created_at': conversation['created_at'].isoformat(),
                'last_activity': conversation['last_activity'].isoformat(),
                'messages': conversation['messages'],
                'context': conversation['context'],
                'metadata': conversation['metadata']
            }
            return json.dumps(export_data, indent=2)
            
        elif format == "text":
            text_output = f"Bee Conversation Export\n"
            text_output += f"{'='*50}\n"
            text_output += f"Conversation ID: {conversation['id']}\n"
            text_output += f"Started: {conversation['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_output += f"Last Activity: {conversation['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_output += f"Total Messages: {conversation['metadata']['message_count']}\n"
            
            if conversation['context'].get('conversation_topics'):
                text_output += f"Topics: {', '.join(conversation['context']['conversation_topics'])}\n"
            
            text_output += f"\nConversation:\n{'='*50}\n\n"
            
            for msg in conversation['messages']:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                role = "You" if msg['role'] == 'user' else "Bee"
                text_output += f"[{timestamp}] {role}: {msg['content']}\n\n"
            
            return text_output
            
        else:
            logger.error(f"Unsupported export format: {format}")
            return None
    
    async def _extract_topics(self, text: str, conversation: Dict[str, Any]):
        """Extract topics from user message (simple implementation)"""
        # This is a placeholder - in production, you'd use NLP/LLM
        # For now, we'll extract some simple patterns
        
        import re
        
        # Look for questions about specific topics
        topic_patterns = {
            'sales': r'\b(sales?|revenue|profit|earnings?)\b',
            'inventory': r'\b(inventory|stock|products?|items?)\b',
            'customers': r'\b(customers?|clients?|users?)\b',
            'analytics': r'\b(analytics?|reports?|data|metrics?)\b',
            'security': r'\b(security|authentication|password|access)\b',
            'help': r'\b(help|how|what|where|when|why)\b'
        }
        
        topics = conversation['context'].get('conversation_topics', [])
        
        for topic, pattern in topic_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                if topic not in topics:
                    topics.append(topic)
        
        # Keep only last 10 topics
        conversation['context']['conversation_topics'] = topics[-10:]
    
    async def _cleanup_old_conversations(self):
        """Periodically clean up old conversations"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                cutoff_time = datetime.now() - timedelta(hours=self.conversation_timeout)
                conversations_to_delete = []
                
                for conv_id, conv in self.conversations.items():
                    if conv['last_activity'] < cutoff_time:
                        conversations_to_delete.append(conv_id)
                
                for conv_id in conversations_to_delete:
                    # TODO: Archive to database before deleting
                    del self.conversations[conv_id]
                    logger.info(f"Cleaned up old conversation {conv_id}")
                
                if conversations_to_delete:
                    logger.info(f"Cleaned up {len(conversations_to_delete)} old conversations")
                    
            except Exception as e:
                logger.error(f"Error in conversation cleanup: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Health check for conversation manager"""
        try:
            # Check if we can access conversations
            _ = len(self.conversations)
            # Check if cleanup task is running (if started)
            if self._cleanup_task:
                return not self._cleanup_task.done()
            return True
        except:
            return False