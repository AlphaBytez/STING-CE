"""
Task Router for Dynamic Model Selection
Analyzes incoming requests to determine the appropriate model based on task type
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
import yaml

logger = logging.getLogger(__name__)


class TaskRouter:
    """Routes requests to appropriate models based on task analysis"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.task_routing = self.config.get('llm_service', {}).get('task_routing', {})
        self.enabled = self.task_routing.get('enabled', False)
        self.task_models = self.task_routing.get('task_models', {})
        self.task_detection = self.task_routing.get('task_detection', {})
        
        # Compile regex patterns for efficiency
        self._compiled_patterns = {}
        for task_type, detection in self.task_detection.items():
            patterns = detection.get('patterns', [])
            self._compiled_patterns[task_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        logger.info(f"Task routing {'enabled' if self.enabled else 'disabled'}")
        if self.enabled:
            logger.info(f"Task types configured: {list(self.task_models.keys())}")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from file"""
        if config_path is None:
            possible_paths = [
                '/app/conf/config.yml',
                '/Users/captain-wolf/Documents/GitHub/STING-CE/STING/conf/config.yml',
            ]
            
            for path in possible_paths:
                try:
                    with open(path, 'r') as f:
                        return yaml.safe_load(f)
                except:
                    continue
        
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return {'llm_service': {'task_routing': {'enabled': False}}}
    
    def detect_task_type(self, message: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Detect the task type from message content
        
        Args:
            message: The user's message
            conversation_history: Optional conversation history for context
            
        Returns:
            Task type string (e.g., 'chat', 'agent', 'analysis', 'coding', 'summarization')
        """
        if not self.enabled:
            return 'chat'
        
        message_lower = message.lower()
        
        # Check each task type's detection rules
        scores = {}
        for task_type, detection in self.task_detection.items():
            score = 0
            
            # Check keywords
            keywords = detection.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    score += 1
            
            # Check patterns
            patterns = self._compiled_patterns.get(task_type, [])
            for pattern in patterns:
                if pattern.search(message):
                    score += 2  # Patterns are weighted higher
            
            scores[task_type] = score
        
        # Find the highest scoring task type
        if scores:
            best_task = max(scores.items(), key=lambda x: x[1])
            if best_task[1] > 0:  # Only return if we found matches
                logger.info(f"Detected task type: {best_task[0]} (score: {best_task[1]})")
                return best_task[0]
        
        # Default to chat if no specific task detected
        return 'chat'
    
    def get_model_for_task(self, task_type: str, available_models: List[str]) -> Tuple[str, str]:
        """
        Get the appropriate model for a given task type
        
        Args:
            task_type: The detected task type
            available_models: List of currently available model names
            
        Returns:
            Tuple of (selected_model, reason)
        """
        if not self.enabled:
            return available_models[0] if available_models else 'tinyllama', "Task routing disabled"
        
        task_config = self.task_models.get(task_type, self.task_models.get('chat', {}))
        primary_model = task_config.get('primary', 'tinyllama')
        fallback_model = task_config.get('fallback', 'phi2')
        
        # Check if primary model is available
        if primary_model in available_models:
            return primary_model, f"Primary model for {task_type} tasks"
        
        # Check if fallback model is available
        if fallback_model in available_models:
            return fallback_model, f"Fallback model for {task_type} tasks"
        
        # Return first available model
        if available_models:
            return available_models[0], f"Default available model (no {task_type} model available)"
        
        # Last resort
        return 'tinyllama', f"Default model (no models available for {task_type})"
    
    def route_request(self, message: str, conversation_history: Optional[List[Dict]] = None,
                     requested_model: Optional[str] = None, available_models: Optional[List[str]] = None) -> Dict:
        """
        Route a request to the appropriate model
        
        Args:
            message: The user's message
            conversation_history: Optional conversation history
            requested_model: Model explicitly requested by user (overrides routing)
            available_models: List of currently available models
            
        Returns:
            Dict with routing decision including model, task_type, and reason
        """
        # If model explicitly requested, use it
        if requested_model:
            return {
                'model': requested_model,
                'task_type': 'explicit',
                'reason': 'Model explicitly requested'
            }
        
        # Detect task type
        task_type = self.detect_task_type(message, conversation_history)
        
        # Get available models list
        if available_models is None:
            # Default available models
            available_models = ['tinyllama', 'phi2', 'deepseek-1.5b', 'llama3']
        
        # Select model for task
        selected_model, reason = self.get_model_for_task(task_type, available_models)
        
        return {
            'model': selected_model,
            'task_type': task_type,
            'reason': reason
        }


# Global router instance
_task_router: Optional[TaskRouter] = None


def get_task_router() -> TaskRouter:
    """Get or create the global task router instance"""
    global _task_router
    if _task_router is None:
        _task_router = TaskRouter()
    return _task_router