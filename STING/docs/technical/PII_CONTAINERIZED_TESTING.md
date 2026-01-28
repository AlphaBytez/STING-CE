# 🐳 STING PII Containerized Testing Architecture

*Technical documentation for the containerized PII detection testing system*

## Overview

The STING PII Containerized Testing system provides a dependency-free, portable testing environment for validating PII detection capabilities. This Docker-based solution eliminates common deployment issues while providing enterprise-scale testing capabilities.

## 🏗️ Architecture Components

### Container Stack
```
┌─────────────────────────────────────────────────────┐
│                  Host System                        │
├─────────────────────────────────────────────────────┤
│  Docker Engine                                      │
│  ├── sting-test-data-generator (OpenJDK 17)        │
│  │   ├── Synthea (Medical Data Generation)          │
│  │   ├── Python 3.9+ (Synthetic Data Generators)   │
│  │   ├── Embedded PII Detector                      │
│  │   └── Test Suite & Benchmarking                  │
│  └── Volume Mounts                                  │
│      ├── /data/output (Test Data)                   │
│      └── /data/results (Test Results)               │
└─────────────────────────────────────────────────────┘
```

### File Structure
```
docker/test-data-generator/
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Service orchestration
├── generate_test_data.py      # Synthetic data generation
├── pii_tester.py             # PII detection testing
└── .dockerignore             # Build exclusions

scripts/
├── generate_test_data.sh      # Data generation wrapper
├── test_pii_detection.sh      # Testing wrapper
└── demo_complete_pipeline.sh  # Full demo pipeline
```

## 🔧 Technical Implementation

### Container Configuration

#### Base Image Selection
```dockerfile
FROM openjdk:17-jdk-slim
```
**Rationale**: OpenJDK 17 provides stable Java runtime for Synthea while maintaining container size efficiency.

#### Dependency Installation
```dockerfile
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    wget \
    unzip \
    bc \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install pandas faker
```
**Key Dependencies**:
- **Git**: For Synthea repository cloning
- **Python 3 + Pandas**: Data processing and synthetic generation
- **Faker**: Realistic synthetic data patterns
- **bc**: Mathematical calculations in shell scripts

#### Volume Management
```yaml
volumes:
  - ./output:/data/output        # Test data output
  - ../../app/services:/app/sting_generators:ro  # Optional STING integration
```

### Embedded PII Detection Engine

The container includes a simplified but comprehensive PII detection engine that mirrors STING's core capabilities:

#### Pattern Library
```python
class ContainerizedPIIDetector:
    def _initialize_patterns(self) -> Dict[PIIType, re.Pattern]:
        return {
            # Medical patterns
            PIIType.MEDICAL_RECORD: re.compile(r'\b(?:MRN|Medical Record Number)[:\s]*([A-Z0-9]{6,12})\b', re.IGNORECASE),
            PIIType.DEA_NUMBER: re.compile(r'\b[A-Z]{2}\d{7}\b'),
            PIIType.NPI_NUMBER: re.compile(r'\b\d{10}\b'),
            
            # Legal patterns
            PIIType.CASE_NUMBER: re.compile(r'\b\d{4}-[A-Z]{2,4}-\d{3,8}\b'),
            PIIType.SETTLEMENT_AMOUNT: re.compile(r'\$[\d,]+(?:\.\d{2})?\b'),
            
            # Financial patterns
            PIIType.CREDIT_CARD: re.compile(r'\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14})\b'),
            PIIType.BANK_ACCOUNT: re.compile(r'\b\d{8,17}\b'),
            
            # General patterns
            PIIType.SSN: re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            PIIType.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }
```

#### Compliance Framework Mapping
```python
def _get_compliance_frameworks(self, pii_type: PIIType) -> List[ComplianceFramework]:
    mapping = {
        # HIPAA (Healthcare)
        PIIType.MEDICAL_RECORD: [ComplianceFramework.HIPAA],
        PIIType.DEA_NUMBER: [ComplianceFramework.HIPAA],
        
        # Attorney-Client Privilege
        PIIType.CASE_NUMBER: [ComplianceFramework.ATTORNEY_CLIENT],
        PIIType.SETTLEMENT_AMOUNT: [ComplianceFramework.ATTORNEY_CLIENT],
        
        # PCI-DSS (Financial)
        PIIType.CREDIT_CARD: [ComplianceFramework.PCI_DSS],
        PIIType.BANK_ACCOUNT: [ComplianceFramework.PCI_DSS],
        
        # GDPR (General Personal Data)
        PIIType.SSN: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
        PIIType.EMAIL: [ComplianceFramework.GDPR, ComplianceFramework.CCPA],
    }
    return mapping.get(pii_type, [])
```

#### Risk Assessment Algorithm
```python
def _get_risk_level(self, pii_type: PIIType) -> str:
    high_risk = {PIIType.SSN, PIIType.CREDIT_CARD, PIIType.SETTLEMENT_AMOUNT, PIIType.MEDICARE_ID}
    low_risk = {PIIType.EMAIL, PIIType.PHONE, PIIType.NAME}
    
    if pii_type in high_risk:
        return "high"
    elif pii_type in low_risk:
        return "low"
    else:
        return "medium"
```

### Synthetic Data Generation

#### Medical Data (Synthea Integration)
```python
def generate_medical_data(self, num_patients=1000):
    synthea_cmd = [
        "./run_synthea",
        "-p", str(num_patients),
        "--exporter.fhir.export=false",
        "--exporter.csv.export=true",
        f"--exporter.baseDirectory=/data/output/medical"
    ]
    
    result = subprocess.run(
        synthea_cmd,
        cwd="/app/synthea",
        timeout=1800  # 30 minute timeout
    )
```

#### Legal Data (Embedded Generator)
```python
def _create_legal_documents(self, num_docs):
    from faker import Faker
    fake = Faker()
    
    for i in range(num_docs):
        if i % 2 == 0:
            # Generate case file
            case_number = f"{random.randint(2020, 2024)}-PI-{random.randint(100000, 999999)}"
            settlement = f"${random.randint(50000, 500000):,}"
            # ... document template
        else:
            # Generate contract
            contract_id = f"CTR-{random.randint(2024, 2024)}-{random.randint(1000, 9999)}"
            # ... contract template
```

#### Financial Data (Embedded Generator)
```python
def _create_financial_documents(self, num_docs):
    for i in range(num_docs):
        loan_app = f"""
LOAN APPLICATION
Application ID: LA-{random.randint(100000, 999999)}
SSN: {fake.ssn()}
Credit Card: {fake.credit_card_number(card_type='visa')}
Bank Account: {fake.bban()}
Annual Income: ${random.randint(40000, 120000):,}
        """
```

## 📊 Performance Optimization

### Container Resource Management
```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2.0'
    reservations:
      memory: 1G
```

**Resource Allocation Strategy**:
- **Memory**: 4GB limit prevents system overload during large data generation
- **CPU**: 2 cores provide optimal performance for parallel processing
- **Reservations**: 1GB guaranteed memory for stable operation

### Processing Optimization

#### Batch Processing
```python
def process_batch(self, documents, batch_size=1000):
    """Process documents in optimized batches"""
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        results = []
        
        for doc in batch:
            detections = self.detector.detect_pii(doc)
            results.extend(detections)
        
        yield results
```

#### Memory Management
```python
def process_large_dataset(self, file_path):
    """Stream processing for large files"""
    if file_path.suffix == '.csv':
        # Process CSV in chunks to manage memory
        for chunk in pd.read_csv(file_path, chunksize=1000):
            for _, row in chunk.iterrows():
                text = self._format_record(row)
                yield self.detector.detect_pii(text)
```

## 🧪 Test Suite Architecture

### Test Scenario Framework
```python
class PIITestSuite:
    def run_demo_scenario_medical(self):
        """Medical HIPAA compliance scenario"""
        
    def run_demo_scenario_legal(self):
        """Legal attorney-client privilege scenario"""
        
    def run_demo_scenario_financial(self):
        """Financial PCI-DSS compliance scenario"""
        
    def run_performance_benchmark(self):
        """Enterprise performance testing"""
        
    def run_comprehensive_test(self):
        """Complete test suite execution"""
```

### Metrics Collection
```python
def collect_metrics(self, detections, processing_time):
    return {
        "processing_time": processing_time,
        "total_detections": len(detections),
        "detections_by_type": self._count_by_type(detections),
        "compliance_summary": self._count_by_compliance(detections),
        "risk_distribution": self._count_by_risk(detections),
        "confidence_stats": self._analyze_confidence(detections)
    }
```

### Results Aggregation
```python
def generate_comprehensive_report(self, scenarios):
    return {
        "test_timestamp": datetime.now().isoformat(),
        "scenarios": scenarios,
        "summary": {
            "total_scenarios": len(scenarios),
            "scenarios_passed": len([s for s in scenarios if s is not None]),
            "total_detections": sum(s.get("total_detections", 0) for s in scenarios),
            "average_processing_time": statistics.mean([s.get("processing_time", 0) for s in scenarios])
        }
    }
```

## 🔧 Build and Deployment

### Container Build Process
```bash
# Build container with caching
docker build -t sting-test-data-generator \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --cache-from sting-test-data-generator:latest \
  docker/test-data-generator/
```

### Automated Testing Pipeline
```bash
#!/bin/bash
# Automated CI/CD testing

# 1. Build container
docker build -t sting-pii-test .

# 2. Run data generation
docker run --rm -v ./output:/data/output \
  sting-pii-test python3 generate_test_data.py

# 3. Run PII detection tests
docker run --rm -v ./output:/data/output \
  sting-pii-test python3 pii_tester.py --scenario all

# 4. Validate results
python3 validate_test_results.py ./output/test_results/
```

### Multi-platform Support
```yaml
# docker-compose.yml platform configuration
services:
  test-data-generator:
    platform: linux/amd64  # Explicit platform for M1 Mac compatibility
    build:
      context: .
      platforms:
        - linux/amd64
        - linux/arm64
```

## 📈 Monitoring and Debugging

### Container Health Checks
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import sys; sys.exit(0)" || exit 1
```

### Debug Mode Activation
```bash
# Enable verbose logging
docker run --rm \
  -e STING_PII_DEBUG=true \
  -e PYTHONUNBUFFERED=1 \
  -v ./output:/data/output \
  sting-test-data-generator \
  python3 pii_tester.py --scenario medical
```

### Performance Profiling
```python
import cProfile
import pstats

def profile_pii_detection(func):
    """Decorator for profiling PII detection performance"""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # Top 10 functions
        
        return result
    return wrapper
```

## 🚨 Error Handling and Recovery

### Graceful Failure Handling
```python
def safe_execute(self, func, *args, **kwargs):
    """Execute function with comprehensive error handling"""
    try:
        return func(*args, **kwargs)
    except subprocess.TimeoutExpired:
        logger.error("Operation timed out")
        return None
    except MemoryError:
        logger.error("Insufficient memory for operation")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### Data Validation
```python
def validate_generated_data(self, output_dir):
    """Validate generated test data quality"""
    validation_results = {
        "medical_files": len(list(Path(output_dir).glob("medical/**/*.csv"))),
        "legal_files": len(list(Path(output_dir).glob("legal/*.txt"))),
        "financial_files": len(list(Path(output_dir).glob("financial/*.txt"))),
        "total_size_mb": sum(f.stat().st_size for f in Path(output_dir).rglob("*") if f.is_file()) / 1024 / 1024
    }
    
    # Validate minimum thresholds
    assert validation_results["medical_files"] > 0, "No medical files generated"
    assert validation_results["legal_files"] > 0, "No legal files generated"
    assert validation_results["financial_files"] > 0, "No financial files generated"
    
    return validation_results
```

## 🔗 Integration Points

### STING Core Integration
The containerized system can optionally integrate with STING's core PII detection:

```python
# Optional integration with actual STING hive_scrambler
try:
    sys.path.append('/app/sting_generators')
    from hive_scrambler import HiveScrambler
    self.use_sting_core = True
except ImportError:
    # Fall back to embedded detector
    self.use_sting_core = False
```

### CI/CD Pipeline Integration
```yaml
# GitHub Actions integration
name: PII Detection Testing
on: [push, pull_request]

jobs:
  test-pii-detection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build test container
        run: docker build -t sting-pii-test docker/test-data-generator/
      - name: Run PII tests
        run: |
          mkdir -p test_output
          docker run --rm -v ./test_output:/data/output sting-pii-test python3 pii_tester.py
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: pii-test-results
          path: test_output/test_results/
```

## 📚 Troubleshooting Guide

### Common Issues and Solutions

**Issue**: Container build fails with Java errors
**Solution**: Ensure Docker has sufficient memory allocated (4GB+)

**Issue**: Synthea generation times out
**Solution**: Reduce patient count or increase timeout in generate_medical_data()

**Issue**: Container runs out of memory during large dataset processing
**Solution**: Implement streaming processing or reduce batch sizes

**Issue**: PII detection results seem inaccurate
**Solution**: Enable debug mode to examine detection patterns and confidence scores

### Performance Tuning
```python
# Optimize for different scenarios
PERFORMANCE_CONFIGS = {
    "quick_demo": {
        "patients": 100,
        "batch_size": 50,
        "workers": 1
    },
    "standard_demo": {
        "patients": 1000,
        "batch_size": 100,
        "workers": 2
    },
    "enterprise_demo": {
        "patients": 10000,
        "batch_size": 500,
        "workers": 4
    }
}
```

---

*Technical documentation version 1.0*  
*Last updated: January 6, 2025*  
*For technical support: Contact STING engineering team*