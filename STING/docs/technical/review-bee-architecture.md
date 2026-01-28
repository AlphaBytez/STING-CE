# ReviewBee 🐝 - Intelligent Report Quality Assurance

## Overview

ReviewBee is STING's intelligent report quality assurance system that ensures generated reports meet user requirements before delivery. It implements the **Critic-Revise** pattern using a lightweight model to analyze reports and a powerful model to regenerate when improvements are needed.

## Core Philosophy

> **"Compare the final output against the original ask."**

ReviewBee's mission is simple: verify that what was generated actually answers what the user asked for. It doesn't need full context of every system—just enough to enforce strict, clear requirements.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Request                                │
│  "Generate a report about X with 3 use cases and architecture"  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Primary LLM Generation                        │
│              (e.g., phi-4-reasoning-plus)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ReviewBee Critic                           │
│                     (lightweight model)                         │
│                                                                 │
│  1. Extract requirements from original request                  │
│  2. Compare report against requirements                         │
│  3. Check grammar, structure, truth                             │
│  4. Generate structured task list                               │
│  5. Score quality (0.0 - 1.0)                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Score < Threshold?
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼ YES                           ▼ NO
┌─────────────────────────┐     ┌─────────────────────────┐
│   Regenerate Report     │     │   Return Original       │
│   with Task List        │     │   Report                │
└─────────────────────────┘     └─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Quality Validation                            │
│                                                                 │
│  ✓ Length ratio ≥ 70% of original                               │
│  ✓ No unexpected character encoding (CJK, etc.)                 │
│  ✓ Structure preserved (headers maintained)                     │
└─────────────────────────────────────────────────────────────────┘
              │
    Validation Passed?
              │
    ┌────────┴────────┐
    │                 │
    ▼ YES             ▼ NO
┌─────────────┐  ┌─────────────┐
│ Use Revised │  │ Keep        │
│ Report      │  │ Original    │
└─────────────┘  └─────────────┘
```

## Key Features

### 1. Requirements Extraction

ReviewBee automatically extracts implicit and explicit requirements from user requests:

- **Word count**: "at least 1000 words", "brief summary"
- **Sections**: "include executive summary", "add architecture diagram"
- **Format**: "use bullet points", "comprehensive analysis"
- **Explicit questions**: Any questions in the request that need answers

### 2. Structured Task List

Instead of vague "improve this" feedback, ReviewBee generates specific, actionable tasks:

```
**Your task list:**
  1. Add the requested deployment architecture section
  2. Include specific HIPAA compliance considerations  
  3. Expand the third use case with more technical detail
```

### 3. Quality Validation

Before accepting any revision, ReviewBee validates it won't make things worse:

| Check | Threshold | Purpose |
|-------|-----------|---------|
| Length ratio | ≥ 70% | Prevent content loss |
| Unexpected chars | < original + 5 | Catch encoding issues |
| Header count | ≥ 50% of original | Preserve structure |

If validation fails, the original report is kept and the revision is rejected.

### 4. Security by Design

- **All data is ephemeral** - dies with the request, never persisted
- **No Redis/cache needed** - actually more secure this way
- **PII-aware** - understands `[PII_TOKEN]` placeholders are intentional
- **Raw critique stays internal** - only safe metadata exposed in API

## Configuration

ReviewBee is configured in `config.yml`:

```yaml
llm_service:
  # ... other config ...
  
  review_bee:
    enabled: true  # Set to false to disable
    mode: "critique_and_revise"  # or "critique_only"
    revision_threshold: 0.8  # Trigger revision if score below this
    critic:
      model: "phi4"  # Lightweight model for critique
    max_iterations: 1  # Currently single-pass
```

### Modes

| Mode | Behavior |
|------|----------|
| `critique_only` | Analyze but never regenerate |
| `critique_and_revise` | Analyze and regenerate if needed |

## API Response

When ReviewBee is enabled, responses include metadata:

```json
{
  "response": "...",
  "review_bee": {
    "enabled": true,
    "critic_model": "phi4",
    "mode": "critique_and_revise",
    "critique_score": 0.75,
    "requirements_met": "PARTIAL",
    "gaps_count": 2,
    "task_list_count": 3,
    "findings_count": 5,
    "revision_applied": true,
    "original_length": 7880,
    "revised_length": 10868,
    "quality_metrics": {
      "length_ratio": 1.38,
      "unexpected_chars": 0,
      "original_headers": 12,
      "revised_headers": 20
    }
  }
}
```

### Response Fields

| Field | Description |
|-------|-------------|
| `critique_score` | Quality score 0.0-1.0 (1.0 = perfect) |
| `requirements_met` | YES / PARTIAL / NO |
| `gaps_count` | Missing items from original request |
| `task_list_count` | Action items generated |
| `revision_applied` | Whether revision was used |
| `revision_rejected` | True if revision failed validation |
| `rejection_reasons` | Why revision was rejected |

## Performance Considerations

- **Adds 1-2 LLM calls** per report when revision triggered
- **Memory overhead**: ~50KB per request (ephemeral)
- **No network latency** for caching (no Redis involved)
- **Critic uses lightweight model** to minimize token usage

## Disabling ReviewBee

For maximum speed or when quality isn't critical:

```yaml
review_bee:
  enabled: false
```

Or use critique-only mode to get feedback without regeneration:

```yaml
review_bee:
  enabled: true
  mode: "critique_only"
```

---

## 🚀 Future Roadmap

> *The following features are planned for future releases*

### Custom ReviewBees

Create specialized reviewers for different domains:

- **ComplianceBee** - HIPAA, SOC2, GDPR compliance checking
- **TechnicalBee** - Code review and technical accuracy
- **ToneBee** - Brand voice and tone consistency
- **FactBee** - Citation and fact verification

### Cloud Orchestration

For heavy workloads, harness cloud computing with local AI orchestration:

```
┌─────────────────────────────────────────────────────────────┐
│                  Local Orchestrator                         │
│  (lightweight, always-on, manages workflow)                 │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ Local GPU │   │ Cloud API │   │ Edge Node │
    │ (fast,    │   │ (powerful │   │ (private, │
    │  private) │   │  scalable)│   │  secure)  │
    └───────────┘   └───────────┘   └───────────┘
```

**Benefits:**
- Local AI handles orchestration, routing, and sensitive decisions
- Cloud resources burst for heavy generation tasks
- Privacy-preserving: only anonymized/tokenized content leaves appliance
- Cost-effective: use cloud only when local resources saturated

### Multi-Pass Refinement

Allow multiple critic-revise cycles with diminishing returns detection:

```yaml
review_bee:
  max_iterations: 3
  convergence_threshold: 0.05  # Stop if improvement < 5%
```

---

*ReviewBee is part of STING's commitment to delivering accurate, requirement-compliant intelligence reports.*
