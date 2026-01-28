"""
PII Serializer

Converts detected PII into semantic tokens that preserve meaning and relationships
while protecting sensitive data.

Token Format: ${EntityType}{Instance}_{PIIType}_hash

Examples:
- "John Smith" -> "$Person1_first_name_hash $Person1_last_name_hash"
- "john@email.com" -> "$Person1_email_hash"
- "123 Main St" -> "$Location1_address_hash"

Features:
- Entity relationship preservation (same person = same prefix)
- Collision-resistant hashing
- Human-readable semantic structure
- LLM-friendly format
"""

import hashlib
from typing import List, Dict, Tuple
from collections import defaultdict
from .detector import PIIDetection, PIIType


class PIISerializer:
    """
    Serializes PII detections into semantic tokens with relationship preservation.

    The serializer maintains entity relationships across a message:
    - Multiple PII items from the same entity get the same entity ID
    - Hash suffix prevents collisions
    - Format is both machine and human readable
    """

    def __init__(self, config):
        """
        Initialize serializer with configuration.

        Args:
            config: PIIProtectionConfig instance
        """
        self.config = config
        self.entity_counters = defaultdict(int)  # Track entity instances

    async def serialize(
        self,
        text: str,
        detections: List[PIIDetection]
    ) -> Tuple[str, Dict[str, str]]:
        """
        Serialize PII in text to tokens.

        Args:
            text: Original text
            detections: List of PII detections (must be sorted by position)

        Returns:
            Tuple of (serialized_text, pii_mapping)
            - serialized_text: Text with PII replaced by tokens
            - pii_mapping: Dict mapping tokens to original values

        Example:
            Input: "Contact John Smith at john@email.com"
            Output: (
                "Contact $Person1_first_name_hash at $Person1_email_hash",
                {
                    "$Person1_first_name_hash": "John Smith",
                    "$Person1_email_hash": "john@email.com"
                }
            )
        """
        if not detections:
            return text, {}

        # Group detections by entity (to preserve relationships)
        entity_groups = self._group_by_entity(detections)

        # Generate tokens for each detection
        token_map = {}
        tokens_by_position = []  # List of (start, end, token)

        for entity_id, group_detections in entity_groups.items():
            for detection in group_detections:
                token = self._generate_token(
                    detection=detection,
                    entity_id=entity_id
                )
                token_map[token] = detection.value
                tokens_by_position.append((
                    detection.start_pos,
                    detection.end_pos,
                    token
                ))

        # Sort by position (reverse order for replacement)
        tokens_by_position.sort(reverse=True)

        # Replace PII with tokens (from end to start to preserve positions)
        serialized_text = text
        for start, end, token in tokens_by_position:
            serialized_text = (
                serialized_text[:start] +
                token +
                serialized_text[end:]
            )

        return serialized_text, token_map

    def _group_by_entity(
        self,
        detections: List[PIIDetection]
    ) -> Dict[str, List[PIIDetection]]:
        """
        Group detections by logical entity.

        Strategy:
        - Proximate detections (within 50 chars) are likely same entity
        - Same PII type instances are tracked separately
        - Names followed by email/phone are grouped together

        Args:
            detections: List of PII detections

        Returns:
            Dict mapping entity_id to list of detections
        """
        entity_groups = {}
        current_entity_id = None
        last_position = -1
        proximity_threshold = 50  # Characters

        for detection in detections:
            # Check if this detection is close to the last one
            is_proximate = (
                current_entity_id is not None and
                detection.start_pos - last_position < proximity_threshold
            )

            # Decide if this starts a new entity
            if not is_proximate or current_entity_id is None:
                # Create new entity
                entity_type = self._get_entity_type(detection.pii_type)
                self.entity_counters[entity_type] += 1
                current_entity_id = f"{entity_type}{self.entity_counters[entity_type]}"
                entity_groups[current_entity_id] = []

            # Add detection to current entity
            entity_groups[current_entity_id].append(detection)
            last_position = detection.end_pos

        return entity_groups

    def _get_entity_type(self, pii_type: PIIType) -> str:
        """
        Map PII type to entity type prefix.

        Args:
            pii_type: Type of PII

        Returns:
            Entity type prefix (e.g., "Person", "Location")
        """
        entity_type_map = {
            PIIType.PERSON_NAME: "Person",
            PIIType.EMAIL: "Person",
            PIIType.PHONE: "Person",
            PIIType.SSN: "Person",
            PIIType.CREDIT_CARD: "Account",
            PIIType.BANK_ACCOUNT: "Account",
            PIIType.ADDRESS: "Location",
            PIIType.IP_ADDRESS: "Network",
            PIIType.MEDICAL_RECORD: "Medical",
            PIIType.ACCOUNT_NUMBER: "Account",
            PIIType.USERNAME: "User",
            PIIType.DATE_OF_BIRTH: "Person",
            PIIType.DRIVERS_LICENSE: "Person",
        }
        return entity_type_map.get(pii_type, "Entity")

    def _generate_token(
        self,
        detection: PIIDetection,
        entity_id: str
    ) -> str:
        """
        Generate a semantic token for a PII detection.

        Format: ${EntityType}{Instance}_{PIIType}_hash

        Args:
            detection: PII detection
            entity_id: Entity identifier (e.g., "Person1")

        Returns:
            Token string

        Example:
            Input: (email detection, "Person1")
            Output: "$Person1_email_a3f5"
        """
        # Get PII type label
        pii_type_label = self._get_pii_type_label(detection.pii_type)

        # Generate short hash for collision prevention
        hash_suffix = self._generate_hash(detection.value)[:4]

        # Construct token
        token = f"${entity_id}_{pii_type_label}_{hash_suffix}"

        return token

    def _get_pii_type_label(self, pii_type: PIIType) -> str:
        """
        Get human-readable label for PII type.

        Args:
            pii_type: PII type enum

        Returns:
            Label string
        """
        label_map = {
            PIIType.PERSON_NAME: "name",
            PIIType.EMAIL: "email",
            PIIType.PHONE: "phone",
            PIIType.SSN: "ssn",
            PIIType.CREDIT_CARD: "card",
            PIIType.BANK_ACCOUNT: "account",
            PIIType.ADDRESS: "address",
            PIIType.IP_ADDRESS: "ip",
            PIIType.MEDICAL_RECORD: "mrn",
            PIIType.ACCOUNT_NUMBER: "acct",
            PIIType.USERNAME: "username",
            PIIType.DATE_OF_BIRTH: "dob",
            PIIType.DRIVERS_LICENSE: "dl",
        }
        return label_map.get(pii_type, "unknown")

    def _generate_hash(self, value: str) -> str:
        """
        Generate a short hash of a value for collision prevention.

        Args:
            value: Value to hash

        Returns:
            Hexadecimal hash string (first 8 chars of SHA256)
        """
        return hashlib.sha256(value.encode()).hexdigest()[:8]

    def reset_counters(self):
        """Reset entity counters (e.g., for new conversation)."""
        self.entity_counters.clear()
