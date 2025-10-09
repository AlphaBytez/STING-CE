# STING CE Developer Preview

This is a clean, focused developer preview of the STING Community Edition platform.

## Overview

STING (Secure Technological Intelligence and Networking Guardian Assistant) is a comprehensive enterprise AI platform that provides secure, private access to large language models with advanced knowledge management, vector search, and AI-as-a-Service capabilities.

This developer preview focuses on the core platform components that provide real value to developers building AI applications with security and privacy in mind.

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
- **Public Bee Service** (Python) - Nectar Bots AI-as-a-Service API
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

### Quick Installation
```bash
# Clone the repository
git clone https://github.com/your-organization/sting-ce-dev-preview.git
cd sting-ce-dev-preview

# Start services
./manage_sting_dev.sh start
```

### Service Management
```bash
# Service lifecycle
./manage_sting_dev.sh start              # Start all services
./manage_sting_dev.sh stop               # Stop all services
./manage_sting_dev.sh restart <service>  # Restart specific service
./manage_sting_dev.sh logs <service>     # View service logs
```

## Development Guidelines

This developer preview focuses on clean, maintainable code with:
1. Clear separation of concerns
2. Well-documented API endpoints
3. Secure authentication patterns
4. Scalable microservices architecture
5. Comprehensive observability

## Contributing

We welcome contributions! Please follow our development workflow:
1. **Fork** the repository and create a feature branch
2. **Read** the documentation in docs/ directory
3. **Follow** code conventions and security best practices
4. **Test** your changes with the provided test suite
5. **Submit** a pull request with detailed description

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
