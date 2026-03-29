# STING — Platform Overview

**Secure Trusted Intelligence and Networking Guardian**
*Your Data. Your AI. Your Rules.*

---

## At a Glance

| Term | What It Is |
|------|-----------|
| **STING** | The platform — a private, self-hosted AI knowledge management system. Nothing leaves your network. |
| **Bee** | The AI assistant users interact with. Available through the web interface and API. |
| **Honey Jars** | Secure knowledge bases. Upload documents, Bee searches them to answer questions. |
| **Hive Scrambler** | The PII protection engine. Strips sensitive data before the AI sees it, reconstructs it after. |
| **QE Bee (Review Bee)** | Quality assurance agent. Checks every AI response for leaks and accuracy before delivery. |
| **Honey Combs** | Data source connectors. Plug external systems into your knowledge bases. |
| **msting** | Command-line management tool. 40+ commands for admins — start, stop, backup, update, diagnose. |
| **External AI Gateway** | Model-agnostic LLM layer. Swap between Ollama, OpenAI, vLLM, or others without code changes. |
| **Vault** | Secret management (HashiCorp Vault). All credentials encrypted and centrally managed. |
| **Kratos** | Identity engine (Ory Kratos). Passwordless auth, passkeys, multi-factor — no passwords to steal. |

---

## What Is STING?

STING is a private AI assistant platform that runs entirely within your organization. Unlike cloud AI services where your data travels to someone else's servers, STING keeps everything — every question, every document, every answer — on your infrastructure. You get the full power of modern AI without giving up control of your information.

---

## The Problem STING Solves

Organizations face a dilemma: employees want to use AI tools to work faster, but sending company data to external AI services creates real risks — data leaks, compliance violations, loss of intellectual property. IT teams are left choosing between banning AI (losing productivity) or allowing it (losing control).

STING eliminates that tradeoff.

---

## How It Works — In Plain Terms

### For Your Employees

Your team accesses Bee through STING's web interface — a clean, modern chat UI that's easy to learn and use. Bee can answer questions, search company knowledge bases, generate reports, and more.

### For Your IT & Security Team

Behind the scenes, every interaction passes through a **PII protection pipeline** that automatically detects and masks sensitive information (social security numbers, credit card numbers, personal data) before it ever reaches the AI model. Your security team sets the rules; STING enforces them automatically.

### For Leadership

You get AI-powered productivity gains across the organization while maintaining complete data sovereignty. Every query, every document, every AI response stays within your walls. There is nothing to audit externally because nothing leaves.

---

## Key Capabilities

### 🐝 Bee — Your Organization's AI Assistant

Bee is the face of STING — a smart, context-aware assistant that employees interact with naturally.

- **Answers questions** using your organization's own knowledge bases
- **Generates reports** with customizable templates and formats
- **Searches documents** semantically — finds answers even when the exact words don't match
- **Learns your organization** — the more knowledge you add, the smarter Bee gets
- **Quality checked** — every response is automatically reviewed for accuracy and data safety before delivery

### 🍯 Honey Jars — Secure Knowledge Bases

Think of Honey Jars as smart filing cabinets that Bee can search through.

- Upload documents (PDFs, Word docs, spreadsheets, text files) and Bee understands them
- Control who can access what — public knowledge for everyone, private jars for specific teams
- Documents are automatically scanned for sensitive data on upload
- Encrypted at rest — even if someone accesses the storage directly, the data is protected

### 🔐 Enterprise-Grade Security

- **Passwordless authentication** — passkeys, biometrics, magic links (no passwords to steal)
- **Multi-factor authentication** — TOTP codes plus hardware keys for admin accounts
- **Secret management** — all credentials stored in HashiCorp Vault (industry standard)
- **Complete audit trail** — every admin action, every AI interaction, every data access logged
- **Role-based access** — admins, moderators, and standard users with appropriate permissions

### 🔍 Automatic PII Protection

This is where STING fundamentally differs from cloud AI services:

1. Employee asks Bee a question
2. STING scans the question for personal information
3. Sensitive data is replaced with safe tokens before the AI sees it
4. The AI processes the sanitized question
5. STING reconstructs the answer with the original data
6. A quality check confirms no sensitive information leaked
7. The clean answer is delivered

**The AI model never sees your employees' personal data.** This happens automatically on every interaction — no employee training required.

---

## Deployment — Simpler Than You Think

### One-Command Install

```
bash -c "$(curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE/main/bootstrap.sh)"
```

A browser-based setup wizard walks you through configuration — hostname, AI model, email, SSL certificates, and more. Most installations are complete in under an hour.

### Runs Anywhere

- **Your servers** — any Linux server with Docker
- **Virtual machines** — pre-built VM appliance available
- **Air-gapped networks** — works fully offline with local AI models

### Choose Your AI

STING doesn't lock you into one AI provider. Run open-source models locally with Ollama for maximum privacy, connect to OpenAI for convenience, or mix and match:

- **Ollama** — local, private, no internet required
- **OpenAI / Azure OpenAI** — cloud-hosted, high performance
- **vLLM / LM Studio** — self-hosted alternatives
- **Any OpenAI-compatible API** — works with most providers

Switching models is a configuration change, not a code change.

---

## Management — Not a Full-Time Job

STING is designed to be managed, not babysat.

- **Web admin panel** — covering every aspect of the platform
- **Command-line tool** (`msting`) — 40+ commands for automation and scripting
- **Automated backups** — encrypted, scheduled, one-command restore
- **Health monitoring** — built-in diagnostics with one-command support bundles
- **Maintenance mode** — graceful user notification during updates
- **Auto-updating SSL** — Let's Encrypt integration with automatic renewal

---

## Who Is STING For?

| Organization Type | Why STING |
|------------------|-----------|
| **Regulated industries** (finance, healthcare, legal) | Data never leaves your infrastructure; PII protection is automatic |
| **Government & defense** | Air-gapped deployment, no external dependencies |
| **Organizations with sensitive IP** | AI-powered productivity without exposing trade secrets |
| **Privacy-conscious companies** | Complete data sovereignty — you own every byte |

---

## What Makes STING Different

| | Cloud AI Services | Self-Hosted Open Source | STING |
|---|---|---|---|
| **Data stays on-premises** | ❌ | ✅ | ✅ |
| **Automatic PII protection** | ❌ | ❌ | ✅ |
| **Enterprise admin tooling** | ✅ | ❌ | ✅ |
| **Installs in under an hour** | N/A | ❌ | ✅ |
| **Air-gap capable** | ❌ | Varies | ✅ |
| **Quality-checked responses** | ❌ | ❌ | ✅ |

---

## Getting Started

1. **Install** — one command, browser-based wizard
2. **Connect your AI** — point to Ollama, OpenAI, or your preferred model
3. **Add knowledge** — upload documents to Honey Jars
4. **Your team starts using AI** — no training required

---

*STING — Bee Smart. Bee Secure.*

*Contact: olliec@alphabytez.dev*
*Documentation: docs.stingassistant.com*
*GitHub: AlphaBytez/STING-CE-Public*

---

> Looking for enterprise features like ChatOps, bot workers, and advanced monitoring? Check out [STING Hive](https://stingassistant.com/hive).
