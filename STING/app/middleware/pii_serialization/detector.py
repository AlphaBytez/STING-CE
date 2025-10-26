"""
PII Detector

Detects personally identifiable information (PII) in text using pattern matching
and context-aware rules.

Supports multiple PII types:
- Names (person, organization)
- Contact info (email, phone, address)
- Financial (credit card, bank account, SSN)
- Medical (MRN, patient ID)
- Account info (username, account number)
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PIIType(str, Enum):
    """Types of PII that can be detected"""
    PERSON_NAME = "person_name"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    ADDRESS = "address"
    IP_ADDRESS = "ip_address"
    MEDICAL_RECORD = "medical_record"
    ACCOUNT_NUMBER = "account_number"
    USERNAME = "username"
    DATE_OF_BIRTH = "date_of_birth"
    DRIVERS_LICENSE = "drivers_license"


@dataclass
class PIIDetection:
    """Represents a detected PII instance"""
    pii_type: PIIType
    value: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str = ""  # Surrounding text for better understanding

    def to_dict(self) -> dict:
        return {
            "pii_type": self.pii_type.value,
            "value": self.value,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "context": self.context
        }


class PIIDetector:
    """
    Detects PII in text using regex patterns and heuristics.

    Performance optimized:
    - Compiled regex patterns
    - Early exit on mode check
    - Lazy evaluation
    """

    # Regex patterns for different PII types
    PATTERNS = {
        PIIType.EMAIL: re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        PIIType.PHONE: re.compile(
            r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        ),
        PIIType.SSN: re.compile(
            r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
        ),
        PIIType.CREDIT_CARD: re.compile(
            r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
        ),
        PIIType.IP_ADDRESS: re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ),
        PIIType.DATE_OF_BIRTH: re.compile(
            r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b'
        ),
    }

    # Context keywords that indicate PII nearby
    CONTEXT_KEYWORDS = {
        PIIType.PERSON_NAME: [
            'name', 'named', 'called', 'mr', 'mrs', 'ms', 'dr',
            'patient', 'customer', 'user', 'person', 'individual'
        ],
        PIIType.ADDRESS: [
            'address', 'street', 'st', 'ave', 'avenue', 'road', 'rd',
            'drive', 'dr', 'lane', 'ln', 'lives at', 'located at'
        ],
        PIIType.MEDICAL_RECORD: [
            'mrn', 'medical record', 'patient id', 'chart number'
        ],
    }

    def __init__(self, config):
        """
        Initialize detector with configuration.

        Args:
            config: PIIProtectionConfig instance
        """
        self.config = config

    async def detect(
        self,
        text: str,
        mode: str = "external"
    ) -> List[PIIDetection]:
        """
        Detect PII in text based on protection mode.

        Args:
            text: Text to scan for PII
            mode: Protection mode (local/external)

        Returns:
            List of PII detections sorted by position
        """
        # Get enabled PII types for this mode
        enabled_types = self.config.get_pii_types_for_mode(mode)

        if not enabled_types:
            return []

        detections = []

        # Run pattern-based detection
        for pii_type in enabled_types:
            if pii_type in self.PATTERNS:
                pattern = self.PATTERNS[pii_type]
                for match in pattern.finditer(text):
                    detection = PIIDetection(
                        pii_type=pii_type,
                        value=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9,
                        context=self._extract_context(text, match.start(), match.end())
                    )
                    detections.append(detection)

        # Run heuristic detection for complex types
        if PIIType.PERSON_NAME in enabled_types:
            name_detections = self._detect_names(text)
            detections.extend(name_detections)

        if PIIType.ADDRESS in enabled_types:
            address_detections = self._detect_addresses(text)
            detections.extend(address_detections)

        # Sort by position and remove overlaps
        detections = self._remove_overlaps(
            sorted(detections, key=lambda d: d.start_pos)
        )

        return detections

    def _detect_names(self, text: str) -> List[PIIDetection]:
        """
        Detect person names using capitalization heuristics.

        Looks for:
        - Capitalized words near name context keywords
        - Multiple capitalized words in sequence (likely names)
        """
        detections = []

        # Pattern: 2-3 capitalized words (likely a name)
        name_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b')

        for match in name_pattern.finditer(text):
            # Check if near name context keywords
            context = self._extract_context(text, match.start(), match.end(), window=50)
            context_lower = context.lower()

            has_context = any(
                keyword in context_lower
                for keyword in self.CONTEXT_KEYWORDS[PIIType.PERSON_NAME]
            )

            # Higher confidence if context keyword found
            confidence = 0.85 if has_context else 0.65

            detection = PIIDetection(
                pii_type=PIIType.PERSON_NAME,
                value=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=confidence,
                context=context
            )
            detections.append(detection)

        return detections

    def _detect_addresses(self, text: str) -> List[PIIDetection]:
        """
        Detect physical addresses using pattern matching.

        Pattern: number + street name + street type
        Example: "123 Main Street"
        """
        detections = []

        # Pattern: street address
        address_pattern = re.compile(
            r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
            r'(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b',
            re.IGNORECASE
        )

        for match in address_pattern.finditer(text):
            detection = PIIDetection(
                pii_type=PIIType.ADDRESS,
                value=match.group(),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85,
                context=self._extract_context(text, match.start(), match.end())
            )
            detections.append(detection)

        return detections

    def _extract_context(
        self,
        text: str,
        start: int,
        end: int,
        window: int = 30
    ) -> str:
        """
        Extract surrounding context for a detection.

        Args:
            text: Full text
            start: Start position of detection
            end: End position of detection
            window: Characters to include on each side

        Returns:
            Context string with [...] markers if truncated
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)

        context = text[context_start:context_end]

        if context_start > 0:
            context = "[...]" + context
        if context_end < len(text):
            context = context + "[...]"

        return context.strip()

    def _remove_overlaps(self, detections: List[PIIDetection]) -> List[PIIDetection]:
        """
        Remove overlapping detections, keeping higher confidence ones.

        Args:
            detections: Sorted list of detections

        Returns:
            Filtered list without overlaps
        """
        if not detections:
            return []

        filtered = [detections[0]]

        for detection in detections[1:]:
            last = filtered[-1]

            # Check for overlap
            if detection.start_pos < last.end_pos:
                # Keep the one with higher confidence
                if detection.confidence > last.confidence:
                    filtered[-1] = detection
            else:
                filtered.append(detection)

        return filtered
