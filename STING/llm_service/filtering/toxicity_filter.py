"""
Toxicity Filter for LLM Gateway
Detects and filters toxic or harmful content
"""

import os
import re
from typing import Tuple, Optional, List, Dict
import logging

logger = logging.getLogger("toxicity-filter")

class ToxicityFilter:
    """Filter for detecting toxic or harmful content in text"""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.detoxify = None
        self.categories = ['toxicity', 'severe_toxicity', 'obscene', 'threat', 'insult', 'identity_attack']
        
        # Precompile some basic regex patterns for a lightweight first pass
        self.basic_patterns = [
            (re.compile(r'\b(fuck|shit|damn|bitch|asshole|cunt)\b', re.IGNORECASE), 'Basic profanity'),
            (re.compile(r'\b(kill|murder|suicide|die|death)\b', re.IGNORECASE), 'Violence references'),
            (re.compile(r'\b(niger|nigger|fag|faggot|retard|spic|chink)\b', re.IGNORECASE), 'Slurs')
        ]
        
        # Load the detoxify model lazily
        logger.info(f"Toxicity filter initialized with threshold {threshold}")
    
    def _load_model(self):
        """Lazy-load the Detoxify model"""
        try:
            from detoxify import Detoxify
            self.detoxify = Detoxify('original')
            logger.info("Detoxify model loaded successfully")
        except ImportError:
            logger.warning("Detoxify package not installed. Using basic pattern matching only.")
        except Exception as e:
            logger.error(f"Error loading Detoxify model: {str(e)}")
    
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains toxic content
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (should_filter, reason)
        """
        # First do a quick check with regex patterns
        for pattern, reason in self.basic_patterns:
            if pattern.search(text):
                logger.info(f"Basic pattern match: {reason}")
                return True, reason
        
        # If Detoxify is available, use it for a more thorough analysis
        if self.detoxify is None and self._should_use_detoxify():
            self._load_model()
        
        if self.detoxify is not None:
            try:
                results = self.detoxify.predict(text)
                
                # Check each category against the threshold
                for category in self.categories:
                    score = results[category]
                    if score > self.threshold:
                        logger.info(f"Detoxify detected {category}: {score:.4f}")
                        return True, f"{category} ({score:.2f})"
                
            except Exception as e:
                logger.error(f"Error in Detoxify prediction: {str(e)}")
        
        return False, None
    
    def _should_use_detoxify(self) -> bool:
        """Determine if we should use the Detoxify model based on text characteristics"""
        # In a real implementation, this might check text length, complexity, etc.
        return True
