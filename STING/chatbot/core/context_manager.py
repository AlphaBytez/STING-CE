import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages conversation context for Bee
    Tracks user preferences, entities, and conversation state
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.contexts = {}  # In-memory storage keyed by conversation_id
        self.global_user_contexts = {}  # User preferences across conversations
        self.context_ttl = config.get('context_ttl_hours', 24)
        self.max_context_size = config.get('max_context_size', 1000)
    
    async def get_context(
        self,
        conversation_id: str,
        user_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get context for a conversation"""
        
        # Initialize context structure
        context = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'conversation_context': {},
            'user_context': {},
            'entities': {},
            'state': {}
        }
        
        # Get conversation-specific context
        if conversation_id in self.contexts:
            context['conversation_context'] = self.contexts[conversation_id]
        
        # Get user-specific global context
        if user_id in self.global_user_contexts:
            context['user_context'] = self.global_user_contexts[user_id]
        
        # Merge additional context if provided
        if additional_context:
            context['conversation_context'].update(additional_context)
        
        # Add system context
        context['system'] = {
            'current_time': datetime.now().isoformat(),
            'platform': 'STING',
            'assistant': 'Bee',
            'capabilities': await self._get_available_capabilities(user_id)
        }
        
        return context
    
    async def update_context(
        self,
        conversation_id: str,
        user_id: str,
        new_context: Dict[str, Any]
    ) -> bool:
        """Update context for a conversation"""
        
        # Update conversation context
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = {}
        
        # Update with new context
        self.contexts[conversation_id].update(new_context)
        
        # Extract and update user preferences
        if 'user_preferences' in new_context:
            if user_id not in self.global_user_contexts:
                self.global_user_contexts[user_id] = {}
            
            self.global_user_contexts[user_id].update(new_context['user_preferences'])
        
        # Track entities mentioned
        if 'entities' in new_context:
            if 'entities' not in self.contexts[conversation_id]:
                self.contexts[conversation_id]['entities'] = {}
            
            for entity_type, entities in new_context['entities'].items():
                if entity_type not in self.contexts[conversation_id]['entities']:
                    self.contexts[conversation_id]['entities'][entity_type] = []
                
                # Add new entities, avoiding duplicates
                for entity in entities:
                    if entity not in self.contexts[conversation_id]['entities'][entity_type]:
                        self.contexts[conversation_id]['entities'][entity_type].append(entity)
        
        # Update last modified timestamp
        self.contexts[conversation_id]['last_updated'] = datetime.now().isoformat()
        
        # Trim context if too large
        await self._trim_context(conversation_id)
        
        logger.info(f"Updated context for conversation {conversation_id}")
        return True
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences across all conversations"""
        return self.global_user_contexts.get(user_id, {})
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update global user preferences"""
        if user_id not in self.global_user_contexts:
            self.global_user_contexts[user_id] = {}
        
        self.global_user_contexts[user_id].update(preferences)
        
        logger.info(f"Updated preferences for user {user_id}")
        return True
    
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text (placeholder for NER)"""
        # This is a simple implementation - in production, use proper NER
        import re
        
        entities = {
            'dates': [],
            'numbers': [],
            'emails': [],
            'urls': [],
            'monetary': []
        }
        
        # Extract dates (simple patterns)
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(?:today|tomorrow|yesterday)\b'
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract numbers
        entities['numbers'] = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        
        # Extract emails
        entities['emails'] = re.findall(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            text
        )
        
        # Extract URLs
        entities['urls'] = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            text
        )
        
        # Extract monetary values
        entities['monetary'] = re.findall(r'\$\d+(?:\.\d{2})?', text)
        
        # Remove empty lists
        entities = {k: v for k, v in entities.items() if v}
        
        return entities
    
    async def get_conversation_state(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get the current state of a conversation"""
        if conversation_id not in self.contexts:
            return {}
        
        return self.contexts[conversation_id].get('state', {})
    
    async def update_conversation_state(
        self,
        conversation_id: str,
        state_update: Dict[str, Any]
    ) -> bool:
        """Update conversation state (e.g., current topic, awaiting response)"""
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = {}
        
        if 'state' not in self.contexts[conversation_id]:
            self.contexts[conversation_id]['state'] = {}
        
        self.contexts[conversation_id]['state'].update(state_update)
        
        return True
    
    async def clear_context(
        self,
        conversation_id: str
    ) -> bool:
        """Clear context for a conversation"""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
            logger.info(f"Cleared context for conversation {conversation_id}")
            return True
        return False
    
    async def _get_available_capabilities(self, user_id: str) -> List[str]:
        """Get available capabilities based on user context"""
        # Basic capabilities available to all users
        capabilities = [
            'chat',
            'context_retention',
            'sentiment_analysis'
        ]
        
        # Add user-specific capabilities
        user_prefs = await self.get_user_preferences(user_id)
        
        if user_prefs.get('advanced_tools_enabled'):
            capabilities.extend([
                'data_analysis',
                'report_generation',
                'secure_messaging'
            ])
        
        if user_prefs.get('role') == 'admin':
            capabilities.extend([
                'admin_tools',
                'user_management',
                'system_configuration'
            ])
        
        return capabilities
    
    async def _trim_context(self, conversation_id: str):
        """Trim context if it exceeds size limits"""
        if conversation_id not in self.contexts:
            return
        
        context = self.contexts[conversation_id]
        
        # Convert to JSON to check size
        context_str = json.dumps(context)
        
        if len(context_str) > self.max_context_size * 1024:  # KB to bytes
            # Remove oldest entries from lists
            if 'entities' in context:
                for entity_type in context['entities']:
                    if len(context['entities'][entity_type]) > 10:
                        # Keep only last 10 entities of each type
                        context['entities'][entity_type] = context['entities'][entity_type][-10:]
            
            # Remove old state entries
            if 'state' in context and len(context['state']) > 20:
                # Keep only most recent state entries
                state_items = sorted(
                    context['state'].items(),
                    key=lambda x: x[1].get('timestamp', ''),
                    reverse=True
                )
                context['state'] = dict(state_items[:20])
            
            logger.info(f"Trimmed context for conversation {conversation_id}")
    
    def is_healthy(self) -> bool:
        """Health check for context manager"""
        try:
            # Basic health check
            _ = len(self.contexts)
            _ = len(self.global_user_contexts)
            return True
        except:
            return False