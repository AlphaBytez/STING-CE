# 🎯 Realistic Test Data Sources for STING PII Detection

*Comprehensive guide to GitHub repositories and public datasets for enterprise-scale PII detection testing*

## Overview

This document provides curated sources of realistic test data for validating STING's enhanced PII detection capabilities at enterprise scale. All sources listed prioritize **synthetic/anonymized data** to ensure compliance with privacy regulations while providing realistic testing scenarios.

## 🏥 Medical/Healthcare Data Sources

### Synthea™ - The Gold Standard for Healthcare Data
- **Repository**: [synthetichealth/synthea](https://github.com/synthetichealth/synthea)
- **Description**: Open-source synthetic patient generator that models complete medical histories
- **Data Formats**: C-CDA, FHIR, CSV, JSON
- **Scale**: Unlimited synthetic patients from birth to present day
- **HIPAA Compliance**: 100% synthetic - no real patient data
- **Key Features**:
  - Realistic patient demographics and medical histories
  - Disease progression modeling based on CDC/NIH statistics
  - Integration with healthcare interoperability standards
  - Customizable disease modules for specific conditions

**Usage for STING:**
```bash
# Download Synthea
git clone https://github.com/synthetichealth/synthea.git
cd synthea

# Generate 1000 patients for testing
./run_synthea -p 1000 --exporter.fhir.export=true --exporter.csv.export=true
```

### Medical Records Libraries
- **Cambridge Health Data Repository**: Large-scale anonymized health records
- **MIMIC-III**: Critical care database (requires training completion)
- **eICU**: Multi-center ICU database with de-identified patient data

**Estimated PII Elements per Patient**:
- Medical Record Numbers: 2-4 per patient
- DEA/NPI Numbers: 3-6 per encounter
- Lab Results with PHI: 15-30 values
- Prescription Data: 5-15 medications
- Insurance Information: 2-3 identifiers

## ⚖️ Legal Document Sources

### Court Records and Legal Datasets
- **Repository**: [freelawproject/courtlistener](https://github.com/freelawproject/courtlistener)
- **Description**: Fully-searchable archive of 5M+ court documents
- **Coverage**: US federal and state courts, 1950-present
- **Data Types**: Opinions, oral arguments, financial records, filings
- **Anonymization**: Real cases but public records (no attorney-client privilege)

### Contract and Agreement Datasets
- **Repository**: [neelguha/legal-ml-datasets](https://github.com/neelguha/legal-ml-datasets)
- **Key Dataset**: CUAD (Contract Understanding Atticus Dataset)
- **Content**: 13,000+ annotations across 510 commercial contracts
- **Legal Concepts**: 50+ contract types with expert labeling
- **Use Case**: Perfect for testing settlement amounts, case numbers, contract IDs

### Synthetic Legal Document Generator (Custom)
**Based on STING's existing `LegalDemoGenerator`**:
```python
# Generate enterprise-scale legal test data
legal_gen = LegalDemoGenerator()
for i in range(10000):
    case_file = legal_gen.generate_case_file()
    contract = legal_gen.generate_contract()
    # Process through STING PII detection
```

**Estimated PII Elements per Document**:
- Case Numbers: 1-3 per document
- Attorney Bar Numbers: 2-5 per case
- Settlement Amounts: $10K-$10M range
- Client Information: 5-10 PII elements
- Financial Terms: 3-8 monetary values

## 💳 Financial/Banking Data Sources

### Credit Card and Banking Datasets
- **Repository**: [amazon-science/fraud-dataset-benchmark](https://github.com/amazon-science/fraud-dataset-benchmark)
- **Description**: Compilation of fraud detection datasets
- **Synthetic Credit Cards**: Generated using Sparkov tool
- **Features**: Transaction date, card numbers, merchant data, amounts
- **Scale**: 100K+ transactions per dataset

### Loan Application Datasets
- **Repository**: [JLZml/Credit-Scoring-Data-Sets](https://github.com/JLZml/Credit-Scoring-Data-Sets)
- **Content**: Credit scoring datasets from financial institutions
- **Coverage**: Benelux, UK, and US financial data
- **Use Case**: Perfect for testing financial PII detection

### LendingClub Dataset
- **Source**: [Kaggle LendingClub Data](https://www.kaggle.com/datasets/wordsforthewise/lending-club)
- **Scale**: 2.26M loan applications (2007-2018)
- **PII Elements**: SSN (anonymized), employment data, addresses, income
- **Size**: ~2GB of financial records

**Estimated PII Elements per Application**:
- Credit Card Numbers: 1-3 per applicant
- Bank Account Numbers: 2-4 accounts
- SSN/Tax ID: 1 per person
- Income/Financial Data: 5-10 values
- Employment Information: 3-5 fields

## 🏢 Enterprise-Scale Processing Architecture

### Recommended Testing Pipeline

1. **Small Scale (1K records)**:
   - Synthea: 100 patients = ~500 medical PII elements
   - Legal: 100 case files = ~800 legal PII elements  
   - Financial: 100 applications = ~600 financial PII elements

2. **Medium Scale (10K records)**:
   - Combined datasets = ~50K PII elements
   - Processing target: <30 seconds total
   - Queue-based processing with Redis

3. **Enterprise Scale (100K+ records)**:
   - LendingClub full dataset = ~2M records
   - Estimated 10M+ PII elements
   - Distributed processing with worker bees
   - Progress tracking and batch reporting

### Queue-Based Processing Implementation

```python
# Enterprise-scale PII processing queue
class EnterpriseScalePIIProcessor:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis', port=6379)
        self.batch_size = 1000
        
    async def process_large_dataset(self, dataset_path):
        # Split into batches
        batches = self.create_batches(dataset_path)
        
        # Queue all batches
        for batch in batches:
            self.redis_client.lpush('pii_processing_queue', 
                                   json.dumps(batch))
        
        # Start worker bees
        await self.start_worker_bees(num_workers=5)
        
    async def worker_bee_processor(self):
        while True:
            batch_data = self.redis_client.brpop('pii_processing_queue')
            if batch_data:
                batch = json.loads(batch_data[1])
                results = self.process_batch(batch)
                self.store_results(results)
```

## 📊 Data Source Quality Matrix

| Source | Realism | Scale | PII Density | STING Compatibility | Setup Effort |
|--------|---------|--------|-------------|-------------------|-------------|
| **Synthea** | ⭐⭐⭐⭐⭐ | Unlimited | High | Perfect | Low |
| **CourtListener** | ⭐⭐⭐⭐ | 5M+ docs | Medium | Good | Medium |
| **LendingClub** | ⭐⭐⭐⭐ | 2M records | High | Perfect | Low |
| **CUAD Contracts** | ⭐⭐⭐⭐ | 13K contracts | Medium | Good | Low |
| **Fraud Benchmark** | ⭐⭐⭐ | 100K+ | Low | Good | Low |

## 🚀 Quick Start Implementation

### 1. Download and Setup Test Data

```bash
# Create test data directory
mkdir -p ~/sting_test_data/{medical,legal,financial}

# Download Synthea (medical data)
cd ~/sting_test_data/medical
git clone https://github.com/synthetichealth/synthea.git
cd synthea && ./run_synthea -p 1000

# Download LendingClub data (requires Kaggle API)
cd ~/sting_test_data/financial
kaggle datasets download -d wordsforthewise/lending-club

# Generate synthetic legal data using STING's generator
cd ~/sting_test_data/legal  
python3 ~/Documents/GitHub/STING-CE/STING/app/services/demo_data_generator.py
```

### 2. Create Enterprise Processing Script

```bash
#!/bin/bash
# enterprise_pii_test.sh - Process large datasets with STING

echo "🎯 ENTERPRISE PII DETECTION TEST"
echo "Processing 10K records across medical/legal/financial domains..."

# Process medical data (Synthea output)
python3 process_large_dataset.py \
  --input ~/sting_test_data/medical/output/csv \
  --type medical \
  --batch-size 1000

# Process financial data (LendingClub)
python3 process_large_dataset.py \
  --input ~/sting_test_data/financial/accepted_2007_to_2018Q4.csv \
  --type financial \
  --batch-size 1000

# Process legal data (Generated)
python3 process_large_dataset.py \
  --input ~/sting_test_data/legal \
  --type legal \
  --batch-size 500

echo "✅ Enterprise-scale testing complete!"
echo "📊 Check results in ~/sting_test_results/"
```

## 🔍 Performance Benchmarking

### Expected Performance Targets

**Processing Speed**:
- 1K records: <5 seconds
- 10K records: <30 seconds  
- 100K records: <5 minutes
- 1M records: <30 minutes

**PII Detection Accuracy** (based on synthetic data):
- Medical PII: 95%+ precision
- Legal PII: 92%+ precision
- Financial PII: 98%+ precision
- Cross-domain contamination: 90%+ detection

**Memory Usage**:
- Batch processing: <2GB per worker
- Queue overhead: <500MB
- Total system: <8GB for 100K records

## 🎭 Demo Scenarios with Real Data

### Medical Office Demo (HIPAA Compliance)
```bash
# Generate 500 realistic patients
./run_synthea -p 500 --state Massachusetts

# Upload to STING honey jar
curl -X POST https://localhost:8443/api/honey-jars/medical-demo/documents \
  -F "file=@synthea_output.csv" \
  -H "Authorization: Bearer $STING_TOKEN"

# Show real-time PII detection
# Expected: 2000+ PHI elements detected
# Compliance: HIPAA violations flagged
# Demo impact: "Wow, 2000 patient records scanned in 10 seconds!"
```

### Law Firm Demo (Attorney-Client Privilege)
```bash
# Use real contract dataset (CUAD)
wget -O contracts.zip "https://github.com/atticus-project/cuad/raw/master/CUAD_v1.zip"

# Process through STING
# Expected: 500+ legal PII elements per contract
# Compliance: Attorney-client privilege warnings
# Demo impact: "Protected client information automatically identified"
```

### Financial Institution Demo (PCI-DSS)
```bash  
# Use LendingClub subset (10K applications)
head -10000 accepted_2007_to_2018Q4.csv > lending_demo.csv

# Upload to STING
# Expected: 50K+ financial PII elements
# Compliance: PCI-DSS violations flagged  
# Demo impact: "Credit application data secured in real-time"
```

## ⚠️ Privacy and Compliance Notes

### Data Source Verification
- ✅ **Synthea**: 100% synthetic, no privacy concerns
- ✅ **CourtListener**: Public records, legally accessible
- ✅ **LendingClub**: Anonymized real data, research-approved
- ✅ **CUAD**: Academic dataset, properly anonymized
- ⚠️ **Always verify** dataset licenses before use

### STING Processing Compliance
- All test data processed locally (no cloud upload)
- PII detection results stored encrypted
- Original test data can be deleted after processing
- Demo mode: Use scrambled outputs only

## 📈 Scaling Beyond GitHub

### Commercial Data Providers
- **Faker.js**: Programmatic synthetic data generation
- **Mockaroo**: Web-based test data generation (1M+ records)
- **Gretel.ai**: AI-powered synthetic data (healthcare/financial)
- **DataFactory**: Enterprise test data management

### Industry Partnerships  
- **Healthcare**: Partner with EHR vendors for anonymized test data
- **Legal**: Work with legal tech companies for document samples
- **Financial**: Collaborate with fintech firms for transaction data

## 🎯 Next Steps for Implementation

1. **Immediate (Week 1)**:
   - Set up Synthea for medical data generation
   - Download and test LendingClub dataset
   - Create enterprise processing script

2. **Short-term (Month 1)**:
   - Implement queue-based processing with Redis
   - Build performance benchmarking suite
   - Create demo scenarios with real datasets

3. **Long-term (Quarter 1)**:
   - Scale to 1M+ record processing
   - Implement distributed worker bee architecture
   - Partner with data providers for continuous testing

---

*Last Updated: January 6, 2025*  
*For questions: Contact the STING development team*  
*Demo-ready datasets available in `/demo_data/realistic/`*