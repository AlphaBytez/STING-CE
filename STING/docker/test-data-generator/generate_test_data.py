#!/usr/bin/env python3
"""
Containerized Test Data Generator for STING
Generates enterprise-scale synthetic test data for PII detection demos
"""

import os
import sys
import json
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContainerizedTestDataGenerator:
    """Generate test data in containerized environment"""
    
    def __init__(self, output_dir="/data/output"):
        self.output_dir = Path(output_dir)
        self.medical_dir = self.output_dir / "medical"
        self.legal_dir = self.output_dir / "legal"
        self.financial_dir = self.output_dir / "financial"
        
        # Create directories
        for dir_path in [self.medical_dir, self.legal_dir, self.financial_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def generate_medical_data(self, num_patients=1000):
        """Generate medical data using Synthea"""
        logger.info(f"🏥 Generating {num_patients} synthetic patients with Synthea...")
        
        try:
            # Run Synthea from its directory
            synthea_cmd = [
                "./run_synthea",
                "-p", str(num_patients),
                "--exporter.fhir.export=false",
                "--exporter.csv.export=true",
                f"--exporter.baseDirectory=/data/output/medical"
            ]
            
            # Change to synthea directory and run
            result = subprocess.run(
                synthea_cmd,
                cwd="/app/synthea",
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Medical data generation completed successfully")
                
                # Count generated files
                csv_files = list(self.medical_dir.glob("**/*.csv"))
                logger.info(f"📊 Generated {len(csv_files)} CSV files")
                
                return len(csv_files)
            else:
                logger.error(f"❌ Synthea failed: {result.stderr}")
                return 0
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Synthea generation timed out")
            return 0
        except Exception as e:
            logger.error(f"❌ Error generating medical data: {e}")
            return 0
    
    def generate_legal_data(self, num_documents=500):
        """Generate legal documents using STING's legal generator"""
        logger.info(f"⚖️  Generating {num_documents} legal documents...")
        
        try:
            # Import the legal generator (embedded version)
            legal_docs = self._create_legal_documents(num_documents)
            
            # Save documents
            for i, doc in enumerate(legal_docs):
                doc_type = "case_file" if i % 2 == 0 else "contract"
                filename = f"{doc_type}_{i+1:04d}.txt"
                filepath = self.legal_dir / filename
                
                with open(filepath, 'w') as f:
                    f.write(doc)
            
            logger.info(f"✅ Generated {len(legal_docs)} legal documents")
            return len(legal_docs)
            
        except Exception as e:
            logger.error(f"❌ Error generating legal data: {e}")
            return 0
    
    def generate_financial_data(self, num_records=1000):
        """Generate financial documents"""
        logger.info(f"💳 Generating {num_records} financial records...")
        
        try:
            # Generate loan applications
            financial_docs = self._create_financial_documents(num_records)
            
            # Save individual documents
            for i, doc in enumerate(financial_docs):
                filename = f"loan_application_{i+1:05d}.txt"
                filepath = self.financial_dir / filename
                
                with open(filepath, 'w') as f:
                    f.write(doc)
            
            # Also create CSV version
            df_data = []
            for i, doc in enumerate(financial_docs):
                df_data.append({
                    'id': i+1,
                    'document_type': 'loan_application',
                    'content': doc
                })
            
            df = pd.DataFrame(df_data)
            df.to_csv(self.financial_dir / "synthetic_financial_records.csv", index=False)
            
            logger.info(f"✅ Generated {len(financial_docs)} financial documents")
            return len(financial_docs)
            
        except Exception as e:
            logger.error(f"❌ Error generating financial data: {e}")
            return 0
    
    def _create_legal_documents(self, num_docs):
        """Embedded legal document generator"""
        from faker import Faker
        import random
        
        fake = Faker()
        documents = []
        
        law_firms = [
            "Smith & Associates",
            "Johnson, Williams & Brown LLP", 
            "Legal Partners Group",
            "Metropolitan Law Offices"
        ]
        
        for i in range(num_docs):
            if i % 2 == 0:
                # Generate case file
                case_number = f"{random.randint(2020, 2024)}-PI-{random.randint(100000, 999999)}"
                settlement = f"${random.randint(50000, 500000):,}"
                
                doc = f"""
CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGED

CASE FILE SUMMARY
{random.choice(law_firms)}

Case Number: {case_number}
Filing Date: {fake.date_this_year()}

CLIENT INFORMATION:
Name: {fake.name()}
Address: {fake.address()}
Phone: {fake.phone_number()}
Email: {fake.email()}
SSN: {fake.ssn()}

CASE DETAILS:
Settlement Amount Sought: {settlement}
Court Docket: {random.randint(2024, 2024)}-CV-{random.randint(10000, 99999)}

CONFIDENTIAL NOTES:
Client has expressed willingness to settle for ${random.randint(25000, 250000):,}.
Key witness: {fake.name()}

Attorney Signature: _________________________
Date: {fake.date_this_year()}
"""
            else:
                # Generate contract
                contract_id = f"CTR-{random.randint(2024, 2024)}-{random.randint(1000, 9999)}"
                
                doc = f"""
SERVICE AGREEMENT

Contract ID: {contract_id}
Date: {fake.date_this_year()}

PARTY 1 (Client):
Name: {fake.name()}
Address: {fake.address()}
Phone: {fake.phone_number()}
Email: {fake.email()}
SSN: {fake.ssn()}

FINANCIAL TERMS:
Total Contract Value: ${random.randint(10000, 100000):,}
Payment Schedule: Monthly payments of ${random.randint(1000, 5000):,}
Bank Account: {fake.bban()}

Client Signature: _________________________
Date: ___________
"""
            
            documents.append(doc.strip())
        
        return documents
    
    def _create_financial_documents(self, num_docs):
        """Embedded financial document generator"""
        from faker import Faker
        import random
        
        fake = Faker()
        documents = []
        
        for i in range(num_docs):
            doc = f"""
LOAN APPLICATION

Application Date: {fake.date_this_year()}
Application ID: LA-{random.randint(100000, 999999)}

APPLICANT INFORMATION:
Full Name: {fake.name()}
Social Security Number: {fake.ssn()}
Date of Birth: {fake.date_of_birth(minimum_age=18, maximum_age=80)}
Phone Number: {fake.phone_number()}
Email Address: {fake.email()}
Current Address: {fake.address()}

FINANCIAL INFORMATION:
Annual Income: ${random.randint(40000, 120000):,}
Employer: {fake.company()}
Bank Account Number: {fake.bban()}
Credit Card: {fake.credit_card_number(card_type='visa')}

LOAN DETAILS:
Loan Amount Requested: ${random.randint(10000, 50000):,}
Loan Purpose: {random.choice(['Home improvement', 'Debt consolidation', 'Personal expenses'])}
Desired Term: {random.choice([24, 36, 48, 60])} months

Applicant Signature: _________________________
Date: ___________
"""
            documents.append(doc.strip())
        
        return documents
    
    def create_summary(self, medical_files, legal_files, financial_files):
        """Create summary of generated data"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "container_version": "1.0",
            "datasets": {
                "medical": {
                    "source": "Synthea synthetic patient generator",
                    "files_generated": medical_files,
                    "location": "/data/output/medical/",
                    "estimated_pii_elements": medical_files * 25,
                    "compliance": ["HIPAA"]
                },
                "legal": {
                    "source": "STING embedded legal generator",
                    "files_generated": legal_files,
                    "location": "/data/output/legal/",
                    "estimated_pii_elements": legal_files * 15,
                    "compliance": ["Attorney-Client Privilege"]
                },
                "financial": {
                    "source": "STING embedded financial generator",
                    "files_generated": financial_files,
                    "location": "/data/output/financial/",
                    "estimated_pii_elements": financial_files * 12,
                    "compliance": ["PCI-DSS", "GDPR"]
                }
            },
            "total_estimated_pii": medical_files * 25 + legal_files * 15 + financial_files * 12
        }
        
        # Save summary
        with open(self.output_dir / "generation_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary

def main():
    """Main generation function"""
    logger.info("🎯 STING Containerized Test Data Generation Starting...")
    
    # Get parameters from environment or use defaults
    num_patients = int(os.environ.get('NUM_PATIENTS', 1000))
    num_legal_docs = int(os.environ.get('NUM_LEGAL_DOCS', 500))
    num_financial_records = int(os.environ.get('NUM_FINANCIAL_RECORDS', 1000))
    
    generator = ContainerizedTestDataGenerator()
    
    # Generate all data types
    medical_files = generator.generate_medical_data(num_patients)
    legal_files = generator.generate_legal_data(num_legal_docs)
    financial_files = generator.generate_financial_data(num_financial_records)
    
    # Create summary
    summary = generator.create_summary(medical_files, legal_files, financial_files)
    
    # Print results
    logger.info("\n" + "="*60)
    logger.info("🎉 TEST DATA GENERATION COMPLETE!")
    logger.info("="*60)
    logger.info(f"🏥 Medical Files: {medical_files}")
    logger.info(f"⚖️  Legal Files: {legal_files}")
    logger.info(f"💳 Financial Files: {financial_files}")
    logger.info(f"🔍 Total Estimated PII Elements: {summary['total_estimated_pii']:,}")
    logger.info(f"📁 Output Directory: /data/output")
    logger.info("📋 Summary saved to: /data/output/generation_summary.json")
    logger.info("\n✅ Ready for enterprise-scale PII detection testing!")

if __name__ == "__main__":
    main()