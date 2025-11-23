# QE Bee Architecture

## Executive Summary

QE Bee (Quality Engineering Bee) is STING-CE's automated output validation system. It operates as a lightweight microservice that reviews AI-generated content for quality issues before delivery to users. The architecture follows STING's minimal worker pattern - a standalone container that communicates with the main app via REST APIs.

## System Overview

```
                                    ┌─────────────────────────────────┐
                                    │         PostgreSQL              │
                                    │  ┌───────────────────────────┐  │
                                    │  │     review_queue          │  │
                                    │  │     review_history        │  │
                                    │  │     webhook_configs       │  │
                                    │  └───────────────────────────┘  │
                                    └─────────────┬───────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
                    ▼                             ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐   ┌───────────────────────────┐
│      Report Worker        │   │      Flask App (API)      │   │    QE Bee Worker          │
│                           │   │                           │   │                           │
│  - Generates reports      │   │  - /api/qe-bee/* routes   │   │  - Polls for reviews      │
│  - Calls complete_job()   │──▶│  - ReviewService          │◀──│  - Validates content      │
│  - Queues for QE review   │   │  - Queue management       │   │  - LLM quality checks     │
│                           │   │  - Webhook delivery       │   │  - Submits results        │
└───────────────────────────┘   └───────────────────────────┘   └───────────────────────────┘
                                            │                               │
                                            │                               │
                                            ▼                               ▼
                                ┌───────────────────────┐       ┌───────────────────────┐
                                │   Webhook Endpoints   │       │    External AI        │
                                │   (User-configured)   │       │    (phi4 model)       │
                                └───────────────────────┘       └───────────────────────┘
```

## Core Components

### 1. QE Bee Worker (`qe_bee_worker.py`)

A lightweight, stateless worker container that:
- Polls the app service for pending reviews
- Performs validation checks on content
- Optionally uses LLM for quality assessment
- Reports results back to the app service

**Design Principles:**
- Single responsibility: only validation logic
- No database access: communicates via REST APIs
- Minimal dependencies: `requests`, `urllib3` only
- Horizontally scalable: multiple workers supported

```python
class QEBeeWorker:
    PII_TOKEN_PATTERN = re.compile(r'\[PII_[A-Z_]+_[a-f0-9]+\]')

    async def start(self):
        while self.is_running:
            job = self._get_next_review()
            if job:
                result = await self._process_review(job)
                self._complete_review(job['id'], result)
            else:
                await asyncio.sleep(self.poll_interval)
```

### 2. Review Service (`review_service.py`)

Flask service layer that manages:
- Review queue operations (CRUD)
- Worker job distribution
- Review history tracking
- Webhook delivery

**Key Methods:**
- `queue_review()` - Add item to review queue
- `get_next_review()` - Atomic job claiming with row locking
- `complete_review()` - Store result and trigger webhooks
- `get_content_for_review()` - Fetch content by target type

### 3. Database Models (`review_models.py`)

Three tables with PostgreSQL enums:

```sql
-- Review Queue (active reviews)
CREATE TABLE review_queue (
    id UUID PRIMARY KEY,
    target_type review_target_type NOT NULL,  -- report, message, document, pii_detection
    target_id VARCHAR(100) NOT NULL,
    review_type review_type NOT NULL,          -- output_validation, pii_check, etc.
    priority INTEGER DEFAULT 5,                -- 1=highest, 10=lowest
    status review_status NOT NULL,             -- pending, reviewing, passed, failed
    result_code review_result_code,
    confidence_score INTEGER,
    worker_id VARCHAR(100),
    created_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Review History (audit trail)
CREATE TABLE review_history (
    id UUID PRIMARY KEY,
    queue_id UUID,
    target_type review_target_type NOT NULL,
    result_code review_result_code NOT NULL,
    model_used VARCHAR(100),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ
);

-- Webhook Configs (user endpoints)
CREATE TABLE webhook_configs (
    id UUID PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    total_sent INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0
);
```

### 4. API Routes (`qe_bee_routes.py`)

Blueprint with three endpoint categories:

1. **User Endpoints** (authenticated)
   - Stats, history, queue viewing
   - Webhook management

2. **Admin Endpoints** (admin only)
   - Full queue management
   - Retry failed reviews

3. **Internal Endpoints** (no auth)
   - Worker communication
   - Job claiming and completion

## Data Flow

### Report Completion Flow

```
1. Report Worker generates report
        │
        ▼
2. report_service.complete_job() called
        │
        ├──▶ Update report status to 'completed'
        │
        └──▶ _queue_for_qe_bee_review()
                    │
                    ▼
3. review_service.queue_review()
        │
        └──▶ INSERT INTO review_queue (status='pending')
```

### Review Processing Flow

```
1. QE Bee Worker polls /api/qe-bee/internal/next-review
        │
        ▼
2. review_service.get_next_review()
        │
        └──▶ SELECT ... FOR UPDATE SKIP LOCKED
        │
        └──▶ UPDATE status='reviewing', worker_id=?
        │
        ▼
3. Worker fetches content via /api/qe-bee/internal/get-content
        │
        ▼
4. Worker performs validation checks
        │
        ├──▶ _check_pii_tokens()      - Regex scan
        ├──▶ _check_completeness()    - Length, truncation
        ├──▶ _check_format()          - Section presence
        └──▶ _llm_quality_check()     - AI assessment (optional)
        │
        ▼
5. Worker POSTs to /api/qe-bee/internal/complete-review
        │
        ▼
6. review_service.complete_review()
        │
        ├──▶ UPDATE review_queue SET status='passed'/'failed'
        ├──▶ INSERT INTO review_history
        └──▶ _send_webhook() / _send_user_webhooks()
```

## Job Distribution

QE Bee uses PostgreSQL's `FOR UPDATE SKIP LOCKED` for atomic job claiming:

```python
def get_next_review(self, worker_id):
    review = ReviewQueue.query.filter(
        ReviewQueue.status == ReviewStatus.PENDING
    ).order_by(
        ReviewQueue.priority.asc(),
        ReviewQueue.created_at.asc()
    ).with_for_update(skip_locked=True).first()

    if review:
        review.status = ReviewStatus.REVIEWING
        review.worker_id = worker_id
        db.session.commit()
```

This ensures:
- No duplicate processing
- Fair job distribution
- Priority ordering respected
- No deadlocks with concurrent workers

## Webhook Delivery

### Delivery Mechanism

```python
def _send_webhook(self, review):
    payload = {
        'event': 'review.completed',
        'review_id': str(review.id),
        'result': {
            'passed': review.status == ReviewStatus.PASSED,
            'code': review.result_code.value,
            'message': review.result_message,
            'confidence': review.confidence_score
        }
    }

    response = requests.post(
        review.webhook_url,
        json=payload,
        timeout=10
    )
```

### User Webhook Configuration

Users can configure up to 5 webhooks (CE edition) with filters:
- `target_types` - Only certain content types
- `result_codes` - Only certain results (e.g., failures only)
- `event_types` - Future: different event categories

## LLM Integration

QE Bee optionally uses a fast LLM (phi4) for quality assessment:

```python
async def _llm_quality_check(self, content, target_type, metadata):
    prompt = f"""You are a quality assurance reviewer.
    Quickly assess this {target_type} output.

    CONTENT TO REVIEW:
    {content[:2000]}

    Respond with ONLY JSON:
    {{"passed": true/false, "score": 1-10, "reason": "brief explanation"}}
    """

    response = self.session.post(
        f"{self.llm_service_url}/generate",
        json={
            'model': self.llm_model,
            'prompt': prompt,
            'options': {'num_predict': 100, 'temperature': 0.1}
        }
    )
```

## Scalability Considerations

### Horizontal Scaling

Multiple QE Bee workers can run simultaneously:
- `SKIP LOCKED` prevents duplicate processing
- Each worker has unique ID for tracking
- Stateless design allows easy scaling

### Performance Tuning

| Setting | Description | Default |
|---------|-------------|---------|
| `QE_BEE_POLL_INTERVAL` | Seconds between polls | 5 |
| `QE_BEE_TIMEOUT` | LLM request timeout | 30 |
| `QE_BEE_LLM_ENABLED` | Enable LLM checks | true |

### Resource Limits

Docker Compose configuration:
```yaml
deploy:
  resources:
    limits:
      memory: 128M
      cpus: '0.25'
    reservations:
      memory: 32M
```

## Security Model

### Authentication

- User endpoints: `require_auth_or_api_key` decorator
- Admin endpoints: Role check (`admin`, `super_admin`)
- Internal endpoints: No auth (container network only)

### Network Isolation

Internal endpoints are only accessible within Docker network:
- Worker → App: HTTPS with verify=False (self-signed)
- App → Worker: Not applicable (worker polls)
- External webhooks: User-configured URLs

### Webhook Security (Future)

Planned HMAC signing for webhook payloads:
```python
# Planned for Enterprise edition
signature = hmac.new(
    webhook.secret.encode(),
    json.dumps(payload).encode(),
    hashlib.sha256
).hexdigest()
headers['X-QE-Bee-Signature'] = f"sha256={signature}"
```

## Error Handling

### Worker Errors

- Network failures: Retry with backoff
- LLM timeout: Skip LLM check, pass with warning
- Content fetch failure: Return `REVIEW_ERROR`

### Service Errors

- Database errors: Rollback transaction
- Webhook failures: Log error, update `total_failed`
- Queue errors: Return None (no job)

## Monitoring & Observability

### Key Metrics

- `review_queue.pending` - Queue depth
- `review_history.processing_time_ms` - Review latency
- `webhook_configs.total_failed` - Webhook reliability
- Pass/fail rates by `result_code`

### Health Check

```bash
curl https://localhost:8443/api/qe-bee/health
# {"status": "healthy", "service": "qe-bee", "timestamp": "..."}
```

## Future Enhancements

### CE Edition
- Review dashboard in admin panel
- User notification integration
- Batch review operations

### Enterprise Edition
- Custom QA/QE agents (user-defined)
- External integrations (Slack, Teams)
- Advanced analytics dashboard
- Compliance-specific review profiles
- Multi-tenant isolation

---

*Architecture document created: November 2025*
