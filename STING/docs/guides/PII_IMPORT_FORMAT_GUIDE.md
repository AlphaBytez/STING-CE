# PII Configuration Import Format Guide

## Overview
The PII Configuration Manager supports importing custom PII detection patterns via JSON files. This guide explains the required format and provides examples.

## File Format Requirements
- **File Type**: JSON (.json)
- **Encoding**: UTF-8
- **Structure**: Array of pattern objects or configuration object with patterns array

## Pattern Object Structure

Each PII pattern must include the following fields:

```json
{
  "name": "Pattern Name",
  "pattern": "\\b[0-9]{3}-[0-9]{2}-[0-9]{4}\\b",
  "description": "Brief description of what this pattern detects",
  "category": "personal|medical|legal|financial|contact",
  "framework": "hipaa|gdpr|pci_dss|legal|custom",
  "severity": "critical|high|medium|low",
  "confidence": 0.95,
  "enabled": true,
  "examples": ["123-45-6789", "987-65-4321"],
  "tags": ["ssn", "pii", "sensitive"]
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the pattern |
| `pattern` | string | Yes | Regular expression pattern (escaped for JSON) |
| `description` | string | Yes | Explanation of what the pattern detects |
| `category` | string | Yes | Category: personal, medical, legal, financial, or contact |
| `framework` | string | Yes | Compliance framework: hipaa, gdpr, pci_dss, legal, or custom |
| `severity` | string | Yes | Risk level: critical, high, medium, or low |
| `confidence` | number | No | Detection confidence score (0.0 to 1.0), default 0.90 |
| `enabled` | boolean | No | Whether pattern is active, default true |
| `examples` | array | No | Example strings that match the pattern |
| `tags` | array | No | Additional tags for categorization |

## Import Formats

### Format 1: Simple Pattern Array
```json
[
  {
    "name": "US Social Security Number",
    "pattern": "\\b\\d{3}-\\d{2}-\\d{4}\\b",
    "description": "Matches SSN format XXX-XX-XXXX",
    "category": "personal",
    "framework": "hipaa",
    "severity": "critical",
    "confidence": 0.95,
    "examples": ["123-45-6789"]
  },
  {
    "name": "Email Address",
    "pattern": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
    "description": "Matches email addresses",
    "category": "contact",
    "framework": "gdpr",
    "severity": "medium",
    "confidence": 0.90,
    "examples": ["user@example.com"]
  }
]
```

### Format 2: Full Configuration Object
```json
{
  "version": "1.0",
  "exported_at": "2025-01-06T10:00:00Z",
  "patterns": [
    {
      "name": "Medical Record Number",
      "pattern": "\\b(?:MRN|Medical Record Number)[:\\s]*([A-Z0-9]{6,12})\\b",
      "description": "Matches medical record numbers",
      "category": "medical",
      "framework": "hipaa",
      "severity": "high",
      "confidence": 0.92,
      "enabled": true,
      "examples": ["MRN: A123456", "Medical Record Number: B7890123"]
    }
  ],
  "compliance_profiles": [
    {
      "name": "HIPAA",
      "description": "Health Insurance Portability and Accountability Act",
      "categories": ["medical", "personal"],
      "active": true
    }
  ],
  "custom_rules": []
}
```

## Regular Expression Notes

### Escaping
- Backslashes in regex patterns must be escaped in JSON: `\b` becomes `\\b`
- Special regex characters that need escaping: `. * + ? ^ $ { } ( ) | [ ] \`

### Common Patterns

#### Personal Information
- **SSN**: `\\b\\d{3}-\\d{2}-\\d{4}\\b`
- **Phone (US)**: `\\b(?:\\+?1[-.]?)?\\(?([0-9]{3})\\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\\b`
- **Date of Birth**: `\\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])[-/](?:19|20)\\d{2}\\b`

#### Medical Information
- **Medical Record**: `\\b(?:MRN|Medical Record Number)[:\\s]*([A-Z0-9]{6,12})\\b`
- **Patient ID**: `\\b(?:Patient ID|PID)[:\\s]*([0-9]{6,10})\\b`
- **Prescription Number**: `\\bRx[:\\s]*([0-9]{6,10})\\b`

#### Legal Information
- **Case Number**: `\\b(?:Case\\s*(?:No\\.?|Number)?[:\\s]*)?((?:\\d{2,4}[-/])?[A-Z]{2,4}[-/]\\d{3,8})\\b`
- **Bar Number**: `\\b(?:Bar\\s*(?:No\\.?|Number)?[:\\s]*)?([0-9]{5,8})\\b`
- **Attorney-Client Privilege**: `(?i)\\b(?:attorney[- ]?client|privileged\\s+communication|confidential\\s+legal)\\b`

#### Financial Information
- **Credit Card**: `\\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\\b`
- **Bank Account**: `\\b[0-9]{8,17}\\b`
- **Routing Number**: `\\b[0-9]{9}\\b`

## Import Process

1. **Prepare your JSON file** following the format above
2. **Navigate to Admin Panel** → **PII Configuration**
3. **Click Import** button
4. **Select your JSON file**
5. **Review imported patterns** in the interface
6. **Save configuration** to apply changes

## Validation Rules

The import process validates:
- JSON syntax correctness
- Required fields presence
- Pattern regex validity
- Category and framework values
- Confidence score range (0.0 - 1.0)
- Severity levels

## Error Handling

Common import errors and solutions:

| Error | Solution |
|-------|----------|
| "Invalid JSON format" | Check JSON syntax, ensure proper escaping |
| "Missing required field: name" | Add the missing field to each pattern |
| "Invalid regex pattern" | Test pattern in regex tester, ensure proper escaping |
| "Unknown category: custom" | Use valid categories: personal, medical, legal, financial, contact |
| "Invalid confidence score" | Ensure confidence is between 0.0 and 1.0 |

## Best Practices

1. **Test patterns** before importing using online regex testers
2. **Include examples** to help users understand what each pattern detects
3. **Use descriptive names** that clearly indicate what is being detected
4. **Set appropriate severity** based on data sensitivity
5. **Group related patterns** by category and framework
6. **Document custom patterns** with detailed descriptions
7. **Version your configurations** for tracking changes
8. **Backup existing configuration** before importing new patterns

## Sample Files

Download sample configuration files:
- [Basic PII Patterns](./sample-pii-patterns-basic.json)
- [HIPAA Compliance Pack](./sample-pii-patterns-hipaa.json)
- [GDPR Compliance Pack](./sample-pii-patterns-gdpr.json)
- [Legal Document Patterns](./sample-pii-patterns-legal.json)
- [Complete Configuration](./sample-pii-config-complete.json)