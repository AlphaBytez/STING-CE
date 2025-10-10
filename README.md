# STING CE Developer Preview

This is a clean, focused developer preview of the STING Community Edition platform with all production code and the original installer/management scripts.

## Overview

STING (Secure Technological Intelligence and Networking Guardian Assistant) is a comprehensive enterprise AI platform that provides secure, private access to large language models with advanced knowledge management, vector search, and AI-as-a-Service capabilities.

This developer preview provides the complete STING platform with:
- ✅ **Full production code** - All services included
- ✅ **Original installer** - Same proven installation process
- ✅ **Complete documentation** - Comprehensive guides and API docs
- ✅ **Clean structure** - Well-organized for development

## Core Features

- 🔒 **Fully Passwordless Authentication** with WebAuthn/FIDO2 passkeys and magic links
- 🤖 **Advanced AI Integration** with Ollama support, Microsoft Phi-3, DeepSeek R1, and Apple Silicon optimization
- 🧠 **Knowledge Management** with vector search, semantic retrieval, and Honey Jar document stores
- 🍯 **Honey Reserve** - Encrypted storage system with 1GB quota per user and lifecycle management
- 🔑 **Nectar Bots** - AI-as-a-Service with API key management and usage analytics
- 🛡️ **PII Compliance** with HIPAA, GDPR, CCPA pattern detection and content filtering
- 📊 **Beeacon Observability** - Complete monitoring with Grafana, Loki, and Promtail

## Architecture

### Services
- **Frontend** (React 18 + Material-UI + Tailwind) - Modern responsive interface
- **Backend API** (Flask/Python) - Core business logic and API orchestration
- **Authentication** (Ory Kratos) - Passwordless identity and session management
- **Knowledge Service** (Python + Chroma) - Vector search and document processing
- **Chatbot Service** (Python) - "Bee" AI assistant with context awareness
- **External AI Service** (Python) - Ollama integration and model management
- **Messaging Service** (Python) - Encrypted messaging with Redis queuing

### Infrastructure & Data
- **PostgreSQL** - Three separated databases (kratos, sting_app, sting_messaging)
- **Redis** - Session management and caching
- **Chroma Vector Database** - Semantic search and embeddings
- **HashiCorp Vault** - Secrets and encryption key management
- **Observability Stack** - Grafana, Loki, Promtail for monitoring and logging

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Node.js 16+
- 16+ GB RAM (32+ GB recommended for optimal AI performance)

### Installation

```bash
# Install STING
./install_sting.sh install

# Or with debug mode
./install_sting.sh install --debug
```

### Service Management

```bash
# Start all services
./manage_sting.sh start

# Stop services
./manage_sting.sh stop

# Restart specific service
./manage_sting.sh restart <service>

# View logs
./manage_sting.sh logs <service>

# Update service
./manage_sting.sh update <service>

# Check status
./manage_sting.sh status
```

## Quick Start

1. **Install STING:**
   ```bash
   ./install_sting.sh install
   ```

2. **Access the platform:**
   - Frontend: https://localhost:8443
   - Backend API: https://localhost:5050

3. **Create your first account** using passwordless authentication

4. **Explore the features:**
   - Upload documents to Honey Jars
   - Chat with Bee AI assistant
   - Create Nectar Bot API keys
   - Store encrypted files in Honey Reserve

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Documentation Index](docs/INDEX.md)** - Complete guide to all documentation
- **[Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes
- **[Developer Preview Guide](docs/guides/DEVELOPER_PREVIEW_GUIDE.md)** - Development workflow
- **[API Overview](docs/api/API_OVERVIEW.md)** - Complete API reference
- **[Features Guide](docs/features/FEATURES.md)** - Detailed feature descriptions

### Key Documentation

#### Getting Started
- [Quick Start](QUICK_START.md)
- [Installation Guide](docs/guides/DEVELOPER_PREVIEW_GUIDE.md)
- [Passkey Setup](docs/guides/PASSKEY_QUICKSTART.md)
- [Ollama Configuration](docs/guides/OLLAMA_SETUP_GUIDE.md)

#### User Guides
- [Honey Jar Knowledge Bases](docs/guides/HONEY_JAR_USER_GUIDE.md)
- [Bee AI Assistant](docs/guides/bee-support-guide.md)
- [Honey Reserve Storage](docs/guides/honey-reserve-management.md)

#### API Documentation
- [API Overview](docs/api/API_OVERVIEW.md)
- [Honey Jar Bulk API](docs/api/HONEY_JAR_BULK_API.md)
- [PII Detection API](docs/api/PII_DETECTION_API.md)

#### Technical Documentation
- [Passwordless Authentication](docs/features/PASSWORDLESS_AUTHENTICATION.md)
- [PII Detection System](docs/features/PII_DETECTION_SYSTEM.md)
- [Vector Search](docs/features/CHROMADB_VECTOR_SEARCH_ENHANCEMENT.md)
- [Observability](docs/features/BEEACON_LOG_MONITORING.md)

## Development Guidelines

This developer preview maintains the production codebase with:
1. Clear separation of concerns
2. Well-documented API endpoints
3. Secure authentication patterns
4. Scalable microservices architecture
5. Comprehensive observability

See [CONTRIBUTING.md](CONTRIBUTING.md) for development standards and practices.

## Project Structure

```
sting-ce-dev-preview/
├── app/                      # Backend API (Flask)
├── frontend/                 # React frontend
├── knowledge_service/        # Vector search & documents
├── chatbot/                  # Bee AI assistant
├── external_ai_service/      # Ollama integration
├── messaging_service/        # Encrypted messaging
├── kratos/                   # Authentication config
├── vault/                    # Secrets management
├── observability/            # Grafana, Loki, Promtail
├── conf/                     # Configuration files
├── lib/                      # Management library
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── docker-compose.yml        # Service orchestration
├── manage_sting.sh          # Management CLI
├── install_sting.sh         # Installer
└── README.md                # This file
```

## Key Services

- **Frontend**: React app on port 8443
- **Backend API**: Flask on port 5050
- **Kratos**: Authentication on ports 4433/4434
- **Knowledge**: Vector search on port 8090
- **Chatbot**: Bee assistant on port 8888
- **External AI**: Ollama interface on port 8091
- **Messaging**: Messaging service on port 8889
- **PostgreSQL**: Database on port 5433
- **Redis**: Cache on port 6379
- **Chroma**: Vector DB on port 8000

## Contributing

We welcome contributions! Please follow our development workflow:

1. **Fork** the repository and create a feature branch
2. **Read** the documentation in docs/ directory
3. **Follow** code conventions and security best practices
4. **Test** your changes with the provided test suite
5. **Submit** a pull request with detailed description

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## What's Different in This Preview?

This developer preview provides:

✅ **Complete Codebase** - All production services included
✅ **Original Installer** - Same proven installation process
✅ **Comprehensive Docs** - 18+ documentation files
✅ **Clean Organization** - Clear directory structure
✅ **Development Ready** - Easy to modify and extend

**Not a Simplified Version** - This is the full STING platform, ready for development and deployment.

## Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Open an issue on GitHub
- **Community**: Join our Discord/Slack

---

Built with ❤️ for secure, private AI applications
