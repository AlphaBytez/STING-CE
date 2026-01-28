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

    def generate_client_memo(self) -> str:
        """Generate attorney-client privileged memo"""
        client = self._generate_persona()
        attorney = random.choice(self.attorneys)
        firm = random.choice(self.law_firms)
        
        return f"""
PRIVILEGED AND CONFIDENTIAL
ATTORNEY-CLIENT COMMUNICATION

{firm}
{attorney[0]}, {attorney[1]}
{attorney[2]}

MEMO TO FILE

Date: {datetime.now().strftime('%m/%d/%Y')}
Matter: {random.choice(self.case_types)[0]} Matter
Client: {client.first_name} {client.last_name}
Client SSN: {client.ssn}
Client DOB: {client.dob}
Client Address: {client.address}

RE: Legal Strategy Discussion

This memorandum documents our privileged discussion with the client regarding 
their legal matter. The following points were addressed:

1. Review of current case status and pending deadlines
2. Discussion of settlement options and potential outcomes
3. Client authorization for document discovery
4. Review of billing and retainer status

BILLING INFORMATION:
Current Retainer Balance: ${random.randint(5000, 25000):,}
Hourly Rate: ${random.randint(250, 500)}/hour
Hours Billed to Date: {random.randint(10, 100)}
Total Fees: ${random.randint(5000, 50000):,}

CLIENT FINANCIAL INFO (for billing purposes):
Bank Account: {random.randint(100000000, 999999999)}
Credit Card on File: 4111-XXXX-XXXX-{random.randint(1000, 9999)}

CONFIDENTIALITY NOTICE:
This memorandum contains privileged attorney-client information and 
attorney work product. Unauthorized disclosure is prohibited.

Prepared by: {attorney[0]}
{attorney[2]}
"""

    def generate_nda(self) -> str:
        """Generate Non-Disclosure Agreement"""
        party1 = self._generate_persona()
        party2 = self._generate_persona()
        
        nda_id = f"NDA-{random.randint(2024, 2024)}-{random.randint(10000, 99999)}"
        
        return f"""
NON-DISCLOSURE AGREEMENT

Agreement ID: {nda_id}
Effective Date: {datetime.now().strftime('%m/%d/%Y')}

DISCLOSING PARTY:
Company: {random.choice(['Innovation Labs', 'TechStart Inc', 'SecureCorp'])}
Representative: {party1.first_name} {party1.last_name}
Title: {random.choice(['CEO', 'CTO', 'VP of Business Development'])}
Address: {party1.address}
Email: {party1.email}
Phone: {party1.phone}
Tax ID: {random.randint(10, 99)}-{random.randint(1000000, 9999999)}

RECEIVING PARTY:
Name: {party2.first_name} {party2.last_name}
SSN: {party2.ssn}
Address: {party2.address}
Email: {party2.email}
Phone: {party2.phone}

TERMS:
1. Duration: {random.randint(2, 5)} years from effective date
2. Scope: All business, technical, and financial information
3. Penalty for breach: ${random.randint(100000, 500000):,}

The Receiving Party agrees to maintain strict confidentiality of all 
proprietary information shared by the Disclosing Party, including but 
not limited to trade secrets, business strategies, financial data, 
customer lists, and technical specifications.

SIGNATURES:

Disclosing Party: _________________________
Date: ___________

Receiving Party: _________________________
Date: ___________

Witness: _________________________
Date: ___________

Notarized by: {random.choice(['John', 'Jane'])} {random.choice(['Smith', 'Jones'])}, Notary Public
Commission #: {random.randint(100000, 999999)}
"""

    def generate_settlement_agreement(self) -> str:
        """Generate legal settlement agreement"""
        plaintiff = self._generate_persona()
        defendant = self._generate_persona()
        attorney1 = random.choice(self.attorneys)
        attorney2 = random.choice(self.attorneys)
        court = random.choice(self.courts)
        
        case_number = f"{random.randint(2020, 2024)}-CV-{random.randint(10000, 99999)}"
        
        return f"""
CONFIDENTIAL SETTLEMENT AGREEMENT AND RELEASE

Case Number: {case_number}
Court: {court}

IN THE MATTER OF:
{plaintiff.first_name} {plaintiff.last_name}, Plaintiff
v.
{defendant.first_name} {defendant.last_name}, Defendant

PARTIES:

PLAINTIFF:
Name: {plaintiff.first_name} {plaintiff.last_name}
SSN: {plaintiff.ssn}
DOB: {plaintiff.dob}
Address: {plaintiff.address}
Phone: {plaintiff.phone}
Represented by: {attorney1[0]}, {attorney1[2]}

DEFENDANT:
Name: {defendant.first_name} {defendant.last_name}
SSN: {defendant.ssn}
DOB: {defendant.dob}
Address: {defendant.address}
Phone: {defendant.phone}
Represented by: {attorney2[0]}, {attorney2[2]}

SETTLEMENT TERMS:

1. Settlement Amount: ${random.randint(25000, 250000):,}
2. Payment Schedule: Lump sum within 30 days
3. Payment Method: Wire transfer

PAYMENT DETAILS:
Beneficiary: {plaintiff.first_name} {plaintiff.last_name}
Bank Name: {random.choice(['First National Bank', 'Citizens Bank', 'Commerce Bank'])}
Account Number: {random.randint(100000000, 999999999)}
Routing Number: {random.randint(100000000, 999999999)}

RELEASE:
Upon receipt of the settlement amount, Plaintiff releases and forever 
discharges Defendant from all claims arising from the incident(s) 
described in the underlying complaint.

CONFIDENTIALITY:
This settlement agreement and its terms shall remain strictly confidential.
Neither party shall disclose the existence or terms of this agreement.

Dated: {datetime.now().strftime('%m/%d/%Y')}

Plaintiff Signature: _________________________
{plaintiff.first_name} {plaintiff.last_name}

Defendant Signature: _________________________
{defendant.first_name} {defendant.last_name}

Plaintiff's Attorney: _________________________
{attorney1[0]}

Defendant's Attorney: _________________________
{attorney2[0]}
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

    def generate_credit_report(self) -> str:
        """Generate credit report with financial PII"""
        person = self._generate_persona()
        
        return f"""
CREDIT REPORT

Report Date: {datetime.now().strftime('%m/%d/%Y')}
Report ID: CR-{random.randint(1000000, 9999999)}

PERSONAL INFORMATION:
Full Name: {person.first_name} {person.last_name}
Social Security Number: {person.ssn}
Date of Birth: {person.dob}
Current Address: {person.address}
Phone: {person.phone}
Email: {person.email}

CREDIT SCORE SUMMARY:
FICO Score: {random.randint(580, 850)}
Score Range: Poor (300-579) | Fair (580-669) | Good (670-739) | Very Good (740-799) | Exceptional (800-850)

ACCOUNT SUMMARY:
Total Open Accounts: {random.randint(3, 12)}
Total Credit Limit: ${random.randint(10000, 100000):,}
Total Balance: ${random.randint(1000, 50000):,}
Credit Utilization: {random.randint(10, 90)}%

ACCOUNT DETAILS:

Account 1 - Credit Card
Creditor: {random.choice(['Chase Bank', 'Capital One', 'American Express'])}
Account Number: XXXX-XXXX-XXXX-{random.randint(1000, 9999)}
Credit Limit: ${random.randint(5000, 25000):,}
Current Balance: ${random.randint(500, 10000):,}
Payment Status: {random.choice(['Current', 'Current', 'Current', '30 Days Late'])}

Account 2 - Auto Loan
Creditor: {random.choice(['Toyota Financial', 'Honda Finance', 'Ford Credit'])}
Account Number: {random.randint(10000000, 99999999)}
Original Amount: ${random.randint(15000, 45000):,}
Current Balance: ${random.randint(5000, 30000):,}
Monthly Payment: ${random.randint(300, 700)}

Account 3 - Mortgage
Creditor: {random.choice(['Wells Fargo', 'Bank of America', 'US Bank'])}
Account Number: {random.randint(100000000, 999999999)}
Original Amount: ${random.randint(150000, 500000):,}
Current Balance: ${random.randint(100000, 450000):,}
Monthly Payment: ${random.randint(1200, 3000):,}

INQUIRIES (Last 2 Years): {random.randint(0, 6)}
COLLECTIONS: {random.randint(0, 2)}
PUBLIC RECORDS: {random.randint(0, 1)}

This report is provided for informational purposes only.
Consumer Rights: You have the right to dispute any inaccurate information.
"""

    def generate_financial_statement(self) -> str:
        """Generate financial statement with sensitive data"""
        person = self._generate_persona()
        
        return f"""
PERSONAL FINANCIAL STATEMENT

Date: {datetime.now().strftime('%m/%d/%Y')}
Statement ID: PFS-{random.randint(100000, 999999)}

PERSONAL INFORMATION:
Name: {person.first_name} {person.last_name}
SSN: {person.ssn}
Date of Birth: {person.dob}
Address: {person.address}
Phone: {person.phone}
Email: {person.email}

ASSETS:
Cash & Checking Accounts:
  {random.choice(['First National Bank', 'Citizens Bank'])} Acct #{random.randint(100000000, 999999999)}: ${random.randint(5000, 50000):,}
  {random.choice(['Chase', 'Wells Fargo'])} Acct #{random.randint(100000000, 999999999)}: ${random.randint(2000, 20000):,}

Savings & CDs:
  Savings Account #{random.randint(100000000, 999999999)}: ${random.randint(10000, 100000):,}
  CD #{random.randint(10000000, 99999999)}: ${random.randint(5000, 25000):,}

Investment Accounts:
  Brokerage Account: ${random.randint(50000, 500000):,}
  401(k) Balance: ${random.randint(100000, 800000):,}
  IRA Balance: ${random.randint(50000, 200000):,}

Real Estate:
  Primary Residence: ${random.randint(200000, 800000):,}

Vehicles:
  {random.choice(['Toyota Camry', 'Honda Accord', 'Ford F-150'])}: ${random.randint(15000, 45000):,}

TOTAL ASSETS: ${random.randint(500000, 2000000):,}

LIABILITIES:
Mortgage Balance: ${random.randint(100000, 400000):,}
Auto Loan Balance: ${random.randint(5000, 30000):,}
Credit Card Debt: ${random.randint(1000, 20000):,}
Student Loans: ${random.randint(0, 50000):,}

TOTAL LIABILITIES: ${random.randint(150000, 500000):,}

NET WORTH: ${random.randint(200000, 1500000):,}

I certify that this statement is true and complete.

Signature: _________________________
Date: {datetime.now().strftime('%m/%d/%Y')}
"""

    def generate_bank_statement(self) -> str:
        """Generate bank statement with account details"""
        person = self._generate_persona()
        account_num = random.randint(100000000, 999999999)
        
        return f"""
BANK STATEMENT

Bank: {random.choice(['First National Bank', 'Citizens Community Bank', 'Heritage Savings'])}
Statement Period: {datetime.now().strftime('%m/01/%Y')} - {datetime.now().strftime('%m/%d/%Y')}

ACCOUNT HOLDER:
Name: {person.first_name} {person.last_name}
SSN: {person.ssn}
Address: {person.address}

ACCOUNT INFORMATION:
Account Type: {random.choice(['Checking', 'Savings'])}
Account Number: {account_num}
Routing Number: {random.randint(100000000, 999999999)}

ACCOUNT SUMMARY:
Beginning Balance: ${random.randint(5000, 25000):,}
Total Deposits: ${random.randint(3000, 15000):,}
Total Withdrawals: ${random.randint(2000, 12000):,}
Ending Balance: ${random.randint(5000, 30000):,}

TRANSACTIONS:
Date        Description                          Amount      Balance
-----------------------------------------------------------------------
{datetime.now().strftime('%m')}/01  Beginning Balance                    -           ${random.randint(5000, 25000):,}
{datetime.now().strftime('%m')}/03  Direct Deposit - Employer            +${random.randint(2000, 5000):,}    ${random.randint(7000, 30000):,}
{datetime.now().strftime('%m')}/05  {random.choice(['Grocery Store', 'Gas Station'])}                -${random.randint(50, 200)}       ${random.randint(6000, 29000):,}
{datetime.now().strftime('%m')}/07  Utility Payment                      -${random.randint(100, 300)}       ${random.randint(6000, 28000):,}
{datetime.now().strftime('%m')}/10  ATM Withdrawal                       -${random.randint(100, 500)}       ${random.randint(5500, 27000):,}
{datetime.now().strftime('%m')}/15  Direct Deposit - Employer            +${random.randint(2000, 5000):,}    ${random.randint(7000, 32000):,}
{datetime.now().strftime('%m')}/17  Online Transfer                      -${random.randint(200, 1000)}      ${random.randint(6000, 31000):,}
{datetime.now().strftime('%m')}/20  {random.choice(['Restaurant', 'Online Purchase'])}                 -${random.randint(30, 150)}       ${random.randint(5800, 30800):,}

DEBIT CARD INFORMATION:
Card Number: {random.randint(4000, 4999)}-XXXX-XXXX-{random.randint(1000, 9999)}
Expiration: {random.randint(1, 12):02d}/{random.randint(25, 28)}

Contact us at 1-800-{random.randint(100, 999)}-{random.randint(1000, 9999)} with questions.
"""

    def generate_tax_document(self) -> str:
        """Generate tax document with sensitive financial data"""
        person = self._generate_persona()
        tax_year = datetime.now().year - 1
        
        return f"""
FORM W-2 WAGE AND TAX STATEMENT
Tax Year: {tax_year}

EMPLOYER INFORMATION:
Employer Name: {random.choice(['Acme Corporation', 'Tech Solutions Inc', 'Global Industries'])}
Employer ID (EIN): {random.randint(10, 99)}-{random.randint(1000000, 9999999)}
Employer Address: {random.randint(100, 9999)} Corporate Dr, Business City, ST {random.randint(10000, 99999)}

EMPLOYEE INFORMATION:
Name: {person.first_name} {person.last_name}
Social Security Number: {person.ssn}
Address: {person.address}

WAGE AND TAX DATA:
Box 1 - Wages, tips, other compensation:     ${random.randint(50000, 150000):,}
Box 2 - Federal income tax withheld:         ${random.randint(5000, 30000):,}
Box 3 - Social Security wages:               ${random.randint(50000, 150000):,}
Box 4 - Social Security tax withheld:        ${random.randint(3000, 9000):,}
Box 5 - Medicare wages and tips:             ${random.randint(50000, 150000):,}
Box 6 - Medicare tax withheld:               ${random.randint(700, 2200):,}

ADDITIONAL INFORMATION:
Box 12a - Retirement plan contributions:     ${random.randint(5000, 20000):,}
Box 12b - Health insurance premiums:         ${random.randint(2000, 8000):,}

STATE TAX INFORMATION:
State: {random.choice(['CA', 'NY', 'TX', 'FL', 'IL'])}
State wages:                                 ${random.randint(50000, 150000):,}
State income tax withheld:                   ${random.randint(2000, 15000):,}

This document contains sensitive tax information.
Keep for your records and use for tax filing purposes.

Generated: {datetime.now().strftime('%m/%d/%Y')}
"""


class HRBenefitsGenerator:
    """Generate HR and employee benefits documents for demo scenarios"""
    
    def __init__(self):
        self.company_names = [
            "Acme Corporation", "TechStart Inc", "Global Innovations LLC",
            "Blue Sky Enterprises", "Summit Solutions Group"
        ]
        
        self.departments = [
            "Engineering", "Sales", "Marketing", "Human Resources",
            "Finance", "Operations", "Customer Success", "Product"
        ]
        
        self.job_titles = [
            "Software Engineer", "Product Manager", "Sales Representative",
            "Marketing Specialist", "HR Coordinator", "Financial Analyst",
            "Operations Manager", "Customer Success Manager"
        ]
    
    def generate_benefits_overview(self) -> str:
        """Generate employee benefits overview document"""
        company = random.choice(self.company_names)
        year = datetime.now().year
        
        return f"""
{company.upper()}
EMPLOYEE BENEFITS GUIDE - {year}

OVERVIEW

Welcome to your benefits package! This guide provides comprehensive information about 
the benefits available to all full-time employees of {company}.

HEALTH INSURANCE

Medical Coverage:
- PPO Plan: ${random.randint(150, 300)}/month employee, ${random.randint(400, 700)}/month family
- HMO Plan: ${random.randint(100, 200)}/month employee, ${random.randint(300, 500)}/month family
- HSA-Compatible HDHP: ${random.randint(80, 150)}/month employee with company HSA contribution

Dental Coverage:
- Basic Plan: ${random.randint(20, 40)}/month
- Premium Plan: ${random.randint(50, 80)}/month with orthodontic coverage

Vision Coverage:
- Standard Plan: ${random.randint(10, 20)}/month
- Includes annual eye exam and $150 frame allowance

RETIREMENT BENEFITS

401(k) Plan:
- Company matches {random.choice(['50%', '100%'])} of contributions up to {random.randint(4, 6)}% of salary
- Immediate vesting for employee contributions
- {random.randint(2, 4)}-year vesting schedule for employer match
- Pre-tax and Roth options available

PAID TIME OFF

Vacation:
- 0-2 years: {random.randint(10, 15)} days annually
- 3-5 years: {random.randint(15, 20)} days annually
- 6+ years: {random.randint(20, 25)} days annually

Sick Leave: {random.randint(5, 10)} days annually
Personal Days: {random.randint(2, 4)} days annually
Holidays: {random.randint(10, 12)} company holidays

ADDITIONAL BENEFITS

- Life Insurance: 2x annual salary (company paid)
- Short-term Disability: 60% of salary, up to 12 weeks
- Long-term Disability: 60% of salary
- Employee Assistance Program (EAP)
- Wellness Program with gym reimbursement up to ${random.randint(50, 100)}/month
- Tuition Reimbursement: Up to ${random.randint(5000, 10000):,}/year
- Commuter Benefits: Pre-tax transit and parking

ENROLLMENT

Open enrollment period: November 1-30
New hire enrollment: Within 30 days of start date
Qualifying life events allow mid-year changes

Contact HR at benefits@{company.lower().replace(' ', '')}.com for questions.

Document ID: BEN-{random.randint(10000, 99999)}
Last Updated: {datetime.now().strftime('%B %Y')}
"""
    
    def generate_pto_policy(self) -> str:
        """Generate PTO and leave policy document"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
PAID TIME OFF (PTO) POLICY

POLICY NUMBER: HR-PTO-{random.randint(100, 999)}
EFFECTIVE DATE: January 1, {datetime.now().year}

1. PURPOSE

This policy establishes guidelines for the accrual, use, and management of 
paid time off for all employees of {company}.

2. ELIGIBILITY

All full-time employees working {random.randint(30, 40)} or more hours per week are 
eligible for PTO benefits beginning on their date of hire.

3. PTO ACCRUAL SCHEDULE

Years of Service     Annual PTO Days     Monthly Accrual
0-1 years           {random.randint(10, 12)} days          {round(random.randint(10, 12)/12, 2)} days
1-3 years           {random.randint(13, 17)} days          {round(random.randint(13, 17)/12, 2)} days
3-5 years           {random.randint(18, 22)} days          {round(random.randint(18, 22)/12, 2)} days
5+ years            {random.randint(23, 28)} days          {round(random.randint(23, 28)/12, 2)} days

4. PTO CARRYOVER

- Maximum carryover: {random.randint(40, 80)} hours per calendar year
- Excess PTO is forfeited on December 31st
- Manager approval required for exceptional circumstances

5. REQUESTING PTO

- Submit requests through the HR portal at least {random.randint(1, 2)} week(s) in advance
- Requests under 3 days may be submitted {random.randint(24, 72)} hours in advance
- Manager approval required for all PTO requests
- Holiday periods require {random.randint(2, 4)} weeks advance notice

6. SICK LEAVE

Separate from PTO, employees receive {random.randint(5, 10)} sick days annually.
Sick leave may be used for:
- Personal illness or injury
- Medical appointments
- Care for immediate family members

7. PARENTAL LEAVE

- Birth parent: {random.randint(12, 16)} weeks paid leave
- Non-birth parent: {random.randint(4, 8)} weeks paid leave
- Must be taken within 12 months of birth/adoption

8. BEREAVEMENT LEAVE

- Immediate family: {random.randint(3, 5)} days paid
- Extended family: {random.randint(1, 3)} days paid

9. JURY DUTY

Full pay provided for jury duty service, not to exceed {random.randint(5, 10)} days.

Contact Human Resources for questions about this policy.

Approved By: HR Director
Review Date: {(datetime.now() + timedelta(days=365)).strftime('%B %Y')}
"""
    
    def generate_employee_handbook_excerpt(self) -> str:
        """Generate employee handbook section"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
EMPLOYEE HANDBOOK

VERSION: {datetime.now().year}.{random.randint(1, 4)}
LAST UPDATED: {datetime.now().strftime('%B %d, %Y')}

WELCOME

Welcome to {company}! We are excited to have you as part of our team. 
This handbook provides important information about your employment, 
our company policies, and the benefits available to you.

COMPANY MISSION

{random.choice([
    "To deliver innovative solutions that transform how businesses operate.",
    "To create exceptional value for our customers through technology and service excellence.",
    "To build products that improve lives and drive sustainable growth."
])}

EMPLOYMENT POLICIES

Equal Employment Opportunity:
{company} is committed to providing equal employment opportunities to all 
employees and applicants without regard to race, color, religion, sex, 
national origin, age, disability, or any other protected characteristic.

At-Will Employment:
Employment at {company} is at-will. This means that either you or the 
company may terminate the employment relationship at any time, with or 
without cause or notice.

WORKPLACE CONDUCT

Professional Behavior:
- Treat all colleagues, customers, and vendors with respect
- Maintain a professional appearance appropriate to your role
- Arrive on time and be prepared for meetings and work
- Communicate openly and honestly

Anti-Harassment Policy:
{company} prohibits harassment of any kind, including:
- Sexual harassment
- Verbal or physical abuse
- Intimidation or bullying
- Discrimination based on protected characteristics

Report any concerns to HR or use the anonymous ethics hotline.

COMPENSATION

Pay Periods:
- Employees are paid {random.choice(['bi-weekly', 'semi-monthly'])}
- Direct deposit is available and encouraged
- Pay stubs accessible through the employee portal

Performance Reviews:
- Annual reviews conducted in {random.choice(['January', 'March', 'July'])}
- Mid-year check-ins with managers
- Merit increases based on performance

TECHNOLOGY AND SECURITY

Acceptable Use:
- Company equipment is for business purposes
- Limited personal use is permitted
- No illegal or inappropriate content
- Respect intellectual property rights

Data Security:
- Protect confidential company information
- Use strong passwords and two-factor authentication
- Report suspicious emails or security concerns
- Lock your computer when away from desk

ACKNOWLEDGMENT

I acknowledge that I have received and read this Employee Handbook. 
I understand that it is my responsibility to familiarize myself with 
these policies and procedures.

Employee Signature: _________________________
Date: ___________
Employee ID: EMP-{random.randint(10000, 99999)}
"""
    
    def generate_compensation_policy(self) -> str:
        """Generate compensation and salary administration policy"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
COMPENSATION & SALARY ADMINISTRATION POLICY

POLICY NUMBER: HR-COMP-{random.randint(100, 999)}
EFFECTIVE DATE: {datetime.now().strftime('%B %d, %Y')}

1. PHILOSOPHY

{company} is committed to providing competitive compensation that 
attracts, retains, and motivates talented employees. Our compensation 
philosophy is based on:

- Market competitiveness (targeting the {random.randint(50, 75)}th percentile)
- Internal equity and fairness
- Pay for performance
- Total rewards perspective

2. PAY GRADES AND RANGES

Level    Title Range                    Salary Range
L1       Entry/Associate               ${random.randint(45, 55):,}K - ${random.randint(60, 70):,}K
L2       Mid-Level                     ${random.randint(65, 75):,}K - ${random.randint(85, 95):,}K
L3       Senior                        ${random.randint(90, 100):,}K - ${random.randint(115, 125):,}K
L4       Lead/Principal                ${random.randint(120, 135):,}K - ${random.randint(150, 165):,}K
L5       Manager/Director              ${random.randint(140, 160):,}K - ${random.randint(185, 200):,}K

3. SALARY REVIEWS

Annual salary reviews occur in {random.choice(['Q1', 'Q2'])} each year.
Factors considered:
- Individual performance rating
- Market data adjustments
- Budget availability
- Time since last increase

4. BONUS PROGRAMS

Annual Bonus:
- Target bonus ranges from {random.randint(5, 10)}% to {random.randint(15, 25)}% of base salary
- Based on company performance and individual contribution
- Paid in {random.choice(['February', 'March'])}

Spot Bonuses:
- Up to ${random.randint(500, 2000):,} for exceptional contributions
- Manager discretion with HR approval
- No limit on number per year

5. EQUITY COMPENSATION

Stock Options/RSUs:
- Granted to eligible employees at hire and through annual refresh
- 4-year vesting schedule with 1-year cliff
- Exercise window: 90 days post-termination

6. PROMOTION GUIDELINES

Promotions require:
- Manager recommendation
- HR review of job qualifications
- Approval from department head
- Typical increase: {random.randint(8, 15)}% of base salary

7. CONFIDENTIALITY

Compensation information is confidential. Employees should not share 
or solicit salary information except as permitted by law.

Questions about compensation should be directed to your HR Business Partner.

Document Control: HR-COMP-{random.randint(1000, 9999)}
Approved By: VP of Human Resources
"""
    
    def generate_onboarding_checklist(self) -> str:
        """Generate new employee onboarding checklist"""
        company = random.choice(self.company_names)
        dept = random.choice(self.departments)
        title = random.choice(self.job_titles)
        
        return f"""
{company.upper()}
NEW EMPLOYEE ONBOARDING CHECKLIST

EMPLOYEE INFORMATION:
Name: [NEW HIRE NAME]
Department: {dept}
Position: {title}
Start Date: {datetime.now().strftime('%B %d, %Y')}
Manager: [MANAGER NAME]

PRE-START (HR TO COMPLETE):
☐ Send offer letter and employment documents
☐ Conduct background check
☐ Set up employee in HRIS system
☐ Create employee email account
☐ Order equipment (laptop, monitor, keyboard)
☐ Assign desk/workspace
☐ Schedule orientation sessions

DAY ONE:
☐ Welcome meeting with HR
☐ Complete I-9 verification
☐ Review and sign employee handbook acknowledgment
☐ Complete tax forms (W-4, state withholding)
☐ Enroll in benefits (health, dental, vision, 401k)
☐ Collect emergency contact information
☐ Issue building access badge
☐ IT setup and system access walkthrough
☐ Meet with manager for role overview

FIRST WEEK:
☐ Complete required compliance training
☐ Review company policies and procedures
☐ Meet with team members and key stakeholders
☐ Shadow team activities
☐ Begin role-specific training
☐ Set up direct deposit
☐ Enroll in relevant mailing lists
☐ 30-day goals discussion with manager

FIRST 30 DAYS:
☐ Complete all required training modules
☐ Attend department meetings
☐ Begin independent work assignments
☐ Feedback session with manager
☐ Connect with mentor/buddy
☐ Review performance expectations

FIRST 90 DAYS:
☐ Complete probationary period review
☐ Full role transition
☐ 90-day performance discussion
☐ Identify professional development goals

TRAINING REQUIREMENTS:
☐ Information Security Awareness
☐ Anti-Harassment Training
☐ Data Privacy (GDPR/CCPA)
☐ Code of Conduct
☐ Emergency Procedures
☐ [Department-specific training]

HR Contact: hr@{company.lower().replace(' ', '')}.com
IT Helpdesk: helpdesk@{company.lower().replace(' ', '')}.com

Form ID: ONB-{random.randint(10000, 99999)}
"""


class ITSecurityGenerator:
    """Generate IT security and compliance documents for demo scenarios"""
    
    def __init__(self):
        self.company_names = [
            "Acme Corporation", "TechStart Inc", "Global Innovations LLC",
            "Blue Sky Enterprises", "Summit Solutions Group"
        ]
    
    def generate_security_incident_report(self) -> str:
        """Generate a security incident report"""
        company = random.choice(self.company_names)
        incident_types = [
            "Phishing Attempt", "Malware Detection", "Unauthorized Access Attempt",
            "Data Exfiltration Alert", "DDoS Attack", "Password Spray Attack"
        ]
        severity = random.choice(["Low", "Medium", "High", "Critical"])
        status = random.choice(["Open", "Investigating", "Contained", "Resolved"])
        
        return f"""
{company.upper()}
SECURITY INCIDENT REPORT

INCIDENT ID: SEC-{datetime.now().year}-{random.randint(1000, 9999)}
DATE REPORTED: {datetime.now().strftime('%B %d, %Y')}
TIME DETECTED: {random.randint(0, 23):02d}:{random.randint(0, 59):02d} UTC

CLASSIFICATION
Incident Type: {random.choice(incident_types)}
Severity: {severity}
Status: {status}

INCIDENT SUMMARY
A security event was detected by our monitoring systems requiring 
investigation and response by the Security Operations Center (SOC).

DETECTION DETAILS
Source: {random.choice(['SIEM Alert', 'EDR Detection', 'User Report', 'Firewall Log', 'IDS/IPS'])}
Affected Systems: {random.randint(1, 15)} devices
Affected Users: {random.randint(0, 50)}
Network Segment: {random.choice(['Corporate', 'DMZ', 'Guest', 'Production'])}

INDICATORS OF COMPROMISE (IoCs)
- IP Address: {random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}
- Hash: {random.randbytes(16).hex()}
- Domain: suspicious-domain-{random.randint(100, 999)}.example.com

TIMELINE
- {datetime.now().strftime('%H:%M')} - Initial detection
- {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M')} - SOC alerted
- {(datetime.now() + timedelta(minutes=15)).strftime('%H:%M')} - Initial assessment
- {(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')} - Containment initiated

RESPONSE ACTIONS
☐ Isolate affected systems
☐ Preserve evidence/logs
☐ Block malicious indicators
☐ Reset compromised credentials
☐ Notify stakeholders
☐ Document findings

BUSINESS IMPACT
- Service Disruption: {random.choice(['None', 'Minimal', 'Moderate', 'Significant'])}
- Data Exposure: {random.choice(['None suspected', 'Under investigation', 'Confirmed - limited'])}
- Financial Impact: ${random.randint(0, 50000):,} (estimated)

LESSONS LEARNED
[To be completed after incident resolution]

ASSIGNED TO: Security Operations Center
ESCALATION: {random.choice(['CISO', 'IT Director', 'VP Engineering'])}
NEXT REVIEW: {(datetime.now() + timedelta(days=1)).strftime('%B %d, %Y')}

Confidentiality: INTERNAL USE ONLY
"""
    
    def generate_security_policy(self) -> str:
        """Generate IT security policy document"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
INFORMATION SECURITY POLICY

DOCUMENT ID: SEC-POL-{random.randint(100, 999)}
VERSION: {random.randint(1, 5)}.{random.randint(0, 9)}
EFFECTIVE DATE: {datetime.now().strftime('%B %d, %Y')}

1. PURPOSE

This policy establishes the information security framework for {company}
to protect our data assets, systems, and infrastructure from threats.

2. SCOPE

This policy applies to:
- All employees, contractors, and third parties
- All information systems and data
- All company-owned and BYOD devices
- Cloud services and SaaS applications

3. PASSWORD REQUIREMENTS

Minimum Requirements:
- Length: {random.randint(12, 16)} characters minimum
- Complexity: uppercase, lowercase, numbers, special characters
- Expiration: Every {random.randint(60, 90)} days
- History: Cannot reuse last {random.randint(10, 15)} passwords

Multi-Factor Authentication (MFA):
- Required for all remote access
- Required for privileged accounts
- Required for cloud applications
- Hardware tokens recommended for admin accounts

4. ACCESS CONTROL

Principle of Least Privilege:
- Access granted based on job function
- Regular access reviews (quarterly)
- Immediate deprovisioning on termination

Privileged Access:
- Separate admin accounts required
- Privileged Access Management (PAM) system
- Session recording for critical systems

5. DATA CLASSIFICATION

Levels:
- Public: No restrictions
- Internal: Company employees only
- Confidential: Need-to-know basis
- Restricted: Highly sensitive, encryption required

Handling Requirements:
- Encryption at rest for Confidential and above
- Encryption in transit for all sensitive data
- Secure deletion procedures

6. ENDPOINT SECURITY

Required Controls:
- Antivirus/EDR solution
- Host-based firewall
- Full disk encryption
- Automatic screen lock ({random.randint(3, 10)} minutes)
- Automatic patching enabled

7. NETWORK SECURITY

- Network segmentation by sensitivity
- VPN required for remote access
- Firewall rules reviewed quarterly
- Intrusion detection/prevention
- Regular penetration testing

8. INCIDENT RESPONSE

All suspected security incidents must be reported to:
- Security Operations: security@{company.lower().replace(' ', '')}.com
- Hotline: 1-800-SEC-{random.randint(1000, 9999)}

Response SLAs:
- Critical: 1 hour response
- High: 4 hours response
- Medium: 24 hours response
- Low: 72 hours response

9. COMPLIANCE

{company} maintains compliance with:
- SOC 2 Type II
- ISO 27001
- GDPR (where applicable)
- HIPAA (for healthcare data)
- PCI DSS (for payment data)

10. VIOLATIONS

Policy violations may result in:
- Verbal warning
- Written warning
- Suspension of access
- Termination
- Legal action

Approved By: Chief Information Security Officer
Review Date: {(datetime.now() + timedelta(days=365)).strftime('%B %Y')}
"""
    
    def generate_access_review_report(self) -> str:
        """Generate access review/audit report"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
QUARTERLY ACCESS REVIEW REPORT

REVIEW PERIOD: Q{random.randint(1, 4)} {datetime.now().year}
REPORT DATE: {datetime.now().strftime('%B %d, %Y')}
REVIEW ID: AR-{datetime.now().year}-{random.randint(100, 999)}

EXECUTIVE SUMMARY

This report summarizes the quarterly access review conducted to ensure 
appropriate access controls are in place across {company}'s systems.

REVIEW SCOPE
- Total Users Reviewed: {random.randint(200, 500)}
- Systems Reviewed: {random.randint(15, 30)}
- Privileged Accounts: {random.randint(20, 50)}

FINDINGS SUMMARY

Access Modifications Required:
- Accounts to Terminate: {random.randint(5, 15)}
- Access to Reduce: {random.randint(10, 25)}
- Access to Elevate: {random.randint(2, 8)}
- No Changes Required: {random.randint(150, 400)}

Orphaned Accounts Discovered: {random.randint(3, 12)}
Service Accounts Reviewed: {random.randint(10, 25)}
Third-Party Access Reviewed: {random.randint(5, 15)}

CRITICAL FINDINGS

1. Terminated Employee Access
   - {random.randint(2, 5)} accounts found for terminated employees
   - Immediate revocation completed
   - Root cause: Delayed HR notification

2. Excessive Privileges
   - {random.randint(5, 10)} users with unnecessary admin access
   - Access reduced to appropriate level

3. Shared Accounts
   - {random.randint(1, 3)} shared accounts identified
   - Converting to individual accounts

COMPLIANCE STATUS
- Access review completion: 100%
- Remediation completion: {random.randint(85, 99)}%
- Target remediation date: {(datetime.now() + timedelta(days=14)).strftime('%B %d, %Y')}

RECOMMENDATIONS
1. Implement automated deprovisioning workflow
2. Enhanced monitoring for privileged accounts
3. Quarterly certification of admin access
4. Training on least privilege principles

NEXT REVIEW: {(datetime.now() + timedelta(days=90)).strftime('%B %Y')}

Prepared By: IT Security Team
Approved By: Chief Information Security Officer
"""
    
    def generate_vulnerability_report(self) -> str:
        """Generate vulnerability assessment report"""
        company = random.choice(self.company_names)
        
        return f"""
{company.upper()}
VULNERABILITY ASSESSMENT REPORT

ASSESSMENT DATE: {datetime.now().strftime('%B %d, %Y')}
REPORT ID: VULN-{datetime.now().year}-{random.randint(1000, 9999)}
CLASSIFICATION: CONFIDENTIAL

SCOPE OF ASSESSMENT
- Internal Network Scan
- External Perimeter Scan
- Web Application Assessment
- Cloud Infrastructure Review

EXECUTIVE SUMMARY

This vulnerability assessment identified the current security posture 
of {company}'s IT infrastructure and provides remediation priorities.

FINDINGS OVERVIEW

Total Vulnerabilities: {random.randint(50, 200)}
- Critical: {random.randint(1, 5)}
- High: {random.randint(5, 20)}
- Medium: {random.randint(20, 50)}
- Low: {random.randint(30, 100)}
- Informational: {random.randint(10, 30)}

CRITICAL VULNERABILITIES

1. CVE-{datetime.now().year}-{random.randint(10000, 99999)}
   - Description: Remote Code Execution in {random.choice(['Apache', 'nginx', 'OpenSSL', 'Log4j'])}
   - Affected Systems: {random.randint(1, 5)}
   - CVSS Score: {random.uniform(9.0, 10.0):.1f}
   - Remediation: Apply vendor patch immediately

2. CVE-{datetime.now().year}-{random.randint(10000, 99999)}
   - Description: SQL Injection in web application
   - Affected Systems: {random.randint(1, 3)}
   - CVSS Score: {random.uniform(8.5, 9.5):.1f}
   - Remediation: Input validation and parameterized queries

REMEDIATION TIMELINE
- Critical: Within 24 hours
- High: Within 7 days
- Medium: Within 30 days
- Low: Within 90 days

TRENDING
- New vulnerabilities this quarter: +{random.randint(10, 30)}%
- Remediation rate: {random.randint(75, 95)}%
- Average time to remediate: {random.randint(5, 20)} days

RISK SCORE
Current Risk Score: {random.randint(40, 80)}/100
Target Risk Score: <30/100

NEXT ASSESSMENT: {(datetime.now() + timedelta(days=30)).strftime('%B %Y')}

Prepared By: Security Assessment Team
Distribution: IT Leadership, CISO
"""


class SalesGenerator:
    """Generate sales and proposal documents for demo scenarios"""
    
    def __init__(self):
        self.company_names = [
            "Acme Corporation", "TechStart Inc", "Global Innovations LLC",
            "Blue Sky Enterprises", "Summit Solutions Group"
        ]
        
        self.products = [
            ("Enterprise Platform", "Full-featured business solution"),
            ("Cloud Analytics Suite", "Data insights and reporting"),
            ("Security Gateway", "Network protection and monitoring"),
            ("Collaboration Hub", "Team communication platform"),
            ("Integration Engine", "API and data connectivity")
        ]
    
    def generate_proposal(self) -> str:
        """Generate sales proposal document"""
        company = random.choice(self.company_names)
        product = random.choice(self.products)
        client = random.choice(["Acme Industries", "Global Tech Corp", "Premier Solutions", "NextGen Enterprises"])
        
        return f"""
{company.upper()}
SALES PROPOSAL

PROPOSAL NUMBER: PROP-{datetime.now().year}-{random.randint(1000, 9999)}
DATE: {datetime.now().strftime('%B %d, %Y')}
VALID UNTIL: {(datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')}

PREPARED FOR:
{client}
Attn: Procurement Department

PREPARED BY:
{random.choice(['John', 'Jane', 'Michael', 'Sarah'])} {random.choice(['Smith', 'Johnson', 'Williams'])}
Account Executive
{company}
Phone: ({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}
Email: sales@{company.lower().replace(' ', '')}.com

EXECUTIVE SUMMARY

{company} is pleased to present this proposal for {product[0]} - 
{product[1]}. We believe our solution will address your business needs
and deliver significant value to your organization.

PROPOSED SOLUTION

Product: {product[0]}
License Type: {random.choice(['Annual Subscription', 'Perpetual License', '3-Year Agreement'])}
Users: {random.randint(50, 500)}

COMPONENTS INCLUDED:
- Core Platform License
- Implementation Services
- Training ({random.randint(8, 40)} hours)
- 24/7 Support ({random.choice(['Standard', 'Premium', 'Enterprise'])} tier)
- Quarterly Business Reviews

PRICING

                                    Unit Price      Qty        Total
Software License               ${random.randint(100, 500):,}     {random.randint(50, 500)}   ${random.randint(50000, 250000):,}
Implementation Services        ${random.randint(150, 300):,}/hr  {random.randint(40, 160)}hrs ${random.randint(6000, 48000):,}
Training                       ${random.randint(2000, 5000):,}   {random.randint(1, 5)}     ${random.randint(2000, 25000):,}
Annual Support                 ${random.randint(15000, 50000):,} 1 yr   ${random.randint(15000, 50000):,}
---------------------------------------------------------------------------
SUBTOTAL                                                         ${random.randint(100000, 300000):,}
Discount (Volume)                                                -${random.randint(5000, 30000):,}
---------------------------------------------------------------------------
TOTAL INVESTMENT                                                 ${random.randint(90000, 280000):,}

PAYMENT TERMS
- 50% upon contract signing
- 50% upon go-live
- Net 30 payment terms

IMPLEMENTATION TIMELINE

Week 1-2: Discovery and Planning
Week 3-6: Configuration and Setup
Week 7-8: Testing and Validation
Week 9-10: Training and Go-Live
Week 11-12: Hypercare Support

PROJECT TEAM
- Project Manager (dedicated)
- Solution Architect
- Implementation Consultant
- Training Specialist

TERMS AND CONDITIONS

This proposal is subject to our standard terms and conditions.
License agreement will be provided upon acceptance.

NEXT STEPS
1. Review and approve proposal
2. Contract execution
3. Kickoff meeting scheduling
4. Begin implementation

We look forward to partnering with {client}!

Authorized Signature: _________________________
Date: ___________
"""
    
    def generate_quote(self) -> str:
        """Generate sales quote"""
        company = random.choice(self.company_names)
        product = random.choice(self.products)
        
        return f"""
{company.upper()}
PRICE QUOTE

QUOTE NUMBER: QT-{datetime.now().year}-{random.randint(10000, 99999)}
QUOTE DATE: {datetime.now().strftime('%B %d, %Y')}
EXPIRATION: {(datetime.now() + timedelta(days=30)).strftime('%B %d, %Y')}

CUSTOMER INFORMATION
Company: [CUSTOMER NAME]
Contact: [CONTACT NAME]
Email: [CONTACT EMAIL]

QUOTE SUMMARY

Item                           SKU              Qty     Unit Price      Total
-------------------------------------------------------------------------------
{product[0]}                   PRD-{random.randint(1000, 9999)}    {random.randint(10, 100)}   ${random.randint(100, 1000):,}     ${random.randint(10000, 100000):,}
Setup Fee                      SVC-SETUP        1       ${random.randint(1000, 5000):,}    ${random.randint(1000, 5000):,}
Annual Maintenance             SVC-MAINT        1       ${random.randint(2000, 10000):,}   ${random.randint(2000, 10000):,}
-------------------------------------------------------------------------------
                                            SUBTOTAL: ${random.randint(15000, 115000):,}
                                   DISCOUNT ({random.randint(5, 20)}%): -${random.randint(1000, 20000):,}
                                            TAX ({random.randint(5, 10)}%): ${random.randint(500, 5000):,}
                                               TOTAL: ${random.randint(15000, 100000):,}

PAYMENT TERMS: Net 30
DELIVERY: {random.randint(2, 6)} weeks from order date

NOTES:
- Quote valid for 30 days
- Prices subject to change after expiration
- Tax calculated based on delivery location

To proceed, please sign below and return to your sales representative.

Customer Signature: _________________________
Print Name: ________________________________
Date: ___________

{company} Representative: ___________________
Date: ___________
"""


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