#!/usr/bin/env python3
"""
Simple PII Detector for Knowledge Service
Self-contained PII detection without Flask app dependencies
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PIIMatch:
    """Represents a detected PII instance"""
    pii_type: str
    value: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str

class SimplePIIDetector:
    """Lightweight PII detector for healthcare and general data"""

    def __init__(self):
        # Healthcare PII patterns
        self.patterns = {
            'ssn': {
                'regex': r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b',
                'confidence': 0.9,
                'description': 'Social Security Number'
            },
            'email': {
                'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'confidence': 0.95,
                'description': 'Email Address'
            },
            'phone': {
                'regex': r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
                'confidence': 0.85,
                'description': 'Phone Number'
            },
            'name': {
                'regex': r'\b(?:Patient|Name|Mr\.|Mrs\.|Dr\.)\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
                'confidence': 0.7,
                'description': 'Person Name'
            },
            'dob': {
                'regex': r'\b(?:DOB|Date of Birth)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                'confidence': 0.9,
                'description': 'Date of Birth'
            },
            'medical_record': {
                'regex': r'\b(?:MRN|Medical Record)\s*:?\s*([A-Z0-9]{6,12})',
                'confidence': 0.8,
                'description': 'Medical Record Number'
            },
            'npi': {
                'regex': r'\bNPI\s*:?\s*(\d{10})\b',
                'confidence': 0.95,
                'description': 'National Provider Identifier'
            },
            'dea': {
                'regex': r'\bDEA\s*:?\s*([A-Z]{2}\d{7})\b',
                'confidence': 0.95,
                'description': 'DEA Number'
            },
            'diagnosis': {
                'regex': r'\b(?:ICD-10|Diagnosis)\s*:?\s*([A-Z]\d{2}\.?\d*)',
                'confidence': 0.8,
                'description': 'ICD-10 Diagnosis Code'
            }
        }

    def detect_pii(self, text: str, mode: str = "healthcare") -> Dict[str, Any]:
        """
        Detect PII in text content

        Args:
            text: Text content to analyze
            mode: Detection mode (healthcare, general, financial)

        Returns:
            Dictionary with detection results
        """
        try:
            matches = []
            pii_count = 0

            for pii_type, pattern_info in self.patterns.items():
                pattern = pattern_info['regex']
                confidence = pattern_info['confidence']
                description = pattern_info['description']

                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Extract context around the match
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].replace('\n', ' ').strip()

                    pii_match = PIIMatch(
                        pii_type=pii_type,
                        value=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        context=context
                    )
                    matches.append(pii_match)
                    pii_count += 1

            # Generate recommendations based on findings
            recommendations = self._generate_recommendations(matches, mode)

            return {
                "pii_detected": pii_count > 0,
                "detection_count": pii_count,
                "matches": [
                    {
                        "type": m.pii_type,
                        "description": self.patterns[m.pii_type]['description'],
                        "confidence": m.confidence,
                        "context": m.context[:50] + "..." if len(m.context) > 50 else m.context
                    }
                    for m in matches
                ],
                "recommendations": recommendations,
                "message": f"Detected {pii_count} PII instances using {mode} mode"
            }

        except Exception as e:
            logger.error(f"Error during PII detection: {e}")
            return {
                "pii_detected": False,
                "detection_count": 0,
                "matches": [],
                "recommendations": [],
                "message": f"PII detection failed: {str(e)}"
            }

    def _generate_recommendations(self, matches: List[PIIMatch], mode: str) -> List[str]:
        """Generate compliance recommendations based on detected PII"""
        recommendations = []

        pii_types = set(match.pii_type for match in matches)

        if 'ssn' in pii_types:
            recommendations.append("SSN detected: Consider encryption and access controls")

        if 'medical_record' in pii_types or 'npi' in pii_types:
            recommendations.append("Healthcare data detected: HIPAA compliance required")

        if 'email' in pii_types or 'name' in pii_types:
            recommendations.append("Personal identifiers detected: GDPR considerations apply")

        if len(matches) > 5:
            recommendations.append("High PII density: Consider data minimization strategies")

        if mode == "healthcare":
            recommendations.append("Healthcare mode: Enable BAA agreements for vendors")

        return recommendations

# Global instance
simple_pii_detector = SimplePIIDetector()