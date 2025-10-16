#!/usr/bin/env python3
"""
Demo Data Generator for STING PII Detection
Generates realistic synthetic documents for medical and legal demonstrations
"""

import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
import re

@dataclass
class DemoPersona:
    """Represents a synthetic person for demo data"""
    first_name: str
    last_name: str
    ssn: str
    dob: str
    email: str
    phone: str
    address: str
    medical_record: str = ""
    insurance_id: str = ""
    
class MedicalDemoGenerator:
    """Generate realistic medical documents for HIPAA demo scenarios"""
    
    def __init__(self):
        self.first_names = [
            "John", "Jane", "Michael", "Sarah", "David", "Lisa", "Robert", "Emily",
            "William", "Ashley", "James", "Jessica", "Christopher", "Amanda", "Daniel", "Jennifer"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Jackson", "White", "Harris"
        ]
        
        self.medical_conditions = [
            "Type 2 Diabetes", "Hypertension", "Asthma", "Arthritis", "Depression",
            "Anxiety Disorder", "High Cholesterol", "Obesity", "Chronic Pain", "Insomnia"
        ]
        
        self.medications = [
            ("Metformin", "500mg", "twice daily"),
            ("Lisinopril", "10mg", "once daily"),
            ("Albuterol", "90mcg", "as needed"),
            ("Ibuprofen", "400mg", "three times daily"),
            ("Sertraline", "50mg", "once daily"),
            ("Atorvastatin", "20mg", "once daily"),
            ("Omeprazole", "20mg", "once daily")
        ]
        
        self.physicians = [
            ("Dr. Michael Johnson", "Internal Medicine", "NPI: 1234567890", "DEA: BJ1234567"),
            ("Dr. Sarah Williams", "Cardiology", "NPI: 2345678901", "DEA: SW2345678"),
            ("Dr. David Chen", "Psychiatry", "NPI: 3456789012", "DEA: DC3456789"),
            ("Dr. Lisa Rodriguez", "Family Medicine", "NPI: 4567890123", "DEA: LR4567890")
        ]
        
        self.hospitals = [
            "St. Mary's Medical Center",
            "General Hospital",
            "University Medical Center",
            "Community Health Center",
            "Regional Medical Center"
        ]
    
    def _generate_persona(self) -> DemoPersona:
        """Generate a synthetic person with medical identifiers"""
        first = random.choice(self.first_names)
        last = random.choice(self.last_names)
        
        # Generate realistic but fake SSN (avoid real ranges)
        ssn = f"999-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        
        # Generate DOB (18-80 years old)
        today = datetime.now()
        age = random.randint(18, 80)
        dob_date = today - timedelta(days=age*365 + random.randint(0, 365))
        dob = dob_date.strftime("%m/%d/%Y")
        
        # Generate contact info
        email = f"{first.lower()}.{last.lower()}@email.com"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        # Generate address
        street_num = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "Park Rd", "First St", "Second Ave", "Elm Dr"]
        address = f"{street_num} {random.choice(street_names)}, City, ST {random.randint(10000, 99999)}"
        
        # Generate medical identifiers
        mrn = f"MRN{random.randint(100000, 999999)}"
        insurance = f"{random.choice(['BC', 'AE', 'UH'])}{random.randint(100000000, 999999999)}"
        
        return DemoPersona(
            first_name=first,
            last_name=last,
            ssn=ssn,
            dob=dob,
            email=email,
            phone=phone,
            address=address,
            medical_record=mrn,
            insurance_id=insurance
        )
    
    def generate_patient_intake_form(self) -> str:
        """Generate a patient intake form with multiple PII types"""
        persona = self._generate_persona()
        
        return f"""
PATIENT INTAKE FORM
St. Mary's Medical Center
Date: {datetime.now().strftime('%m/%d/%Y')}

PATIENT INFORMATION:
Name: {persona.first_name} {persona.last_name}
Date of Birth: {persona.dob}
Social Security Number: {persona.ssn}
Medical Record Number: {persona.medical_record}
Phone Number: {persona.phone}
Email Address: {persona.email}

CURRENT ADDRESS:
{persona.address}

INSURANCE INFORMATION:
Primary Insurance: Blue Cross Blue Shield
Policy Number: {persona.insurance_id}
Group Number: {random.randint(100000, 999999)}

EMERGENCY CONTACT:
Name: {random.choice(self.first_names)} {random.choice(self.last_names)}
Relationship: Spouse
Phone: ({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}

MEDICAL HISTORY:
Current Medications:
- {self.medications[0][0]} {self.medications[0][1]} {self.medications[0][2]}
- {self.medications[1][0]} {self.medications[1][1]} {self.medications[1][2]}

Known Allergies: Penicillin, Latex

Previous Diagnoses:
- {random.choice(self.medical_conditions)} (ICD-10: {random.choice(['E11.9', 'I10', 'J45.9'])})
- {random.choice(self.medical_conditions)}

PHYSICIAN INFORMATION:
Referring Physician: {self.physicians[0][0]}
Specialty: {self.physicians[0][1]}
{self.physicians[0][2]}
{self.physicians[0][3]}

Patient Signature: _________________________ Date: ___________
"""
    
    def generate_lab_results(self) -> str:
        """Generate lab results with medical PII and clinical values"""
        persona = self._generate_persona()
        physician = random.choice(self.physicians)
        
        return f"""
LABORATORY RESULTS REPORT

Patient: {persona.first_name} {persona.last_name}
DOB: {persona.dob}
MRN: {persona.medical_record}
SSN: {persona.ssn}

Order Date: {datetime.now().strftime('%m/%d/%Y')}
Collection Date: {(datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')}
Report Date: {datetime.now().strftime('%m/%d/%Y')}

Ordering Physician: {physician[0]}
{physician[2]}

TEST RESULTS:

COMPLETE BLOOD COUNT (CBC)
- White Blood Cell Count: {random.randint(4000, 11000)} cells/mm3 (Normal: 4,000-11,000)
- Red Blood Cell Count: {random.uniform(4.2, 5.4):.1f} million cells/mm3 (Normal: 4.2-5.4)
- Hemoglobin: {random.uniform(12.0, 16.0):.1f} g/dL (Normal: 12.0-16.0)
- Hematocrit: {random.randint(36, 48)}% (Normal: 36-48%)

COMPREHENSIVE METABOLIC PANEL (CMP)
- Glucose: {random.randint(70, 140)} mg/dL (Normal: 70-100)
- Creatinine: {random.uniform(0.6, 1.3):.2f} mg/dL (Normal: 0.6-1.3)
- Blood Urea Nitrogen: {random.randint(7, 25)} mg/dL (Normal: 7-25)
- Sodium: {random.randint(136, 145)} mEq/L (Normal: 136-145)

LIPID PANEL
- Total Cholesterol: {random.randint(150, 250)} mg/dL (Normal: <200)
- HDL Cholesterol: {random.randint(40, 70)} mg/dL (Normal: >40)
- LDL Cholesterol: {random.randint(70, 160)} mg/dL (Normal: <100)
- Triglycerides: {random.randint(50, 200)} mg/dL (Normal: <150)

NOTES: All values within normal limits except elevated glucose.
Recommend follow-up with primary care physician.

Reviewed by: {physician[0]}, MD
Date: {datetime.now().strftime('%m/%d/%Y')}
"""
    
    def generate_prescription(self) -> str:
        """Generate prescription with DEA numbers and medication details"""
        persona = self._generate_persona()
        physician = random.choice(self.physicians)
        medication = random.choice(self.medications)
        
        return f"""
PRESCRIPTION

Patient Information:
Name: {persona.first_name} {persona.last_name}
Address: {persona.address}
Date of Birth: {persona.dob}
Phone: {persona.phone}

Prescriber Information:
{physician[0]}
St. Mary's Medical Center
123 Hospital Drive, Medical City, ST 12345
Phone: (555) 123-4567
{physician[3]}
{physician[2]}

Date: {datetime.now().strftime('%m/%d/%Y')}

Rx:
{medication[0]} {medication[1]}
Sig: Take {medication[2]} with food
Qty: 90 tablets
Refills: 2

Generic Substitution Permitted: Yes

Prescriber Signature: ________________________

DEA#: {physician[3].split(': ')[1]}
NPI#: {physician[2].split(': ')[1]}
"""

class LegalDemoGenerator:
    """Generate realistic legal documents for attorney-client privilege demos"""
    
    def __init__(self):
        self.law_firms = [
            "Smith & Associates",
            "Johnson, Williams & Brown LLP",
            "Legal Partners Group",
            "Metropolitan Law Offices",
            "Corporate Legal Services"
        ]
        
        self.attorneys = [
            ("James Mitchell", "Partner", "Bar #: 1234567"),
            ("Sarah Thompson", "Senior Associate", "Bar #: 2345678"),
            ("Michael Rodriguez", "Partner", "Bar #: 3456789"),
            ("Lisa Chen", "Associate", "Bar #: 4567890")
        ]
        
        self.case_types = [
            ("Personal Injury", "PI"),
            ("Corporate Law", "CL"),
            ("Family Law", "FL"),
            ("Criminal Defense", "CR"),
            ("Real Estate", "RE")
        ]
        
        self.courts = [
            "Superior Court of California",
            "U.S. District Court",
            "Family Court",
            "Municipal Court",
            "Circuit Court"
        ]
    
    def _generate_persona(self) -> DemoPersona:
        """Generate synthetic person for legal scenarios"""
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Lisa", "Robert", "Emily"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        
        first = random.choice(first_names)
        last = random.choice(last_names)
        
        ssn = f"999-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        today = datetime.now()
        age = random.randint(25, 70)
        dob_date = today - timedelta(days=age*365 + random.randint(0, 365))
        dob = dob_date.strftime("%m/%d/%Y")
        
        email = f"{first.lower()}.{last.lower()}@email.com"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        street_num = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "Park Rd", "First St", "Second Ave", "Elm Dr"]
        address = f"{street_num} {random.choice(street_names)}, City, ST {random.randint(10000, 99999)}"
        
        return DemoPersona(
            first_name=first,
            last_name=last,
            ssn=ssn,
            dob=dob,
            email=email,
            phone=phone,
            address=address
        )
    
    def generate_case_file(self) -> str:
        """Generate case file with legal PII and privileged information"""
        client = self._generate_persona()
        opposing = self._generate_persona()
        attorney = random.choice(self.attorneys)
        case_type = random.choice(self.case_types)
        court = random.choice(self.courts)
        
        case_number = f"{random.randint(2020, 2024)}-{case_type[1]}-{random.randint(100000, 999999)}"
        
        return f"""
CONFIDENTIAL - ATTORNEY-CLIENT PRIVILEGED

CASE FILE SUMMARY
{random.choice(self.law_firms)}

Case Number: {case_number}
Court: {court}
Case Type: {case_type[0]}
Filing Date: {datetime.now().strftime('%m/%d/%Y')}

CLIENT INFORMATION:
Name: {client.first_name} {client.last_name}
Address: {client.address}
Phone: {client.phone}
Email: {client.email}
SSN: {client.ssn}
Date of Birth: {client.dob}

OPPOSING PARTY:
Name: {opposing.first_name} {opposing.last_name}
Address: {opposing.address}
Phone: {opposing.phone}

ATTORNEY INFORMATION:
Lead Attorney: {attorney[0]}
Title: {attorney[1]}
{attorney[2]}
Firm: {random.choice(self.law_firms)}

CASE DETAILS:
Settlement Amount Sought: ${random.randint(50000, 500000):,}
Court Docket: {random.randint(2024, 2024)}-CV-{random.randint(10000, 99999)}

CONFIDENTIAL NOTES:
Client has expressed willingness to settle for ${random.randint(25000, 250000):,}.
Opposing counsel contacted regarding pre-trial settlement negotiations.
Key witness: {random.choice(['John', 'Jane'])} {random.choice(['Wilson', 'Anderson'])}

FINANCIAL INFORMATION:
Client's Annual Income: ${random.randint(40000, 120000):,}
Bank Account: {random.randint(100000000, 999999999)}
Trust Account ID: IOLTA-{random.randint(100000, 999999)}

This document contains attorney-client privileged information and work product.
Distribution limited to authorized personnel only.

Attorney Signature: _________________________
Date: {datetime.now().strftime('%m/%d/%Y')}
"""
    
    def generate_contract(self) -> str:
        """Generate contract with legal identifiers and financial terms"""
        party1 = self._generate_persona()
        party2 = self._generate_persona()
        
        contract_id = f"CTR-{random.randint(2024, 2024)}-{random.randint(1000, 9999)}"
        
        return f"""
SERVICE AGREEMENT

Contract ID: {contract_id}
Date: {datetime.now().strftime('%m/%d/%Y')}

PARTY 1 (Client):
Name: {party1.first_name} {party1.last_name}
Address: {party1.address}
Phone: {party1.phone}
Email: {party1.email}
SSN: {party1.ssn}

PARTY 2 (Service Provider):
Business Name: {random.choice(['ABC Consulting', 'Professional Services Inc', 'Business Solutions LLC'])}
Representative: {party2.first_name} {party2.last_name}
Address: {party2.address}
Phone: {party2.phone}
Email: {party2.email}
Tax ID: {random.randint(10, 99)}-{random.randint(1000000, 9999999)}

FINANCIAL TERMS:
Total Contract Value: ${random.randint(10000, 100000):,}
Payment Schedule: Monthly payments of ${random.randint(1000, 5000):,}
Bank Account for Payments: {random.randint(100000000, 999999999)}
Routing Number: {random.randint(100000000, 999999999)}

TERMS AND CONDITIONS:
1. Service period: 12 months from contract execution
2. Payment due within 30 days of invoice
3. Late payment penalty: 1.5% per month
4. Confidentiality provisions apply

Client Signature: _________________________
Date: ___________

Service Provider Signature: _________________________  
Date: ___________

Witness: {random.choice(['John', 'Jane'])} {random.choice(['Smith', 'Jones'])}
Notary Public ID: {random.randint(10000, 99999)}
"""

class FinancialDemoGenerator:
    """Generate financial documents for PCI-DSS compliance demos"""
    
    def generate_loan_application(self) -> str:
        """Generate loan application with financial PII"""
        applicant = self._generate_persona()
        
        return f"""
LOAN APPLICATION

Application Date: {datetime.now().strftime('%m/%d/%Y')}
Application ID: LA-{random.randint(100000, 999999)}

APPLICANT INFORMATION:
Full Name: {applicant.first_name} {applicant.last_name}
Social Security Number: {applicant.ssn}
Date of Birth: {applicant.dob}
Phone Number: {applicant.phone}
Email Address: {applicant.email}
Current Address: {applicant.address}

FINANCIAL INFORMATION:
Annual Income: ${random.randint(40000, 120000):,}
Employer: {random.choice(['Tech Corp', 'Medical Center', 'Manufacturing Inc', 'Retail Solutions'])}
Bank Account Number: {random.randint(100000000, 999999999)}
Routing Number: {random.randint(100000000, 999999999)}
Credit Card: 4532-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}

LOAN DETAILS:
Loan Amount Requested: ${random.randint(10000, 50000):,}
Loan Purpose: {random.choice(['Home improvement', 'Debt consolidation', 'Personal expenses'])}
Desired Term: {random.choice([24, 36, 48, 60])} months

I certify that the information provided is true and accurate.

Applicant Signature: _________________________
Date: ___________
"""
    
    def _generate_persona(self) -> DemoPersona:
        """Generate persona for financial scenarios"""
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Lisa"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
        
        first = random.choice(first_names)
        last = random.choice(last_names)
        
        ssn = f"999-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
        today = datetime.now()
        age = random.randint(25, 65)
        dob_date = today - timedelta(days=age*365 + random.randint(0, 365))
        dob = dob_date.strftime("%m/%d/%Y")
        
        email = f"{first.lower()}.{last.lower()}@email.com"
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        street_num = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "Park Rd"]
        address = f"{street_num} {random.choice(street_names)}, City, ST {random.randint(10000, 99999)}"
        
        return DemoPersona(
            first_name=first,
            last_name=last,
            ssn=ssn,
            dob=dob,
            email=email,
            phone=phone,
            address=address
        )

def generate_demo_dataset() -> Dict[str, List[str]]:
    """Generate a complete demo dataset with various document types"""
    medical_gen = MedicalDemoGenerator()
    legal_gen = LegalDemoGenerator()
    financial_gen = FinancialDemoGenerator()
    
    dataset = {
        "medical": [
            medical_gen.generate_patient_intake_form(),
            medical_gen.generate_lab_results(),
            medical_gen.generate_prescription(),
            medical_gen.generate_patient_intake_form(),  # Second sample
            medical_gen.generate_lab_results()  # Second sample
        ],
        "legal": [
            legal_gen.generate_case_file(),
            legal_gen.generate_contract(),
            legal_gen.generate_case_file(),  # Second sample
            legal_gen.generate_contract()  # Second sample
        ],
        "financial": [
            financial_gen.generate_loan_application(),
            financial_gen.generate_loan_application(),  # Second sample
        ]
    }
    
    return dataset

def save_demo_files(output_dir: str = "demo_data"):
    """Save demo files to disk for easy testing"""
    import os
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    dataset = generate_demo_dataset()
    
    for category, documents in dataset.items():
        category_dir = os.path.join(output_dir, category)
        os.makedirs(category_dir, exist_ok=True)
        
        for i, doc in enumerate(documents, 1):
            filename = f"{category}_sample_{i}.txt"
            filepath = os.path.join(category_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(doc)
            
            print(f"Generated: {filepath}")
    
    # Generate summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "categories": list(dataset.keys()),
        "total_documents": sum(len(docs) for docs in dataset.values()),
        "files_created": []
    }
    
    for category, documents in dataset.items():
        for i in range(len(documents)):
            summary["files_created"].append(f"{category}/demo_sample_{i+1}.txt")
    
    with open(os.path.join(output_dir, "summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✅ Generated {summary['total_documents']} demo documents in '{output_dir}/'")
    print("📋 Summary saved to summary.json")

if __name__ == "__main__":
    # Generate and save demo files
    save_demo_files()
    
    # Also generate sample to stdout for testing
    print("\n" + "="*60)
    print("SAMPLE MEDICAL DOCUMENT:")
    print("="*60)
    medical_gen = MedicalDemoGenerator()
    print(medical_gen.generate_patient_intake_form())