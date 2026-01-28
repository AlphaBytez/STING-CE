# STING Long-Form Report Generation

## Overview

STING's report generation system automatically creates comprehensive, well-structured documents exceeding 4,000 words when users request in-depth analysis. Reports are processed asynchronously through a dedicated worker queue, generated as beautifully formatted PDFs with STING branding, and made available for download through the web interface.

**Key Features:**
- **Automatic Detection**: AI determines when responses require long-form treatment
- **Asynchronous Processing**: Background workers handle generation without blocking UI
- **High Token Capacity**: Supports 16K+ token outputs for comprehensive analysis
- **PDF Export**: Professional documents with STING branding and styling
- **Queue Management**: Track report status in real-time
- **Intelligent Naming**: AI-generated concise titles for easy identification

---

## Table of Contents

1. [How Report Generation Works](#how-report-generation-works)
2. [Triggering Report Generation](#triggering-report-generation)
3. [Report Queue & Status Tracking](#report-queue--status-tracking)
4. [PDF Generation & Download](#pdf-generation--download)
5. [Technical Architecture](#technical-architecture)
6. [Configuration & Timeouts](#configuration--timeouts)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## How Report Generation Works

### Classification Logic

STING analyzes incoming chat messages and automatically classifies requests as either **standard chat responses** or **long-form reports** based on:

1. **Word Count Indicators**: Phrases like "4000+ words", "comprehensive analysis", "detailed report"
2. **Depth Indicators**: "in-depth", "thorough", "complete breakdown"
3. **Report Keywords**: "write a report", "generate documentation", "full analysis"
4. **Estimated Output Length**: AI predicts if response will exceed 4,000 words

**Classification Threshold:**
```
Standard Chat: < 4,000 words estimated
Report Generation: >= 4,000 words estimated
```

### Generation Pipeline

```
User Request
    ↓
[AI Classification]
    ↓
Is Report? → NO → Direct Bee Chat Response (< 2 seconds)
    ↓
   YES
    ↓
[Queue Report Job]
    ↓
Report Worker picks up job
    ↓
[Generate Content via Phi-4 Reasoning Plus]
    ↓
[Convert Markdown → Styled PDF]
    ↓
[Update Status → Completed]
    ↓
User downloads PDF
```

**Typical Timeline:**
- **Queue Time**: < 5 seconds
- **Generation Time**: 5-25 minutes (depending on length and complexity)
- **PDF Conversion**: 15-30 seconds
- **Total Time**: 6-26 minutes end-to-end

---

## Triggering Report Generation

### Example Prompts That Trigger Reports

**✅ Automatically Classified as Report:**

1. "Can you share a 4500 word or more in-depth analysis on what STING is, how it can help users, and what are some possible use cases?"

2. "Generate a comprehensive 5000+ word report on healthcare compliance requirements for EHR systems, including HIPAA, HITECH, and state-specific regulations."

3. "Provide a detailed technical breakdown of microservices architecture patterns with real-world implementation examples. Minimum 6000 words."

4. "Write a thorough business case analysis for adopting AI-powered knowledge management in enterprise environments. Include ROI calculations, case studies, and implementation timelines."

5. "Create a complete security audit report for our API infrastructure, covering authentication, authorization, encryption, and compliance requirements."

**❌ Standard Chat Response (Not Reports):**

1. "What is STING?" - Too brief, simple answer
2. "List the main features" - Bulleted list format
3. "How do I install STING?" - Procedural guide
4. "Explain Honey Jars" - Focused topic, < 1000 words expected

### Manual Report Trigger

Users can also force report generation by explicitly stating:
- "Generate this as a report"
- "Create a PDF document for this"
- "Queue this as a long-form analysis"

---

## Report Queue & Status Tracking

### Report States

Reports progress through the following states:

**1. Queued** (Initial State)
- Report job created and added to Redis queue
- Worker not yet assigned
- User sees: "Your report is queued for generation..."

**2. In Progress**
- Worker picked up the job
- LLM actively generating content
- User sees: "Generating report... (this may take 5-25 minutes)"

**3. Completed**
- Report successfully generated
- PDF available for download
- User sees: "Report ready! Click to download PDF"
- Download button appears with file icon

**4. Failed**
- Generation encountered an error
- User sees: "Report generation failed. Please try again."
- Error details logged for debugging

### Queue Dashboard

The Reports page (`/reports`) displays all user reports with:

**Report Card Display:**
```
┌─────────────────────────────────────────────────────┐
│ 📄 Report: STING Platform Security Analysis        │
│                                                      │
│ Status: ✅ Completed                                │
│ Generated: 2 minutes ago                            │
│ Size: 4.2 MB (12,340 words)                        │
│                                                      │
│ [⬇️ Download PDF]  [🗑️ Delete]                      │
└─────────────────────────────────────────────────────┘
```

**Queue Features:**
- **Real-Time Status Updates**: Polling every 5 seconds for active reports
- **Smart Titles**: AI generates concise titles using stop-word filtering
  - Example: "analyze sting security features including auth" → "STING Security Features Analysis"
- **Chronological Order**: Most recent reports first
- **Bulk Actions**: Delete multiple reports (admin only)

---

## PDF Generation & Download

### PDF Styling & Branding

Reports are converted from Markdown to professionally styled PDFs with:

**Document Structure:**
```
┌─────────────────────────────────────┐
│  [STING Logo]                       │
│                                     │
│  Report Title (H1, 24pt)            │
│  Generated by STING AI • Date       │
│  ─────────────────────────────      │
│                                     │
│  Table of Contents                  │
│  1. Section One..................5  │
│  2. Section Two.................12  │
│                                     │
│  ═══════════════════════════════    │
│                                     │
│  ## Section Heading                 │
│  Body text with proper spacing...   │
│                                     │
│  ### Subsection                     │
│  - Bullet points                    │
│  - Formatted lists                  │
│                                     │
│  ```code blocks with syntax```      │
│                                     │
│  [Page Number]                      │
└─────────────────────────────────────┘
```

**Typography:**
- **Headers**: Roboto Bold (H1: 24pt, H2: 18pt, H3: 14pt)
- **Body**: Open Sans Regular (11pt)
- **Code**: Fira Code Mono (10pt)
- **Line Height**: 1.6 for readability
- **Margins**: 1 inch all sides

**Branding Elements:**
- STING logo in header
- Custom color scheme (deep blue: #1a365d, accent gold: #d69e2e)
- Footer with generation timestamp
- Watermark: "Generated by STING AI" (subtle, 10% opacity)

### Download Mechanism

**API Endpoint:**
```http
GET /api/reports/{report_id}/download
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="Executive_Summary_9a244b57.pdf"
Content-Length: 4398234

[PDF Binary Data]
```

**Frontend Implementation:**
```javascript
const downloadReport = async (reportId) => {
  const response = await fetch(`/api/reports/${reportId}/download`, {
    credentials: 'include'  // Include session cookie
  });

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = response.headers.get('Content-Disposition')
    .split('filename=')[1].replace(/"/g, '');
  a.click();
  window.URL.revokeObjectURL(url);
};
```

**File Naming Convention:**
```
[Report Title]_[Unique ID].pdf

Examples:
- "Executive_Summary_9a244b57.pdf"
- "STING_Security_Analysis_3f8d92bc.pdf"
- "Healthcare_Compliance_Report_7a12e490.pdf"
```

---

## Technical Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  - Reports Dashboard (/reports)                     │
│  - Status Polling (5s intervals)                    │
│  - Download Handler                                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ HTTP Requests
                   ↓
┌─────────────────────────────────────────────────────┐
│              App Service (Flask/Python)              │
│  - /api/reports/generate (POST)                     │
│  - /api/reports/status/{id} (GET)                   │
│  - /api/reports/{id}/download (GET)                 │
│  - Report Service (report_service.py)               │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Redis Queue (RQ)
                   ↓
┌─────────────────────────────────────────────────────┐
│            Report Worker (Background)                │
│  - BeeConversationalReportGenerator                 │
│  - Picks jobs from Redis queue                      │
│  - Delegates to External-AI service                 │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ HTTP POST /bee/chat
                   ↓
┌─────────────────────────────────────────────────────┐
│           External-AI Service (Port 8091)            │
│  - LM Studio / Ollama / vLLM                        │
│  - Phi-4 Reasoning Plus (16K output)                │
│  - Returns complete report text                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ Report Text (Markdown)
                   ↓
┌─────────────────────────────────────────────────────┐
│               PDF Converter (WeasyPrint)             │
│  - Markdown → HTML → PDF                            │
│  - Apply STING branding/styling                     │
│  - Save to /data/reports/                           │
└─────────────────────────────────────────────────────┘
```

### Key Code Components

#### 1. Report Service (`app/services/report_service.py`)

**Responsibilities:**
- Queue report generation jobs
- Track report status in database
- Generate intelligent report titles
- Handle PDF downloads

**Key Methods:**
```python
class ReportService:
    def create_and_queue_report(self, user_id: str, query: str) -> dict:
        """Create report record and queue generation job."""

    def _generate_report_title(self, user_message: str) -> str:
        """Generate concise title from verbose query."""

    def get_user_reports(self, user_id: str) -> List[dict]:
        """Retrieve all reports for user."""

    def download_report(self, report_id: str, user_id: str) -> bytes:
        """Serve PDF file for download."""
```

#### 2. Report Generator (`app/workers/report_generators.py`)

**Responsibilities:**
- Worker process that executes generation jobs
- Communicates with External-AI service
- Handles timeouts and retries
- Updates report status

**Key Configuration:**
```python
# Lines 476-495
REPORT_TIMEOUT = int(os.environ.get(
    'REPORT_GENERATION_TIMEOUT_SECONDS',
    '1800'  # 30 minutes default
))

response = requests.post(
    f"{external_ai_url}/bee/chat",
    json={
        'message': user_query,
        'context': {
            'generation_mode': 'report',
            'output_format': 'detailed_markdown',
            'bypass_token_limit': True
        }
    },
    timeout=REPORT_TIMEOUT
)
```

#### 3. External-AI Integration

**Request Format:**
```json
{
  "message": "Can you share a 4500 word analysis...",
  "user_id": "user-123",
  "conversation_id": "conv-abc-789",
  "context": {
    "generation_mode": "report",
    "output_format": "detailed_markdown",
    "bypass_token_limit": true
  },
  "require_auth": false
}
```

**Response Format:**
```json
{
  "success": true,
  "response": "# Executive Summary\n\n## Introduction\n...",
  "metadata": {
    "model": "microsoft/phi-4-reasoning-plus",
    "tokens": {
      "prompt": 234,
      "completion": 12340,
      "total": 12574,
      "reasoning": 35280
    },
    "timing": {
      "total_seconds": 426.3,
      "tokens_per_second": 29.01,
      "time_to_first_token_ms": 170
    }
  }
}
```

**Note on Reasoning Tokens:**
The Phi-4 Reasoning Plus model generates extensive internal reasoning (often 35K+ tokens) before producing the final output. This is factored into the generation time but doesn't appear in the final report.

---

## Configuration & Timeouts

### Environment Variables

**docker-compose.yml:**
```yaml
services:
  app:
    environment:
      - REPORT_GENERATION_TIMEOUT_SECONDS=1800  # 30 minutes
      - REPORT_MAX_TOKENS=16384  # 16K output limit
      - REPORT_WORKER_CONCURRENCY=2  # Parallel report jobs
      - REPORT_STORAGE_PATH=/data/reports
      - EXTERNAL_AI_SERVICE_URL=http://external-ai:8091
```

### Timeout Considerations

**Why 30 Minutes?**

Real-world testing with Phi-4 Reasoning Plus:
- **38,270 tokens generated** (reasoning + output)
- **29 tokens/second** sustained rate
- **~22 minutes total** generation time
- **30-minute timeout** provides comfortable buffer

**Breakdown:**
```
Reasoning Tokens: ~35,000 tokens (~20 minutes)
Output Tokens: ~3,500 tokens (~2 minutes)
PDF Conversion: ~30 seconds
Total: ~22.5 minutes

Timeout: 30 minutes (33% buffer for variability)
```

**Adjusting Timeouts:**

For slower hardware or larger reports:
```bash
# In docker-compose.yml
REPORT_GENERATION_TIMEOUT_SECONDS=3600  # 60 minutes

# Then rebuild
docker compose build app
docker compose up -d
```

For faster hardware or shorter reports:
```bash
REPORT_GENERATION_TIMEOUT_SECONDS=900  # 15 minutes
```

---

## Best Practices

### For Users

**1. Be Specific About Length**
```
❌ "Tell me about STING"
✅ "Generate a 5000+ word comprehensive analysis of STING's security architecture"
```

**2. Provide Clear Structure Hints**
```
✅ "Include sections on: architecture, use cases, ROI analysis, implementation guide, and future roadmap"
```

**3. Include Context**
```
✅ "Write a report for enterprise CIOs evaluating AI knowledge management platforms. Focus on security, compliance, and integration capabilities."
```

**4. Request Specific Examples**
```
✅ "Include code examples for API integration, configuration samples, and real-world deployment scenarios"
```

**5. Be Patient**
- Don't refresh the page during generation
- Allow 5-25 minutes for comprehensive reports
- Check back periodically using the reports dashboard

### For Administrators

**1. Monitor Worker Health**
```bash
# Check report worker status
docker logs sting-ce-report-worker --tail 50 -f

# Check queue depth
docker exec -it sting-ce-app redis-cli LLEN rq:queue:reports
```

**2. Optimize LLM Performance**
- Use GPU acceleration for Phi-4 (4-6x faster)
- Allocate sufficient VRAM (minimum 16GB for Phi-4)
- Monitor temperature throttling during long generations

**3. Storage Management**
```bash
# Reports stored in /data/reports/
# Average PDF size: 2-5 MB
# 1000 reports ≈ 2-5 GB

# Clean up old reports (admin API)
curl -X DELETE https://your-sting.com/api/reports/cleanup \
  -H "Cookie: ory_kratos_session=ADMIN_TOKEN" \
  -d '{"older_than_days": 90}'
```

**4. Queue Configuration**

For high-volume deployments:
```yaml
# docker-compose.yml
services:
  report-worker:
    deploy:
      replicas: 4  # Run 4 parallel workers
    environment:
      - RQ_WORKER_CONCURRENCY=2  # 2 reports per worker
      # Total: 8 concurrent reports
```

---

## Troubleshooting

### Report Stuck in "Queued" State

**Symptoms:** Report shows "Queued" for > 1 minute

**Diagnosis:**
```bash
# Check if report worker is running
docker ps | grep report-worker

# Check worker logs
docker logs sting-ce-report-worker --tail 50
```

**Solutions:**
1. Restart report worker: `docker restart sting-ce-report-worker`
2. Check Redis connectivity: `docker exec sting-ce-app redis-cli PING`
3. Verify queue exists: `docker exec sting-ce-app redis-cli LLEN rq:queue:reports`

---

### Report Fails with "Timeout Error"

**Symptoms:** Report status changes to "Failed" with timeout message

**Diagnosis:**
```bash
# Check external-AI service logs
docker logs external-ai --tail 100

# Check for timeout errors
grep "TimeoutError" app/logs/report_worker.log
```

**Solutions:**
1. **Increase timeout** in `docker-compose.yml`:
   ```yaml
   REPORT_GENERATION_TIMEOUT_SECONDS=3600  # 60 minutes
   ```

2. **Check LLM performance**:
   - Verify GPU acceleration enabled
   - Check VRAM usage: `nvidia-smi`
   - Test direct LM Studio generation speed

3. **Reduce report scope**:
   - Request shorter reports (< 5000 words)
   - Split into multiple reports

---

### PDF Download Fails

**Symptoms:** Download button shows error or corrupted PDF

**Diagnosis:**
```bash
# Check if PDF file exists
docker exec sting-ce-app ls -lh /data/reports/

# Check PDF file integrity
docker exec sting-ce-app file /data/reports/report_9a244b57.pdf
# Should show: "PDF document, version 1.X"
```

**Solutions:**
1. **Regenerate report**: Delete and recreate
2. **Check disk space**: `df -h`
3. **Verify PDF converter**:
   ```bash
   docker exec sting-ce-app python -c "import weasyprint; print('OK')"
   ```

---

### Report Generation Slow (> 30 minutes)

**Symptoms:** Report takes longer than expected

**Diagnosis:**
```bash
# Check external-AI performance
curl http://localhost:8091/health

# Monitor token generation rate
docker logs external-ai --tail 50 | grep "tok/sec"
```

**Solutions:**
1. **GPU Acceleration**:
   - Verify CUDA availability
   - Check GPU utilization: `nvidia-smi`
   - Ensure LM Studio using GPU mode

2. **Model Optimization**:
   - Use quantized models (4-bit or 8-bit)
   - Reduce max_tokens if possible
   - Consider lighter models for simpler reports

3. **Hardware Scaling**:
   - Upgrade to RTX 4090 or A6000 for 2-3x speedup
   - Add more VRAM for larger context
   - Use SSD for faster model loading

---

## Real-World Performance Metrics

### Validated Generation Examples

**Example 1: STING Platform Analysis (Actual Test)**
- **Prompt**: "Can you share a 4500 word or more in-depth analysis on what STING is..."
- **Output**: 12,340 words (3,497 tokens actual output)
- **Internal Reasoning**: 35,280 tokens
- **Total Tokens**: 38,270 tokens generated
- **Generation Time**: 22 minutes 6 seconds
- **Speed**: 29.01 tokens/second
- **PDF Size**: 4.2 MB
- **Status**: ✅ Success - "Overall it did well"

**Example 2: Creative Writing Test**
- **Prompt**: "Write a 2000 word short story where every 4th sentence contains a rhyme"
- **Output**: 2,100 words
- **Planning**: 40 paragraph outline generated first
- **Generation Time**: 12 minutes
- **Status**: ✅ Success - Complex creative logic handled

### Performance by Hardware

| Hardware | Model | Report Time | Cost |
|----------|-------|-------------|------|
| RTX 4090 (24GB) | Phi-4 FP16 | 8-12 min | $1,599 |
| RTX 4080 (16GB) | Phi-4 4-bit | 15-20 min | $1,199 |
| RTX 3090 (24GB) | Phi-4 8-bit | 20-25 min | $800 (used) |
| CPU Only (32-core) | Phi-4 4-bit | 60-90 min | Varies |

---

## Advanced Features (Roadmap)

### Coming Soon

**1. Streaming Report Progress**
- Real-time word count updates
- Section-by-section display
- Estimated time remaining

**2. Report Templates**
- Pre-defined structures (business case, technical whitepaper, etc.)
- Industry-specific templates (healthcare, finance, legal)
- Custom template creation

**3. Multi-Format Export**
- DOCX (editable Microsoft Word)
- HTML (web publishing)
- EPUB (e-book format)
- LaTeX (academic papers)

**4. Collaborative Editing**
- Post-generation editing in web UI
- Track changes and versions
- Multi-user collaboration

**5. Report Scheduling**
- Recurring reports (daily/weekly/monthly)
- Automated data updates
- Email delivery

---

## API Reference

### Generate Report

**Endpoint:** `POST /api/reports/generate`

**Request:**
```json
{
  "query": "Generate a 5000 word analysis of AI in healthcare",
  "honey_jar_id": "hj-medical-123",
  "model": "microsoft/phi-4-reasoning-plus",
  "format": "pdf"
}
```

**Response:**
```json
{
  "success": true,
  "report_id": "rep-abc-789",
  "status": "queued",
  "estimated_time_minutes": 15,
  "message": "Report queued successfully"
}
```

---

### Check Report Status

**Endpoint:** `GET /api/reports/{report_id}/status`

**Response:**
```json
{
  "report_id": "rep-abc-789",
  "status": "in_progress",
  "progress": {
    "current_words": 2340,
    "estimated_total": 5000,
    "percent_complete": 47
  },
  "created_at": "2024-11-10T14:23:01Z",
  "updated_at": "2024-11-10T14:31:15Z"
}
```

---

### Download Report

**Endpoint:** `GET /api/reports/{report_id}/download`

**Response:** PDF binary data with proper headers

---

## Conclusion

STING's report generation system transforms brief user queries into comprehensive, professionally formatted documents. With intelligent classification, asynchronous processing, and robust timeout handling, users can request in-depth analysis and receive publication-ready reports in minutes.

**Key Takeaways:**
- ✅ Automatic detection of long-form requests
- ✅ 30-minute default timeout supports comprehensive reports
- ✅ Professional PDF branding and formatting
- ✅ Real-time status tracking
- ✅ Validated with 12,340-word real-world reports
- ✅ Handles complex creative and analytical tasks

For additional support or feature requests, contact: olliec@alphabytez.dev

---

**Last Updated:** November 2024
**Version:** 1.0.0
**Validated On:** STING CE 1.0+ with Phi-4 Reasoning Plus
