"""
Enhanced Context Manager with Memory Capabilities
Provides immediate improvements to context awareness while laying groundwork for full memory system
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class EnhancedContextManager:
    """
    Enhanced context management with entity tracking and memory capabilities.
    This is a transitional implementation that improves context awareness
    while we build the full memory architecture.
    """
    
    def __init__(self):
        # Entity tracking per conversation
        self.entities: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Key facts per conversation
        self.facts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # User preferences (cross-conversation)
        self.user_preferences: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Temporary memory store (will be replaced by database)
        self.memory_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from text.
        """
        entities = {
            'names': [],
            'locations': [],
            'organizations': [],
            'dates': [],
            'numbers': [],
            'preferences': []
        }
        
        # Name extraction patterns
        name_patterns = [
            r"my name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"I'm ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"I am ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"call me ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"this is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        for pattern in name_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1)
                if name and len(name) > 1:
                    entities['names'].append(name)
        
        # Location patterns
        location_pattern = r"(?:in|from|at|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        locations = re.findall(location_pattern, text)
        entities['locations'].extend([loc for loc in locations if len(loc) > 2])
        
        # Preference patterns
        preference_patterns = [
            r"I (?:like|love|prefer|enjoy) (.*?)(?:\.|,|!|$)",
            r"I (?:don't|do not|hate|dislike) (.*?)(?:\.|,|!|$)",
            r"my favorite (.*?) is (.*?)(?:\.|,|!|$)"
        ]
        
        for pattern in preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                preference = match.group(0)
                entities['preferences'].append(preference)
        
        return entities
    
    def extract_facts(self, text: str, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract facts from text based on entities.
        """
        facts = []
        
        # If we found a name, create a user identity fact
        if entities.get('names'):
            for name in entities['names']:
                facts.append({
                    'type': 'user_identity',
                    'subject': 'user',
                    'predicate': 'has_name',
                    'object': name,
                    'confidence': 0.9,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Extract preference facts
        for pref in entities.get('preferences', []):
            if 'like' in pref or 'love' in pref or 'prefer' in pref:
                facts.append({
                    'type': 'preference',
                    'subject': 'user',
                    'predicate': 'likes',
                    'object': pref,
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat()
                })
            elif "don't" in pref or 'hate' in pref or 'dislike' in pref:
                facts.append({
                    'type': 'preference',
                    'subject': 'user',
                    'predicate': 'dislikes',
                    'object': pref,
                    'confidence': 0.8,
                    'timestamp': datetime.now().isoformat()
                })
        
        return facts
    
    def process_message(self, conversation_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """
        Process a message to extract and store context information.
        """
        # Extract entities
        entities = self.extract_entities(message)
        
        # Extract facts
        facts = self.extract_facts(message, entities)
        
        # Store entities for this conversation
        if entities['names']:
            self.entities[conversation_id]['user_name'] = entities['names'][0]
            # Also store as user preference (cross-conversation)
            self.user_preferences[user_id]['name'] = entities['names'][0]
        
        if entities['locations']:
            self.entities[conversation_id]['locations'] = entities['locations']
        
        # Store facts
        self.facts[conversation_id].extend(facts)
        
        # Store in memory (temporary - will be database later)
        memory_entry = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'entities': entities,
            'facts': facts
        }
        self.memory_store[user_id].append(memory_entry)
        
        return {
            'entities': entities,
            'facts': facts,
            'stored': True
        }
    
    def get_conversation_context(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get enriched context for a conversation.
        """
        context = {
            'entities': self.entities.get(conversation_id, {}),
            'facts': self.facts.get(conversation_id, []),
            'user_preferences': self.user_preferences.get(user_id, {}),
            'recent_memories': self._get_recent_memories(user_id, limit=5)
        }
        
        # Add user name if known
        if 'name' in context['user_preferences']:
            context['user_name'] = context['user_preferences']['name']
        elif 'user_name' in context['entities']:
            context['user_name'] = context['entities']['user_name']
        
        return context
    
    def get_system_aware_context(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get context with enhanced system awareness including AAL2 status
        """
        # Get base conversation context
        base_context = self.get_conversation_context(conversation_id, user_id)
        
        # Add system context
        try:
            import asyncio
            from app.services.system_context_service import get_enhanced_system_context
            
            # Get system context
            try:
                loop = asyncio.get_event_loop()
                system_context = loop.run_until_complete(get_enhanced_system_context())
            except RuntimeError:
                # If no event loop, create one
                system_context = asyncio.run(get_enhanced_system_context())
            
            base_context['system'] = {
                'datetime': system_context['datetime'],
                'timezone': system_context['datetime']['timezone'],
                'environment': system_context['environment']['deployment_type'],
                'platform': system_context['system']['platform'],
                'services_healthy': system_context['services']['overall'] == 'healthy',
                'redis_available': system_context['redis']['available']
            }
            
            # Add AAL2 context if user_id is available
            if user_id and user_id != 'unknown':
                try:
                    from app.decorators.aal2 import get_aal2_status
                    # Convert string user_id to int if needed
                    user_id_int = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
                    aal2_status = get_aal2_status(user_id_int)
                    
                    base_context['security'] = {
                        'aal2_verified': aal2_status['aal2_verified'],
                        'passkey_enrolled': aal2_status['passkey_enrolled'],
                        'verification_method': aal2_status.get('verification_method'),
                        'security_level': 'high' if aal2_status['aal2_verified'] else 'standard'
                    }
                except Exception as e:
                    logger.debug(f"Could not get AAL2 status for user {user_id}: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to get system context for enhanced awareness: {e}")
            # Add minimal system context
            from datetime import datetime, timezone
            base_context['system'] = {
                'datetime': {'utc': datetime.now(timezone.utc).isoformat()},
                'timezone': 'UTC',
                'environment': 'unknown',
                'services_healthy': True  # Assume healthy if we can't check
            }
        
        return base_context
    
    def _get_recent_memories(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent memories for a user.
        """
        memories = self.memory_store.get(user_id, [])
        return memories[-limit:] if memories else []
    
    def build_context_prompt(self, conversation_id: str, user_id: str) -> str:
        """
        Build a context prompt for the LLM.
        """
        context = self.get_conversation_context(conversation_id, user_id)
        prompt_parts = []
        
        # Add user identity if known
        if 'user_name' in context:
            prompt_parts.append(f"The user's name is {context['user_name']}.")
        
        # Add known facts
        for fact in context['facts'][-5:]:  # Last 5 facts
            if fact['type'] == 'preference':
                if fact['predicate'] == 'likes':
                    prompt_parts.append(f"The user {fact['object']}.")
                elif fact['predicate'] == 'dislikes':
                    prompt_parts.append(f"The user {fact['object']}.")
        
        # Add location context if available
        if 'locations' in context['entities']:
            locations = context['entities']['locations']
            if locations:
                prompt_parts.append(f"The user mentioned these locations: {', '.join(locations[:3])}.")
        
        if prompt_parts:
            return "\n\nContext:\n" + "\n".join(prompt_parts) + "\n"
        return ""
    
    def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Simple keyword search in memories (will be replaced by vector search).
        """
        memories = self.memory_store.get(user_id, [])
        query_lower = query.lower()
        
        # Score memories by relevance
        scored_memories = []
        for memory in memories:
            score = 0
            message_lower = memory['message'].lower()
            
            # Check for query terms
            for term in query_lower.split():
                if term in message_lower:
                    score += 1
            
            # Boost recent memories
            age = datetime.now() - datetime.fromisoformat(memory['timestamp'])
            if age < timedelta(hours=1):
                score += 2
            elif age < timedelta(days=1):
                score += 1
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for score, memory in scored_memories[:limit]]
    
    def clear_conversation_context(self, conversation_id: str):
        """
        Clear context for a specific conversation.
        """
        if conversation_id in self.entities:
            del self.entities[conversation_id]
        if conversation_id in self.facts:
            del self.facts[conversation_id]
    
    def export_user_memories(self, user_id: str) -> Dict[str, Any]:
        """
        Export all memories for a user.
        """
        return {
            'user_id': user_id,
            'preferences': dict(self.user_preferences.get(user_id, {})),
            'memories': self.memory_store.get(user_id, []),
            'export_timestamp': datetime.now().isoformat()
        }