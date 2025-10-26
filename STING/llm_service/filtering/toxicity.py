import re
from typing import Tuple, List, Optional
import logging

# In production, you would use a proper toxicity detection model like Detoxify
# For this example, we'll use a simple keyword-based approach
class ToxicityFilter:
    def __init__(self, enabled: bool = True, threshold: float = 0.7):
        self.enabled = enabled
        self.threshold = threshold
        self.logger = logging.getLogger("toxicity-filter")
        
        # Simple list of toxic keywords for demonstration
        self.toxic_patterns = [
            r'\b(hate|idiot|stupid|dumb|moron)\b',
            r'\b(kill|hurt|harm|attack)\b',
            r'\b(racist|sexist|bigot)\b',
            r'\b(explicit content|porn|nsfw)\b'
        ]
        
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains toxic content
        Returns: (is_toxic, reason)
        """
        if not self.enabled:
            return False, None
            
        # In a real implementation, this would call a proper toxicity detection model
        for pattern in self.toxic_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                reason = f"Potentially harmful content detected: {', '.join(matches)}"
                self.logger.warning(reason)
                return True, reason
                
        return False, None
