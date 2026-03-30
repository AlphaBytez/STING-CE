# Changelog

All notable changes to STING-CE (Community Edition) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-ce] - 2026-03-30

### 🚀 Major Release — Validated Fresh Install Pipeline

Complete overhaul of the installation pipeline, configuration system, and mobile experience. First release with a fully validated end-to-end fresh install process.

### ✨ Added

#### Session Jar System
- **Session Jar API** — Upload and manage temporary file-based knowledge during conversations
- **Session Jar Promotion** — Promote session jars to permanent Honey Jars with AI-generated summaries
- **Session Jar UI Modal** — Interactive modal for naming and promoting session jars

#### Report Generation
- **Report Progress Tracking** — Real-time status messages and stage tracking during report generation
- **Report Quality Review** — Multi-pass iterative refinement with convergence detection via Review Bee
- **Report Type Classification** — Dynamic LLM temperature tuning based on report content type
- **Report Access Control** — Database-level access control for generated reports

#### AI & Context Management
- **Query Strategy Detection** — LLM-powered response strategy classification (direct answer, analysis, troubleshooting, etc.)
- **Enhanced Bee Context Manager** — Improved web search with multi-query extraction and entity disambiguation
- **Bee System Prompt Improvements** — More nuanced personality and response formatting

#### Database & Migrations
- **Database Management Module** (`database.sh`) — Automated migration tracking, application, and verification
- **Migration 017** — Report progress columns (status_message, current_stage)
- **Migration 018** — Session jar columns (jar_type, conversation_id, max_size_bytes)

#### Documentation
- **Features Overview** — Comprehensive feature catalog for community users
- **Technical Features** — Detailed architecture and implementation reference
- **Documentation Hub** — Quick-links README pointing to docs.stingassistant.com

### 🔧 Changed

#### Installation Pipeline (Breaking)
- **Configuration Schema Alignment** — Restructured `config.yml.default` to match enterprise schema (`email` → `email_service`, `ai.llm` → `llm_service`, added `public_bee`)
- **Config Loader Overhaul** — Full rewrite with LLM alias generation, feature limits, caching settings, and Hive Mode placeholders
- **Bootstrap Mode** — Encryption key generation now works in bootstrap mode for fresh installs
- **Docker Volume Handling** — Fixed config_data volume shadowing with conf-defaults fallback
- **Utils Container** — Changed default INIT_MODE from `development` to `bootstrap`

#### Mobile Experience
- **Mobile Chat** — Enhanced with API fallback, improved message context, markdown rendering with syntax highlighting
- **Mobile Reports** — Significant refactoring of report display, filtering, and navigation
- **Mobile Report Detail** — Improved layout and readability for mobile viewports
- **Mobile Navigation** — Updated bottom nav and header components

#### Development Environment
- **Dev Container** — Switched from `universal:2` (15GB) to `ubuntu-22.04` base (~1GB) with explicit Python 3.11, Node.js, and Docker-in-Docker features
- **Tailscale Integration** — Graceful skip when not available in dev environments

### 🐛 Fixed
- **npm ci lock file mismatch** — Changed to `npm install` for Docker build tolerance across npm versions
- **Docker volume shadowing** — Config files now properly populated on fresh installs via conf-defaults backup
- **Config file quoting** — Fixed shell variable expansion in `docker cp` commands
- **Mobile API fallback** — Graceful degradation from external AI endpoint to legacy chat endpoint

### 🗑️ Removed
- **Obsolete DNS docs** — Removed `dns-fix-implementation.md` and `troubleshooting-dns.md` (no longer needed)

---

## [1.0.0-ce] - 2025-10-16

### 🎉 Initial Public Release

First public release of STING-CE (Secure Trusted Intelligence and Networking Guardian - Community Edition).

### ✨ Added

#### Core Platform
- **Web-based Setup Wizard** - Interactive installation with guided configuration
- **One-line Bootstrap Installer** - Quick deployment via curl command
- **Universal Installer** - Automatic platform detection (macOS, WSL, Debian/Ubuntu)
- **Docker-based Architecture** - Complete microservices deployment
- **Management Scripts** - Comprehensive service management via `manage_sting.sh`
- **Health Checks** - Automatic validation of all services

#### Authentication & Security
- **Passwordless Authentication** - WebAuthn/Passkeys and Magic Links via Ory Kratos
- **Multi-Factor Authentication** - TOTP, recovery codes, and biometric options
- **Session Management** - AAL2 (Authentication Assurance Level 2) support
- **Email Verification** - Built-in email validation flows
- **HashiCorp Vault Integration** - Secure secrets management
- **PII Protection** - Automatic detection and serialization of sensitive data
- **Audit Logging** - Comprehensive security event tracking
- **Zero-Trust Architecture** - Service isolation and authentication

#### AI & Knowledge Management
- **Bee AI Assistant** (B. Sting) - Context-aware chatbot with conversation management
- **Honey Jar System** - Semantic knowledge base management with vector search
- **ChromaDB Integration** - Vector embeddings for semantic search
- **Ollama Support** - Local LLM deployment (phi3:mini, deepseek-r1)
- **Multi-LLM Support** - Compatible with OpenAI, LM Studio, vLLM
- **Document Processing** - Support for PDF, DOCX, HTML, JSON, Markdown, TXT
- **Background Processing** - Automatic document chunking and embedding generation
- **Knowledge Search** - Semantic similarity search across knowledge bases

#### User Interface
- **Modern Glass Morphism Theme** - STING V2 design with floating elements
- **Responsive Design** - Optimized for desktop, tablet, and mobile
- **Multiple Themes** - Customizable themes (modern glass, retro terminal, etc.)
- **Dark Mode Support** - Built-in light and dark theme support
- **Accessibility** - WCAG-compliant design with keyboard navigation
- **Real-time Chat Interface** - WebSocket-based communication with Bee

#### Infrastructure
- **PostgreSQL Database** - Separate databases for app, Kratos, and messaging
- **Redis Cache** - Session storage and caching
- **Mailpit** - Development email testing
- **Grafana Observability** - Optional monitoring with Loki and Promtail
- **Nginx Reverse Proxy** - HTTPS termination and routing

#### Documentation
- **Comprehensive README** - Installation, features, and quick start guide
- **Security Policy** (SECURITY.md) - Vulnerability reporting and security guidelines
- **Contributing Guidelines** (CONTRIBUTING.md) - How to contribute to the project
- **Credits** (CREDITS.md) - Acknowledgment of open-source dependencies
- **Developer Guide** (docs/CLAUDE.md) - Complete technical reference
- **API Documentation** - REST API reference in docs/api/
- **Architecture Docs** - System and technical architecture guides

### 🔧 Technical Details

#### Platform Support
- **Linux**: Ubuntu 20.04+, Debian 11+
- **macOS**: Native Ollama support with Metal acceleration
- **WSL2**: Full Windows Subsystem for Linux support

#### Requirements
- **RAM**: 8GB minimum (16GB recommended)
- **CPU**: 4 cores minimum
- **Disk**: 50GB free space
- **Docker**: Installed automatically if not present

#### Default Ports
- Frontend: `https://localhost:8443`
- API: `https://localhost:5050`
- Mailpit (dev): `http://localhost:8025`
- Ollama: `http://localhost:11434`
- Vault UI: `http://localhost:8200`

### 📦 Dependencies

See [CREDITS.md](CREDITS.md) for complete list of open-source dependencies.

**Major Dependencies:**
- Ory Kratos v1.3.0 - Authentication
- HashiCorp Vault - Secrets management
- ChromaDB v0.5.20 - Vector database
- Ollama - LLM deployment
- PostgreSQL - Relational database
- Redis - Cache and sessions
- React 18 - Frontend framework
- Flask - Backend API
- FastAPI - Knowledge service

### 🚧 Known Limitations

- Some features are under active development and may require additional configuration
- Not all advanced features are production-ready
- Enterprise features are not included in Community Edition
- Some UI themes may need refinement
- Documentation is being continuously improved

### 🙏 Acknowledgments

Built with ❤️ by [AlphaBytez](https://github.com/AlphaBytez) using incredible open-source projects from the community.

Special thanks to:
- Ory community for authentication patterns
- ChromaDB team for vector database innovation
- Ollama project for accessible LLM deployment
- All open-source contributors

### 📞 Contact

- **Security Issues**: security@alphabytez.dev
- **General Contact**: olliec@alphabytez.dev
- **GitHub Issues**: https://github.com/AlphaBytez/STING-CE/issues

---

*Bee Smart. Bee Secure.*

## Versioning Scheme

STING-CE follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backwards-compatible)
- **PATCH** version: Bug fixes (backwards-compatible)
- **-ce** suffix: Community Edition identifier

Example: `1.2.3-ce`
- `1` = Major version
- `2` = Minor version
- `3` = Patch version
- `-ce` = Community Edition

## Release Types

- **Stable**: Recommended for production use (e.g., `1.0.0-ce`)
- **Beta**: Feature complete but may have bugs (e.g., `1.0.0-beta.1`)
- **Alpha**: Early testing, expect issues (e.g., `1.0.0-alpha.1`)
- **RC**: Release candidate, final testing (e.g., `1.0.0-rc.1`)
