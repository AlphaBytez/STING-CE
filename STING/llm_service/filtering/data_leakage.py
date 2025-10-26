import re
from typing import Tuple, List, Optional, Dict, Any, Pattern
import logging
from .base_filter import BaseFilter

class DataLeakageFilter(BaseFilter):
    """Filter for detecting and preventing potential data leakage"""
    
    def __init__(self, enabled: bool = True, config: Dict[str, Any] = None):
        super().__init__(enabled, config)
        
        # Get patterns from config or use defaults
        user_patterns = self.config.get('sensitive_patterns', [])
        
        # Track statistics
        self.total_checks = 0
        self.filtered_count = 0
        self.pattern_matches = {}
        
        # Initialize patterns
        self._initialize_patterns(user_patterns)
    
    def _initialize_patterns(self, user_patterns: List[str]):
        """Initialize regex patterns for sensitive data detection"""
        # Core patterns for sensitive data
        core_patterns = {
            'api_key': [
                r'(api[_\-\s]?key|apikey)[=:"\'\s]+[a-zA-Z0-9_\-]{16,}',
                r'(access[_\-\s]?key)[=:"\'\s]+[A-Za-z0-9+/=]{16,}',
                r'sk-[a-zA-Z0-9]{30,}',  # OpenAI-style API keys
            ],
            'auth_token': [
                r'(auth[_\-\s]?token|token|refresh[_\-\s]?token)[=:"\'\s]+[a-zA-Z0-9_\-\.]{16,}',
                r'(bearer|Bearer)[=:"\'\s]+[a-zA-Z0-9_\-\.]{16,}',
                r'(jwt|JWT)[=:"\'\s]+[a-zA-Z0-9_\-\.]{30,}',
            ],
            'password': [
                r'(password|passwd|pwd)[=:"\'\s]+\S{8,}',
                r'(db[_\-\s]?password)[=:"\'\s]+\S{8,}',
            ],
            'connection_string': [
                r'(postgres|postgresql|mysql|mongodb|mongo|sql|oracle):(//|@).+:.*@.+',
                r'(connection[_\-\s]?string)[=:"\'\s]+.+:.+@.+',
            ],
            'internal_endpoint': [
                r'(internal|private)[_\-\s]?(api|endpoint|url)[=:"\'\s]+https?://\S+',
                r'(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.16\.)',
            ],
            'pii': [
                r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # SSN
                r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # Credit card
                r'([\w\.-]+)@([\w\.-]+\.\w{2,})',  # Email
            ],
            'code_snippet': [
                r'<\?php\s+.+\?>',
                r'from\s+\w+\s+import',
                r'import\s+[\w\., ]+\s*;?',
                r'const\s+\w+\s*=',
                r'function\s+\w+\s*\(',
                r'class\s+\w+\s*[:{]',
            ],
            'system_info': [
                r'(username|user):\s+"[^"]+"',
                r'hostname:\s+"[^"]+"',
                r'system:\s+"[^"]+"',
                r'password:\s+"[^"]+"',
            ]
        }
        
        # Add custom patterns from configuration
        if user_patterns:
            core_patterns['custom'] = [rf'{p}' for p in user_patterns]
        
        # Compile all patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in core_patterns.items():
            self.compiled_patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
            self.pattern_matches[category] = 0
    
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains potential data leakage
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (has_leakage, reason)
        """
        if not self.enabled:
            return False, None
        
        self.total_checks += 1
        
        # Check each category of patterns
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Don't log the actual matches for security reasons
                    self.pattern_matches[category] += 1
                    self.filtered_count += 1
                    reason = f"Potential data leakage detected: {category}"
                    self.logger.warning(f"{reason} (pattern matched)")
                    return True, reason
        
        return False, None
    
    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about this filter's operation"""
        stats = super().get_stats()
        stats.update({
            "total_checks": self.total_checks,
            "filtered_count": self.filtered_count,
            "filter_rate": self.filtered_count / self.total_checks if self.total_checks > 0 else 0,
            "pattern_matches": self.pattern_matches,
        })
        return stats
