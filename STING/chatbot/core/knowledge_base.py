"""
STING Assistant Knowledge Base Manager

This module provides a centralized knowledge base for all AI models in STING,
ensuring consistent understanding of the platform's identity and capabilities.
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Manages the STING Assistant knowledge base for AI models."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the knowledge base.
        
        Args:
            config_path: Path to the knowledge base YAML file
        """
        if config_path is None:
            # Default to the standard knowledge base location
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'conf', 'knowledge_base.yml'
            )
        
        self.config_path = config_path
        self.knowledge = self._load_knowledge()
        
    def _load_knowledge(self) -> Dict[str, Any]:
        """Load knowledge from the YAML configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Knowledge base file not found at {self.config_path}")
            return self._get_default_knowledge()
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return self._get_default_knowledge()
    
    def _get_default_knowledge(self) -> Dict[str, Any]:
        """Return default knowledge if config file is not available."""
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
    
    def get_system_prompt(self, role: str = 'bee') -> str:
        """
        Generate a system prompt that includes STING knowledge.
        
        Args:
            role: The AI assistant role (default: 'bee')
            
        Returns:
            A comprehensive system prompt with STING knowledge
        """
        identity = self.knowledge.get('system_identity', {})
        core = self.knowledge.get('core_knowledge', {})
        ai_assistants = core.get('ai_assistants', {})
        ai_config = ai_assistants.get(role, {})
        
        # Check if simple prompt is requested
        if ai_config.get('simple_prompt', False):
            return f"You are {role.capitalize()}, a helpful AI assistant. Answer questions directly and be helpful."
        
        prompt = f"""You are {role.capitalize()}, an AI assistant integrated into {identity.get('full_name', 'STING-CE')} ({identity.get('short_name', 'STING Assistant')}).

ABOUT STING Assistant:
{core.get('what_is_sting', '')}

YOUR ROLE:
You are a helpful, friendly, and knowledgeable AI assistant within the STING Assistant platform. You help users with:
- Understanding and using STING Assistant's features
- Secure communication and messaging
- Platform navigation and functionality
- Intelligent analysis and assistance

KEY CAPABILITIES OF STING Assistant:
"""
        
        # Add key features
        features = core.get('key_features', [])
        for feature in features:
            prompt += f"- {feature}\n"
        
        # Add response guidelines
        guidelines = self.knowledge.get('response_guidelines', [])
        if guidelines:
            prompt += "\nRESPONSE GUIDELINES:\n"
            for guideline in guidelines:
                prompt += f"- {guideline}\n"
        
        return prompt.strip()
    
    def get_context_for_query(self, query: str) -> str:
        """
        Get relevant knowledge context based on a user query.
        
        Args:
            query: The user's question or message
            
        Returns:
            Relevant context from the knowledge base
        """
        query_lower = query.lower()
        context_parts = []
        
        # Check for common questions
        common_questions = self.knowledge.get('common_questions', {})
        for question_key, answer in common_questions.items():
            keywords = question_key.replace('_', ' ').split()
            if any(keyword in query_lower for keyword in keywords):
                context_parts.append(answer)
        
        # Check for specific topics
        if any(word in query_lower for word in ['who', 'what', 'sting', 'bot', 'purpose']):
            identity = self.knowledge.get('system_identity', {})
            context_parts.append(
                f"I am part of {identity.get('full_name', 'STING Assistant')}, "
                f"also known as {identity.get('short_name', 'STING Assistant')}."
            )
        
        if any(word in query_lower for word in ['feature', 'capability', 'can', 'do']):
            features = self.knowledge.get('core_knowledge', {}).get('key_features', [])
            if features:
                context_parts.append("STING Assistant features include: " + ", ".join(features[:3]))
        
        return "\n\n".join(context_parts)
    
    def get_full_knowledge(self) -> Dict[str, Any]:
        """Return the complete knowledge base."""
        return self.knowledge
    
    def reload(self):
        """Reload the knowledge base from the configuration file."""
        self.knowledge = self._load_knowledge()
        logger.info("Knowledge base reloaded")


# Singleton instance for easy access
_knowledge_base_instance = None


def get_knowledge_base() -> KnowledgeBase:
    """Get the singleton KnowledgeBase instance."""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance