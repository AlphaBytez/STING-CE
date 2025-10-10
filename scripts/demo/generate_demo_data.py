#!/usr/bin/env python3
"""
Demo Data Generation Script for STING Platform

This script generates realistic demo data for testing and demonstration purposes.
It creates sample honey jars, documents, reports, and PII patterns.
"""

import os
import sys
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Sample data templates
SAMPLE_HONEY_JARS = [
    {
        "name": "Customer Support Tickets",
        "description": "Collection of customer support interactions and resolutions",
        "category": "customer_service",
        "tags": ["support", "tickets", "customer_service"]
    },
    {
        "name": "Product Documentation",
        "description": "Technical documentation and user guides",
        "category": "documentation",
        "tags": ["docs", "technical", "guides"]
    },
    {
        "name": "Marketing Materials",
        "description": "Marketing campaigns, copy, and promotional content",
        "category": "marketing",
        "tags": ["marketing", "campaigns", "content"]
    },
    {
        "name": "HR Policies",
        "description": "Human resources policies and procedures",
        "category": "hr",
        "tags": ["hr", "policies", "procedures"]
    },
    {
        "name": "Financial Reports",
        "description": "Quarterly and annual financial data",
        "category": "finance",
        "tags": ["finance", "reports", "quarterly"]
    },
    {
        "name": "Security Protocols",
        "description": "Security procedures and incident response plans",
        "category": "security",
        "tags": ["security", "protocols", "incident_response"]
    },
    {
        "name": "Research & Development",
        "description": "R&D projects and innovation documentation",
        "category": "research",
        "tags": ["research", "development", "innovation"]
    },
    {
        "name": "Legal Contracts",
        "description": "Legal agreements and contract templates",
        "category": "legal",
        "tags": ["legal", "contracts", "agreements"]
    }
]

SAMPLE_DOCUMENTS = [
    {
        "title": "Customer Onboarding Guide",
        "content": "Welcome to our platform! This guide will help you get started with all the essential features...",
        "type": "guide",
        "pii_patterns": ["email", "phone"]
    },
    {
        "title": "Security Incident Report - Q3 2024",
        "content": "Summary of security incidents for Q3 2024. Three minor incidents were detected and resolved...",
        "type": "report",
        "pii_patterns": ["ssn", "email"]
    },
    {
        "title": "Employee Handbook",
        "content": "This handbook outlines company policies, procedures, and benefits for all employees...",
        "type": "policy",
        "pii_patterns": ["phone", "address"]
    },
    {
        "title": "Data Privacy Assessment",
        "content": "Annual assessment of data privacy practices and GDPR compliance measures...",
        "type": "assessment",
        "pii_patterns": ["email", "ssn", "medical"]
    }
]

PII_PATTERNS = {
    "email": [
        "john.doe@company.com",
        "sarah.johnson@example.org",
        "michael.brown@testcorp.net",
        "lisa.wilson@demo.io"
    ],
    "phone": [
        "(555) 123-4567",
        "555-987-6543",
        "+1-555-246-8135",
        "555.159.7531"
    ],
    "ssn": [
        "123-45-6789",
        "987-65-4321",
        "555-12-3456",
        "111-22-3333"
    ],
    "address": [
        "123 Main Street, Anytown, ST 12345",
        "456 Oak Avenue, Springfield, IL 62701",
        "789 Pine Road, Hometown, CA 90210",
        "321 Elm Street, Smallville, KS 67001"
    ],
    "medical": [
        "Patient ID: MRN-123456",
        "Diagnosis Code: ICD-10-Z00.00",
        "DOB: 01/15/1980",
        "Insurance: Policy #ABC123456"
    ]
}

REPORT_TEMPLATES = [
    {
        "name": "Security Audit Report",
        "type": "security",
        "description": "Comprehensive security assessment and recommendations"
    },
    {
        "name": "PII Compliance Report",
        "type": "compliance",
        "description": "Review of PII handling and privacy compliance"
    },
    {
        "name": "Data Analytics Summary",
        "type": "analytics",
        "description": "Monthly data processing and insights summary"
    },
    {
        "name": "Performance Metrics",
        "type": "performance",
        "description": "System performance and optimization report"
    }
]

def generate_honey_jars(scenario: str, count: int = None) -> List[Dict[str, Any]]:
    """Generate sample honey jars based on scenario"""
    if count is None:
        count = {
            'basic': 5,
            'comprehensive': 20,
            'security-focused': 8,
            'pii-scrubbing': 3
        }.get(scenario, 5)
    
    jars = []
    selected_templates = random.sample(SAMPLE_HONEY_JARS, min(count, len(SAMPLE_HONEY_JARS)))
    
    for i, template in enumerate(selected_templates):
        jar = {
            "id": str(uuid.uuid4()),
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "tags": template["tags"],
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "document_count": random.randint(5, 25),
            "size_bytes": random.randint(1024*1024, 50*1024*1024),  # 1MB to 50MB
            "owner": "demo-user",
            "permissions": "public" if random.random() > 0.3 else "private"
        }
        
        # Add scenario-specific modifications
        if scenario == 'security-focused':
            jar["category"] = "security"
            jar["tags"].extend(["audit", "compliance", "security"])
        elif scenario == 'pii-scrubbing':
            jar["tags"].extend(["pii", "sensitive", "scrubbing"])
            
        jars.append(jar)
    
    return jars

def generate_documents(honey_jars: List[Dict], scenario: str) -> List[Dict[str, Any]]:
    """Generate sample documents for honey jars"""
    documents = []
    
    for jar in honey_jars:
        doc_count = jar.get("document_count", 10)
        
        for i in range(doc_count):
            doc_template = random.choice(SAMPLE_DOCUMENTS)
            
            # Generate content with PII patterns
            content = doc_template["content"]
            pii_injected = []
            
            if scenario in ['comprehensive', 'pii-scrubbing']:
                # Inject PII patterns into content
                for pattern_type in doc_template.get("pii_patterns", []):
                    if pattern_type in PII_PATTERNS:
                        pii_value = random.choice(PII_PATTERNS[pattern_type])
                        content += f" Contact information: {pii_value}"
                        pii_injected.append(pattern_type)
            
            document = {
                "id": str(uuid.uuid4()),
                "honey_jar_id": jar["id"],
                "title": f"{doc_template['title']} #{i+1}",
                "content": content,
                "type": doc_template["type"],
                "size_bytes": len(content.encode('utf-8')),
                "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "pii_detected": pii_injected if scenario == 'pii-scrubbing' else [],
                "processed": random.random() > 0.2,  # 80% processed
                "metadata": {
                    "source": "demo_generator",
                    "category": jar["category"],
                    "sensitivity": "medium" if pii_injected else "low"
                }
            }
            
            documents.append(document)
    
    return documents

def generate_reports(scenario: str, count: int = None) -> List[Dict[str, Any]]:
    """Generate sample reports"""
    if count is None:
        count = {
            'basic': 10,
            'comprehensive': 50,
            'security-focused': 15,
            'pii-scrubbing': 5
        }.get(scenario, 10)
    
    reports = []
    
    for i in range(count):
        template = random.choice(REPORT_TEMPLATES)
        
        # Generate realistic report data
        status = random.choice(['completed', 'processing', 'failed'])
        created_date = datetime.now() - timedelta(days=random.randint(0, 60))
        
        report = {
            "id": str(uuid.uuid4()),
            "title": f"{template['name']} - {created_date.strftime('%B %Y')}",
            "type": template["type"],
            "description": template["description"],
            "status": status,
            "created_at": created_date.isoformat(),
            "completed_at": (created_date + timedelta(minutes=random.randint(5, 120))).isoformat() if status == 'completed' else None,
            "size_bytes": random.randint(1024, 10*1024*1024),  # 1KB to 10MB
            "metadata": {
                "generator": "demo_data_script",
                "version": "1.0",
                "scenario": scenario,
                "processing_time_seconds": random.randint(30, 1800)
            }
        }
        
        # Add scenario-specific data
        if scenario == 'security-focused' and template["type"] == "security":
            report["metadata"]["findings"] = random.randint(0, 5)
            report["metadata"]["severity"] = random.choice(["low", "medium", "high"])
        elif scenario == 'pii-scrubbing':
            report["metadata"]["pii_items_found"] = random.randint(0, 100)
            report["metadata"]["scrubbed_items"] = random.randint(0, report["metadata"]["pii_items_found"])
        
        reports.append(report)
    
    return reports

def save_demo_data(data: Dict[str, Any], scenario: str):
    """Save generated demo data to files"""
    output_dir = os.path.join(os.path.dirname(__file__), 'generated')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"demo_data_{scenario}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Demo data saved to: {filepath}")
    return filepath

def main():
    parser = argparse.ArgumentParser(description='Generate demo data for STING platform')
    parser.add_argument('--scenario', choices=['basic', 'comprehensive', 'security-focused', 'pii-scrubbing'], 
                       default='basic', help='Demo scenario to generate')
    parser.add_argument('--output', help='Output file path (optional)')
    parser.add_argument('--honey-jars', type=int, help='Number of honey jars to generate')
    parser.add_argument('--reports', type=int, help='Number of reports to generate')
    
    args = parser.parse_args()
    
    print(f"Generating demo data for scenario: {args.scenario}")
    
    # Generate data
    honey_jars = generate_honey_jars(args.scenario, args.honey_jars)
    documents = generate_documents(honey_jars, args.scenario)
    reports = generate_reports(args.scenario, args.reports)
    
    demo_data = {
        "scenario": args.scenario,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "honey_jars": len(honey_jars),
            "documents": len(documents),
            "reports": len(reports),
            "total_size_bytes": sum(doc.get("size_bytes", 0) for doc in documents + reports)
        },
        "honey_jars": honey_jars,
        "documents": documents,
        "reports": reports,
        "pii_patterns": PII_PATTERNS if args.scenario in ['comprehensive', 'pii-scrubbing'] else {}
    }
    
    # Save data
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(demo_data, f, indent=2, ensure_ascii=False)
        print(f"Demo data saved to: {args.output}")
    else:
        save_demo_data(demo_data, args.scenario)
    
    # Print summary
    print("\nDemo Data Generation Summary:")
    print(f"  Scenario: {args.scenario}")
    print(f"  Honey Jars: {len(honey_jars)}")
    print(f"  Documents: {len(documents)}")
    print(f"  Reports: {len(reports)}")
    print(f"  Total Size: {demo_data['summary']['total_size_bytes'] / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()