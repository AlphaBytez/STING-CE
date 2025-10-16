#!/usr/bin/env python3
"""
Upload Comprehensive STING Documentation for Law Firm POC
Creates honey jars with complete STING knowledge including enterprise features,
business overview, and law firm specific use cases.
"""

import os
import sys
import json
import requests
import tempfile
import uuid
from pathlib import Path

def get_session_token(email="admin@sting.local", password="Password1!"):
    """Get authentication token"""
    try:
        session = requests.Session()
        session.verify = False
        
        # Initialize login flow
        flow_response = session.get("https://localhost:4433/self-service/login/api")
        if flow_response.status_code != 200:
            return None
            
        flow_data = flow_response.json()
        flow_id = flow_data["id"]
        
        # Submit login
        login_data = {
            "method": "password",
            "password": password,
            "password_identifier": email
        }
        
        login_response = session.post(
            f"https://localhost:4433/self-service/login?flow={flow_id}",
            json=login_data
        )
        
        if login_response.status_code == 200:
            response_data = login_response.json()
            return response_data.get('session_token')
        return None
    except:
        return None

def create_honey_jar(name, description, session_token):
    """Create honey jar"""
    headers = {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}
    data = {"name": name, "description": description, "type": "public"}
    
    try:
        response = requests.post("http://localhost:8090/honey-jars", json=data, headers=headers)
        if response.status_code == 200:
            return response.json().get('id')
    except:
        pass
    return None

def upload_document(jar_id, file_path, session_token):
    """Upload individual document"""
    if not os.path.exists(file_path):
        return False
        
    headers = {"Authorization": f"Bearer {session_token}"}
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'text/markdown')}
            data = {'tags': ['documentation', 'enterprise', 'law-firm']}
            
            response = requests.post(
                f"http://localhost:8090/honey-jars/{jar_id}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"  ✅ {filename}")
                return True
            else:
                print(f"  ❌ {filename}: {response.status_code}")
                return False
    except Exception as e:
        print(f"  ❌ {filename}: {e}")
        return False

def upload_comprehensive_docs():
    """Upload comprehensive STING documentation for law firm POC"""
    print("🏛️ Uploading STING Documentation for Law Firm POC")
    print("=" * 60)
    
    # Get authentication
    print("🔐 Authenticating...")
    session_token = get_session_token()
    if not session_token:
        print("❌ Authentication failed")
        return False
    print("✅ Authenticated successfully")
    
    # Create comprehensive honey jar
    print("\n🍯 Creating comprehensive STING knowledge base...")
    jar_id = create_honey_jar(
        "STING Enterprise Documentation",
        "Complete STING platform documentation including enterprise features, business overview, and law firm applications",
        session_token
    )
    
    if not jar_id:
        print("❌ Failed to create honey jar")
        return False
    print(f"✅ Created honey jar: {jar_id}")
    
    # Document categories for law firm knowledge
    doc_categories = {
        "Core Platform": [
            "docs/STING_QUICK_REFERENCE.md",
            "docs/ARCHITECTURE.md", 
            "docs/INSTALLATION.md",
            "docs/API_REFERENCE.md"
        ],
        "Business & Enterprise": [
            "docs/BUSINESS_OVERVIEW.md",
            "docs/STING_TECHNICAL_WHITEPAPER.md",
            "docs/sales/SALES_PITCH_DECK.md"
        ],
        "Security & Compliance": [
            "docs/security/authentication-requirements.md",
            "docs/features/PII_DETECTION_SYSTEM.md",
            "docs/features/DATA_PROTECTION_ARCHITECTURE.md"
        ],
        "Features & Guides": [
            "docs/features/HONEY_JAR_USER_GUIDE.md",
            "docs/guides/AI_ASSISTANT.md",
            "docs/BEE_AGENTIC_CAPABILITIES.md"
        ]
    }
    
    total_uploaded = 0
    
    for category, files in doc_categories.items():
        print(f"\n📁 {category}:")
        category_count = 0
        for file_path in files:
            if upload_document(jar_id, file_path, session_token):
                category_count += 1
                total_uploaded += 1
        print(f"   Uploaded {category_count}/{len(files)} documents")
    
    # Create law firm specific content
    print(f"\n📋 Creating law firm specific content...")
    law_firm_content = """# STING for Law Firms: Comprehensive Guide

## Executive Summary

STING (Secure Trusted Intelligence and Networking Guardian) provides law firms with enterprise-grade AI capabilities while maintaining the highest standards of client confidentiality and regulatory compliance.

## Key Benefits for Law Firms

### 1. **Client Confidentiality & Privilege Protection**
- **Complete On-Premises Deployment**: All data remains within your infrastructure
- **Zero External Dependencies**: No data ever leaves your firm
- **Attorney-Client Privilege Safeguards**: Built-in protections for privileged communications
- **Document Classification**: Automatic identification and protection of sensitive legal documents

### 2. **Regulatory Compliance**
- **GDPR Compliant**: Full European data protection compliance
- **State Bar Requirements**: Meets confidentiality requirements in all US jurisdictions
- **Audit Trails**: Comprehensive logging for regulatory reporting
- **Data Retention Policies**: Automated compliance with document retention requirements

### 3. **Legal Practice Enhancement**
- **Contract Analysis**: AI-powered contract review and risk identification
- **Legal Research**: Intelligent search across case law, statutes, and firm knowledge
- **Brief Generation**: AI-assisted legal writing and document preparation
- **Case Strategy**: Pattern analysis across similar cases and outcomes

### 4. **Knowledge Management**
- **Firm Expertise Capture**: Preserve and share institutional knowledge
- **Precedent Library**: Searchable database of successful strategies and documents
- **Client Matter Organization**: Secure, organized access to all case materials
- **Cross-Practice Collaboration**: Safe knowledge sharing between practice groups

## Technical Architecture for Law Firms

### Security First Design
- **End-to-End Encryption**: All data encrypted at rest and in transit
- **Role-Based Access**: Granular permissions for different staff levels
- **Secure Authentication**: Multi-factor authentication with passkey support
- **Network Isolation**: Complete air-gapped deployment options available

### Scalability & Performance
- **Multi-Tenant Architecture**: Support for multiple practice groups
- **High Availability**: 99.9% uptime with disaster recovery
- **Scalable Processing**: Handle large document volumes efficiently
- **Integration Ready**: APIs for existing practice management systems

## Use Cases by Practice Area

### **Corporate Law**
- Contract analysis and risk assessment
- M&A due diligence document review
- Regulatory compliance monitoring
- Corporate governance documentation

### **Litigation**
- Discovery document analysis
- Legal precedent research
- Brief writing assistance  
- Case strategy development

### **Real Estate**
- Property document review
- Title analysis and verification
- Lease agreement optimization
- Zoning and compliance research

### **Intellectual Property**
- Patent and trademark research
- IP portfolio management
- Prior art analysis
- Filing deadline tracking

### **Employment Law**
- Policy development and review
- Compliance monitoring
- Investigation documentation
- Training material creation

## Implementation Options

### **Standard Deployment**
- On-premises installation
- 50-500 attorneys
- Full feature access
- Standard support

### **Enterprise Deployment** 
- Multi-office support
- 500+ attorneys
- Custom integrations
- Dedicated support team

### **Cloud Hybrid**
- Private cloud deployment
- Enhanced security options
- Disaster recovery included
- 24/7 monitoring

## Competitive Advantages

### **vs. Public AI Services**
- **Client Data Security**: Never exposed to external services
- **Regulatory Compliance**: Built for legal industry requirements
- **Customization**: Tailored to legal workflows and terminology

### **vs. Traditional Legal Tech**
- **Modern AI Capabilities**: Latest language models and AI techniques
- **Unified Platform**: Single solution for multiple legal tech needs
- **Cost Effective**: Reduce multiple vendor relationships

## Investment & ROI

### **Cost Savings**
- Reduce external counsel fees by 30-40%
- Increase attorney productivity by 25%
- Minimize compliance violations and penalties
- Streamline document review processes

### **Revenue Enhancement**
- Faster case resolution
- Higher quality work product
- Expanded service capabilities
- Improved client satisfaction

### **Risk Reduction**
- Enhanced confidentiality protection
- Automated compliance monitoring
- Reduced human error in document review
- Comprehensive audit capabilities

## Getting Started

### **Phase 1: Assessment** (2-4 weeks)
- Infrastructure evaluation
- Security requirements review
- Practice area prioritization
- Integration planning

### **Phase 2: Pilot** (4-6 weeks)
- Single practice group deployment
- Core staff training
- Basic workflow integration
- Success metrics establishment

### **Phase 3: Full Deployment** (8-12 weeks)
- Firm-wide rollout
- Advanced feature enablement
- Custom integration completion
- Comprehensive staff training

## Support & Training

### **Implementation Support**
- Dedicated project manager
- Technical integration assistance
- Security configuration review
- Performance optimization

### **Ongoing Support**
- 24/7 technical support
- Regular system updates
- Security monitoring
- Performance reporting

### **Training Programs**
- Administrator certification
- Attorney user training
- Support staff education
- Best practices workshops

## Conclusion

STING represents the future of legal technology: powerful AI capabilities combined with the security, compliance, and confidentiality requirements of the legal profession. By deploying STING, law firms can maintain their competitive edge while ensuring client data remains absolutely secure and confidential.

**Contact us today to schedule a confidential demonstration and see how STING can transform your legal practice while maintaining the highest ethical and security standards.**
"""
    
    # Save law firm guide to temporary file and upload
    law_firm_file = "/tmp/sting_law_firm_guide.md"
    with open(law_firm_file, 'w') as f:
        f.write(law_firm_content)
    
    if upload_document(jar_id, law_firm_file, session_token):
        total_uploaded += 1
    os.unlink(law_firm_file)
    
    print(f"\n🎉 Upload Complete!")
    print(f"   Total documents uploaded: {total_uploaded}")
    print(f"   Honey jar ID: {jar_id}")
    print(f"\n💡 Test Query: Ask Bee Chat:")
    print(f"   'Hi Bee! What is STING and how can it help my law firm?'")
    print(f"\n   Bee should now provide comprehensive information about:")
    print(f"   • Enterprise security features")
    print(f"   • Legal industry compliance")
    print(f"   • Attorney-client privilege protection")
    print(f"   • Specific law firm use cases")
    print(f"   • ROI and competitive advantages")
    
    return True

if __name__ == "__main__":
    success = upload_comprehensive_docs()
    sys.exit(0 if success else 1)