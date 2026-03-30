# STING — Technical Features Overview (Mar 2026)

**Secure Trusted Intelligence and Networking Guardian**
*Your Data. Your AI. Your Rules.*

**Version:** 2.0.0-ce | **Architecture:** Self-hosted, Docker Compose orchestrated | **License:** Community Edition (CE)

---

## Executive Summary

STING is a private, on-premises AI-powered knowledge management platform. Every component — from LLM inference to vector search — runs within the organization's infrastructure. No data leaves the deployment.

STING serves two audiences through a single platform:

1. **Administrators** manage the platform through a web UI and CLI, controlling AI models, knowledge bases, user access, and PII policies.
2. **End users** interact with Bee (the AI assistant) through the web interface to ask questions, search knowledge bases, and generate reports.

---

## Platform Architecture

### Microservice Stack (20 services, Docker Compose)

| Layer | Services | Technology |
|-------|----------|------------|
| **Identity & Security** | Ory Kratos, HashiCorp Vault, Nginx reverse proxy | Passwordless auth, secret management, SSL termination |
| **Core Application** | Flask API, React frontend, Gunicorn | 47+ API route modules, Ant Design + Tailwind UI |
| **AI & Knowledge** | External AI Gateway, ChromaDB, Knowledge Service | Multi-LLM support, vector embeddings, semantic search |
| **Communication** | Messaging Service | Redis-backed messaging |
| **Data** | PostgreSQL 16, Redis 5.0+, ChromaDB 0.5.20 | 3 databases, caching, vector storage |
| **Monitoring** | SearXNG, Report Worker, Profile Service | Privacy-respecting search, async report generation |

### External Integration

LLM hosting is **not bundled** — organizations choose their own:
- **Local**: Ollama (on-premises, air-gapped capable)
- **Cloud**: OpenAI, vLLM, LM Studio, or any OpenAI-compatible API
- **Hybrid**: Primary local with cloud fallback

The **External AI Gateway** abstracts LLM providers behind a unified API with a singleton Provider Registry pattern — switching models requires zero code changes.

---

## Core Features

### 🍯 Honey Jars — Knowledge Management

Secure, access-controlled knowledge containers with full-text and semantic search.

| Capability | Details |
|-----------|---------|
| **Document ingestion** | PDF, DOCX, TXT, CSV, Markdown, HTML — auto-chunked for vector indexing |
| **Semantic search** | ChromaDB vector embeddings for meaning-based retrieval |
| **Access control** | Public, private, and team-scoped jars with role-based permissions |
| **PII scanning** | Documents are scanned on upload; PII is flagged before indexing |
| **Bulk operations** | REST API for batch upload, export, and import |
| **Encryption at rest** | AES-256 encryption with Vault-managed keys; `HONEY_RESERVE_MASTER_KEY` for reserve encryption |

### 🐝 Bee AI Assistant

Context-aware AI assistant powered by retrieval-augmented generation (RAG).

| Capability | Details |
|-----------|---------|
| **Multi-model support** | Ollama, OpenAI, MiniMax, vLLM, LM Studio — hot-swappable via Provider Registry |
| **Knowledge grounding** | Bee queries Honey Jars for relevant context before responding |
| **Conversation management** | Thread persistence, conversation history, context window tracking |
| **Report generation** | Long-form report synthesis with configurable models, fallback chain, and max tokens |
| **Review Bee (QE)** | Automated quality assurance agent validates outputs for PII leaks, truncation, and format issues |
| **Streaming responses** | Real-time token streaming via Nginx LLM proxy with upstream failover |
| **Web research** | SearXNG privacy-respecting metasearch for grounded web answers |

### 🔐 Security & Authentication

| Capability | Details |
|-----------|---------|
| **Passwordless by default** | Ory Kratos identity management with magic links |
| **Multi-factor authentication** | TOTP, WebAuthn, passkeys, biometric support |
| **AAL2 enforcement** | Admins required to complete dual-method enrollment (TOTP + passkey) |
| **Secret management** | HashiCorp Vault for all API keys, tokens, and credentials |
| **PII detection middleware** | Request/response scanning with configurable patterns and compliance frameworks |
| **Role-based access** | Admin, moderator, user roles with decorator-based enforcement (`@require_auth`, `@require_admin`, `@require_aal2`) |
| **Rate limiting** | Per-endpoint rate limits with Redis-backed tracking |
| **TLS everywhere** | Self-signed (dev), Let's Encrypt (auto-renewing), or custom certificates |

### 🔍 PII Protection Pipeline

Automatic detection and handling of personally identifiable information at every layer.

```
User Input → PII Middleware (request scan)
    → Hive Scrambler (replaces PII with tokens before LLM)
        → LLM Processing (sees only tokens, never real PII)
            → Reconstruction (tokens → original data)
                → QE Bee (validates no PII leaked)
                    → Response to User
```

- **Pattern library**: SSN, credit cards, emails, phone numbers, custom regex patterns
- **Compliance frameworks**: Configurable per-organization policies
- **Audit logging**: Every PII detection event is logged with type, location, and action taken

---

## Administration

### Web Admin Panel

| Page | Capabilities |
|------|-------------|
| **Dashboard** | System health, usage stats, quick actions |
| **Honey Jars** | Knowledge base management, uploads, access control |
| **Reports** | Report generation queue, history, templates |
| **Bee Chat** | AI assistant interaction, sandbox testing |
| **Templates** | Report and notification templates |
| **User Management** | Roles, permissions, MFA status |
| **Settings** | System configuration, email, SSL, maintenance mode |

### msting CLI

System-wide management interface (`/usr/local/bin/msting`) with 40+ commands backed by 44 shell modules (~26,000 lines):

```
Service Management     Build & Update          Configuration
─────────────────     ──────────────          ─────────────
start [service]       build [service]         sync-config
stop [service]        update [service|all]    regenerate-env
restart [service...]  cache-buzz [--full]     reset-config
recreate [--cascade]  update --nightly        vault-secret list/set
status [-v]                                    
validate [service]    Admin & Users           Maintenance
logs [service]        ───────────────         ───────────
                      create admin/user       maintenance on/off
SSL & Certs           delete admin/user       backup [--encrypt]
───────────           reset-mfa               restore <file>
setup-ssl                                     debug [--plain]
renew-ssl             Diagnostics             buzz collect
ssl-status            ───────────             
export-certs          status -v               
                      validate [service]       
```

### Install Wizard

Browser-based first-run configuration — System → Data Disk → Admin Account → LLM Backend → Report LLM → Email/SMTP → SSL/TLS → Review & Deploy.

---

## Data Architecture

### PostgreSQL 16 (3 databases)

| Database | Purpose | Key Tables |
|----------|---------|-----------|
| `sting_app` | Application data | users, honey_jars, reports, conversations, pii_audit_log |
| `kratos_db` | Identity management | Managed by Ory Kratos |
| `sting_messaging` | Secure messaging | messages, channels, notifications |

Extensions: `uuid-ossp`, `pgcrypto` | Migration files | Role-based access (`app_user`, `kratos_user`, `messaging_user`)

### ChromaDB 0.5.20

Vector embeddings for semantic search across Honey Jar content. Documents are chunked, embedded, and indexed for retrieval-augmented generation.

### Redis 5.0+

Session management, caching, rate limiting, and pub/sub for real-time events.

---

## Deployment Options

| Method | Description |
|--------|-------------|
| **Docker Compose** | Standard deployment — `install_sting.sh` handles full setup |
| **OVA Appliance** | Pre-built VM image via Packer (`.github/workflows/build-ova.yml`) |
| **Codespace** | Development environment with Tailscale networking |
| **Air-gapped** | Fully offline with local Ollama and self-signed certs |

### System Requirements

- **OS**: Ubuntu 22.04+ or macOS 13+
- **CPU**: 4+ cores (8+ recommended with local LLM)
- **RAM**: 16 GB minimum (32+ recommended with local LLM)
- **Disk**: 50 GB minimum
- **Docker**: Docker Engine 24+ with Compose V2

---

## Integration Points

### REST API (47+ route modules)

Full API documentation at `/api/` covering:
- Authentication & sessions
- Honey Jar CRUD, search, bulk operations
- Chat conversations & history
- Report generation & retrieval
- PII detection & audit
- User & admin management

### Service-to-Service Communication

| Path | Protocol | Purpose |
|------|----------|---------|
| App → External AI → Ollama/LLM | HTTPS via Nginx LLM proxy | Chat & report generation |
| App → Knowledge Service → ChromaDB | Internal HTTP | Vector search |
| Kratos → App (webhooks) | HTTPS | Identity lifecycle events |

---

## Technology Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend API** | Python, Flask, SQLAlchemy, Gunicorn | Python 3.11, Flask 2.x, SQLAlchemy 1.x |
| **Frontend** | React, Ant Design, MUI, Tailwind CSS | React 18, Craco build |
| **Microservices** | FastAPI, Pydantic | FastAPI 0.100+ |
| **Identity** | Ory Kratos | 1.3.0 |
| **Secrets** | HashiCorp Vault | Latest |
| **Database** | PostgreSQL | 16 |
| **Cache** | Redis | 5.0+ |
| **Vector DB** | ChromaDB | 0.5.20 |
| **Reverse Proxy** | Nginx | 1.27 Alpine |
| **Search** | SearXNG | Latest |
| **Containers** | Docker + Compose V2 | Engine 24+ |
| **LLM (external)** | Ollama, OpenAI, vLLM, LM Studio | User's choice |

---

## Security Posture

- **Zero external data transmission** — all processing happens on-premises
- **Defense in depth** — TLS everywhere, Vault secret management, PII scanning at every layer
- **Audit trail** — all admin actions, PII events, and authentication events are logged
- **Principle of least privilege** — 3-tier role system, per-database users, service API keys
- **Automatic vulnerability scanning** — dependency pinning with CVE-driven security comments
- **Responsible disclosure** — `security@alphabytez.dev` for vulnerability reports

---

*STING — Bee Smart. Bee Secure.*

*Contact: olliec@alphabytez.dev | GitHub: AlphaBytez/STING-CE-Public*

---

> Looking for enterprise features like ChatOps, bot workers, and advanced monitoring? Check out [STING Hive](https://stingassistant.com/hive).
