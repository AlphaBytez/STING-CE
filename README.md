# STING-CE (Community Edition)

> **Secure Trusted Intelligence and Networking Guardian**
>
> Developed by [AlphaBytez](https://github.com/alphabytez)
>
> *Bee Smart. Bee Secure.*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![AlphaBytez](https://img.shields.io/badge/by-AlphaBytez-blue.svg)](https://github.com/alphabytez)

Self-hosted platform for secure, private LLM deployment with complete data sovereignty. Features innovative "Honey Jar" knowledge management, enterprise-grade authentication, and the Bee AI assistant. Built for developers who value privacy and control over their AI infrastructure.

## ✨ Features

### 🔐 Modern Authentication
- **Passwordless Authentication** - Magic links and WebAuthn/Passkeys
- **Multi-Factor Authentication** - TOTP, SMS, and biometric options
- **Email Verification** - Built-in with automatic validation
- **Session Management** - AAL2 (Two-factor) session controls
- **OAuth2/OIDC** - Standard protocol support via Ory Kratos

### 🍯 Honey Jar Knowledge Management
- **Semantic Search** - Vector-based knowledge retrieval with ChromaDB
- **Multi-Format Support** - PDF, DOCX, HTML, JSON, Markdown, TXT
- **Private & Secure** - Your data stays on your infrastructure
- **Bee Integration** - AI assistant queries your knowledge bases for context
- **Background Processing** - Automatic document chunking and embedding

### 🤖 AI-Powered Assistant (Bee)
- **Intelligent Chat Interface** - Natural language queries with Bee (B. Sting)
- **Knowledge Base Integration** - ChromaDB-powered context retrieval from Honey Jars
- **Multi-LLM Support** - Works with Ollama, OpenAI, LM Studio, vLLM
- **Contextual Responses** - Bee leverages your knowledge bases for accurate answers

### 🔒 Security & Privacy
- **Vault Integration** - HashiCorp Vault for secrets management
- **PII Protection** - Automatic serialization for sensitive data
- **Audit Logging** - Comprehensive security event tracking
- **Zero-Trust Architecture** - All services isolated and authenticated

### 🐳 Easy Deployment
- **Docker-Based** - One-command deployment
- **Web Setup Wizard** - Interactive first-run configuration
- **Automatic Validation** - Built-in health checks for all services
- **Hot Reload** - Development mode with live updates

## 🚀 Quick Start

### Prerequisites

- **OS**: Ubuntu 20.04+, Debian 11+, or similar Linux distribution
- **RAM**: 8GB minimum (16GB recommended)
- **CPU**: 4 cores minimum
- **Disk**: 50GB free space
- **Docker**: Installed automatically if not present

### Installation (Guided Setup)

The easiest way to install STING-CE is with the web-based setup wizard:

```bash
# Clone the repository
git clone https://github.com/AlphaBytez/STING-CE-Public.git
cd STING-CE-Public/STING

# Run the installer (includes web wizard)
./install_sting.sh
```

The installer will:
1. ✅ Check system requirements
2. ✅ Install Docker (if needed)
3. ✅ Launch the web setup wizard at `http://localhost:8335`
4. ✅ Guide you through configuration (domain, email, LLM settings)
5. ✅ Install and start all services
6. ✅ Validate email delivery
7. ✅ Create your admin account

**After installation:**
- **Frontend**: https://localhost:8443
- **API**: https://localhost:5050
- **Mailpit** (dev mode): http://localhost:8025

### Upgrading/Reinstalling

If you already have STING-CE installed and want to upgrade or reinstall:

```bash
cd STING-CE-Public/STING

# Reinstall (preserves your data and configuration)
./manage_sting.sh reinstall

# Fresh install (removes everything - use with caution!)
./manage_sting.sh reinstall --fresh
```

**Note:** Running `./install_sting.sh` on an existing installation will detect this and direct you to use the reinstall command instead.

### Installation (Command Line)

For headless servers or automated deployments:

```bash
# Clone the repository
git clone https://github.com/AlphaBytez/STING-CE-Public.git
cd STING-CE-Public/STING

# Create configuration from template
cp conf/config.yml.default conf/config.yml

# Edit configuration (set domain, email settings, etc.)
nano conf/config.yml

# Run installer in non-interactive mode
./install_sting.sh --non-interactive

# Start services
./manage_sting.sh start
```

## 📖 Documentation

Comprehensive documentation is available in the `STING/docs/` directory:

- **Installation**: [STING/docs/INSTALL.md](STING/docs/INSTALL.md)
- **Configuration**: [STING/docs/operations/](STING/docs/operations/)
- **API Reference**: [STING/docs/api/](STING/docs/api/)
- **Security**: [SECURITY.md](SECURITY.md)

## 🛠️ Management

### Service Management

```bash
cd STING

# Start all services
./manage_sting.sh start

# Stop all services
./manage_sting.sh stop

# Restart a specific service
./manage_sting.sh restart [service]

# View logs
./manage_sting.sh logs [service]

# Check service status
./manage_sting.sh status
```

## 🏗️ Architecture

STING-CE uses a microservices architecture:

- **Frontend**: React-based UI with Vite
- **API**: Flask REST API with PII protection
- **Kratos**: Ory Kratos for authentication flows
- **Vault**: HashiCorp Vault for secrets
- **Bee**: AI assistant chatbot (B. Sting)
- **Knowledge**: ChromaDB vector database for Honey Jars
- **Database**: PostgreSQL for application data
- **Redis**: Caching and session storage
- **Mailpit**: Development email catcher

## 🐛 Troubleshooting

### Common Issues

**Email Delivery Not Working**
```bash
cd STING
python3 scripts/health/validate_mailpit.py
```

**Docker Permission Denied**
```bash
sudo usermod -aG docker $USER
# Logout and login again
```

**Port Already in Use**
```bash
# Find what's using the port
sudo lsof -i :8443

# Change port in config.yml or kill the process
```

**Services Not Starting**
```bash
cd STING

# Check logs
docker compose logs

# Check system resources
free -h
df -h

# Restart with cleanup
./manage_sting.sh restart
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔒 Security

Security is our top priority. Please see [SECURITY.md](SECURITY.md) for:
- Reporting vulnerabilities
- Security best practices
- Supported versions
- Disclosure policy

**DO NOT** create public issues for security vulnerabilities.

## 📜 License

STING-CE is released under the [Apache License 2.0](LICENSE).

```
Copyright 2024 AlphaBytez and the STING-CE Community

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## 🏢 About AlphaBytez

STING-CE is developed and maintained by **AlphaBytez**, a software development company focused on security, authentication, and AI-powered solutions.

> *Bee Smart. Bee Secure.*

- **Contact**: [olliec@alphabytez.dev](mailto:olliec@alphabytez.dev)
- **Security**: [security@alphabytez.dev](mailto:security@alphabytez.dev)
- **GitHub**: [@AlphaBytez](https://github.com/AlphaBytez)

## 🙏 Acknowledgments

STING-CE is built on the shoulders of giants:

- **Ory Kratos** - Modern authentication flows
- **HashiCorp Vault** - Secrets management
- **ChromaDB** - Vector database for AI
- **Ollama** - Local LLM deployment
- **Docker** - Containerization

See [CREDITS.md](CREDITS.md) for complete list of third-party libraries.

## 📊 Project Status

- **Version**: 1.0.0-ce
- **Status**: Active Development
- **Platform**: Linux (Ubuntu/Debian)
- **License**: Apache 2.0
- **Language**: Python 3.11+, JavaScript (React)

---

<div align="center">

Made with ❤️ by **[AlphaBytez](https://github.com/alphabytez)** and the STING-CE Community

*Bee Smart. Bee Secure.*

**Get Started**: `cd STING && ./install_sting.sh` 🚀

</div>
