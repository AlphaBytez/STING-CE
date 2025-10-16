"""
PII Deserializer

Converts serialized PII tokens back to original values in AI responses.

Features:
- Fast token replacement
- Partial replacement support (missing cache entries)
- Preserves response formatting
"""

import re
from typing import Dict


class PIIDeserializer:
    """
    Deserializes PII tokens in AI responses back to original values.

    Simple and fast - just replaces tokens with cached values.
    """

    def __init__(self, config):
        """
        Initialize deserializer with configuration.

        Args:
            config: PIIProtectionConfig instance
        """
        self.config = config

    async def deserialize(
        self,
        text: str,
        pii_map: Dict[str, str]
    ) -> str:
        """
        Replace PII tokens in text with original values.

        Args:
            text: Text containing PII tokens
            pii_map: Mapping of tokens to original values

        Returns:
            Text with tokens replaced

        Example:
            Input: "Contact $Person1_name_hash at $Person1_email_hash"
            Map: {
                "$Person1_name_hash": "John Smith",
                "$Person1_email_hash": "john@email.com"
            }
            Output: "Contact John Smith at john@email.com"
        """
        if not pii_map:
            return text

        # Replace each token with its original value
        deserialized_text = text
        for token, original_value in pii_map.items():
            deserialized_text = deserialized_text.replace(token, original_value)

        return deserialized_text

    def find_tokens(self, text: str) -> list[str]:
        """
        Find all PII tokens in text.

        Args:
            text: Text to search

        Returns:
            List of token strings found
        """
        # Pattern: ${word}{number}_{word}_{hash}
        token_pattern = re.compile(r'\$[A-Z][a-z]+\d+_[a-z]+_[a-f0-9]{4}')
        return token_pattern.findall(text)
