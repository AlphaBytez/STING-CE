"""
Template for creating custom filters for the LLM Gateway

To create a custom filter:
1. Copy this template to the 'custom' directory
2. Rename it to something meaningful (e.g., brand_filter.py)
3. Implement the check() method
4. The filter will be automatically loaded at startup
"""

from typing import Tuple, Optional, Dict, Any
import re
import logging

# This function marks this class as a filter
def filter_decorator(cls):
    cls.is_filter = True
    return cls

@filter_decorator
class CustomFilterTemplate:
    """Template for a custom filter"""
    
    # A unique name for this filter (used in logs and API)
    filter_name = "custom_filter"
    
    def __init__(self):
        """Initialize the filter with any necessary resources"""
        self.logger = logging.getLogger(f"filter-{self.filter_name}")
        self.logger.info(f"Initializing {self.filter_name}")
        
        # Add your initialization code here
        # For example, compile regex patterns, load lists of terms, etc.
    
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text should be filtered
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (should_filter, reason)
        """
        # Implement your filtering logic here
        # Return True and a reason if the text should be filtered
        # Return False and None if the text is okay
        
        # Example:
        # if "forbidden term" in text.lower():
        #     return True, "Contains forbidden term"
        
        return False, None
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """Update the filter configuration"""
        # Implement if your filter supports runtime configuration updates
        pass
