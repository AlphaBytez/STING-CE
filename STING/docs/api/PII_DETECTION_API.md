# 📡 STING PII Detection API Reference

*Complete API documentation for PII detection endpoints and integration*

## Base URL
```
https://your-sting-instance.com/api/pii
```

## Authentication
All API requests require authentication via Bearer token:
```bash
Authorization: Bearer <your-jwt-token>
```

## Core Endpoints

### 🔍 Detect PII in Text

**POST** `/detect`

Analyzes text content and returns detected PII elements with compliance classification.

#### Request Body
```json
{
  "text": "Patient John Smith, SSN: 999-12-3456, MRN: 123456",
  "detection_mode": "medical",
  "confidence_threshold": 0.85,
  "compliance_frameworks": ["HIPAA", "GDPR"],
  "include_context": true,
  "mask_results": false
}
```

#### Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | string | Yes | - | Text content to analyze |
| `detection_mode` | enum | No | "general" | Detection mode: general, medical, legal, financial |
| `confidence_threshold` | float | No | 0.85 | Minimum confidence score (0.0-1.0) |
| `compliance_frameworks` | array | No | ["GDPR"] | Target compliance frameworks |
| `include_context` | boolean | No | true | Include surrounding text context |
| `mask_results` | boolean | No | false | Return masked PII values |

#### Response
```json
{
  "request_id": "uuid4-string",
  "processing_time_ms": 145,
  "detection_mode": "medical",
  "total_detections": 3,
  "detections": [
    {
      "id": "det_001",
      "pii_type": "social_security_number",
      "original_value": "999-12-3456",
      "masked_value": "[SSN]",
      "start_position": 25,
      "end_position": 36,
      "confidence": 0.98,
      "risk_level": "high",
      "compliance_frameworks": ["HIPAA", "GDPR"],
      "context": "Patient John Smith, SSN: 999-12-3456, MRN: 123456",
      "detection_method": "pattern_match"
    },
    {
      "id": "det_002",
      "pii_type": "medical_record_number",
      "original_value": "123456",
      "masked_value": "[MRN]",
      "start_position": 43,
      "end_position": 49,
      "confidence": 0.92,
      "risk_level": "medium",
      "compliance_frameworks": ["HIPAA"],
      "context": "Patient John Smith, SSN: 999-12-3456, MRN: 123456",
      "detection_method": "contextual_pattern"
    },
    {
      "id": "det_003",
      "pii_type": "person_name",
      "original_value": "John Smith",
      "masked_value": "[NAME]",
      "start_position": 8,
      "end_position": 18,
      "confidence": 0.89,
      "risk_level": "low",
      "compliance_frameworks": ["GDPR"],
      "context": "Patient John Smith, SSN: 999-12-3456, MRN: 123456",
      "detection_method": "named_entity_recognition"
    }
  ],
  "compliance_summary": {
    "HIPAA": {
      "elements_detected": 2,
      "risk_levels": {"high": 1, "medium": 1},
      "compliance_status": "violations_detected"
    },
    "GDPR": {
      "elements_detected": 2,
      "risk_levels": {"high": 1, "low": 1},
      "compliance_status": "personal_data_detected"
    }
  }
}
```

### 📄 Analyze Document

**POST** `/analyze-document`

Uploads and analyzes a document file for PII content.

#### Request (Multipart Form)
```bash
curl -X POST https://your-sting-instance.com/api/pii/analyze-document \
  -H "Authorization: Bearer <token>" \
  -F "file=@patient_records.pdf" \
  -F "detection_mode=medical" \
  -F "compliance_frameworks=HIPAA,GDPR"
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | Document file (PDF, DOCX, TXT, CSV) |
| `detection_mode` | string | No | Detection mode |
| `compliance_frameworks` | string | No | Comma-separated frameworks |
| `extract_text_only` | boolean | No | Return extracted text without PII analysis |

#### Response
```json
{
  "request_id": "uuid4-string",
  "filename": "patient_records.pdf",
  "file_size_bytes": 245760,
  "pages_processed": 5,
  "processing_time_ms": 2340,
  "extracted_text_length": 12450,
  "total_detections": 47,
  "detections": [...],
  "compliance_summary": {...},
  "document_classification": {
    "detected_type": "medical_record",
    "confidence": 0.94,
    "indicators": ["medical_record_number", "patient_id", "diagnosis_code"]
  }
}
```

### 🔧 Configure Detection Settings

**POST** `/configure`

Updates PII detection configuration for the current user or organization.

#### Request Body
```json
{
  "default_detection_mode": "medical",
  "confidence_threshold": 0.85,
  "enabled_pii_types": [
    "social_security_number",
    "medical_record_number",
    "credit_card_number"
  ],
  "compliance_frameworks": {
    "HIPAA": {
      "enabled": true,
      "required_pii_types": ["medical_record_number", "patient_id"],
      "risk_threshold": "medium"
    },
    "PCI_DSS": {
      "enabled": true,
      "required_pii_types": ["credit_card_number"],
      "risk_threshold": "high"
    }
  },
  "custom_patterns": {
    "employee_id": {
      "pattern": "\\bEMP-\\d{6}\\b",
      "description": "Company employee ID",
      "risk_level": "low",
      "compliance_frameworks": ["GDPR"]
    }
  }
}
```

#### Response
```json
{
  "configuration_id": "config_123",
  "updated_at": "2025-01-06T15:30:00Z",
  "status": "applied",
  "enabled_patterns": 23,
  "custom_patterns": 1,
  "compliance_frameworks": 4
}
```

### 📊 Get Detection Statistics

**GET** `/statistics`

Retrieves PII detection statistics and analytics.

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date (ISO 8601) |
| `end_date` | string | End date (ISO 8601) |
| `compliance_framework` | string | Filter by framework |
| `detection_mode` | string | Filter by detection mode |

#### Response
```json
{
  "period": {
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-06T23:59:59Z",
    "days": 6
  },
  "totals": {
    "documents_processed": 1247,
    "pii_detections": 18394,
    "high_risk_detections": 3421,
    "compliance_violations": 47
  },
  "by_pii_type": {
    "social_security_number": 1247,
    "credit_card_number": 892,
    "medical_record_number": 1156,
    "email_address": 2341
  },
  "by_compliance_framework": {
    "HIPAA": 8934,
    "GDPR": 12456,
    "PCI_DSS": 2134,
    "Attorney_Client": 445
  },
  "performance_metrics": {
    "average_processing_time_ms": 156,
    "documents_per_minute": 387,
    "accuracy_rate": 0.967
  }
}
```

### 🏥 Health Check

**GET** `/health`

Returns system health status for PII detection service.

#### Response
```json
{
  "status": "healthy",
  "timestamp": "2025-01-06T15:30:00Z",
  "version": "1.2.0",
  "components": {
    "pattern_engine": "operational",
    "compliance_mapping": "operational",
    "text_extraction": "operational",
    "redis_queue": "operational"
  },
  "performance": {
    "avg_response_time_ms": 145,
    "requests_per_minute": 1247,
    "error_rate": 0.002
  }
}
```

## Batch Processing Endpoints

### 🚀 Submit Batch Job

**POST** `/batch/submit`

Submits a batch PII detection job for large datasets.

#### Request Body
```json
{
  "job_name": "quarterly_compliance_scan",
  "input_source": {
    "type": "honey_jar",
    "honey_jar_id": "jar_12345",
    "file_patterns": ["*.pdf", "*.docx"]
  },
  "detection_settings": {
    "detection_mode": "medical",
    "compliance_frameworks": ["HIPAA"],
    "confidence_threshold": 0.85
  },
  "processing_options": {
    "batch_size": 1000,
    "parallel_workers": 4,
    "priority": "normal"
  },
  "output_settings": {
    "include_masked_content": true,
    "generate_compliance_report": true,
    "export_format": "json"
  }
}
```

#### Response
```json
{
  "job_id": "batch_job_789",
  "status": "queued",
  "estimated_documents": 5420,
  "estimated_completion": "2025-01-06T16:45:00Z",
  "tracking_url": "/api/pii/batch/status/batch_job_789"
}
```

### 📈 Check Batch Status

**GET** `/batch/status/{job_id}`

Retrieves status and progress of a batch PII detection job.

#### Response
```json
{
  "job_id": "batch_job_789",
  "status": "processing",
  "progress": {
    "documents_processed": 2341,
    "total_documents": 5420,
    "percentage": 43.2,
    "estimated_remaining": "00:12:34"
  },
  "current_stats": {
    "pii_detections": 34567,
    "high_risk_elements": 4123,
    "processing_rate": "156 docs/min"
  },
  "started_at": "2025-01-06T15:30:00Z",
  "estimated_completion": "2025-01-06T16:42:30Z"
}
```

### 📋 Get Batch Results

**GET** `/batch/results/{job_id}`

Retrieves results from a completed batch job.

#### Response
```json
{
  "job_id": "batch_job_789",
  "status": "completed",
  "completion_time": "2025-01-06T16:41:22Z",
  "summary": {
    "documents_processed": 5420,
    "total_pii_detections": 78234,
    "compliance_violations": 123,
    "processing_time": "00:71:22"
  },
  "results_download_url": "/api/pii/batch/download/batch_job_789",
  "compliance_report_url": "/api/pii/batch/report/batch_job_789"
}
```

## WebSocket Real-time Updates

### 🔄 Real-time Detection Stream

Connect to WebSocket for real-time PII detection updates:

```javascript
const ws = new WebSocket('wss://your-sting-instance.com/ws/pii/realtime');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('PII Detection:', data);
};

// Send document for real-time processing
ws.send(JSON.stringify({
  action: 'analyze',
  text: 'Patient record content...',
  detection_mode: 'medical'
}));
```

#### WebSocket Message Format
```json
{
  "type": "pii_detection",
  "timestamp": "2025-01-06T15:30:00Z",
  "document_id": "doc_123",
  "detections": [...],
  "compliance_status": "violations_detected"
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "PII_DETECTION_FAILED",
    "message": "Unable to process document due to unsupported format",
    "details": {
      "supported_formats": ["pdf", "docx", "txt", "csv"],
      "received_format": "xlsx"
    },
    "request_id": "req_456",
    "timestamp": "2025-01-06T15:30:00Z"
  }
}
```

### Error Codes
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_DETECTION_MODE` | 400 | Unsupported detection mode |
| `CONFIDENCE_THRESHOLD_INVALID` | 400 | Threshold must be 0.0-1.0 |
| `FILE_TOO_LARGE` | 413 | File exceeds maximum size limit |
| `UNSUPPORTED_FILE_FORMAT` | 415 | File format not supported |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `PII_DETECTION_FAILED` | 500 | Internal processing error |
| `SERVICE_UNAVAILABLE` | 503 | Detection service temporarily down |

## Rate Limits

| Endpoint | Limit | Window |
|----------|--------|--------|
| `/detect` | 1000 requests | 1 hour |
| `/analyze-document` | 100 requests | 1 hour |
| `/batch/submit` | 10 jobs | 1 day |
| WebSocket connections | 10 concurrent | Per user |

## SDK Examples

### Python SDK
```python
import requests
from sting_pii import PIIDetectionClient

# Initialize client
client = PIIDetectionClient(
    base_url="https://your-sting-instance.com",
    api_token="your-jwt-token"
)

# Detect PII in text
result = client.detect_pii(
    text="Patient John Smith, SSN: 999-12-3456",
    detection_mode="medical",
    compliance_frameworks=["HIPAA"]
)

print(f"Found {result.total_detections} PII elements")
for detection in result.detections:
    print(f"- {detection.pii_type}: {detection.masked_value}")
```

### JavaScript SDK
```javascript
import { PIIDetectionClient } from '@sting/pii-detection';

const client = new PIIDetectionClient({
  baseURL: 'https://your-sting-instance.com',
  apiToken: 'your-jwt-token'
});

// Analyze document
const result = await client.analyzeDocument({
  file: documentFile,
  detectionMode: 'financial',
  complianceFrameworks: ['PCI_DSS', 'GDPR']
});

console.log(`Processed ${result.filename}`);
console.log(`Found ${result.total_detections} PII elements`);
```

### cURL Examples

#### Basic text analysis
```bash
curl -X POST https://your-sting-instance.com/api/pii/detect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Credit card: 4532-1234-5678-9012",
    "detection_mode": "financial",
    "compliance_frameworks": ["PCI_DSS"]
  }'
```

#### Document analysis
```bash
curl -X POST https://your-sting-instance.com/api/pii/analyze-document \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@financial_records.pdf" \
  -F "detection_mode=financial" \
  -F "compliance_frameworks=PCI_DSS,GDPR"
```

#### Batch job submission
```bash
curl -X POST https://your-sting-instance.com/api/pii/batch/submit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "compliance_audit_q1",
    "input_source": {
      "type": "honey_jar",
      "honey_jar_id": "medical_records_2024"
    },
    "detection_settings": {
      "detection_mode": "medical",
      "compliance_frameworks": ["HIPAA"]
    }
  }'
```

## Webhook Configuration

### PII Detection Webhooks

Configure webhooks to receive notifications when PII is detected:

```json
{
  "webhook_url": "https://your-app.com/webhooks/pii-detected",
  "events": [
    "pii.high_risk_detected",
    "pii.compliance_violation",
    "pii.batch_job_completed"
  ],
  "secret": "your-webhook-secret",
  "active": true
}
```

#### Webhook Payload Example
```json
{
  "event": "pii.high_risk_detected",
  "timestamp": "2025-01-06T15:30:00Z",
  "data": {
    "document_id": "doc_123",
    "pii_type": "credit_card_number",
    "risk_level": "high",
    "compliance_frameworks": ["PCI_DSS"],
    "user_id": "user_456"
  },
  "signature": "sha256=signature-hash"
}
```

---

*API Documentation version 1.0*  
*Last updated: January 6, 2025*  
*For API support: Contact STING development team*