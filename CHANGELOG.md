# Changelog

All notable changes to STING-CE (Community Edition) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **GitHub Issues**: https://github.com/AlphaBytez/STING-CE-Public/issues

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
