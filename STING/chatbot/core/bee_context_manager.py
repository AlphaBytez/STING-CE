"""
Bee Context Manager - Persistent conversation context management for Bee
Maintains conversation history and manages system prompts efficiently
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import os

# Import token counter
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.token_counter import get_token_counter

logger = logging.getLogger(__name__)


class BeeContextManager:
    """
    Manages persistent conversation contexts for Bee chatbot.
    - Maintains conversation history per session
    - Handles system prompt initialization
    - Implements sliding window for token management
    - Prevents redundant system prompt transmission
    """
    
    def __init__(self, 
                 max_context_length: int = 4096,
                 max_history_messages: int = 20,
                 session_timeout_minutes: int = 30,
                 model: str = "llama3.2:latest"):
        """
        Initialize the Bee Context Manager.
        
        Args:
            max_context_length: Maximum token length for context window
            max_history_messages: Maximum number of messages to keep in history
            session_timeout_minutes: Minutes before a session expires
            model: Model name for token counting
        """
        self.max_context_length = max_context_length
        self.max_history_messages = max_history_messages
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # Session storage: session_id -> context data
        self.sessions: Dict[str, Dict] = {}
        
        # System prompt cache
        self.system_prompt: Optional[str] = None
        self.system_prompt_initialized = False
        
        # Initialize token counter
        self.token_counter = get_token_counter(model)
        self.model = model
        
    def initialize_system_prompt(self, system_prompt: str) -> None:
        """
        Initialize the system prompt that will be used for all new sessions.
        This is called once at startup.
        
        Args:
            system_prompt: The Bee system prompt
        """
        self.system_prompt = system_prompt
        self.system_prompt_initialized = True
        logger.info("System prompt initialized")
        
    def create_session(self, session_id: str) -> Dict:
        """
        Create a new conversation session.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            Session context dictionary
        """
        if not self.system_prompt_initialized:
            raise RuntimeError("System prompt must be initialized before creating sessions")
            
        session_context = {
            'session_id': session_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'conversation_history': [],
            'system_prompt_sent': False,
            'message_count': 0
        }
        
        self.sessions[session_id] = session_context
        logger.info(f"Created new session: {session_id}")
        return session_context
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve an existing session or None if it doesn't exist/expired.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session context or None
        """
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        
        # Check if session has expired
        if datetime.now() - session['last_activity'] > self.session_timeout:
            logger.info(f"Session {session_id} has expired")
            del self.sessions[session_id]
            return None
            
        # Update last activity
        session['last_activity'] = datetime.now()
        return session
        
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
        """
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
            
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        session['conversation_history'].append(message)
        session['message_count'] += 1
        
        # Apply sliding window to maintain history limits
        self._apply_sliding_window(session)
        
    def get_context_for_llm(self, session_id: str, user_message: str) -> List[Dict[str, str]]:
        """
        Get the context to send to the LLM for a given user message.
        Includes system prompt only for first message in session.
        
        Args:
            session_id: Session identifier
            user_message: The current user message
            
        Returns:
            List of messages formatted for LLM
        """
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id)
            
        messages = []
        
        # Include system prompt only if it hasn't been sent in this session
        if not session['system_prompt_sent']:
            messages.append({
                'role': 'system',
                'content': self.system_prompt
            })
            session['system_prompt_sent'] = True
        
        # Add conversation history (already filtered by sliding window)
        for msg in session['conversation_history']:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
            
        # Add current user message
        messages.append({
            'role': 'user',
            'content': user_message
        })
        
        # Add to history
        self.add_message(session_id, 'user', user_message)
        
        return messages
        
    def _apply_sliding_window(self, session: Dict) -> None:
        """
        Apply sliding window to maintain conversation within limits.
        Keeps most recent messages up to max_history_messages.
        
        Args:
            session: Session context dictionary
        """
        history = session['conversation_history']
        
        # Trim by message count first
        if len(history) > self.max_history_messages:
            # Keep the most recent messages
            session['conversation_history'] = history[-self.max_history_messages:]
        
        # Now apply token-based trimming
        # Calculate actual tokens for all messages
        messages_for_counting = [
            {"role": msg['role'], "content": msg['content']} 
            for msg in session['conversation_history']
        ]
        
        token_info = self.token_counter.count_messages_tokens(messages_for_counting)
        total_tokens = token_info['total']
        
        # Apply buffer (leave space for response)
        buffer_percent = float(os.getenv('BEE_CONVERSATION_TOKEN_BUFFER_PERCENT', '20'))
        max_allowed_tokens = int(self.max_context_length * (1 - buffer_percent / 100))
        
        if total_tokens > max_allowed_tokens:
            logger.info(f"Session {session['session_id']} exceeds token limit: {total_tokens} > {max_allowed_tokens}")
            
            # Use token counter to fit messages within limit
            fitted_messages = self.token_counter.fit_messages_to_limit(
                messages_for_counting,
                max_allowed_tokens,
                preserve_system=True,
                preserve_recent=10
            )
            
            # Update session history with fitted messages
            session['conversation_history'] = [
                {
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': datetime.now().isoformat()
                }
                for msg in fitted_messages
            ]
            
            # Store information about pruning
            if 'metadata' not in session:
                session['metadata'] = {}
            session['metadata']['last_pruning'] = {
                'timestamp': datetime.now().isoformat(),
                'original_count': len(history),
                'pruned_count': len(session['conversation_history']),
                'original_tokens': total_tokens,
                'pruned_tokens': self.token_counter.count_messages_tokens(fitted_messages)['total']
            }
                
    def update_assistant_response(self, session_id: str, response: str) -> None:
        """
        Add assistant's response to the conversation history.
        
        Args:
            session_id: Session identifier
            response: Assistant's response
        """
        self.add_message(session_id, 'assistant', response)
        
    def get_conversation_summary(self, session_id: str) -> Dict:
        """
        Get a summary of the conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary dictionary
        """
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Session not found or expired'}
            
        return {
            'session_id': session_id,
            'created_at': session['created_at'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'message_count': session['message_count'],
            'history_length': len(session['conversation_history']),
            'system_prompt_sent': session['system_prompt_sent']
        }
        
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was cleared, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
            return True
        return False
        
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            del self.sessions[session_id]
            
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        return len(expired_sessions)
        
    def get_active_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)
        
    def export_session(self, session_id: str) -> Optional[str]:
        """
        Export a session's conversation history as JSON.
        
        Args:
            session_id: Session identifier
            
        Returns:
            JSON string or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
            
        export_data = {
            'session_id': session_id,
            'created_at': session['created_at'].isoformat(),
            'conversation_history': session['conversation_history']
        }
        
        return json.dumps(export_data, indent=2)
    
    def get_session_token_usage(self, session_id: str) -> Optional[Dict]:
        """
        Get detailed token usage information for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Token usage information or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Calculate current token usage
        messages_for_counting = [
            {"role": msg['role'], "content": msg['content']} 
            for msg in session['conversation_history']
        ]
        
        token_info = self.token_counter.count_messages_tokens(messages_for_counting)
        
        # Add context limit information
        buffer_percent = float(os.getenv('BEE_CONVERSATION_TOKEN_BUFFER_PERCENT', '20'))
        max_allowed_tokens = int(self.max_context_length * (1 - buffer_percent / 100))
        
        token_info['context_limit'] = self.max_context_length
        token_info['max_allowed_tokens'] = max_allowed_tokens
        token_info['buffer_tokens'] = self.max_context_length - max_allowed_tokens
        token_info['utilization_percent'] = (token_info['total'] / max_allowed_tokens * 100) if max_allowed_tokens > 0 else 0
        token_info['model'] = self.model
        
        # Add pruning history if available
        if 'metadata' in session and 'last_pruning' in session['metadata']:
            token_info['last_pruning'] = session['metadata']['last_pruning']
        
        return token_info


# Example usage and integration
if __name__ == "__main__":
    # Initialize the context manager
    context_manager = BeeContextManager(
        max_context_length=4096,
        max_history_messages=20,
        session_timeout_minutes=30
    )
    
    # Load system prompt
    with open('../chatbot/prompts/bee_system_prompt.txt', 'r') as f:
        system_prompt = f.read()
    
    context_manager.initialize_system_prompt(system_prompt)
    
    # Example conversation
    session_id = "test_session_123"
    
    # First message - will include system prompt
    messages = context_manager.get_context_for_llm(session_id, "Hello Bee!")
    print(f"First request messages: {len(messages)} messages")
    print(f"Includes system prompt: {any(m['role'] == 'system' for m in messages)}")
    
    # Simulate response
    context_manager.update_assistant_response(session_id, "Hi! I'm Bee. How can I help?")
    
    # Second message - won't include system prompt
    messages = context_manager.get_context_for_llm(session_id, "What can you help me with?")
    print(f"\nSecond request messages: {len(messages)} messages")
    print(f"Includes system prompt: {any(m['role'] == 'system' for m in messages)}")
    
    # Get session summary
    summary = context_manager.get_conversation_summary(session_id)
    print(f"\nSession summary: {summary}")