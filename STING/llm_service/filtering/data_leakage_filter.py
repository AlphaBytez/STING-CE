"""
Data Leakage Filter for LLM Gateway
Prevents sensitive information from being included in responses
"""

import re
from typing import List, Tuple, Optional, Dict, Any
import logging
import os

logger = logging.getLogger("data-leakage-filter")

class DataLeakageFilter:
    """Filter for preventing data leakage in LLM responses"""
    
    def __init__(self, patterns: Optional[List[str]] = None):
        # Default sensitive patterns if none provided
        self.patterns = patterns or [
            # API keys and tokens
            r'(api[_-]?key|apikey|token|secret|password)["\s:=]+[A-Za-z0-9_\-]{10,}',
            # AWS keys
            r'(AKIA|ASIA)[A-Z0-9]{16}',
            # Credit card numbers
            r'\b(?:\d{4}[- ]?){3}\d{4}\b',
            # Social security numbers
            r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # IP addresses
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            # Internal URLs or paths
            r'https?://(?:localhost|internal|intranet|private)',
            # Database connection strings
            r'(mongodb|mysql|postgresql|redis)://[^\s]+',
            # Authorization headers
            r'Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]+',
            # Private keys
            r'-----BEGIN\s+PRIVATE\s+KEY-----'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [(re.compile(pattern, re.IGNORECASE), pattern) for pattern in self.patterns]
        
        # Load custom patterns from environment if available
        self._load_custom_patterns()
        
        logger.info(f"Data leakage filter initialized with {len(self.compiled_patterns)} patterns")
    
    def _load_custom_patterns(self):
        """Load custom patterns from environment variable or file"""
        # Check for patterns in environment variable
        env_patterns = os.environ.get("DATA_LEAKAGE_PATTERNS")
        if env_patterns:
            try:
                patterns = env_patterns.split(",")
                for pattern in patterns:
                    pattern = pattern.strip()
                    if pattern:
                        self.compiled_patterns.append((re.compile(pattern, re.IGNORECASE), pattern))
                logger.info(f"Loaded {len(patterns)} patterns from environment")
            except Exception as e:
                logger.error(f"Error loading patterns from environment: {str(e)}")
        
        # Check for patterns file
        patterns_file = os.environ.get("DATA_LEAKAGE_PATTERNS_FILE")
        if patterns_file and os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    for line in f:
                        pattern = line.strip()
                        if pattern and not pattern.startswith('#'):
                            self.compiled_patterns.append((re.compile(pattern, re.IGNORECASE), pattern))
                logger.info(f"Loaded patterns from file: {patterns_file}")
            except Exception as e:
                logger.error(f"Error loading patterns from file: {str(e)}")
    
    def check(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if text contains patterns indicating potential data leakage
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (should_filter, reason)
        """
        for compiled_pattern, pattern_desc in self.compiled_patterns:
            if compiled_pattern.search(text):
                logger.info(f"Data leakage pattern matched: {pattern_desc}")
                return True, "Potential sensitive information detected"
        
        return False, None
