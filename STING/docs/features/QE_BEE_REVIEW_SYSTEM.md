# 🐝 QE Bee (Quality Engineering Bee) Review System

## Overview

QE Bee is STING-CE's automated output validation agent that reviews all AI-generated content before delivery to users. It acts as a quality gate, ensuring outputs are complete, properly sanitized, and meet quality standards.

**Key Value Proposition:**
- Catches incomplete PII deserialization before users see raw tokens
- Validates output completeness and format
- Optional LLM-powered quality assessment
- Webhook notifications for integration with external systems

## Key Features

- 🔍 **PII Token Detection** - Automatically detects unresolved `[PII_*]` tokens in outputs
- 📊 **Completeness Validation** - Checks for truncated or empty responses
- 📋 **Format Validation** - Verifies reports have expected structure/sections
- 🤖 **LLM Quality Review** - Optional AI-powered content quality assessment
- 🔔 **Webhook Notifications** - Alerts on review completion (pass/fail)
- 📈 **Review Analytics** - Track pass rates, common issues, processing times

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STING-CE Platform                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │ Report Worker │───▶│   Review Queue   │◀───│  QE Bee Worker   │  │
│  │   (Reports)   │    │   (PostgreSQL)   │    │   (Validator)    │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│         │                     │                       │             │
│         │                     │                       │             │
│         ▼                     ▼                       ▼             │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  Bee Chatbot │    │  Review History  │    │  External AI     │  │
│  │  (Messages)  │    │    (Audit Log)   │    │  (phi4 model)    │  │
│  └──────────────┘    └──────────────────┘    └──────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│                      ┌──────────────────┐                          │
│                      │ Webhook Delivery │                          │
│                      │  (Notifications) │                          │
│                      └──────────────────┘                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Review Flow

```
1. Content Generated
        │
        ▼
2. Auto-queued for Review (priority-based)
        │
        ▼
3. QE Bee Worker Claims Job
        │
        ├──▶ 4a. PII Token Check
        │         └──▶ Scan for [PII_*] patterns
        │
        ├──▶ 4b. Completeness Check
        │         └──▶ Min length, truncation indicators
        │
        ├──▶ 4c. Format Validation
        │         └──▶ Expected sections, structure
        │
        └──▶ 4d. LLM Quality Check (optional)
                  └──▶ AI assessment of coherence
        │
        ▼
5. Review Result Stored
        │
        ├──▶ PASS: Content delivered to user
        │
        ├──▶ PASS_WITH_WARNINGS: Delivered with notes
        │
        └──▶ FAIL: Content flagged, user notified
        │
        ▼
6. Webhook Notification Sent (if configured)
```

## Review Types

| Review Type | Description | Checks Performed |
|------------|-------------|------------------|
| `output_validation` | Standard output review | PII, completeness, format |
| `pii_check` | PII-focused review | PII tokens only |
| `quality_check` | Quality assessment | LLM-powered content review |
| `format_validation` | Structure check | Section presence, markdown |
| `compliance_check` | Compliance review | Reserved for Enterprise |

## Result Codes

### Pass Codes
| Code | Description |
|------|-------------|
| `PASS` | All checks passed |
| `PASS_WITH_WARNINGS` | Passed with minor issues noted |

### Fail Codes - PII Related
| Code | Description |
|------|-------------|
| `PII_TOKENS_REMAINING` | Found unresolved `[PII_*]` tokens |
| `PII_DESERIALIZATION_INCOMPLETE` | PII restore failed |

### Fail Codes - Output Related
| Code | Description |
|------|-------------|
| `OUTPUT_TRUNCATED` | Content appears cut off |
| `OUTPUT_EMPTY` | Content is empty or too short |
| `OUTPUT_MALFORMED` | Invalid structure |
| `GENERATION_ERROR` | Content generation failed |

### Fail Codes - Quality Related
| Code | Description |
|------|-------------|
| `QUALITY_LOW` | LLM assessment score < 5/10 |
| `CONTENT_INCOHERENT` | Content lacks coherence |
| `OFF_TOPIC` | Content doesn't match request |

### Fail Codes - Format Related
| Code | Description |
|------|-------------|
| `FORMAT_INVALID` | Doesn't match expected format |
| `MISSING_SECTIONS` | Required sections missing |

### System Codes
| Code | Description |
|------|-------------|
| `REVIEW_TIMEOUT` | Review exceeded time limit |
| `REVIEW_ERROR` | System error during review |
| `SKIPPED_BY_CONFIG` | Review skipped per config |

## Configuration

### Environment Variables

```bash
# Enable/disable QE Bee
QE_BEE_ENABLED=true

# LLM model for quality reviews (fast model recommended)
QE_BEE_MODEL=phi4

# Enable LLM-powered quality checks
QE_BEE_LLM_ENABLED=true

# Review timeout in seconds
QE_BEE_TIMEOUT=30

# Worker poll interval in seconds
QE_BEE_POLL_INTERVAL=5
```

### config.yml Settings

```yaml
ai:
  qe_bee:
    enabled: true
    model: "phi4"
    llm_enabled: true
    timeout: 30
    poll_interval: 5
    webhooks:
      enabled: true
      max_per_user: 5
```

## API Endpoints

### User Endpoints (requires authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qe-bee/stats` | Get review statistics |
| GET | `/api/qe-bee/history` | Get review history |
| GET | `/api/qe-bee/queue` | Get current queue status |
| GET | `/api/qe-bee/review/<id>` | Get specific review details |

### Webhook Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qe-bee/webhooks` | List user webhooks |
| POST | `/api/qe-bee/webhooks` | Create webhook |
| PUT | `/api/qe-bee/webhooks/<id>` | Update webhook |
| DELETE | `/api/qe-bee/webhooks/<id>` | Delete webhook |
| POST | `/api/qe-bee/webhooks/<id>/test` | Test webhook |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qe-bee/admin/queue` | Full queue status |
| POST | `/api/qe-bee/admin/review/<id>/retry` | Retry failed review |

### Internal Worker Endpoints (no auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/qe-bee/internal/next-review` | Get next job |
| POST | `/api/qe-bee/internal/complete-review` | Submit result |
| GET | `/api/qe-bee/internal/get-content` | Fetch content |
| POST | `/api/qe-bee/internal/queue-review` | Queue item |

## Webhook Payload

When a review completes, webhooks receive this payload:

```json
{
  "event": "review.completed",
  "review_id": "uuid-here",
  "target_type": "report",
  "target_id": "report-uuid",
  "result": {
    "passed": true,
    "code": "PASS",
    "message": "All checks passed",
    "confidence": 95
  },
  "timestamp": "2025-11-21T23:24:20.538Z",
  "user_id": "user-uuid"
}
```

## Database Schema

### review_queue
Primary queue table for pending reviews.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| target_type | ENUM | report, message, document, pii_detection |
| target_id | VARCHAR(100) | ID of item to review |
| review_type | ENUM | Type of review to perform |
| priority | INTEGER | 1=highest, 10=lowest |
| status | ENUM | pending, reviewing, passed, failed, escalated |
| result_code | ENUM | Result code from review |
| result_message | TEXT | Human-readable result |
| confidence_score | INTEGER | 0-100 confidence |
| review_details | JSONB | Detailed findings |
| webhook_url | VARCHAR(500) | Optional webhook URL |
| worker_id | VARCHAR(100) | Processing worker ID |
| created_at | TIMESTAMP | Queue time |
| completed_at | TIMESTAMP | Completion time |

### review_history
Audit trail of all completed reviews.

### webhook_configs
User webhook configurations (max 5 per user in CE).

## Integration with Report Worker

QE Bee automatically reviews all completed reports:

```python
# In report_service.py complete_job()
def complete_job(self, report_id, result_file_id, result_summary):
    # ... mark report complete ...

    # Queue for QE Bee review
    self._queue_for_qe_bee_review(report_id, user_id)
```

## PII Token Detection

QE Bee uses regex to detect unresolved PII tokens:

```python
PII_TOKEN_PATTERN = re.compile(r'\[PII_[A-Z_]+_[a-f0-9]+\]')

# Matches patterns like:
# [PII_EMAIL_a1b2c3d4]
# [PII_PHONE_NUMBER_deadbeef]
# [PII_SSN_12345678]
```

## CE vs Enterprise

| Feature | CE Edition | Enterprise |
|---------|-----------|------------|
| PII Token Detection | ✅ | ✅ |
| Completeness Check | ✅ | ✅ |
| Format Validation | ✅ | ✅ |
| LLM Quality Review | ✅ | ✅ |
| Local Webhooks | ✅ (5 max) | ✅ (unlimited) |
| External Integrations | ❌ | ✅ (Slack, Teams, etc.) |
| Custom QA Agents | ❌ | ✅ |
| Review Dashboard | ✅ | ✅ (enhanced) |

## Troubleshooting

### Reviews Not Processing

1. Check QE Bee worker is running:
   ```bash
   docker ps | grep qe-bee
   ```

2. Check worker logs:
   ```bash
   docker logs sting-ce-qe-bee-worker
   ```

3. Verify database tables exist:
   ```bash
   docker exec sting-ce-db psql -U postgres -d sting_app \
     -c "SELECT COUNT(*) FROM review_queue;"
   ```

### High Failure Rate

1. Check for PII deserialization issues in Bee/HiveScrambler
2. Review LLM model availability (phi4)
3. Check content generation quality in report worker

### Webhook Delivery Failures

1. Verify webhook URL is reachable from container network
2. Check webhook endpoint returns 2xx status
3. Review webhook_configs.last_error for details

## See Also

- [PII Detection System](PII_DETECTION_SYSTEM.md)
- [Bee Support System](BEE_SUPPORT_SYSTEM.md)
- [Report Generation](../guides/REPORT_GENERATION.md)
- [Webhook Configuration](../guides/WEBHOOK_SETUP.md)

---

*Document created: November 2025*
*Last updated: November 2025*
