# File Upload Technical Specifications

## Overview

This document defines the technical limitations, supported formats, and processing specifications for file uploads in STING's Bee Chat and Honey Jar systems.

## File Size Limitations

### Maximum File Sizes

| Upload Type | Single File | Batch Upload | Total per Request |
|-------------|-------------|--------------|-------------------|
| Bee Chat Temporary | 100MB | 10 files | 500MB |
| Honey Jar Document | 100MB | 50 files | 1GB |
| API Upload | 100MB | 100 files | 2GB |
| Direct Import | 500MB | N/A | 500MB |

### Size Handling

```python
FILE_SIZE_LIMITS = {
    'max_single_file': 104857600,  # 100MB in bytes
    'max_batch_size': 1073741824,  # 1GB total
    'chunk_size': 1048576,  # 1MB chunks for streaming
    'warning_threshold': 52428800,  # 50MB warning
}
```

## Supported File Formats

### Document Formats

| Format | Extensions | MIME Types | Features |
|--------|------------|------------|----------|
| PDF | .pdf | application/pdf | Full text extraction, metadata |
| Word | .docx, .doc | application/vnd.openxmlformats-officedocument.wordprocessingml.document | Text, tables, metadata |
| Text | .txt | text/plain | Direct processing |
| Markdown | .md | text/markdown | Preserves formatting |
| HTML | .html, .htm | text/html | Strips tags, preserves structure |

### Data Formats

| Format | Extensions | MIME Types | Features |
|--------|------------|------------|----------|
| JSON | .json | application/json | Schema validation, nested parsing |
| CSV | .csv | text/csv | Auto-detect delimiter, headers |
| XML | .xml | application/xml | XPath support |
| YAML | .yaml, .yml | application/x-yaml | Configuration parsing |

### Image Formats (Future OCR Support)

| Format | Extensions | MIME Types | Current Support |
|--------|------------|------------|-----------------|
| PNG | .png | image/png | Stored only |
| JPEG | .jpg, .jpeg | image/jpeg | Stored only |
| WebP | .webp | image/webp | Stored only |
| GIF | .gif | image/gif | Stored only |

## Processing Specifications

### Text Extraction Pipeline

```python
EXTRACTION_CONFIG = {
    'pdf': {
        'library': 'PyPDF2',
        'fallback': 'pdfplumber',
        'ocr_enabled': False,  # Future feature
        'max_pages': 5000,
        'timeout': 300  # 5 minutes
    },
    'docx': {
        'library': 'python-docx',
        'preserve_formatting': False,
        'extract_tables': True,
        'extract_images': False
    },
    'text': {
        'encodings': ['utf-8', 'utf-16', 'latin-1', 'cp1252'],
        'max_line_length': 10000,
        'normalize_whitespace': True
    }
}
```

### Chunking Strategy

```python
CHUNKING_CONFIG = {
    'default': {
        'chunk_size': 1000,  # characters
        'overlap': 200,      # character overlap
        'min_chunk_size': 100,
        'max_chunk_size': 2000
    },
    'sentence_aware': {
        'strategy': 'nltk_sentence',
        'sentences_per_chunk': 3-5,
        'respect_paragraphs': True
    },
    'semantic': {
        'strategy': 'embedding_similarity',
        'similarity_threshold': 0.8,
        'max_chunk_tokens': 512
    }
}
```

## Upload Rate Limiting

### User Limits

```python
RATE_LIMITS = {
    'uploads_per_minute': 10,
    'uploads_per_hour': 100,
    'uploads_per_day': 500,
    'bandwidth_per_hour': 5368709120,  # 5GB
}
```

### API Rate Limits

```python
API_RATE_LIMITS = {
    'authenticated': {
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'burst_allowance': 20
    },
    'public': {
        'requests_per_minute': 10,
        'requests_per_hour': 100,
        'burst_allowance': 5
    }
}
```

## Security Validations

### File Content Validation

```python
SECURITY_CHECKS = {
    'mime_type_validation': True,
    'file_signature_check': True,  # Magic bytes
    'virus_scanning': False,  # Future integration
    'content_filtering': {
        'check_executables': True,
        'block_macros': True,
        'scan_embedded_files': True
    }
}
```

### Blocked Patterns

```python
BLOCKED_PATTERNS = [
    r'\.exe$', r'\.dll$', r'\.so$',  # Executables
    r'\.bat$', r'\.sh$', r'\.ps1$',  # Scripts
    r'\.zip$', r'\.rar$', r'\.7z$',  # Archives (configurable)
]
```

## Processing Timeouts

| File Size | Processing Timeout | Queue Priority |
|-----------|-------------------|----------------|
| 0-1MB | 30 seconds | High |
| 1-10MB | 2 minutes | Normal |
| 10-50MB | 5 minutes | Normal |
| 50-100MB | 10 minutes | Low |

## Error Handling

### Common Error Codes

| Code | Error | Description | User Action |
|------|-------|-------------|-------------|
| 413 | File Too Large | Exceeds size limit | Reduce file size |
| 415 | Unsupported Type | File format not supported | Convert to supported format |
| 429 | Rate Limited | Too many uploads | Wait and retry |
| 507 | Insufficient Storage | Honey Reserve full | Clear space |
| 422 | Processing Failed | Extraction error | Check file integrity |

### Retry Strategy

```python
RETRY_CONFIG = {
    'max_retries': 3,
    'backoff_factor': 2,
    'retry_statuses': [502, 503, 504],
    'retry_exceptions': ['ConnectionError', 'Timeout']
}
```

## Performance Optimizations

### Concurrent Processing

```python
CONCURRENCY_CONFIG = {
    'max_workers': 4,
    'queue_size': 100,
    'priority_queues': ['urgent', 'normal', 'background'],
    'worker_timeout': 300
}
```

### Caching Strategy

```python
CACHE_CONFIG = {
    'extracted_text_ttl': 3600,  # 1 hour
    'chunk_cache_ttl': 7200,     # 2 hours
    'embedding_cache_ttl': 86400, # 24 hours
    'max_cache_size': 1073741824  # 1GB
}
```

## Monitoring and Metrics

### Key Metrics

```python
MONITORING_METRICS = [
    'upload_success_rate',
    'average_processing_time',
    'extraction_failure_rate',
    'storage_utilization',
    'queue_depth',
    'worker_utilization'
]
```

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Success Rate | <95% | <90% |
| Processing Time | >2min avg | >5min avg |
| Queue Depth | >100 | >500 |
| Storage Usage | >80% | >95% |

## Future Enhancements

### Planned Format Support

1. **Office Formats**
   - Excel (.xlsx, .xls)
   - PowerPoint (.pptx, .ppt)
   - OpenDocument formats

2. **Code Files**
   - Syntax highlighting
   - Language detection
   - Dependency extraction

3. **Media Files**
   - Audio transcription
   - Video frame extraction
   - OCR for images

### Advanced Processing

1. **Smart Chunking**
   - Topic modeling
   - Semantic boundaries
   - Context preservation

2. **Multi-language Support**
   - Language detection
   - Translation options
   - Multilingual search

3. **Real-time Processing**
   - Streaming uploads
   - Progressive extraction
   - Live preview

---

*This specification is subject to change based on system requirements and user feedback.*