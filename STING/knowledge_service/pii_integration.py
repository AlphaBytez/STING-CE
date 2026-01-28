#!/usr/bin/env python3
"""
PII Integration Service for Knowledge Service
Integrates PII detection with honey jar document processing
"""

import sys
import os
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add app directory to path to import PII components
sys.path.append('/app')

try:
    # Try to import main PII system first
    from app.services.hive_scrambler import HiveScrambler, PIIDetectionMode
    from app.services.pii_audit_service import pii_audit_service
    from app.models.pii_audit_models import PIIDetectionRecord
    PII_AVAILABLE = True
    PII_MODE = "full"
except ImportError as e:
    logging.warning(f"Main PII system not available: {e}")
    try:
        # Fallback to simple PII detector
        from simple_pii_detector import simple_pii_detector
        PII_AVAILABLE = True
        PII_MODE = "simple"
        logging.info("✅ Using simple PII detector as fallback")
    except ImportError as e2:
        logging.warning(f"Simple PII detector not available: {e2}")
        PII_AVAILABLE = False
        PII_MODE = "none"

logger = logging.getLogger(__name__)

class PIIIntegrationService:
    """
    Service to integrate PII detection with honey jar document processing
    """
    
    def __init__(self):
        self.pii_available = PII_AVAILABLE
        self.pii_mode = PII_MODE

        if self.pii_available and PII_MODE == "full":
            # Initialize full PII scrambler with different modes
            self.scramblers = {
                'general': HiveScrambler(PIIDetectionMode.GENERAL),
                'medical': HiveScrambler(PIIDetectionMode.MEDICAL),
                'legal': HiveScrambler(PIIDetectionMode.LEGAL),
                'financial': HiveScrambler(PIIDetectionMode.FINANCIAL)
            }

            # Enable audit logging
            for scrambler in self.scramblers.values():
                scrambler.enable_audit = True
                scrambler.audit_service = pii_audit_service

            logger.info("✅ PII Integration Service initialized with full audit logging")
        elif self.pii_available and PII_MODE == "simple":
            # Use simple detector
            self.simple_detector = simple_pii_detector
            logger.info("✅ PII Integration Service initialized with simple detector")
        else:
            self.scramblers = {}
            logger.warning("⚠️ PII Integration Service initialized in disabled mode")
    
    def is_available(self) -> bool:
        """Check if PII detection is available"""
        return self.pii_available
    
    async def detect_pii_in_document(self, 
                                   document_text: str,
                                   user_id: str,
                                   document_id: str,
                                   honey_jar_id: str,
                                   honey_jar_type: str = "public",
                                   detection_mode: str = "auto") -> Dict[str, Any]:
        """
        Detect PII in document text and log results
        
        Args:
            document_text: The text content to analyze
            user_id: ID of user who uploaded the document
            document_id: ID of the document
            honey_jar_id: ID of the honey jar
            honey_jar_type: Type of honey jar (public, private, etc.)
            detection_mode: PII detection mode (auto, general, medical, legal, financial)
            
        Returns:
            Dict containing detection results and recommendations
        """
        if not self.pii_available:
            return {
                "pii_detected": False,
                "detection_count": 0,
                "message": "PII detection not available",
                "recommendations": []
            }
        
        try:
            if self.pii_mode == "simple":
                # Use simple PII detector
                logger.info(f"🔍 Running simple PII detection on document {document_id}")
                pii_results = self.simple_detector.detect_pii(
                    text=document_text,
                    mode=detection_mode if detection_mode != "auto" else "healthcare"
                )
                return pii_results

            else:
                # Use full scrambler system
                # Auto-detect mode if specified
                if detection_mode == "auto":
                    detection_mode = self._auto_detect_mode(document_text)

                # Use appropriate scrambler
                scrambler = self.scramblers.get(detection_mode, self.scramblers['general'])

                # Detect PII with audit logging
                detections = scrambler.detect_pii_with_audit(
                    text=document_text,
                    user_id=user_id,
                    document_id=document_id,
                    honey_jar_id=honey_jar_id
                )
            
            # Analyze results
            high_risk_count = sum(1 for d in detections if d.risk_level == "high")
            medium_risk_count = sum(1 for d in detections if d.risk_level == "medium")
            low_risk_count = sum(1 for d in detections if d.risk_level == "low")
            
            # Generate recommendations based on findings
            recommendations = self._generate_recommendations(
                detections, honey_jar_type, detection_mode
            )
            
            # Create summary
            result = {
                "pii_detected": len(detections) > 0,
                "detection_count": len(detections),
                "detection_mode": detection_mode,
                "risk_summary": {
                    "high": high_risk_count,
                    "medium": medium_risk_count,
                    "low": low_risk_count
                },
                "pii_types": list(set(d.pii_type.value for d in detections)),
                "compliance_frameworks": list(set(
                    fw.value for d in detections 
                    for fw in (d.compliance_frameworks or [])
                )),
                "recommendations": recommendations,
                "audit_logged": True
            }
            
            # Log summary
            if detections:
                logger.info(f"PII detected in document {document_id}: "
                          f"{len(detections)} detections, "
                          f"{high_risk_count} high risk, "
                          f"mode: {detection_mode}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting PII in document {document_id}: {e}")
            return {
                "pii_detected": False,
                "detection_count": 0,
                "error": str(e),
                "recommendations": []
            }
    
    async def get_pii_summary_for_honey_jar(self, 
                                          honey_jar_id: str,
                                          user_id: str) -> Dict[str, Any]:
        """
        Get PII detection summary for a honey jar
        """
        if not self.pii_available:
            return {"error": "PII detection not available"}
        
        try:
            # This would query the PII audit database for summary statistics
            # For now, return a placeholder
            return {
                "honey_jar_id": honey_jar_id,
                "total_documents_scanned": 0,
                "total_pii_detections": 0,
                "high_risk_detections": 0,
                "most_common_pii_types": [],
                "compliance_frameworks": [],
                "last_scan_date": None
            }
            
        except Exception as e:
            logger.error(f"Error getting PII summary for honey jar {honey_jar_id}: {e}")
            return {"error": str(e)}
    
    def _auto_detect_mode(self, text: str) -> str:
        """
        Automatically detect the appropriate PII detection mode based on document content
        """
        text_lower = text.lower()
        
        # Medical indicators
        medical_indicators = [
            'patient', 'medical', 'hospital', 'diagnosis', 'treatment',
            'prescription', 'medication', 'doctor', 'physician', 'clinic',
            'health', 'hipaa', 'phi', 'medical record', 'lab result'
        ]
        
        # Legal indicators  
        legal_indicators = [
            'attorney', 'lawyer', 'client', 'case', 'court', 'legal',
            'contract', 'agreement', 'settlement', 'litigation', 'counsel',
            'law firm', 'bar number', 'docket', 'privilege'
        ]
        
        # Financial indicators
        financial_indicators = [
            'bank', 'account', 'credit', 'financial', 'payment', 'transaction',
            'routing', 'ssn', 'social security', 'tax', 'pci', 'card number'
        ]
        
        # Count indicators
        medical_score = sum(1 for indicator in medical_indicators if indicator in text_lower)
        legal_score = sum(1 for indicator in legal_indicators if indicator in text_lower)  
        financial_score = sum(1 for indicator in financial_indicators if indicator in text_lower)
        
        # Determine mode based on highest score
        if medical_score >= 2:
            return 'medical'
        elif legal_score >= 2:
            return 'legal'
        elif financial_score >= 2:
            return 'financial'
        else:
            return 'general'
    
    def _generate_recommendations(self, 
                                detections: List,
                                honey_jar_type: str,
                                detection_mode: str) -> List[str]:
        """
        Generate recommendations based on PII detection results
        """
        recommendations = []
        
        if not detections:
            recommendations.append("✅ No PII detected - document is safe for current access level")
            return recommendations
        
        # High-risk PII recommendations
        high_risk_detections = [d for d in detections if d.risk_level == "high"]
        if high_risk_detections:
            recommendations.append(
                f"🚨 {len(high_risk_detections)} high-risk PII types detected. "
                "Consider restricting access to authorized personnel only."
            )
            
            if honey_jar_type == "public":
                recommendations.append(
                    "⚠️ High-risk PII in public honey jar. Consider moving to private or team access."
                )
        
        # Compliance recommendations
        compliance_frameworks = set()
        for detection in detections:
            if detection.compliance_frameworks:
                compliance_frameworks.update(fw.value for fw in detection.compliance_frameworks)
        
        if 'hipaa' in compliance_frameworks:
            recommendations.append(
                "🏥 HIPAA-regulated PII detected. Ensure PHI handling compliance and access controls."
            )
        
        if 'gdpr' in compliance_frameworks:
            recommendations.append(
                "🇪🇺 GDPR-regulated PII detected. Ensure data subject rights and retention policies."
            )
            
        if 'pci_dss' in compliance_frameworks:
            recommendations.append(
                "💳 PCI-DSS regulated data detected. Consider immediate removal or encryption."
            )
        
        if 'attorney_client' in compliance_frameworks:
            recommendations.append(
                "⚖️ Attorney-client privileged information detected. Ensure confidentiality controls."
            )
        
        # Mode-specific recommendations
        if detection_mode == 'medical':
            recommendations.append(
                "🔬 Medical context detected. Review PHI handling policies and access permissions."
            )
        elif detection_mode == 'legal':
            recommendations.append(
                "📜 Legal context detected. Verify attorney-client privilege protections are in place."
            )
        elif detection_mode == 'financial':
            recommendations.append(
                "💰 Financial context detected. Ensure PCI-DSS compliance and data security."
            )
        
        return recommendations

# Singleton instance for knowledge service use
pii_integration = PIIIntegrationService()