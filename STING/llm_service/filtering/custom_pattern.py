from typing import Tuple, List, Optional, Dict, Any
import re
import logging
from .base_filter import BaseFilter

class CustomPatternFilter(BaseFilter):
    """
    User-defined custom pattern filter that can be created through the UI
    """
    
    def __init__(self, enabled: bool = True, filter_id: str = None, config: Dict[str, Any] = None):
        super().__init__(enabled, config)
        self.filter_id = filter_id or "custom_filter"
        self.name = config.get("name", self.filter_id)
        self.description = config.get("description", "")
        self.categories = {}
        self.compiled_patterns = {}
        self.total_checks = 0
        self.filtered_count = 0
        self.category_matches = {}
        
        # Initialize patterns from config
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns from config"""
        pattern_categories = self.config.get("patterns", {})
        
        for category, patterns in pattern_categories.items():
            if isinstance(patterns, list) and patterns:
                self.compiled_patterns[category] = []
                for pattern in patterns:
                    try:
                        # Support for regex flags
                        flags = 0
                        if self.config.get("case_insensitive", True):
                            flags |= re.IGNORECASE
                            
                        self.compiled_patterns[category].append(re.compile(pattern, flags))
                        self.category_matches[category] = 0
                    except re.error as e:
                        self.logger.error(f"Invalid regex pattern '{pattern}': {e}")
    
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """Check if text matches any of the custom patterns"""
        if not self.enabled or not self.compiled_patterns:
            return False, None
            
        self.total_checks += 1
        
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    self.category_matches[category] += 1
                    self.filtered_count += 1
                    
                    # Use custom reason message if provided
                    reason_template = self.config.get("reason_templates", {}).get(
                        category, f"Content filtered: {category} detected"
                    )
                    reason = reason_template
                    
                    self.logger.warning(f"Custom filter '{self.name}' matched: {category}")
                    return True, reason
                    
        return False, None
        
    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about this filter's operation"""
        stats = super().get_stats()
        stats.update({
            "filter_id": self.filter_id,
            "name": self.name,
            "description": self.description,
            "total_checks": self.total_checks,
            "filtered_count": self.filtered_count,
            "filter_rate": self.filtered_count / self.total_checks if self.total_checks > 0 else 0,
            "category_matches": self.category_matches,
            "pattern_categories": list(self.compiled_patterns.keys())
        })
        return stats
