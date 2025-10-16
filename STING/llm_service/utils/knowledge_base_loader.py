"""
Knowledge Base Loader for LLM Service
Provides access to STING Assistant knowledge base for consistent AI responses
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_knowledge_base(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the STING knowledge base configuration.
    
    Args:
        config_path: Optional path to knowledge base file
        
    Returns:
        Dictionary containing knowledge base data
    """
    if config_path is None:
        # Try multiple possible locations
        possible_paths = [
            '/app/conf/knowledge_base.yml',  # Docker container path
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'conf', 'knowledge_base.yml'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'conf', 'knowledge_base.yml'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
    
    # Return default knowledge if file not found
    return {
        'system_identity': {
            'name': 'STING-CE',
            'full_name': 'Secure Trusted Intelligence and Networking Guardian Assistant - Community Edition',
            'short_name': 'STING Assistant',
            'purpose': 'A comprehensive secure communication and intelligence platform'
        },
        'core_knowledge': {
            'what_is_sting': 'STING Assistant is an advanced secure communication platform with AI assistance.'
        }
    }


def get_sting_system_prompt(role: str = 'assistant', model_size: str = 'large') -> str:
    """
    Get a system prompt that includes STING knowledge.
    
    Args:
        role: The AI assistant role
        model_size: 'small' for TinyLlama, 'large' for bigger models
        
    Returns:
        System prompt with STING context
    """
    knowledge = load_knowledge_base()
    identity = knowledge.get('system_identity', {})
    
    # Get Bee assistant info
    bee_info = knowledge.get('core_knowledge', {}).get('ai_assistants', {}).get('bee', {})
    preferred_name = bee_info.get('preferred_name', 'B. or Bee for short')
    
    # Simplified prompt for small models
    if model_size == 'small':
        return f"""You are Bee, AI assistant for STING Assistant. I prefer to be called {preferred_name}. 
Be friendly and helpful. Only explain STING details when directly asked about it."""
    
    # Full prompt for larger models
    core = knowledge.get('core_knowledge', {})
    
    prompt = f"""You are Bee, an AI assistant integrated into {identity.get('full_name', 'STING-CE')} ({identity.get('short_name', 'STING Assistant')}). 
I prefer to be called {preferred_name}.

ABOUT STING Assistant:
{core.get('what_is_sting', 'STING Assistant is an advanced secure communication platform.')}

You help users with secure communication, intelligence analysis, and platform navigation. 
Always be helpful, professional, and security-conscious."""
    
    # Add key features if available
    features = core.get('key_features', [])
    if features:
        prompt += "\n\nKEY CAPABILITIES:"
        for feature in features[:5]:  # Limit to avoid token bloat
            prompt += f"\n- {feature}"
    
    return prompt.strip()