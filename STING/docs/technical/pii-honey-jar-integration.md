# PII Detection Integration with Honey Jar Processing

## Overview

The PII (Personally Identifiable Information) detection system has been successfully integrated with STING's honey jar document processing pipeline. This integration provides automatic PII scanning, audit logging, and compliance recommendations for all documents uploaded to honey jars.

## Architecture

### Components

1. **PII Integration Service** (`knowledge_service/pii_integration.py`)
   - Main service orchestrating PII detection with honey jar processing
   - Handles auto-detection of document context (medical, legal, financial, general)
   - Provides compliance recommendations based on detected PII

2. **Enhanced Knowledge Service** (`knowledge_service/app.py`)
   - Modified document upload and approval processes to include PII detection
   - New API endpoints for PII management and analysis
   - Integrated audit logging during document processing

3. **PII Audit System** (from previous implementation)
   - Database models for PII detection records (`app/models/pii_audit_models.py`)
   - Audit service for logging and retention management (`app/services/pii_audit_service.py`) 
   - Configurable retention policies via `conf/config.yml.default`

## Integration Points

### Document Upload Process

The PII detection has been integrated into the honey jar document upload workflow:

```
1. Document Upload → 2. Text Extraction → 3. PII Detection → 4. Content Chunking → 5. ChromaDB Indexing
```

#### Before Integration:
- Upload → Extract → Chunk → Index

#### After Integration:
- Upload → Extract → **PII Scan** → Chunk → Index
- **Audit Log** → **Compliance Check** → **Recommendations**

### Document Approval Process

PII detection also occurs during the document approval workflow for public honey jars:

```
Admin/Owner Approves → Text Extraction → PII Detection → Processing → ChromaDB Indexing
```

## New API Endpoints

### 1. Get Honey Jar PII Summary
```
GET /honey-jars/{honey_jar_id}/pii-summary
```
Returns PII detection statistics for a specific honey jar.

### 2. Rescan Document for PII
```
POST /honey-jars/{honey_jar_id}/documents/{document_id}/pii-rescan?detection_mode=auto
```
Rescans a document with a specific PII detection mode (auto, general, medical, legal, financial).

### 3. PII Service Status
```
GET /pii/status
```
Returns the current status and capabilities of the PII detection service.

## Auto-Detection Logic

The system automatically determines the appropriate PII detection mode based on document content:

- **Medical Mode**: Triggered by keywords like "patient", "medical", "diagnosis", "prescription"
- **Legal Mode**: Triggered by keywords like "attorney", "client", "case", "settlement"
- **Financial Mode**: Triggered by keywords like "bank", "account", "credit", "payment"
- **General Mode**: Default fallback for documents that don't match specific contexts

## PII Detection Results

Each document processing now returns enhanced results including:

```json
{
  "document_id": "doc-123",
  "status": "completed", 
  "chunks": 15,
  "pii_analysis": {
    "pii_detected": true,
    "detection_count": 8,
    "detection_mode": "medical",
    "risk_summary": {
      "high": 2,
      "medium": 3,
      "low": 3
    },
    "pii_types": ["ssn", "medical_record_number", "patient_name"],
    "compliance_frameworks": ["hipaa", "gdpr"],
    "recommendations": [
      "🚨 2 high-risk PII types detected. Consider restricting access.",
      "🏥 HIPAA-regulated PII detected. Ensure PHI handling compliance."
    ],
    "audit_logged": true
  }
}
```

## Compliance Features

### Framework Detection
- **HIPAA**: Medical records, patient data, PHI
- **GDPR**: EU personal data, right to erasure
- **PCI-DSS**: Payment card information
- **Attorney-Client**: Legal privileged communications
- **CCPA**: California consumer privacy data

### Risk-Based Recommendations
- **High-Risk**: Immediate access restriction recommendations
- **Public Honey Jars**: Warnings about sensitive data exposure
- **Compliance**: Framework-specific handling guidance

## Audit Logging

All PII detections are automatically logged to the audit system:

- **Detection Records**: Metadata without actual PII values (security best practice)
- **Retention Policies**: Configurable per compliance framework
- **User Attribution**: Links detections to uploading users
- **Honey Jar Context**: Associates with specific honey jars for access control

## Configuration

PII detection can be configured via `conf/config.yml.default`:

```yaml
pii_detection:
  enabled: true
  integration:
    honey_jar_integration: true  # Enable automatic scanning
    bee_integration: true        # Send results to Bee Chat
```

## Security Considerations

1. **No PII Storage**: Only hashed values and metadata are stored in audit logs
2. **User Attribution**: All detections linked to uploading users for accountability
3. **Access Control**: PII rescan requires appropriate permissions
4. **Compliance Mapping**: Automatic framework detection for regulatory requirements

## Testing

A comprehensive test suite (`tests/test_pii_honey_jar_integration.py`) verifies:

- PII detection during document processing
- Auto-mode classification accuracy
- Audit logging functionality
- API endpoint responses
- Compliance framework mapping

## Performance Impact

- **Minimal Overhead**: PII detection adds ~100-500ms per document
- **Async Processing**: Non-blocking integration with existing workflows
- **Selective Scanning**: Only enabled for configured honey jar types
- **Caching**: PII analysis results cached in document metadata

## Future Enhancements

1. **Real-time Notifications**: Alert administrators of high-risk PII
2. **Batch Processing**: Queue-based PII scanning for large document sets
3. **Custom Patterns**: User-configurable PII detection rules
4. **Data Loss Prevention**: Block uploads containing sensitive PII
5. **Compliance Reporting**: Automated PII exposure reports

## Troubleshooting

### PII Service Not Available
If PII detection shows as unavailable:
1. Check that app service has access to PII components
2. Verify database migration has created audit tables
3. Ensure config.yml has PII detection enabled

### Integration Errors
Common integration issues:
1. **Import Errors**: Check Python path includes `/app` directory
2. **Database Errors**: Ensure PII audit tables exist
3. **Permission Errors**: Verify knowledge service can write audit logs

## Summary

The PII detection integration provides STING with enterprise-grade data protection capabilities, automatically scanning all honey jar documents for sensitive information while maintaining detailed audit trails and providing actionable compliance recommendations. This implementation supports the demo scenarios for medical and legal use cases while ensuring regulatory compliance.