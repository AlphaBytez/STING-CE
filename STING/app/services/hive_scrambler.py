#!/usr/bin/env python3
"""
Hive Scrambler - PII Detection and Scrambling Service
Patent-pending privacy-preserving technology for STING
"""

import re
import hashlib
import json
import uuid
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Setup logging
logger = logging.getLogger(__name__)

class PIIType(Enum):
    """Types of PII that can be detected"""
    # Personal Identifiers
    SSN = "social_security_number"
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport_number"
    
    # Financial
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    ROUTING_NUMBER = "routing_number"
    
    # Contact Information
    EMAIL = "email_address"
    PHONE = "phone_number"
    ADDRESS = "physical_address"
    
    # Personal Information
    NAME = "person_name"
    DATE_OF_BIRTH = "date_of_birth"
    
    # Healthcare (HIPAA)
    MEDICAL_RECORD = "medical_record_number"
    HEALTH_INSURANCE = "health_insurance_id"
    DEA_NUMBER = "dea_number"
    NPI_NUMBER = "npi_number"
    ICD_CODE = "icd_diagnosis_code"
    CPT_CODE = "cpt_procedure_code"
    MEDICARE_ID = "medicare_id"
    MEDICAID_ID = "medicaid_id"
    PRESCRIPTION = "prescription_info"
    LAB_RESULT = "lab_result"
    DIAGNOSIS = "medical_diagnosis"
    MEDICATION = "medication_name"
    PATIENT_ID = "patient_id"
    
    # Legal (Attorney-Client Privilege)
    CASE_NUMBER = "case_number"
    BAR_NUMBER = "bar_number"
    COURT_DOCKET = "court_docket"
    CLIENT_MATTER_ID = "client_matter_id"
    SETTLEMENT_AMOUNT = "settlement_amount"
    CONTRACT_ID = "contract_id"
    DEPOSITION_ID = "deposition_id"
    TRUST_ACCOUNT = "trust_account"
    LEGAL_CITATION = "legal_citation"
    WITNESS_NAME = "witness_name"
    JUDGE_NAME = "judge_name"
    
    # Digital Identifiers
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    USERNAME = "username"
    
    # Credentials
    API_KEY = "api_key"
    PASSWORD = "password"
    SECRET_KEY = "secret_key"

class ComplianceFramework(Enum):
    """Compliance frameworks for PII protection"""
    HIPAA = "hipaa"
    GDPR = "gdpr"
    CCPA = "ccpa"
    PCI_DSS = "pci_dss"
    ATTORNEY_CLIENT = "attorney_client"
    GLBA = "glba"
    FERPA = "ferpa"
    SOX = "sox"

class DetectionMode(Enum):
    """Detection modes for different contexts"""
    GENERAL = "general"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    EDUCATIONAL = "educational"

@dataclass
class PIIDetection:
    """Represents a detected PII instance"""
    pii_type: PIIType
    original_value: str
    start_position: int
    end_position: int
    confidence: float
    context: str
    compliance_frameworks: List[ComplianceFramework] = None
    masked_value: str = ""
    detection_method: str = "pattern_match"
    risk_level: str = "medium"

@dataclass
class ScrambledData:
    """Result of scrambling operation"""
    scrambled_text: str
    detections: List[PIIDetection]
    mapping: Dict[str, str]  # scrambled -> original
    metadata: Dict[str, Any]

class HiveScrambler:
    """Main Hive Scrambler class for PII detection and scrambling"""
    
    def __init__(self, seed: Optional[str] = None, detection_mode: DetectionMode = DetectionMode.GENERAL, enable_audit: bool = True):
        """
        Initialize Hive Scrambler
        
        Args:
            seed: Optional seed for consistent scrambling (useful for testing)
            detection_mode: Detection mode for specialized PII patterns
            enable_audit: Whether to enable PII audit logging and serialization
        """
        self.seed = seed or str(uuid.uuid4())
        self.detection_mode = detection_mode
        self.enable_audit = enable_audit
        self.patterns = self._initialize_patterns()
        self.medical_patterns = self._initialize_medical_patterns()
        self.legal_patterns = self._initialize_legal_patterns()
        self.scramble_mapping = {}
        self.reverse_mapping = {}
        
        # Initialize audit service if enabled
        if self.enable_audit:
            try:
                from app.services.pii_audit_service import pii_audit_service
                self.audit_service = pii_audit_service
                logger.info("PII audit service initialized")
            except ImportError:
                logger.warning("PII audit service not available - audit logging disabled")
                self.enable_audit = False
                self.audit_service = None
        else:
            self.audit_service = None
        
        # Load specialized terminology for context detection
        self._load_specialized_terms()
        
    def _initialize_patterns(self) -> Dict[PIIType, re.Pattern]:
        """Initialize regex patterns for PII detection"""
        return {
            # US Social Security Number
            PIIType.SSN: re.compile(
                r'\b(?!000|666|9\d{2})\d{3}[-.\s]?(?!00)\d{2}[-.\s]?(?!0000)\d{4}\b',
                re.IGNORECASE
            ),
            
            # Credit Card (basic pattern - production would use Luhn check)
            PIIType.CREDIT_CARD: re.compile(
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b'
            ),
            
            # Email Address
            PIIType.EMAIL: re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            
            # Phone Number (US format)
            PIIType.PHONE: re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            ),
            
            # IP Address (IPv4)
            PIIType.IP_ADDRESS: re.compile(
                r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
            ),
            
            # API Key patterns (common formats)
            PIIType.API_KEY: re.compile(
                r'\b(?:sk_live_|pk_live_|api_key["\s:=]+|apikey["\s:=]+|token["\s:=]+)[A-Za-z0-9_\-]{20,}\b',
                re.IGNORECASE
            ),
            
            # Basic name pattern (would use NER in production)
            PIIType.NAME: re.compile(
                r'\b[A-Z][a-z]+\s+(?:[A-Z]\.\s+)?[A-Z][a-z]+\b'
            ),
            
            # Date of Birth (various formats)
            PIIType.DATE_OF_BIRTH: re.compile(
                r'\b(?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12][0-9]|3[01])[-/.](?:19|20)\d{2}\b'
            ),
        }
    
    def _initialize_medical_patterns(self) -> Dict[PIIType, re.Pattern]:
        """Initialize medical-specific regex patterns for HIPAA compliance"""
        return {
            # Medical Record Number (various formats)
            PIIType.MEDICAL_RECORD: re.compile(
                r'\b(?:MRN|Medical Record Number|Med Rec #?)[:\s]*([A-Z0-9]{6,12})\b',
                re.IGNORECASE
            ),
            
            # DEA Number (2 letters + 7 digits)
            PIIType.DEA_NUMBER: re.compile(
                r'\b(?:DEA[:\s]*)?([A-Z]{2}\d{7})\b'
            ),
            
            # NPI Number (10 digits)
            PIIType.NPI_NUMBER: re.compile(
                r'\b(?:NPI[:\s]*)(\d{10})\b',
                re.IGNORECASE
            ),
            
            # ICD-10 Codes
            PIIType.ICD_CODE: re.compile(
                r'\b([A-Z]\d{2}(?:\.\d{1,4})?)\b'
            ),
            
            # CPT Codes (5 digits)
            PIIType.CPT_CODE: re.compile(
                r'\b(?:CPT[:\s]*)(\d{5})\b',
                re.IGNORECASE
            ),
            
            # Medicare ID (new format: 1EG4-TE5-MK73)
            PIIType.MEDICARE_ID: re.compile(
                r'\b([0-9][A-Z][A-Z0-9]\d-[A-Z][A-Z0-9]\d-[A-Z][A-Z0-9]\d{2})\b'
            ),
            
            # Lab Results (numeric values with units)
            PIIType.LAB_RESULT: re.compile(
                r'\b(\d+(?:\.\d+)?)\s*(mg/dL|mmol/L|mEq/L|IU/mL|cells/mm3|%)\b'
            ),
        }
    
    def _initialize_legal_patterns(self) -> Dict[PIIType, re.Pattern]:
        """Initialize legal-specific regex patterns for attorney-client privilege"""
        return {
            # Case Numbers (various formats)
            PIIType.CASE_NUMBER: re.compile(
                r'\b(?:Case\s*(?:No\.?|Number)?[:\s]*)?((?:\d{2,4}[-/])?[A-Z]{2,4}[-/]\d{3,8}(?:[-/]\w+)?)\b',
                re.IGNORECASE
            ),
            
            # Bar Number
            PIIType.BAR_NUMBER: re.compile(
                r'\b(?:Bar\s*(?:No\.?|Number)?[:\s]*)?(\d{6,10})\b',
                re.IGNORECASE
            ),
            
            # Court Docket
            PIIType.COURT_DOCKET: re.compile(
                r'\b(?:Docket\s*(?:No\.?|Number)?[:\s]*)?((?:\d{2,4}[-/])?[A-Z]{2}[-/]\d{3,6})\b',
                re.IGNORECASE
            ),
            
            # Settlement/Financial Amounts
            PIIType.SETTLEMENT_AMOUNT: re.compile(
                r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|thousand|billion))?',
                re.IGNORECASE
            ),
            
            # Legal Citations
            PIIType.LEGAL_CITATION: re.compile(
                r'\b\d+\s+[A-Z][a-z]+\.?\s*(?:2d|3d)?\s*\d+\b'
            ),
        }
    
    def _load_specialized_terms(self):
        """Load specialized terminology for context detection"""
        self.medical_terms = {
            "patient", "diagnosis", "treatment", "prescription", "medication",
            "physician", "doctor", "nurse", "hospital", "clinic", "surgery",
            "symptoms", "condition", "allergy", "immunization", "vaccine",
            "laboratory", "x-ray", "mri", "ct scan", "blood test", "biopsy"
        }
        
        self.legal_terms = {
            "plaintiff", "defendant", "attorney", "lawyer", "counsel", "court",
            "judge", "jury", "witness", "testimony", "evidence", "motion",
            "brief", "discovery", "deposition", "interrogatory", "settlement",
            "verdict", "appeal", "litigation", "contract", "agreement"
        }
        
        self.medications = {
            "amoxicillin", "lisinopril", "metformin", "atorvastatin", "omeprazole",
            "simvastatin", "losartan", "albuterol", "gabapentin", "hydrochlorothiazide",
            "metoprolol", "azithromycin", "amlodipine", "sertraline", "prednisone"
        }
    
    def detect_pii(self, text: str, auto_detect_context: bool = True) -> List[PIIDetection]:
        """
        Detect PII in the given text with mode-specific patterns
        
        Args:
            text: Text to scan for PII
            auto_detect_context: Whether to auto-detect document context
            
        Returns:
            List of PIIDetection objects with compliance framework assignments
        """
        detections = []
        
        # Auto-detect context if requested
        if auto_detect_context and self.detection_mode == DetectionMode.GENERAL:
            self.detection_mode = self._detect_document_context(text)
        
        # Process general patterns
        for pii_type, pattern in self.patterns.items():
            detections.extend(self._process_pattern_matches(text, pii_type, pattern))
        
        # Process specialized patterns based on detection mode
        if self.detection_mode in [DetectionMode.MEDICAL, DetectionMode.GENERAL]:
            for pii_type, pattern in self.medical_patterns.items():
                detections.extend(self._process_pattern_matches(text, pii_type, pattern, "medical"))
        
        if self.detection_mode in [DetectionMode.LEGAL, DetectionMode.GENERAL]:
            for pii_type, pattern in self.legal_patterns.items():
                detections.extend(self._process_pattern_matches(text, pii_type, pattern, "legal"))
        
        # Detect medications and conditions with context awareness
        detections.extend(self._detect_medical_entities(text))
        
        # Sort by position and deduplicate
        detections = self._deduplicate_detections(detections)
        detections.sort(key=lambda x: x.start_position)
        
        return detections
    
    def detect_pii_with_audit(self, 
                            text: str, 
                            user_id: str,
                            document_id: str = None,
                            honey_jar_id: str = None,
                            auto_detect_context: bool = True) -> List[PIIDetection]:
        """
        Detect PII with audit logging and serialization
        
        Args:
            text: Text to scan for PII
            user_id: ID of user performing the detection
            document_id: Optional document identifier
            honey_jar_id: Optional honey jar identifier
            auto_detect_context: Whether to auto-detect document context
            
        Returns:
            List of PIIDetection objects with audit logging applied
        """
        # Perform detection
        detections = self.detect_pii(text, auto_detect_context)
        
        # Audit logging if enabled
        if self.enable_audit and self.audit_service and detections:
            try:
                self.audit_service.batch_record_detections(
                    detections=detections,
                    user_id=user_id,
                    document_id=document_id,
                    honey_jar_id=honey_jar_id,
                    detection_mode=self.detection_mode.value
                )
                logger.info(f"Audit logged {len(detections)} PII detections for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to audit log PII detections: {e}")
                # Continue even if audit logging fails
        
        return detections
    
    def get_pii_summary(self, detections: List[PIIDetection]) -> Dict[str, Any]:
        """
        Generate summary statistics for PII detections
        
        Args:
            detections: List of PII detections
            
        Returns:
            Dictionary with summary statistics
        """
        if not detections:
            return {
                "total_detections": 0,
                "by_type": {},
                "by_risk_level": {},
                "by_compliance_framework": {},
                "detection_mode": self.detection_mode.value
            }
        
        summary = {
            "total_detections": len(detections),
            "by_type": {},
            "by_risk_level": {"high": 0, "medium": 0, "low": 0},
            "by_compliance_framework": {},
            "detection_mode": self.detection_mode.value,
            "highest_risk_level": "low",
            "compliance_violations": 0
        }
        
        for detection in detections:
            # Count by type
            pii_type = detection.pii_type.value
            summary["by_type"][pii_type] = summary["by_type"].get(pii_type, 0) + 1
            
            # Count by risk level
            summary["by_risk_level"][detection.risk_level] += 1
            
            # Track highest risk level
            if detection.risk_level == "high":
                summary["highest_risk_level"] = "high"
            elif detection.risk_level == "medium" and summary["highest_risk_level"] != "high":
                summary["highest_risk_level"] = "medium"
            
            # Count by compliance framework
            if detection.compliance_frameworks:
                for framework in detection.compliance_frameworks:
                    fw_name = framework.value
                    summary["by_compliance_framework"][fw_name] = summary["by_compliance_framework"].get(fw_name, 0) + 1
            
            # Count compliance violations (high risk items)
            if detection.risk_level == "high":
                summary["compliance_violations"] += 1
        
        return summary
    
    def serialize_detections(self, detections: List[PIIDetection]) -> str:
        """
        Serialize PII detections to JSON (without original values for security)
        
        Args:
            detections: List of PII detections
            
        Returns:
            JSON string with serialized detections
        """
        serialized = []
        
        for detection in detections:
            # Create serialized version without original values
            detection_data = {
                "pii_type": detection.pii_type.value,
                "start_position": detection.start_position,
                "end_position": detection.end_position,
                "confidence": detection.confidence,
                "risk_level": detection.risk_level,
                "detection_method": detection.detection_method,
                "compliance_frameworks": [fw.value for fw in (detection.compliance_frameworks or [])],
                "masked_value": detection.masked_value,
                "context_hash": hashlib.sha256(detection.context.encode('utf-8')).hexdigest() if detection.context else None,
                "value_hash": hashlib.sha256(detection.original_value.encode('utf-8')).hexdigest()
            }
            serialized.append(detection_data)
        
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "detection_mode": self.detection_mode.value,
            "total_detections": len(detections),
            "detections": serialized
        }, indent=2)
    
    def _process_pattern_matches(self, text: str, pii_type: PIIType, pattern: re.Pattern, 
                               detection_method: str = "pattern_match") -> List[PIIDetection]:
        """Process regex pattern matches into PIIDetection objects"""
        detections = []
        
        for match in pattern.finditer(text):
            # Extract context (100 chars before and after for better context)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            
            # Calculate confidence with context awareness
            confidence = self._calculate_confidence(pii_type, match.group(), context)
            
            # Determine compliance frameworks
            compliance_frameworks = self._get_compliance_frameworks(pii_type, context)
            
            # Generate masked value
            masked_value = self._generate_masked_value(pii_type, match.group())
            
            # Determine risk level
            risk_level = self._assess_risk_level(pii_type, context)
            
            detection = PIIDetection(
                pii_type=pii_type,
                original_value=match.group(),
                start_position=match.start(),
                end_position=match.end(),
                confidence=confidence,
                context=context,
                compliance_frameworks=compliance_frameworks,
                masked_value=masked_value,
                detection_method=detection_method,
                risk_level=risk_level
            )
            detections.append(detection)
        
        return detections
    
    def _detect_document_context(self, text: str) -> DetectionMode:
        """Auto-detect document context based on terminology"""
        text_lower = text.lower()
        
        medical_score = sum(1 for term in self.medical_terms if term in text_lower)
        legal_score = sum(1 for term in self.legal_terms if term in text_lower)
        
        # Check for specific indicators
        if any(indicator in text_lower for indicator in ['patient', 'diagnosis', 'prescription', 'medical record']):
            medical_score += 5
        if any(indicator in text_lower for indicator in ['plaintiff', 'defendant', 'case number', 'attorney']):
            legal_score += 5
        
        if medical_score >= 3:
            return DetectionMode.MEDICAL
        elif legal_score >= 3:
            return DetectionMode.LEGAL
        else:
            return DetectionMode.GENERAL
    
    def _detect_medical_entities(self, text: str) -> List[PIIDetection]:
        """Detect medical entities like medications and conditions"""
        detections = []
        
        if self.detection_mode not in [DetectionMode.MEDICAL, DetectionMode.GENERAL]:
            return detections
        
        # Detect medications
        for medication in self.medications:
            pattern = re.compile(r'\b' + re.escape(medication) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                # Check if it's in medical context
                context_start = max(0, match.start() - 200)
                context_end = min(len(text), match.end() + 200)
                context = text[context_start:context_end].lower()
                
                if any(term in context for term in ['mg', 'dosage', 'prescribed', 'medication', 'drug']):
                    detection = PIIDetection(
                        pii_type=PIIType.MEDICATION,
                        original_value=match.group(),
                        start_position=match.start(),
                        end_position=match.end(),
                        confidence=0.8,
                        context=context,
                        compliance_frameworks=[ComplianceFramework.HIPAA],
                        masked_value=f"[MEDICATION_{len(medication)}]",
                        detection_method="entity_detection",
                        risk_level="medium"
                    )
                    detections.append(detection)
        
        return detections
    
    def scramble(self, text: str, preserve_format: bool = True) -> ScrambledData:
        """
        Scramble PII in the text while preserving semantic meaning
        
        Args:
            text: Text containing PII to scramble
            preserve_format: Whether to preserve format (e.g., XXX-XX-XXXX for SSN)
            
        Returns:
            ScrambledData object with scrambled text and mappings
        """
        detections = self.detect_pii(text)
        scrambled_text = text
        offset = 0
        
        for detection in detections:
            # Generate scrambled value
            scrambled_value = self._generate_scrambled_value(
                detection.pii_type,
                detection.original_value,
                preserve_format
            )
            
            # Store mapping
            mapping_key = f"{detection.pii_type.value}_{len(self.scramble_mapping)}"
            self.scramble_mapping[mapping_key] = detection.original_value
            self.reverse_mapping[detection.original_value] = mapping_key
            
            # Replace in text with placeholder
            placeholder = f"{{{{{mapping_key}}}}}"
            
            # Adjust positions based on offset from previous replacements
            start = detection.start_position + offset
            end = detection.end_position + offset
            
            scrambled_text = (
                scrambled_text[:start] + 
                placeholder + 
                scrambled_text[end:]
            )
            
            # Update offset
            offset += len(placeholder) - (end - start)
        
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "detections_count": len(detections),
            "pii_types": list(set(d.pii_type.value for d in detections)),
            "seed": self.seed
        }
        
        return ScrambledData(
            scrambled_text=scrambled_text,
            detections=detections,
            mapping=self.scramble_mapping.copy(),
            metadata=metadata
        )
    
    def unscramble(self, scrambled_text: str, mapping: Dict[str, str]) -> str:
        """
        Restore original values from scrambled text
        
        Args:
            scrambled_text: Text with scrambled placeholders
            mapping: Mapping of placeholders to original values
            
        Returns:
            Original text with PII restored
        """
        unscrambled = scrambled_text
        
        for placeholder, original in mapping.items():
            unscrambled = unscrambled.replace(f"{{{{{placeholder}}}}}", original)
        
        return unscrambled
    
    def _generate_scrambled_value(
        self, 
        pii_type: PIIType, 
        original: str, 
        preserve_format: bool
    ) -> str:
        """Generate a scrambled value that preserves format if requested"""
        if not preserve_format:
            # Simple hash-based scrambling
            hash_val = hashlib.sha256(
                f"{self.seed}:{pii_type.value}:{original}".encode()
            ).hexdigest()[:12]
            return f"{pii_type.name}_{hash_val}"
        
        # Format-preserving scrambling
        if pii_type == PIIType.SSN:
            # Preserve XXX-XX-XXXX format
            if '-' in original:
                return "XXX-XX-XXXX"
            else:
                return "XXXXXXXXX"
                
        elif pii_type == PIIType.PHONE:
            # Preserve phone format
            if '(' in original:
                return "(XXX) XXX-XXXX"
            elif '-' in original:
                return "XXX-XXX-XXXX"
            else:
                return "XXXXXXXXXX"
                
        elif pii_type == PIIType.EMAIL:
            # Preserve email format
            parts = original.split('@')
            if len(parts) == 2:
                domain_parts = parts[1].split('.')
                return f"user@{'x' * len(domain_parts[0])}.{domain_parts[-1]}"
            
        elif pii_type == PIIType.CREDIT_CARD:
            # Show last 4 digits only
            return f"****-****-****-{original[-4:]}"
            
        elif pii_type == PIIType.IP_ADDRESS:
            # Preserve IP format
            return "XXX.XXX.XXX.XXX"
        
        # Default: return type indicator
        return f"[{pii_type.name}]"
    
    def _get_compliance_frameworks(self, pii_type: PIIType, context: str) -> List[ComplianceFramework]:
        """Determine applicable compliance frameworks for detected PII"""
        frameworks = []
        
        # Healthcare/HIPAA
        if pii_type in [PIIType.MEDICAL_RECORD, PIIType.DEA_NUMBER, PIIType.NPI_NUMBER,
                       PIIType.ICD_CODE, PIIType.CPT_CODE, PIIType.MEDICARE_ID, 
                       PIIType.MEDICAID_ID, PIIType.PRESCRIPTION, PIIType.LAB_RESULT,
                       PIIType.DIAGNOSIS, PIIType.MEDICATION, PIIType.PATIENT_ID]:
            frameworks.append(ComplianceFramework.HIPAA)
        
        # Legal/Attorney-Client Privilege
        if pii_type in [PIIType.CASE_NUMBER, PIIType.BAR_NUMBER, PIIType.COURT_DOCKET,
                       PIIType.CLIENT_MATTER_ID, PIIType.SETTLEMENT_AMOUNT, PIIType.CONTRACT_ID,
                       PIIType.DEPOSITION_ID, PIIType.TRUST_ACCOUNT, PIIType.LEGAL_CITATION,
                       PIIType.WITNESS_NAME, PIIType.JUDGE_NAME]:
            frameworks.append(ComplianceFramework.ATTORNEY_CLIENT)
        
        # Financial/PCI-DSS
        if pii_type in [PIIType.CREDIT_CARD, PIIType.BANK_ACCOUNT, PIIType.ROUTING_NUMBER]:
            frameworks.append(ComplianceFramework.PCI_DSS)
            frameworks.append(ComplianceFramework.GLBA)
        
        # Personal Data/GDPR & CCPA
        if pii_type in [PIIType.NAME, PIIType.EMAIL, PIIType.PHONE, PIIType.ADDRESS,
                       PIIType.DATE_OF_BIRTH, PIIType.SSN, PIIType.DRIVERS_LICENSE]:
            frameworks.append(ComplianceFramework.GDPR)
            frameworks.append(ComplianceFramework.CCPA)
        
        return frameworks
    
    def _generate_masked_value(self, pii_type: PIIType, original_value: str) -> str:
        """Generate a masked version of the PII for display purposes"""
        # Use existing method but enhance for new types
        if pii_type in [PIIType.DEA_NUMBER, PIIType.NPI_NUMBER]:
            return f"[{pii_type.name}]"
        elif pii_type == PIIType.ICD_CODE:
            return "X##.##"
        elif pii_type == PIIType.CPT_CODE:
            return "#####"
        elif pii_type == PIIType.MEDICARE_ID:
            return "1XX#-XX#-XX##"
        elif pii_type in [PIIType.CASE_NUMBER, PIIType.COURT_DOCKET]:
            return "[CASE-####-XX]"
        elif pii_type == PIIType.SETTLEMENT_AMOUNT:
            return "$[AMOUNT]"
        elif pii_type == PIIType.BAR_NUMBER:
            return "[BAR-######]"
        else:
            # Fall back to existing method
            return self._generate_scrambled_value(pii_type, original_value, True)
    
    def _assess_risk_level(self, pii_type: PIIType, context: str) -> str:
        """Assess risk level of detected PII"""
        # High risk: Financial and sensitive identifiers
        if pii_type in [PIIType.SSN, PIIType.CREDIT_CARD, PIIType.API_KEY, 
                       PIIType.PASSWORD, PIIType.BANK_ACCOUNT, PIIType.SETTLEMENT_AMOUNT]:
            return "high"
        
        # Medium risk: Medical and legal sensitive data
        if pii_type in [PIIType.MEDICAL_RECORD, PIIType.PRESCRIPTION, PIIType.DIAGNOSIS,
                       PIIType.CASE_NUMBER, PIIType.CLIENT_MATTER_ID, PIIType.DEA_NUMBER]:
            return "medium"
        
        # Low risk: Basic contact information
        if pii_type in [PIIType.EMAIL, PIIType.PHONE, PIIType.NAME]:
            # Check context - medical/legal context increases risk
            context_lower = context.lower()
            if any(term in context_lower for term in ['patient', 'client', 'defendant', 'plaintiff']):
                return "medium"
            return "low"
        
        return "medium"  # Default
    
    def _deduplicate_detections(self, detections: List[PIIDetection]) -> List[PIIDetection]:
        """Remove duplicate or overlapping detections, keeping highest confidence"""
        if not detections:
            return []
        
        # Sort by start position, then by confidence (highest first)
        detections.sort(key=lambda x: (x.start_position, -x.confidence))
        
        deduplicated = []
        last_end = -1
        
        for detection in detections:
            # Skip if this detection overlaps with a previous one
            if detection.start_position >= last_end:
                deduplicated.append(detection)
                last_end = detection.end_position
            # If overlapping, only keep if significantly higher confidence
            elif detection.confidence > deduplicated[-1].confidence + 0.2:
                deduplicated[-1] = detection
                last_end = detection.end_position
        
        return deduplicated
    
    def _calculate_confidence(self, pii_type: PIIType, value: str, context: str = "") -> float:
        """
        Calculate confidence score for PII detection with context awareness
        
        Args:
            pii_type: Type of PII detected
            value: The detected value
            context: Surrounding context text
            
        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.7
        context_lower = context.lower()
        
        # Pattern-specific confidence adjustments
        if pii_type == PIIType.SSN:
            if re.match(r'^\d{3}-\d{2}-\d{4}$', value):
                base_confidence = 0.95
            elif re.match(r'^\d{9}$', value):
                base_confidence = 0.8
                
        elif pii_type == PIIType.EMAIL:
            common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
            if any(domain in value.lower() for domain in common_domains):
                base_confidence = 0.9
                
        elif pii_type == PIIType.CREDIT_CARD:
            if self._luhn_check(value.replace('-', '').replace(' ', '')):
                base_confidence = 0.98
            elif len(value.replace('-', '').replace(' ', '')) in [15, 16]:
                base_confidence = 0.85
        
        # Medical PII confidence boosts
        elif pii_type in [PIIType.MEDICAL_RECORD, PIIType.DEA_NUMBER, PIIType.NPI_NUMBER]:
            base_confidence = 0.85
            if any(term in context_lower for term in ['patient', 'doctor', 'hospital', 'medical']):
                base_confidence = min(0.95, base_confidence + 0.1)
        
        elif pii_type in [PIIType.ICD_CODE, PIIType.CPT_CODE]:
            if any(term in context_lower for term in ['diagnosis', 'procedure', 'code']):
                base_confidence = 0.9
                
        elif pii_type == PIIType.MEDICATION:
            if any(term in context_lower for term in ['mg', 'dosage', 'prescribed', 'medication']):
                base_confidence = 0.9
        
        # Legal PII confidence boosts
        elif pii_type in [PIIType.CASE_NUMBER, PIIType.COURT_DOCKET]:
            if any(term in context_lower for term in ['case', 'court', 'docket', 'lawsuit']):
                base_confidence = 0.95
                
        elif pii_type == PIIType.BAR_NUMBER:
            if any(term in context_lower for term in ['attorney', 'lawyer', 'bar']):
                base_confidence = 0.95
                
        elif pii_type == PIIType.SETTLEMENT_AMOUNT:
            if any(term in context_lower for term in ['settlement', 'damages', 'award']):
                base_confidence = 0.9
        
        # Context-based adjustments for names
        elif pii_type == PIIType.NAME:
            if any(term in context_lower for term in ['patient', 'client', 'defendant', 'plaintiff']):
                base_confidence = min(0.95, base_confidence + 0.2)
        
        # Detection mode boosts
        if self.detection_mode == DetectionMode.MEDICAL and pii_type in [
            PIIType.MEDICAL_RECORD, PIIType.DEA_NUMBER, PIIType.NPI_NUMBER,
            PIIType.ICD_CODE, PIIType.CPT_CODE, PIIType.MEDICATION
        ]:
            base_confidence = min(0.95, base_confidence + 0.05)
            
        elif self.detection_mode == DetectionMode.LEGAL and pii_type in [
            PIIType.CASE_NUMBER, PIIType.BAR_NUMBER, PIIType.COURT_DOCKET,
            PIIType.SETTLEMENT_AMOUNT, PIIType.LEGAL_CITATION
        ]:
            base_confidence = min(0.95, base_confidence + 0.05)
        
        return base_confidence
    
    def generate_report(self, detections: List[PIIDetection]) -> Dict[str, Any]:
        """
        Generate a summary report of PII detections
        
        Args:
            detections: List of PIIDetection objects
            
        Returns:
            Summary report dictionary
        """
        if not detections:
            return {
                "total_detections": 0,
                "risk_level": "low",
                "summary": "No PII detected"
            }
        
        pii_counts = {}
        high_risk_count = 0
        
        for detection in detections:
            pii_type = detection.pii_type.value
            pii_counts[pii_type] = pii_counts.get(pii_type, 0) + 1
            
            # Count high-risk PII types
            if detection.pii_type in [
                PIIType.SSN, 
                PIIType.CREDIT_CARD, 
                PIIType.API_KEY,
                PIIType.PASSWORD
            ]:
                high_risk_count += 1
        
        # Determine risk level
        if high_risk_count > 5:
            risk_level = "critical"
        elif high_risk_count > 0:
            risk_level = "high"
        elif len(detections) > 10:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "total_detections": len(detections),
            "risk_level": risk_level,
            "pii_types": pii_counts,
            "high_risk_items": high_risk_count,
            "summary": f"Detected {len(detections)} PII items across {len(pii_counts)} categories",
            "recommendations": self._generate_recommendations(risk_level, pii_counts)
        }
    
    def _generate_recommendations(
        self, 
        risk_level: str, 
        pii_counts: Dict[str, int]
    ) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.append(
                "Immediate action required: Critical PII detected in data"
            )
            recommendations.append(
                "Enable encryption for all data transmissions"
            )
        
        if PIIType.API_KEY.value in pii_counts:
            recommendations.append(
                "Rotate all detected API keys immediately"
            )
            recommendations.append(
                "Use environment variables or secure vaults for credentials"
            )
        
        if PIIType.SSN.value in pii_counts or PIIType.CREDIT_CARD.value in pii_counts:
            recommendations.append(
                "Implement tokenization for sensitive financial data"
            )
            recommendations.append(
                "Ensure PCI DSS compliance for credit card handling"
            )
        
        if not recommendations:
            recommendations.append(
                "Continue monitoring for PII in data flows"
            )
        
        return recommendations


# Example usage and testing
if __name__ == "__main__":
    # Initialize scrambler
    scrambler = HiveScrambler(seed="test-seed-123")
    
    # Test text with various PII
    test_text = """
    Customer: John Smith
    SSN: 123-45-6789
    Email: john.smith@example.com
    Phone: (555) 123-4567
    Credit Card: 4532-1234-5678-9012
    
    API Configuration:
    api_key: sk_live_abcdef123456789
    Server IP: 192.168.1.100
    
    Medical Record: MRN-123456
    Date of Birth: 01/15/1985
    """
    
    print("Original Text:")
    print(test_text)
    print("\n" + "="*60 + "\n")
    
    # Detect PII
    detections = scrambler.detect_pii(test_text)
    print(f"Found {len(detections)} PII instances:")
    for detection in detections:
        print(f"  - {detection.pii_type.value}: {detection.original_value} "
              f"(confidence: {detection.confidence:.2f})")
    
    print("\n" + "="*60 + "\n")
    
    # Scramble text
    result = scrambler.scramble(test_text)
    print("Scrambled Text:")
    print(result.scrambled_text)
    
    print("\n" + "="*60 + "\n")
    
    # Generate report
    report = scrambler.generate_report(detections)
    print("PII Detection Report:")
    print(json.dumps(report, indent=2))
    
    print("\n" + "="*60 + "\n")
    
    # Unscramble
    restored = scrambler.unscramble(result.scrambled_text, result.mapping)
    print("Restored Text:")
    print(restored)
    
    # Verify restoration
    print(f"\nRestoration successful: {restored == test_text}")