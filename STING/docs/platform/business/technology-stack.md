# STING-CE Technology Stack

## Overview

STING-CE is built on proven, enterprise-grade open-source technologies. This document provides transparency into our technology choices, helping you understand the foundation of our platform.

## Core Technologies

### 🐳 **Containerization & Orchestration**

#### Docker
- **Purpose**: Container runtime for all services
- **Version**: 20.10+
- **Website**: https://www.docker.com/
- **Why we chose it**: Industry standard, excellent isolation, reproducible deployments

#### Docker Compose
- **Purpose**: Multi-container orchestration
- **Version**: v2.0+
- **Website**: https://docs.docker.com/compose/
- **Why we chose it**: Simple yet powerful for development and small deployments

### 🗄️ **Databases & Storage**

#### PostgreSQL
- **Purpose**: Primary relational database
- **Version**: 16
- **Website**: https://www.postgresql.org/
- **License**: PostgreSQL License (BSD-style)
- **Why we chose it**: Rock-solid reliability, excellent JSON support, strong community

#### Redis
- **Purpose**: Caching, session storage, message queue
- **Version**: 7-alpine
- **Website**: https://redis.io/
- **License**: BSD 3-Clause
- **Why we chose it**: Lightning fast, versatile, battle-tested

#### ChromaDB
- **Purpose**: Vector database for semantic search
- **Version**: Latest
- **Website**: https://www.trychroma.com/
- **License**: Apache 2.0
- **Why we chose it**: Excellent for AI embeddings, easy integration

### 🔐 **Security & Authentication**

#### Ory Kratos
- **Purpose**: Identity and user management
- **Version**: Latest stable
- **Website**: https://www.ory.sh/kratos/
- **License**: Apache 2.0
- **Why we chose it**: Modern, secure, supports WebAuthn/passkeys

#### HashiCorp Vault
- **Purpose**: Secrets management and encryption
- **Version**: Latest
- **Website**: https://www.vaultproject.io/
- **License**: Mozilla Public License 2.0
- **Why we chose it**: Industry leader in secrets management

### 🤖 **AI/ML Frameworks**

#### Hugging Face Transformers
- **Purpose**: LLM model loading and inference
- **Website**: https://huggingface.co/transformers/
- **License**: Apache 2.0
- **Why we chose it**: Vast model ecosystem, excellent performance

#### LangChain
- **Purpose**: LLM application framework
- **Website**: https://www.langchain.com/
- **License**: MIT
- **Why we chose it**: Flexible, well-documented, active community

#### Microsoft Presidio
- **Purpose**: PII detection and anonymization
- **Website**: https://microsoft.github.io/presidio/
- **License**: MIT
- **Why we chose it**: Comprehensive PII detection, customizable

### 🌐 **Web Technologies**

#### Frontend

##### React
- **Purpose**: User interface framework
- **Version**: 18+
- **Website**: https://react.dev/
- **License**: MIT
- **Why we chose it**: Component-based, huge ecosystem, excellent performance

##### Material-UI (MUI)
- **Purpose**: UI component library
- **Version**: 5+
- **Website**: https://mui.com/
- **License**: MIT
- **Why we chose it**: Beautiful components, accessibility built-in

##### Tailwind CSS
- **Purpose**: Utility-first CSS framework
- **Website**: https://tailwindcss.com/
- **License**: MIT
- **Why we chose it**: Rapid development, consistent styling

#### Backend

##### Flask
- **Purpose**: Python web framework
- **Version**: 3.0+
- **Website**: https://flask.palletsprojects.com/
- **License**: BSD 3-Clause
- **Why we chose it**: Lightweight, flexible, extensive ecosystem

##### FastAPI
- **Purpose**: Modern API framework (LLM services)
- **Website**: https://fastapi.tiangolo.com/
- **License**: MIT
- **Why we chose it**: High performance, automatic API documentation

##### Nginx
- **Purpose**: Reverse proxy and load balancer
- **Website**: https://nginx.org/
- **License**: BSD 2-Clause
- **Why we chose it**: High performance, proven reliability

### 📨 **Messaging & Queues**

#### Bull Queue
- **Purpose**: Job queue management
- **Website**: https://github.com/OptimalBits/bull
- **License**: MIT
- **Why we chose it**: Redis-based, reliable, good monitoring

#### Socket.IO
- **Purpose**: Real-time communication
- **Website**: https://socket.io/
- **License**: MIT
- **Why we chose it**: WebSocket with fallbacks, battle-tested

### 📊 **Monitoring & Logging**

#### Prometheus
- **Purpose**: Metrics collection
- **Website**: https://prometheus.io/
- **License**: Apache 2.0
- **Why we chose it**: Industry standard, powerful querying

#### Grafana
- **Purpose**: Metrics visualization
- **Website**: https://grafana.com/
- **License**: AGPL v3
- **Why we chose it**: Beautiful dashboards, extensive integrations

### 🧪 **Development Tools**

#### Python
- **Version**: 3.9+
- **Website**: https://www.python.org/
- **License**: PSF License
- **Used for**: Backend services, AI/ML processing

#### Node.js
- **Version**: 18+ LTS
- **Website**: https://nodejs.org/
- **License**: MIT
- **Used for**: Frontend build, some microservices

#### TypeScript
- **Purpose**: Type-safe JavaScript
- **Website**: https://www.typescriptlang.org/
- **License**: Apache 2.0
- **Used for**: Frontend development

## LLM Models Supported

### Open Models (via Hugging Face)

#### Meta Llama 3
- **Model**: meta-llama/Llama-3.1-8B
- **Website**: https://ai.meta.com/llama/
- **License**: Llama 3 Community License
- **Use case**: General conversation and analysis

#### Microsoft Phi-3
- **Model**: microsoft/Phi-3-medium-128k-instruct
- **Website**: https://azure.microsoft.com/en-us/products/phi-3
- **License**: MIT
- **Use case**: Efficient inference, long context

#### Zephyr
- **Model**: HuggingFaceH4/zephyr-7b-beta
- **Website**: https://huggingface.co/HuggingFaceH4/zephyr-7b-beta
- **License**: Apache 2.0
- **Use case**: Instruction following, technical tasks

### External APIs (Optional)

- **OpenAI GPT-4**: Via API key
- **Anthropic Claude**: Via API key
- **Google Gemini**: Via API key

## Infrastructure Requirements

### Minimum Requirements (CE)
```yaml
CPU: 4 cores
RAM: 16GB
Storage: 100GB SSD
OS: Linux (Ubuntu 20.04+) or macOS
Docker: 20.10+
```

### Recommended for Production
```yaml
CPU: 8+ cores
RAM: 32GB+
Storage: 500GB+ SSD
GPU: Optional (NVIDIA for acceleration)
Network: 100Mbps+
```

## Security Considerations

### Data Protection
- All data encrypted at rest (AES-256)
- TLS 1.3 for all communications
- No telemetry or phone-home features
- Your data never leaves your infrastructure

### Compliance
- GDPR compliant architecture
- HIPAA-ready deployment options
- SOC 2 design principles
- Zero-trust security model

## License Information

### STING-CE License
- **Type**: MIT License
- **Commercial use**: Yes
- **Modification**: Yes
- **Distribution**: Yes
- **Private use**: Yes

### Key Python Libraries

#### tiktoken
- **Purpose**: Accurate token counting for LLM context management
- **Version**: 0.5.2+
- **Website**: https://github.com/openai/tiktoken
- **License**: MIT
- **Why we chose it**: Fast BPE tokenization for GPT, Llama, and other model families

#### SQLAlchemy
- **Purpose**: SQL toolkit and ORM
- **Version**: 2.0+
- **Website**: https://www.sqlalchemy.org/
- **License**: MIT
- **Used for**: Database models and operations

#### asyncpg
- **Purpose**: Fast PostgreSQL client for asyncio
- **Version**: 0.29.0+
- **Website**: https://github.com/MagicStack/asyncpg
- **License**: Apache 2.0
- **Used for**: High-performance async database operations

#### Pydantic
- **Purpose**: Data validation using Python type annotations
- **Version**: 2.0+
- **Website**: https://pydantic-docs.helpmanual.io/
- **License**: MIT
- **Used for**: API request/response validation

### Third-Party Licenses

#### License Overview
All dependencies are carefully selected for license compatibility:
- **Permissive Licenses**: MIT, Apache 2.0, BSD (majority of dependencies)
- **Weak Copyleft**: LGPL (psycopg2 - used as dynamic library)
- **File-level Copyleft**: MPL 2.0 (HashiCorp Vault - used as separate service)
- **No GPL in Core**: Avoided to maintain maximum flexibility

#### License Documentation
- **Full License List**: See [LICENSE-THIRD-PARTY.md](/LICENSE-THIRD-PARTY.md)
- **Credits & Acknowledgments**: See [CREDITS.md](/CREDITS.md)
- **STING License**: See [LICENSE](/LICENSE)

#### Automated License Management
```bash
# Run license audit
python scripts/audit-licenses.py

# Export license report
python scripts/audit-licenses.py --export licenses.json

# Check compatibility
python scripts/audit-licenses.py --check-compatibility
```

#### Key License Highlights

##### Python Dependencies
- **tiktoken** (MIT) - Fast BPE tokenizer for accurate token counting
- **LangChain** (MIT) - LLM application framework
- **FastAPI** (MIT) - Modern web framework
- **SQLAlchemy** (MIT) - SQL toolkit and ORM
- **pandas** (BSD-3) - Data analysis library
- **cryptography** (Apache 2.0/BSD) - Cryptographic primitives

##### JavaScript Dependencies
- **React** (MIT) - UI framework
- **Ant Design** (MIT) - Component library
- **Material-UI** (MIT) - Material Design components
- **Tailwind CSS** (MIT) - Utility-first CSS

##### Infrastructure
- **PostgreSQL** (PostgreSQL License) - Similar to BSD/MIT
- **Redis** (BSD-3) - In-memory data store
- **Nginx** (BSD-2) - Web server
- **Docker** (Apache 2.0) - Containerization

#### Compliance Notes
1. **Commercial Use**: All licenses allow commercial use
2. **Distribution**: Proper attribution required
3. **Modifications**: Allowed under all licenses
4. **Patent Grants**: Apache 2.0 includes patent protection

## Support & Community

### Getting Help
- **Documentation**: `/docs` directory
- **GitHub Issues**: https://github.com/your-org/STING-CE
- **Community Forum**: Coming soon
- **Email**: support@stingassistant.com

### Contributing
We welcome contributions! See CONTRIBUTING.md for guidelines.

## Why Open Source?

We believe in transparency and community collaboration. By building on open-source technologies:
- You can inspect every component
- No vendor lock-in
- Community-driven improvements
- Lower total cost of ownership

## Comparison with Alternatives

| Feature | STING-CE | OpenAI Enterprise | Google Vertex AI |
|---------|----------|-------------------|------------------|
| On-premise deployment | ✅ | ❌ | ❌ |
| Data never leaves | ✅ | ❌ | ❌ |
| Open source | ✅ | ❌ | ❌ |
| Custom models | ✅ | Limited | ✅ |
| No usage limits | ✅ | ❌ | ❌ |
| One-time cost | ✅ | ❌ | ❌ |

## Future Stack Additions

We're evaluating these technologies for future releases:
- **Apache Kafka**: For enterprise-scale message processing
- **Kubernetes**: For container orchestration at scale
- **Apache Airflow**: For complex workflow orchestration
- **MinIO**: For S3-compatible object storage
- **Keycloak**: As an alternative identity provider

## Verification

You can verify our technology usage by:
1. Inspecting our `docker-compose.yml` files
2. Reviewing Dockerfiles in the repository
3. Checking `package.json` and `requirements.txt`
4. Running `docker compose ps` to see all services

---

*We believe in building on the shoulders of giants. Every technology in our stack is chosen for reliability, security, and community support.*

*Last Updated: January 2025*
*Version: 1.0*