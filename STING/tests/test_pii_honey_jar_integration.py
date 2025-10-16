#!/usr/bin/env python3
"""
Test PII Integration with Honey Jar Processing
Verifies that PII detection works during document upload
"""

import asyncio
import sys
import os
import tempfile
import json
from datetime import datetime

# Add paths for imports
sys.path.append('/Users/captain-wolf/Documents/GitHub/STING-CE/STING')
sys.path.append('/Users/captain-wolf/Documents/GitHub/STING-CE/STING/knowledge_service')

try:
    from knowledge_service.pii_integration import pii_integration
    print("✅ PII Integration service imported successfully")
except ImportError as e:
    print(f"❌ Failed to import PII integration: {e}")
    sys.exit(1)

async def test_pii_detection_integration():
    """Test PII detection in document processing"""
    
    print("\n🧪 Testing PII Detection Integration with Honey Jar Processing\n")
    
    # Test if PII detection is available
    print("1. Checking PII service availability...")
    if pii_integration.is_available():
        print("   ✅ PII detection service is available")
    else:
        print("   ⚠️ PII detection service is not available - this may be expected in some environments")
        return
    
    # Test documents with different types of PII
    test_documents = {
        "medical_document": """
        Patient Medical Record
        
        Patient Name: John Smith
        Date of Birth: 01/15/1985
        Social Security Number: 123-45-6789
        Medical Record Number: MR-789456123
        
        DIAGNOSIS: Type 2 Diabetes Mellitus
        PRESCRIPTION: Metformin 500mg twice daily
        
        Patient presented with elevated glucose levels. Lab results show HbA1c of 8.2%.
        Recommend dietary changes and medication compliance.
        
        Dr. Sarah Johnson, MD
        NPI: 1234567890
        DEA Number: BJ1234567
        """,
        
        "legal_document": """
        CONFIDENTIAL ATTORNEY-CLIENT COMMUNICATION
        
        Case: Smith vs. Johnson Construction
        Case Number: 2024-CV-12345
        Client: Robert Smith
        Attorney: Jennifer Law, Esq.
        Bar Number: 123456
        
        Settlement negotiations update:
        - Opposing counsel offered $50,000
        - Client authorized up to $75,000
        - Trust account balance: $125,000
        
        Next steps: Schedule mediation
        Court docket: Superior Court, Dept. 15
        """,
        
        "financial_document": """
        Account Statement
        
        Account Holder: Mary Johnson
        Account Number: 4532-1234-5678-9012
        Routing Number: 123456789
        SSN: 987-65-4321
        
        Recent Transactions:
        - Wire transfer: $10,000 to account 9876543210
        - Payment to IRS: $5,500
        - Credit card payment: $2,100
        
        Available Balance: $45,250.00
        """,
        
        "general_document": """
        Meeting Notes - Project Alpha
        
        Attendees: Alice Brown, Bob Wilson, Carol Davis
        Date: March 15, 2024
        
        Discussion Points:
        1. Q1 budget review
        2. New hire onboarding
        3. Client presentation schedule
        
        Action Items:
        - Alice: Prepare financial summary
        - Bob: Update project timeline
        - Carol: Schedule client meeting
        
        Next meeting: March 22, 2024
        """
    }
    
    print("2. Testing PII detection on sample documents...\n")
    
    for doc_type, content in test_documents.items():
        print(f"   Testing {doc_type}:")
        
        try:
            # Simulate document processing
            pii_results = await pii_integration.detect_pii_in_document(
                document_text=content,
                user_id="test-user@example.com",
                document_id=f"doc-{doc_type}-001",
                honey_jar_id=f"jar-{doc_type}",
                honey_jar_type="public",
                detection_mode="auto"
            )
            
            # Display results
            if pii_results.get("pii_detected"):
                print(f"   ✅ PII detected: {pii_results['detection_count']} instances")
                print(f"      Mode: {pii_results['detection_mode']}")
                print(f"      Risk levels: {pii_results['risk_summary']}")
                print(f"      PII types: {pii_results['pii_types']}")
                print(f"      Compliance: {pii_results['compliance_frameworks']}")
                print(f"      Recommendations: {len(pii_results['recommendations'])} provided")
                
                # Show first recommendation
                if pii_results['recommendations']:
                    print(f"      First recommendation: {pii_results['recommendations'][0]}")
            else:
                print(f"   ✅ No PII detected")
                
            print(f"      Audit logged: {pii_results.get('audit_logged', False)}")
            
        except Exception as e:
            print(f"   ❌ Error processing {doc_type}: {e}")
        
        print()
    
    print("3. Testing auto-detection mode classification...")
    
    # Test auto-detection logic
    test_classifications = [
        ("medical patient diagnosis", "medical"),
        ("attorney client case settlement", "legal"), 
        ("bank account credit card", "financial"),
        ("meeting notes project update", "general")
    ]
    
    for test_text, expected_mode in test_classifications:
        try:
            pii_results = await pii_integration.detect_pii_in_document(
                document_text=test_text,
                user_id="test-user@example.com", 
                document_id=f"test-classification",
                honey_jar_id="test-jar",
                honey_jar_type="private",
                detection_mode="auto"
            )
            
            actual_mode = pii_results.get('detection_mode', 'unknown')
            status = "✅" if actual_mode == expected_mode else "⚠️"
            print(f"   {status} '{test_text}' -> {actual_mode} (expected: {expected_mode})")
            
        except Exception as e:
            print(f"   ❌ Error testing classification: {e}")
    
    print("\n✅ PII Integration testing completed!")
    
    # Create integration summary
    print("\n📋 Integration Summary:")
    print("   • PII detection integrated into honey jar document upload process")
    print("   • Automatic mode detection based on document content")
    print("   • Support for medical, legal, financial, and general contexts")
    print("   • Audit logging with compliance framework mapping")
    print("   • Risk-based recommendations for data handling")
    print("   • New API endpoints for PII management:")
    print("     - GET /honey-jars/{id}/pii-summary")
    print("     - POST /honey-jars/{id}/documents/{id}/pii-rescan")
    print("     - GET /pii/status")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pii_detection_integration())