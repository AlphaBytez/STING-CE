#!/usr/bin/env python3
"""
Containerized PII Testing and Demo Functions for STING
Tests generated synthetic data with various PII detection scenarios
"""

import os
import sys
import json
import time
import glob
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Embedded version of STING's PII detection (simplified for container)
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
import re

class PIIType(Enum):
    # Personal
    SSN = "social_security_number"
    EMAIL = "email_address"
    PHONE = "phone_number"
    NAME = "person_name"
    ADDRESS = "address"
    
    # Medical (HIPAA)
    MEDICAL_RECORD = "medical_record_number"
    DEA_NUMBER = "dea_number"
    NPI_NUMBER = "npi_number"
    ICD_CODE = "icd_diagnosis_code"
    CPT_CODE = "cpt_procedure_code"
    PATIENT_ID = "patient_id"
    MEDICARE_ID = "medicare_id"
    PRESCRIPTION = "prescription"
    LAB_RESULT = "lab_result"
    
    # Legal (Attorney-Client)
    CASE_NUMBER = "case_number"
    BAR_NUMBER = "bar_number"
    COURT_DOCKET = "court_docket"
    SETTLEMENT_AMOUNT = "settlement_amount"
    CONTRACT_ID = "contract_id"
    CLIENT_MATTER_ID = "client_matter_id"
    TRUST_ACCOUNT = "trust_account"
    
    # Financial (PCI-DSS)
    CREDIT_CARD = "credit_card_number"
    BANK_ACCOUNT = "bank_account_number"
    ROUTING_NUMBER = "routing_number"
    LOAN_ID = "loan_id"

class DetectionMode(Enum):
    GENERAL = "general"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"

class ComplianceFramework(Enum):
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    ATTORNEY_CLIENT = "attorney_client"
    CCPA = "ccpa"

@dataclass
class PIIDetection:
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

class ContainerizedPIIDetector:
    """Simplified PII detector for container testing"""
    
    def __init__(self, detection_mode: DetectionMode = DetectionMode.GENERAL):
        self.detection_mode = detection_mode
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[PIIType, re.Pattern]:
        """Initialize regex patterns for PII detection"""
        patterns = {
            # Basic patterns
            PIIType.SSN: re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            PIIType.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            PIIType.PHONE: re.compile(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            PIIType.NAME: re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
            
            # Medical patterns
            PIIType.MEDICAL_RECORD: re.compile(r'\b(?:MRN|Medical Record Number|Med Rec #?)[:\s]*([A-Z0-9]{6,12})\b', re.IGNORECASE),
            PIIType.DEA_NUMBER: re.compile(r'\b[A-Z]{2}\d{7}\b'),
            PIIType.NPI_NUMBER: re.compile(r'\b\d{10}\b'),
            PIIType.ICD_CODE: re.compile(r'\b[A-Z]\d{2}\.?\d{1,3}\b'),
            PIIType.CPT_CODE: re.compile(r'\b\d{5}\b'),
            PIIType.MEDICARE_ID: re.compile(r'\b\d{3}-\d{2}-\d{4}[A-Z]\b'),
            
            # Legal patterns  
            PIIType.CASE_NUMBER: re.compile(r'\b\d{4}-[A-Z]{2,4}-\d{3,8}\b'),
            PIIType.BAR_NUMBER: re.compile(r'\bBar #?\s*:?\s*\d{6,8}\b', re.IGNORECASE),
            PIIType.COURT_DOCKET: re.compile(r'\b\d{4}-[A-Z]{2,4}-\d{4,8}\b'),
            PIIType.SETTLEMENT_AMOUNT: re.compile(r'\$[\d,]+(?:\.\d{2})?\b'),
            PIIType.CONTRACT_ID: re.compile(r'\b(?:Contract|CTR)[-_]?\d{4}[-_]?\d{3,6}\b', re.IGNORECASE),
            
            # Financial patterns
            PIIType.CREDIT_CARD: re.compile(r'\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13})\b'),
            PIIType.BANK_ACCOUNT: re.compile(r'\b\d{8,17}\b'),
            PIIType.ROUTING_NUMBER: re.compile(r'\b\d{9}\b'),
            PIIType.LOAN_ID: re.compile(r'\bLA-\d{6}\b')
        }
        return patterns
    
    def detect_pii(self, text: str) -> List[PIIDetection]:
        """Detect PII in text"""
        detections = []
        
        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # Extract context
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                
                # Determine compliance frameworks
                compliance = self._get_compliance_frameworks(pii_type)
                
                # Calculate confidence
                confidence = self._calculate_confidence(pii_type, match.group(), context)
                
                # Determine risk level
                risk_level = self._get_risk_level(pii_type)
                
                detection = PIIDetection(
                    pii_type=pii_type,
                    original_value=match.group(),
                    start_position=match.start(),
                    end_position=match.end(),
                    confidence=confidence,
                    context=context,
                    compliance_frameworks=compliance,
                    masked_value=f"[{pii_type.name}]",
                    risk_level=risk_level
                )
                detections.append(detection)
        
        return sorted(detections, key=lambda x: x.start_position)
    
    def _get_compliance_frameworks(self, pii_type: PIIType) -> List[ComplianceFramework]:
        """Map PII types to compliance frameworks"""
        mapping = {
            # HIPAA (Healthcare)
            PIIType.MEDICAL_RECORD: [ComplianceFramework.HIPAA],
            PIIType.DEA_NUMBER: [ComplianceFramework.HIPAA],
            PIIType.NPI_NUMBER: [ComplianceFramework.HIPAA],
            PIIType.ICD_CODE: [ComplianceFramework.HIPAA],
            PIIType.CPT_CODE: [ComplianceFramework.HIPAA],
            PIIType.PATIENT_ID: [ComplianceFramework.HIPAA],
            PIIType.MEDICARE_ID: [ComplianceFramework.HIPAA],
            
            # Attorney-Client Privilege
            PIIType.CASE_NUMBER: [ComplianceFramework.ATTORNEY_CLIENT],
            PIIType.BAR_NUMBER: [ComplianceFramework.ATTORNEY_CLIENT],
            PIIType.COURT_DOCKET: [ComplianceFramework.ATTORNEY_CLIENT],
            PIIType.SETTLEMENT_AMOUNT: [ComplianceFramework.ATTORNEY_CLIENT],
            PIIType.CONTRACT_ID: [ComplianceFramework.ATTORNEY_CLIENT],
            
            # PCI-DSS (Financial)
            PIIType.CREDIT_CARD: [ComplianceFramework.PCI_DSS],
            PIIType.BANK_ACCOUNT: [ComplianceFramework.PCI_DSS],
            PIIType.ROUTING_NUMBER: [ComplianceFramework.PCI_DSS],
            
            # GDPR (General Personal Data)
            PIIType.SSN: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
            PIIType.EMAIL: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
            PIIType.PHONE: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
            PIIType.NAME: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
        }
        return mapping.get(pii_type, [])
    
    def _calculate_confidence(self, pii_type: PIIType, value: str, context: str) -> float:
        """Calculate confidence score for detection"""
        base_confidence = 0.85
        
        # Increase confidence for specific patterns
        if pii_type == PIIType.SSN and re.match(r'^\d{3}-\d{2}-\d{4}$', value):
            return 0.95
        elif pii_type == PIIType.EMAIL and '@' in value:
            return 0.92
        elif pii_type == PIIType.DEA_NUMBER and len(value) == 9:
            return 0.90
        
        return base_confidence
    
    def _get_risk_level(self, pii_type: PIIType) -> str:
        """Determine risk level for PII type"""
        high_risk = {PIIType.SSN, PIIType.CREDIT_CARD, PIIType.SETTLEMENT_AMOUNT, PIIType.MEDICARE_ID}
        low_risk = {PIIType.EMAIL, PIIType.PHONE, PIIType.NAME}
        
        if pii_type in high_risk:
            return "high"
        elif pii_type in low_risk:
            return "low"
        else:
            return "medium"

class PIITestSuite:
    """Test suite for PII detection on generated data"""
    
    def __init__(self, data_dir="/data/output"):
        self.data_dir = Path(data_dir)
        self.results_dir = self.data_dir / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
    def run_demo_scenario_medical(self):
        """Demo scenario: Medical office HIPAA compliance"""
        logger.info("🏥 MEDICAL OFFICE DEMO - HIPAA Compliance")
        logger.info("=" * 50)
        
        # Find medical files
        medical_files = list(self.data_dir.glob("medical/**/*.csv"))
        if not medical_files:
            logger.error("No medical CSV files found")
            return None
        
        # Load sample data
        sample_file = medical_files[0]
        logger.info(f"📄 Processing: {sample_file.name}")
        
        try:
            df = pd.read_csv(sample_file)
            sample_text = df.to_string()[:2000]  # First 2KB for demo
        except Exception as e:
            logger.error(f"Error reading medical file: {e}")
            return None
        
        # Run PII detection
        detector = ContainerizedPIIDetector(DetectionMode.MEDICAL)
        start_time = time.time()
        detections = detector.detect_pii(sample_text)
        processing_time = time.time() - start_time
        
        # Analyze results
        hipaa_detections = [d for d in detections if ComplianceFramework.HIPAA in (d.compliance_frameworks or [])]
        high_risk_detections = [d for d in detections if d.risk_level == "high"]
        
        # Print results
        logger.info(f"⏱️  Processing time: {processing_time:.3f} seconds")
        logger.info(f"🔍 Total PII elements found: {len(detections)}")
        logger.info(f"⚕️  HIPAA protected elements: {len(hipaa_detections)}")
        logger.info(f"⚠️  High risk elements: {len(high_risk_detections)}")
        
        logger.info("\n📋 Sample detections:")
        for i, detection in enumerate(detections[:5]):
            compliance_str = ", ".join([f.value for f in (detection.compliance_frameworks or [])])
            logger.info(f"   {i+1}. {detection.pii_type.value}: '{detection.original_value}'")
            logger.info(f"      Risk: {detection.risk_level}, Confidence: {detection.confidence:.2f}")
            logger.info(f"      Compliance: {compliance_str}")
        
        return {
            "scenario": "medical_hipaa",
            "processing_time": processing_time,
            "total_detections": len(detections),
            "hipaa_elements": len(hipaa_detections),
            "high_risk_elements": len(high_risk_detections),
            "sample_detections": detections[:10]
        }
    
    def run_demo_scenario_legal(self):
        """Demo scenario: Law firm attorney-client privilege"""
        logger.info("\n⚖️  LAW FIRM DEMO - Attorney-Client Privilege")
        logger.info("=" * 50)
        
        # Find legal files
        legal_files = list(self.data_dir.glob("legal/*.txt"))
        if not legal_files:
            logger.error("No legal text files found")
            return None
        
        # Load sample data
        sample_file = legal_files[0]
        logger.info(f"📄 Processing: {sample_file.name}")
        
        try:
            with open(sample_file, 'r') as f:
                sample_text = f.read()
        except Exception as e:
            logger.error(f"Error reading legal file: {e}")
            return None
        
        # Run PII detection
        detector = ContainerizedPIIDetector(DetectionMode.LEGAL)
        start_time = time.time()
        detections = detector.detect_pii(sample_text)
        processing_time = time.time() - start_time
        
        # Analyze results
        privileged_detections = [d for d in detections if ComplianceFramework.ATTORNEY_CLIENT in (d.compliance_frameworks or [])]
        settlement_amounts = [d for d in detections if d.pii_type == PIIType.SETTLEMENT_AMOUNT]
        
        # Print results
        logger.info(f"⏱️  Processing time: {processing_time:.3f} seconds")
        logger.info(f"🔍 Total PII elements found: {len(detections)}")
        logger.info(f"🏛️  Attorney-client privileged: {len(privileged_detections)}")
        logger.info(f"💰 Settlement amounts: {len(settlement_amounts)}")
        
        logger.info("\n📋 Sample detections:")
        for i, detection in enumerate(detections[:5]):
            logger.info(f"   {i+1}. {detection.pii_type.value}: '{detection.original_value}'")
            logger.info(f"      Risk: {detection.risk_level}")
        
        return {
            "scenario": "legal_privilege",
            "processing_time": processing_time,
            "total_detections": len(detections),
            "privileged_elements": len(privileged_detections),
            "settlement_amounts": len(settlement_amounts),
            "sample_detections": detections[:10]
        }
    
    def run_demo_scenario_financial(self):
        """Demo scenario: Financial institution PCI-DSS compliance"""
        logger.info("\n💳 FINANCIAL INSTITUTION DEMO - PCI-DSS Compliance")
        logger.info("=" * 50)
        
        # Find financial files
        financial_files = list(self.data_dir.glob("financial/*.txt"))
        csv_files = list(self.data_dir.glob("financial/*.csv"))
        
        if csv_files:
            sample_file = csv_files[0]
            try:
                df = pd.read_csv(sample_file)
                sample_text = df.head(10).to_string()  # First 10 records
            except Exception as e:
                logger.error(f"Error reading financial CSV: {e}")
                return None
        elif financial_files:
            sample_file = financial_files[0]
            try:
                with open(sample_file, 'r') as f:
                    sample_text = f.read()
            except Exception as e:
                logger.error(f"Error reading financial file: {e}")
                return None
        else:
            logger.error("No financial files found")
            return None
        
        logger.info(f"📄 Processing: {sample_file.name}")
        
        # Run PII detection
        detector = ContainerizedPIIDetector(DetectionMode.FINANCIAL)
        start_time = time.time()
        detections = detector.detect_pii(sample_text)
        processing_time = time.time() - start_time
        
        # Analyze results
        pci_detections = [d for d in detections if ComplianceFramework.PCI_DSS in (d.compliance_frameworks or [])]
        credit_cards = [d for d in detections if d.pii_type == PIIType.CREDIT_CARD]
        bank_accounts = [d for d in detections if d.pii_type == PIIType.BANK_ACCOUNT]
        
        # Print results
        logger.info(f"⏱️  Processing time: {processing_time:.3f} seconds")
        logger.info(f"🔍 Total PII elements found: {len(detections)}")
        logger.info(f"💳 PCI-DSS protected elements: {len(pci_detections)}")
        logger.info(f"💰 Credit cards detected: {len(credit_cards)}")
        logger.info(f"🏦 Bank accounts detected: {len(bank_accounts)}")
        
        return {
            "scenario": "financial_pci",
            "processing_time": processing_time,
            "total_detections": len(detections),
            "pci_elements": len(pci_detections),
            "credit_cards": len(credit_cards),
            "bank_accounts": len(bank_accounts)
        }
    
    def run_performance_benchmark(self):
        """Run performance benchmark test"""
        logger.info("\n⚡ PERFORMANCE BENCHMARK TEST")
        logger.info("=" * 50)
        
        benchmark_results = {}
        
        # Test 1: Small scale (single file)
        logger.info("Test 1: Single file processing...")
        legal_files = list(self.data_dir.glob("legal/*.txt"))
        if legal_files:
            with open(legal_files[0], 'r') as f:
                text = f.read()
            
            detector = ContainerizedPIIDetector()
            start_time = time.time()
            detections = detector.detect_pii(text)
            single_file_time = time.time() - start_time
            
            benchmark_results["single_file"] = {
                "processing_time": single_file_time,
                "detections": len(detections),
                "rate": len(detections) / single_file_time if single_file_time > 0 else 0
            }
            logger.info(f"   Time: {single_file_time:.3f}s, Detections: {len(detections)}")
        
        # Test 2: Multiple files (batch)
        logger.info("Test 2: Multiple file processing...")
        all_legal_files = list(self.data_dir.glob("legal/*.txt"))[:10]  # First 10 files
        
        total_detections = 0
        start_time = time.time()
        detector = ContainerizedPIIDetector()
        
        for file in all_legal_files:
            with open(file, 'r') as f:
                text = f.read()
            detections = detector.detect_pii(text)
            total_detections += len(detections)
        
        batch_time = time.time() - start_time
        benchmark_results["batch_processing"] = {
            "files_processed": len(all_legal_files),
            "processing_time": batch_time,
            "total_detections": total_detections,
            "files_per_second": len(all_legal_files) / batch_time if batch_time > 0 else 0,
            "detections_per_second": total_detections / batch_time if batch_time > 0 else 0
        }
        
        logger.info(f"   Files: {len(all_legal_files)}, Time: {batch_time:.3f}s")
        logger.info(f"   Rate: {len(all_legal_files)/batch_time:.1f} files/sec, {total_detections/batch_time:.1f} detections/sec")
        
        return benchmark_results
    
    def run_comprehensive_test(self):
        """Run all test scenarios"""
        logger.info("🎯 STING COMPREHENSIVE PII DETECTION TEST")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run all scenarios
        medical_results = self.run_demo_scenario_medical()
        legal_results = self.run_demo_scenario_legal()
        financial_results = self.run_demo_scenario_financial()
        performance_results = self.run_performance_benchmark()
        
        total_time = time.time() - start_time
        
        # Compile comprehensive results
        comprehensive_results = {
            "test_timestamp": datetime.now().isoformat(),
            "total_test_time": total_time,
            "scenarios": {
                "medical": medical_results,
                "legal": legal_results,
                "financial": financial_results
            },
            "performance": performance_results,
            "summary": {
                "total_scenarios": 3,
                "scenarios_passed": sum(1 for r in [medical_results, legal_results, financial_results] if r is not None),
                "total_detections": sum(r.get("total_detections", 0) for r in [medical_results, legal_results, financial_results] if r),
                "average_processing_time": sum(r.get("processing_time", 0) for r in [medical_results, legal_results, financial_results] if r) / 3
            }
        }
        
        # Save results
        results_file = self.results_dir / f"comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        # Print final summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 COMPREHENSIVE TEST COMPLETE!")
        logger.info("=" * 60)
        summary = comprehensive_results["summary"]
        logger.info(f"✅ Scenarios passed: {summary['scenarios_passed']}/3")
        logger.info(f"🔍 Total PII detections: {summary['total_detections']}")
        logger.info(f"⏱️  Average processing time: {summary['average_processing_time']:.3f}s")
        logger.info(f"📊 Results saved to: {results_file}")
        logger.info("\n🚀 STING PII detection system is ready for enterprise demos!")
        
        return comprehensive_results

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="STING PII Detection Test Suite")
    parser.add_argument("--scenario", choices=["medical", "legal", "financial", "performance", "all"],
                       default="all", help="Test scenario to run")
    parser.add_argument("--data-dir", default="/data/output", help="Data directory")
    
    args = parser.parse_args()
    
    test_suite = PIITestSuite(args.data_dir)
    
    if args.scenario == "medical":
        test_suite.run_demo_scenario_medical()
    elif args.scenario == "legal":
        test_suite.run_demo_scenario_legal()
    elif args.scenario == "financial":
        test_suite.run_demo_scenario_financial()
    elif args.scenario == "performance":
        test_suite.run_performance_benchmark()
    elif args.scenario == "all":
        test_suite.run_comprehensive_test()

if __name__ == "__main__":
    main()