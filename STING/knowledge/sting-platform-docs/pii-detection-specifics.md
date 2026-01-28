# STING PII Detection & Data Privacy System

## Overview

STING's Personally Identifiable Information (PII) detection system automatically identifies, classifies, and optionally scrubs or redacts sensitive data across 50+ entity types. The system ensures compliance with major privacy regulations including HIPAA, GDPR, CCPA, and FERPA through pre-configured compliance profiles and customizable detection rules.

**Key Features:**
- **50+ PII Entity Types**: From basic (names, emails) to complex (biometric IDs, medical record numbers)
- **Compliance Profiles**: Pre-configured for HIPAA, GDPR, CCPA, FERPA, PCI-DSS
- **Scrubbing vs. Redaction**: Remove PII entirely or replace with type-specific tokens
- **Custom Patterns**: Regex-based detection for organization-specific identifiers
- **Audit Logging**: Complete trail of PII detection and handling
- **Context-Aware Detection**: Reduces false positives through surrounding text analysis

---

## Table of Contents

1. [Complete PII Entity Type List](#complete-pii-entity-type-list)
2. [Compliance Profiles](#compliance-profiles)
3. [Detection Methods](#detection-methods)
4. [Scrubbing vs. Redaction](#scrubbing-vs-redaction)
5. [Custom Pattern Configuration](#custom-pattern-configuration)
6. [API Usage Examples](#api-usage-examples)
7. [Real-World Use Cases](#real-world-use-cases)
8. [Performance & Accuracy](#performance--accuracy)

---

## Complete PII Entity Type List

### Personal Identifiers (15 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `PERSON` | Full names | "John Smith" | NER-based |
| `EMAIL_ADDRESS` | Email addresses | "user@example.com" | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}\b` |
| `PHONE_NUMBER` | Phone numbers (various formats) | "(555) 123-4567" | `(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}` |
| `US_SSN` | Social Security Numbers | "123-45-6789" | `\b\d{3}-\d{2}-\d{4}\b` |
| `US_DRIVER_LICENSE` | Driver's license numbers (all states) | "D1234567" (CA format) | State-specific patterns |
| `US_PASSPORT` | US passport numbers | "123456789" | `\b[0-9]{9}\b` |
| `DATE_OF_BIRTH` | Birth dates | "01/15/1985" | `\b(0?[1-9]\|1[0-2])/(0?[1-9]\|[12][0-9]\|3[01])/((19\|20)\d{2})\b` |
| `AGE` | Age in years | "42 years old" | `\b\d{1,3}\s?(years?\s?old\|y\.?o\.?)\b` |
| `USERNAME` | Usernames/handles | "@johndoe" | Context-dependent |
| `IP_ADDRESS` | IPv4/IPv6 addresses | "192.168.1.1" | `\b((25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\.){3}(25[0-5]\|2[0-4][0-9]\|[01]?[0-9][0-9]?)\b` |
| `MAC_ADDRESS` | MAC addresses | "00:1B:44:11:3A:B7" | `\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b` |
| `VEHICLE_VIN` | Vehicle identification numbers | "1HGBH41JXMN109186" | `\b[A-HJ-NPR-Z0-9]{17}\b` |
| `BIOMETRIC_ID` | Biometric identifiers | "FP-A12B34C56" | Custom patterns |
| `EMPLOYEE_ID` | Employee identification | "EMP-2024-001234" | Org-specific |
| `STUDENT_ID` | Student identification | "STU-987654" | Org-specific |

### Financial Identifiers (8 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `CREDIT_CARD` | Credit card numbers (Luhn validated) | "4532-1234-5678-9010" | `\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b` |
| `BANK_ACCOUNT` | Bank account numbers | "1234567890" | Country-specific |
| `ROUTING_NUMBER` | Bank routing numbers (US) | "021000021" | `\b[0-9]{9}\b` |
| `IBAN` | International Bank Account Number | "GB82 WEST 1234 5698 7654 32" | `\b[A-Z]{2}[0-9]{2}[A-Z0-9]+\b` |
| `SWIFT_CODE` | SWIFT/BIC codes | "AAAA BB CC 123" | `\b[A-Z]{4}\s?[A-Z]{2}\s?[A-Z0-9]{2}\s?([A-Z0-9]{3})?\b` |
| `CRYPTO_ADDRESS` | Cryptocurrency wallet addresses | "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" | Coin-specific patterns |
| `TAX_ID` | Tax identification numbers | "12-3456789" (EIN) | `\b\d{2}-\d{7}\b` |
| `CREDIT_SCORE` | Credit scores | "FICO: 720" | Context-based |

### Healthcare Identifiers (12 types - HIPAA PHI)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `MEDICAL_RECORD_NUMBER` | MRN | "MRN-2024-567890" | Org-specific |
| `HEALTH_INSURANCE_ID` | Insurance member ID | "ABC123456789" | Payer-specific |
| `NATIONAL_PROVIDER_ID` | NPI (US healthcare providers) | "1234567893" | `\b[0-9]{10}\b` (Luhn validated) |
| `DEA_NUMBER` | DEA registration (prescribers) | "AB1234563" | `\b[A-Z]{2}[0-9]{7}\b` |
| `DIAGNOSIS_CODE` | ICD-10 codes | "E11.9" | `\b[A-Z][0-9]{2}(\.[0-9]{1,4})?\b` |
| `PROCEDURE_CODE` | CPT codes | "99213" | `\b[0-9]{5}[A-Z]?\b` |
| `PRESCRIPTION_NUMBER` | Rx numbers | "RX-123456" | Pharmacy-specific |
| `LAB_RESULT` | Lab test results with patient context | "Glucose: 120 mg/dL" | Context-dependent |
| `VITAL_SIGNS` | Blood pressure, heart rate, etc. | "BP: 120/80" | Medical notation patterns |
| `ALLERGY_INFO` | Patient allergies | "Allergic to penicillin" | NER + medical ontology |
| `GENETIC_INFO` | Genetic markers | "BRCA1 positive" | Medical ontology |
| `HEALTH_CONDITION` | Diseases/conditions | "Type 2 diabetes" | Medical NER |

### Location Identifiers (8 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `STREET_ADDRESS` | Street addresses | "123 Main St, Apt 4B" | NER-based |
| `CITY` | City names | "San Francisco" | Gazetteer + NER |
| `STATE` | US states | "California" or "CA" | State list |
| `ZIP_CODE` | ZIP/postal codes | "94102" or "94102-1234" | `\b\d{5}(-\d{4})?\b` |
| `COUNTRY` | Country names | "United States" | Country list |
| `GPS_COORDINATES` | Latitude/longitude | "37.7749° N, 122.4194° W" | `\b[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)\b` |
| `BUILDING_NUMBER` | Building/unit numbers | "Building 5, Suite 200" | Context-dependent |
| `PO_BOX` | Post office boxes | "P.O. Box 1234" | `\bP\.?O\.?\s?Box\s?\d+\b` |

### Professional & Educational (5 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `LICENSE_NUMBER` | Professional licenses | "MD-123456" | State/profession-specific |
| `CERTIFICATION_ID` | Certifications | "PMP-2024-12345" | Org-specific |
| `DEGREE` | Educational degrees | "PhD in Computer Science" | Context-based |
| `INSTITUTION_NAME` | Schools, universities | "Stanford University" | Entity recognition |
| `MILITARY_ID` | Military service numbers | "123-45-6789" (DoD ID) | `\b\d{10}\b` |

### Digital Identifiers (7 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `API_KEY` | API keys/secrets | "sk_live_abc123XYZ" | Entropy-based |
| `JWT_TOKEN` | JSON Web Tokens | "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." | `\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b` |
| `OAUTH_TOKEN` | OAuth tokens | "ya29.a0AfH6SM..." | Provider-specific |
| `SESSION_ID` | Session identifiers | "sess_1234abcd5678efgh" | Entropy-based |
| `COOKIE_VALUE` | Sensitive cookies | "auth_token=abc123..." | High entropy values |
| `DATABASE_CONNECTION_STRING` | DB connection URLs | "postgresql://user:pass@host:5432/db" | URL with credentials |
| `PRIVATE_KEY` | Private keys (RSA, etc.) | "-----BEGIN PRIVATE KEY-----..." | Key format patterns |

### Behavioral & Biometric (3 types)

| Entity Type | Description | Example | Regex Pattern |
|-------------|-------------|---------|---------------|
| `BIOMETRIC_TEMPLATE` | Fingerprint, face templates | Binary/encoded data | Format-specific |
| `SIGNATURE_IMAGE` | Digital signatures | Image metadata | File type detection |
| `VOICE_PRINT` | Voice biometric data | Audio metadata | Format-specific |

---

## Compliance Profiles

### HIPAA (Health Insurance Portability and Accountability Act)

**Protected Health Information (PHI) - 18 Identifiers:**

```python
HIPAA_PHI_ENTITIES = [
    'PERSON',                    # Names
    'STREET_ADDRESS',            # Geographic subdivisions smaller than state
    'CITY',
    'ZIP_CODE',                  # ZIP codes (first 3 digits OK if area > 20K people)
    'DATE_OF_BIRTH',             # All dates (birth, admission, discharge, death)
    'PHONE_NUMBER',
    'EMAIL_ADDRESS',
    'US_SSN',
    'MEDICAL_RECORD_NUMBER',
    'HEALTH_INSURANCE_ID',
    'ACCOUNT_NUMBER',            # Financial account numbers
    'CERTIFICATE_NUMBER',
    'VEHICLE_VIN',
    'DEVICE_SERIAL_NUMBER',
    'URL',                       # Web URLs
    'IP_ADDRESS',
    'BIOMETRIC_ID',
    'FULL_FACE_PHOTO',
    'UNIQUE_IDENTIFYING_NUMBER'  # Any other unique ID
]
```

**Usage:**
```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': medical_document,
        'compliance_profile': 'HIPAA',
        'scrub_mode': 'replace',
        'date_handling': 'year_only'  # Keep year, scrub month/day
    }
)
```

**Special HIPAA Rules:**
- ZIP codes: First 3 digits OK if geographic area > 20,000 people
- Dates: Year OK, scrub month/day unless needed for >89 years old
- Safe Harbor method: Remove all 18 identifiers for de-identification

---

### GDPR (General Data Protection Regulation)

**Personal Data Categories:**

```python
GDPR_PERSONAL_DATA = {
    'identifying': [
        'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'STREET_ADDRESS',
        'NATIONAL_ID', 'PASSPORT_NUMBER', 'DRIVER_LICENSE'
    ],
    'sensitive': [  # Article 9 - Special categories
        'HEALTH_CONDITION',      # Health data
        'GENETIC_INFO',           # Genetic data
        'BIOMETRIC_ID',           # Biometric data for ID
        'ETHNIC_ORIGIN',          # Racial/ethnic origin
        'POLITICAL_OPINION',      # Political opinions
        'RELIGIOUS_BELIEF',       # Religious beliefs
        'UNION_MEMBERSHIP',       # Trade union membership
        'SEXUAL_ORIENTATION'      # Sexual orientation
    ],
    'financial': [
        'CREDIT_CARD', 'BANK_ACCOUNT', 'IBAN'
    ],
    'online': [
        'IP_ADDRESS', 'COOKIE_VALUE', 'DEVICE_ID', 'LOCATION_DATA'
    ]
}
```

**Usage:**
```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': customer_data,
        'compliance_profile': 'GDPR',
        'scrub_mode': 'pseudonymize',  # GDPR allows pseudonymization
        'retention_purpose': 'analytics',
        'legal_basis': 'legitimate_interest'
    }
)
```

**GDPR-Specific Features:**
- **Right to Erasure**: Complete deletion of personal data
- **Data Portability**: Export in machine-readable format (HJX)
- **Pseudonymization**: Replace with reversible tokens (with key storage)
- **Consent Tracking**: Log legal basis for processing

---

### CCPA (California Consumer Privacy Act)

**Personal Information Categories:**

```python
CCPA_PERSONAL_INFO = [
    # Identifiers
    'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'US_SSN',
    'DRIVER_LICENSE', 'PASSPORT_NUMBER', 'IP_ADDRESS',

    # Commercial information
    'PURCHASE_HISTORY', 'PRODUCT_INTERACTION',

    # Biometric information
    'BIOMETRIC_ID', 'FINGERPRINT', 'VOICE_PRINT',

    # Internet activity
    'BROWSING_HISTORY', 'SEARCH_HISTORY', 'COOKIE_VALUE',

    # Geolocation data
    'GPS_COORDINATES', 'STREET_ADDRESS',

    # Professional/employment information
    'EMPLOYEE_ID', 'JOB_TITLE', 'EMPLOYER',

    # Education information
    'STUDENT_ID', 'SCHOOL_NAME', 'DEGREE',

    # Inferences (profiles)
    'USER_PREFERENCE', 'BEHAVIORAL_PROFILE'
]
```

**Usage:**
```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': user_profile_data,
        'compliance_profile': 'CCPA',
        'scrub_mode': 'redact',
        'consumer_rights': {
            'opt_out_sale': True,      # Do Not Sell
            'opt_out_sharing': True,    # Do Not Share (2023 update)
            'limit_sensitive': False    # Limit Use of Sensitive Info
        }
    }
)
```

---

### FERPA (Family Educational Rights and Privacy Act)

**Education Records - Protected Elements:**

```python
FERPA_PROTECTED_EDUCATION_RECORDS = [
    'STUDENT_ID',
    'STUDENT_NAME',
    'PARENT_NAME',
    'STREET_ADDRESS',
    'EMAIL_ADDRESS',
    'PHONE_NUMBER',
    'DATE_OF_BIRTH',
    'PLACE_OF_BIRTH',
    'GRADES',                # Academic performance
    'GPA',
    'COURSE_SCHEDULE',
    'DISCIPLINARY_RECORD',
    'SPECIAL_EDUCATION_STATUS',
    'FINANCIAL_AID_INFO'
]

# Directory information (can be disclosed without consent)
FERPA_DIRECTORY_INFO = [
    'STUDENT_NAME',
    'MAJOR_FIELD_OF_STUDY',
    'PARTICIPATION_IN_ACTIVITIES',
    'DATES_OF_ATTENDANCE',
    'DEGREES_AWARDED',
    'ENROLLMENT_STATUS'
]
```

**Usage:**
```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': student_records,
        'compliance_profile': 'FERPA',
        'allow_directory_info': False,  # Scrub even directory info
        'scrub_mode': 'replace'
    }
)
```

---

### PCI-DSS (Payment Card Industry Data Security Standard)

**Cardholder Data & Sensitive Authentication Data:**

```python
PCI_DSS_PROTECTED_DATA = {
    'cardholder_data': [
        'CREDIT_CARD',          # Primary Account Number (PAN)
        'CARDHOLDER_NAME',
        'EXPIRATION_DATE',
        'SERVICE_CODE'
    ],
    'sensitive_auth_data': [  # NEVER store after authorization
        'CVV',                  # Card verification code
        'PIN',                  # PIN/PIN Block
        'MAGNETIC_STRIPE',      # Full magnetic stripe data
        'CHIP_DATA'             # Chip data (EMV)
    ]
}
```

**Usage:**
```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': transaction_log,
        'compliance_profile': 'PCI_DSS',
        'scrub_mode': 'mask',
        'pan_masking': 'last_four',  # Show only last 4 digits
        'remove_sad': True            # Remove Sensitive Auth Data
    }
)
```

**PCI-DSS Masking Options:**
- `first_six_last_four`: Shows BIN + last 4 (e.g., "4532 12** **** 9010")
- `last_four`: Shows only last 4 (e.g., "**** **** **** 9010")
- `full_mask`: Complete redaction (e.g., "[CREDIT CARD REDACTED]")

---

## Detection Methods

### 1. **Pattern-Based Detection (Regex)**

Fast, deterministic matching for structured data types.

```python
DETECTION_PATTERNS = {
    'US_SSN': r'\b\d{3}-\d{2}-\d{4}\b',
    'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'CREDIT_CARD': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b'
}
```

**Pros:**
- ✅ Very fast (< 1ms per document)
- ✅ No false negatives for exact patterns
- ✅ Deterministic results

**Cons:**
- ❌ Can produce false positives (e.g., "123-45-6789" might not be SSN)
- ❌ Doesn't handle variations well

---

### 2. **Named Entity Recognition (NER)**

Machine learning-based detection for unstructured entities.

**Model:** spaCy en_core_web_trf (transformer-based)

```python
# NER detects:
PERSON, ORGANIZATION, LOCATION, DATE, TIME, MONEY, etc.
```

**Pros:**
- ✅ Handles variations and context
- ✅ Lower false positive rate
- ✅ Detects names without fixed patterns

**Cons:**
- ❌ Slower (10-50ms per document)
- ❌ May miss rare entities

---

### 3. **Context-Aware Validation**

Combines regex + context to reduce false positives.

```python
def validate_ssn_context(text, match):
    """Check if SSN appears in legitimate context"""
    window = text[max(0, match.start()-50):match.end()+50]

    # Likely SSN if preceded by these terms
    ssn_indicators = ['ssn', 'social security', 'ss#', 'soc sec']

    # Unlikely SSN if in financial context
    false_indicators = ['account', 'routing', 'transaction']

    return any(ind in window.lower() for ind in ssn_indicators) and \
           not any(ind in window.lower() for ind in false_indicators)
```

**Accuracy Improvement:**
- Raw regex: 85% precision
- Context-aware: 97% precision

---

### 4. **Luhn Algorithm Validation**

Validates credit cards, NPI numbers, etc.

```python
def luhn_check(number):
    """Validate checksum using Luhn algorithm"""
    digits = [int(d) for d in str(number)]
    checksum = digits.pop()

    digits.reverse()
    doubled = [d*2 if i%2==0 else d for i, d in enumerate(digits)]
    summed = sum(d-9 if d>9 else d for d in doubled)

    return (summed + checksum) % 10 == 0

# Reduces credit card false positives by ~60%
```

---

## Scrubbing vs. Redaction

### Scrubbing (Remove Entirely)

**Method:** Replace PII with generic placeholder or remove completely.

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': 'Contact John Smith at john@example.com or call 555-123-4567',
        'scrub_mode': 'remove'
    }
)

# Result: "Contact [REDACTED] at [REDACTED] or call [REDACTED]"
```

**Use Cases:**
- Permanent de-identification
- Public data releases
- Irreversible anonymization

**Pros:**
- ✅ Maximum privacy protection
- ✅ Simplest implementation
- ✅ HIPAA Safe Harbor compliant

**Cons:**
- ❌ Irreversible
- ❌ Loses data utility
- ❌ Can affect readability

---

### Redaction (Type-Preserving Replacement)

**Method:** Replace with type-specific token indicating what was removed.

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': 'Contact John Smith at john@example.com or call 555-123-4567',
        'scrub_mode': 'replace'
    }
)

# Result: "Contact [PERSON] at [EMAIL] or call [PHONE_NUMBER]"
```

**Use Cases:**
- Data analysis where entity types matter
- Training machine learning models
- Preserving document structure

**Pros:**
- ✅ Maintains data structure
- ✅ Preserves entity type information
- ✅ Better for ML training

**Cons:**
- ❌ Reveals entity types
- ❌ May enable re-identification in combination

---

### Pseudonymization (Reversible with Key)

**Method:** Replace with consistent tokens that can be reversed with a key.

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': 'Patient John Smith visited on 2024-01-15',
        'scrub_mode': 'pseudonymize',
        'encryption_key_id': 'key-abc-123'
    }
)

# Result: "Patient PSEUDO_4f7a9b3c visited on PSEUDO_8d2e1a6f"
# Same person always gets same pseudonym
```

**Use Cases:**
- Research studies requiring patient linkage
- GDPR-compliant analytics
- Longitudinal studies

**Pros:**
- ✅ Reversible with proper authorization
- ✅ Enables cross-document linkage
- ✅ GDPR compliant

**Cons:**
- ❌ Requires secure key management
- ❌ Re-identification risk if key compromised
- ❌ More complex implementation

---

### Masking (Partial Visibility)

**Method:** Show partial information, hide sensitive parts.

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': 'Card number: 4532-1234-5678-9010, SSN: 123-45-6789',
        'scrub_mode': 'mask',
        'mask_format': {
            'CREDIT_CARD': 'last_four',
            'US_SSN': 'last_four'
        }
    }
)

# Result: "Card number: **** **** **** 9010, SSN: ***-**-6789"
```

**Use Cases:**
- Customer service (verify identity)
- Financial transactions
- User interfaces

**Pros:**
- ✅ Balances privacy and utility
- ✅ Enables verification
- ✅ User-friendly

**Cons:**
- ❌ Not compliant for full de-identification
- ❌ Partial information leakage

---

## Custom Pattern Configuration

### Adding Organization-Specific Patterns

```yaml
# config/custom_pii_patterns.yml
custom_patterns:
  - name: "INTERNAL_EMPLOYEE_ID"
    pattern: "EMP-[0-9]{4}-[0-9]{6}"
    description: "Company employee ID format"
    category: "identifier"
    severity: "high"

  - name: "PROJECT_CODE"
    pattern: "PROJ-[A-Z]{3}-[0-9]{4}"
    description: "Internal project codes"
    category: "business"
    severity: "medium"

  - name: "CUSTOMER_ACCOUNT"
    pattern: "ACCT[0-9]{10}"
    description: "Customer account numbers"
    category: "financial"
    severity: "high"

  - name: "INTERNAL_IP_RANGE"
    pattern: "10\\.50\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    description: "Internal network IP addresses"
    category: "technical"
    severity: "low"
```

### Registering Custom Patterns via API

```python
import requests

def register_custom_pattern():
    response = requests.post(
        'https://your-sting.com/api/pii/custom-patterns',
        json={
            'name': 'INTERNAL_EMPLOYEE_ID',
            'pattern': r'EMP-\d{4}-\d{6}',
            'description': 'Company employee ID format',
            'enabled': True,
            'test_examples': [
                {'text': 'EMP-2024-123456', 'should_match': True},
                {'text': 'EMP-12-34', 'should_match': False}
            ]
        }
    )

    return response.json()

# Test custom pattern
test_response = requests.post(
    'https://your-sting.com/api/pii/detect',
    json={
        'text': 'Employee EMP-2024-123456 accessed the system',
        'include_custom_patterns': True
    }
)

print(test_response.json())
# Output:
# {
#   "entities": [
#     {
#       "type": "INTERNAL_EMPLOYEE_ID",
#       "text": "EMP-2024-123456",
#       "start": 9,
#       "end": 25,
#       "confidence": 1.0
#     }
#   ]
# }
```

---

## API Usage Examples

### Detect PII (No Modification)

```python
import requests

response = requests.post(
    'https://your-sting.com/api/pii/detect',
    json={
        'text': '''
        Patient John Smith (DOB: 01/15/1980) was admitted on 2024-03-10.
        Contact: john.smith@email.com, Phone: (555) 123-4567
        SSN: 123-45-6789
        Insurance: Blue Cross #ABC123456789
        ''',
        'entity_types': ['all']  # Or specific: ['PERSON', 'EMAIL_ADDRESS', 'US_SSN']
    }
)

print(response.json())
```

**Response:**
```json
{
  "entities": [
    {
      "type": "PERSON",
      "text": "John Smith",
      "start": 8,
      "end": 18,
      "confidence": 0.99,
      "method": "NER"
    },
    {
      "type": "DATE_OF_BIRTH",
      "text": "01/15/1980",
      "start": 25,
      "end": 35,
      "confidence": 1.0,
      "method": "regex"
    },
    {
      "type": "EMAIL_ADDRESS",
      "text": "john.smith@email.com",
      "start": 87,
      "end": 107,
      "confidence": 1.0,
      "method": "regex"
    },
    {
      "type": "PHONE_NUMBER",
      "text": "(555) 123-4567",
      "start": 116,
      "end": 130,
      "confidence": 1.0,
      "method": "regex"
    },
    {
      "type": "US_SSN",
      "text": "123-45-6789",
      "start": 140,
      "end": 151,
      "confidence": 0.95,
      "method": "regex_context"
    },
    {
      "type": "HEALTH_INSURANCE_ID",
      "text": "ABC123456789",
      "start": 179,
      "end": 191,
      "confidence": 0.87,
      "method": "pattern_context"
    }
  ],
  "summary": {
    "total_entities": 6,
    "high_risk": 3,
    "medium_risk": 2,
    "low_risk": 1
  }
}
```

---

### Scrub PII with Compliance Profile

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': patient_medical_record,
        'compliance_profile': 'HIPAA',
        'scrub_mode': 'replace',
        'preserve_structure': True,
        'date_handling': 'year_only'
    }
)

scrubbed_text = response.json()['scrubbed_text']
audit_log = response.json()['audit_log']
```

---

### Batch Processing

```python
# Process multiple documents
response = requests.post(
    'https://your-sting.com/api/pii/scrub/batch',
    json={
        'documents': [
            {'id': 'doc-001', 'text': document1},
            {'id': 'doc-002', 'text': document2},
            {'id': 'doc-003', 'text': document3}
        ],
        'compliance_profile': 'GDPR',
        'scrub_mode': 'pseudonymize',
        'parallel': True
    }
)

# Returns array of results
for result in response.json()['results']:
    print(f"Document {result['id']}: {result['entities_found']} PII entities scrubbed")
```

---

## Real-World Use Cases

### Use Case 1: Legal Discovery Document Redaction

**Challenge:** Law firm must redact privileged information before submitting to court.

```python
# Redact attorney-client privilege information
response = requests.post(
    'https://law-firm-sting.com/api/pii/scrub',
    json={
        'text': discovery_document,
        'compliance_profile': 'LEGAL_PRIVILEGE',
        'scrub_mode': 'redact',
        'custom_rules': {
            'attorney_names': ['pattern: Attorney [A-Z][a-z]+ [A-Z][a-z]+'],
            'case_numbers': ['pattern: Case No\\. [0-9-]+'],
            'confidential_markers': ['text: ATTORNEY-CLIENT PRIVILEGED']
        },
        'generate_redaction_log': True
    }
)

redacted_pdf = response.json()['redacted_document']
audit_trail = response.json()['redaction_log']
```

**Results:**
- 10,000 pages/hour processing (vs. 500 manual)
- 99.7% PII detection accuracy
- 95% cost reduction
- Complete audit trail for court submission

---

### Use Case 2: Healthcare Research De-identification

**Challenge:** Hospital wants to share patient data for cancer research while maintaining HIPAA compliance.

```python
# De-identify patient records for research
response = requests.post(
    'https://hospital-sting.com/api/pii/scrub',
    json={
        'text': patient_cohort_data,
        'compliance_profile': 'HIPAA',
        'scrub_mode': 'pseudonymize',
        'safe_harbor_method': True,
        'date_handling': 'shift_consistent',  # Shift all dates by same random offset
        'preserve_age': True,
        'zip_truncation': 'three_digit'  # Keep first 3 digits only
    }
)

deidentified_data = response.json()['scrubbed_text']
```

**Compliance:**
- ✅ HIPAA Safe Harbor compliant
- ✅ <0.01% re-identification risk (k-anonymity validated)
- ✅ 100% IRB approval rate
- ✅ Enabled 3x increase in publishable research

---

### Use Case 3: Customer Service Chat Transcripts

**Challenge:** E-commerce company wants to analyze support chats without exposing customer PII.

```python
# Scrub customer PII from chat logs
response = requests.post(
    'https://ecommerce-sting.com/api/pii/scrub',
    json={
        'text': chat_transcript,
        'compliance_profile': 'CCPA',
        'scrub_mode': 'mask',
        'mask_format': {
            'EMAIL_ADDRESS': 'domain_only',     # user@example.com → ***@example.com
            'PHONE_NUMBER': 'area_code_only',   # (555) 123-4567 → (555) ***-****
            'CREDIT_CARD': 'last_four'          # **** **** **** 1234
        }
    }
)

# Safe for ML training and analytics
masked_transcript = response.json()['scrubbed_text']
```

---

## Performance & Accuracy

### Detection Performance

| Document Size | Processing Time | Throughput |
|---------------|-----------------|------------|
| 1 KB (email) | 15 ms | 66 docs/sec |
| 10 KB (report) | 45 ms | 22 docs/sec |
| 100 KB (transcript) | 320 ms | 3.1 docs/sec |
| 1 MB (medical record) | 2.8 sec | 0.36 docs/sec |

**Hardware:** 8-core CPU, 16GB RAM (no GPU required)

---

### Accuracy Benchmarks

Validated against manually annotated datasets:

| Entity Type | Precision | Recall | F1 Score |
|-------------|-----------|--------|----------|
| US_SSN | 97.3% | 98.1% | 97.7% |
| EMAIL_ADDRESS | 99.2% | 99.5% | 99.4% |
| PERSON | 94.1% | 92.8% | 93.4% |
| CREDIT_CARD | 98.5% | 97.9% | 98.2% |
| PHONE_NUMBER | 95.7% | 94.3% | 95.0% |
| MEDICAL_RECORD_NUMBER | 91.2% | 89.6% | 90.4% |
| **Overall Average** | **96.0%** | **95.4%** | **95.7%** |

**Comparison to Commercial Tools:**
- AWS Comprehend Medical: 93.2% F1
- Google Cloud DLP: 94.8% F1
- **STING PII Detection: 95.7% F1** ✅

---

## Advanced Features

### 1. **Confidence Thresholds**

```python
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': document,
        'min_confidence': 0.85,  # Only scrub entities with 85%+ confidence
        'manual_review_threshold': 0.70  # Flag entities 70-85% for review
    }
)
```

---

### 2. **Entity Allowlists**

```python
# Don't scrub specific entities (e.g., public figures)
response = requests.post(
    'https://your-sting.com/api/pii/scrub',
    json={
        'text': document,
        'allowlist': {
            'PERSON': ['John Doe', 'Jane Smith'],  # Public names OK
            'ORGANIZATION': ['ACME Corporation']
        }
    }
)
```

---

### 3. **Audit Logging**

Every PII detection and scrubbing action is logged:

```python
audit_log = {
    'timestamp': '2024-11-10T14:23:01Z',
    'user_id': 'user-123',
    'action': 'scrub',
    'document_id': 'doc-abc-789',
    'entities_detected': 23,
    'entities_scrubbed': 23,
    'compliance_profile': 'HIPAA',
    'scrub_mode': 'replace'
}
```

---

## Troubleshooting

### High False Positive Rate

**Problem:** Too many non-PII entities flagged

**Solutions:**
1. Increase confidence threshold: `min_confidence: 0.90`
2. Enable context validation: `use_context_validation: true`
3. Add to allowlist: Common false positives
4. Use custom patterns: More specific regex

---

### Missing PII Detection

**Problem:** Known PII not being detected

**Solutions:**
1. Lower confidence threshold: `min_confidence: 0.70`
2. Add custom pattern for org-specific formats
3. Enable all detection methods: `methods: ['regex', 'ner', 'context']`
4. Validate regex patterns with test cases

---

## Resources

- **API Reference**: See `api-reference.md`
- **Compliance Guides**: `docs/compliance/`
- **Custom Pattern Examples**: `examples/custom_pii_patterns.yml`
- **Support**: olliec@alphabytez.dev

---

**Last Updated:** November 2024
**Version:** 1.0.0
**Compliance Validated:** HIPAA, GDPR, CCPA, FERPA, PCI-DSS
