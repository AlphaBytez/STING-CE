# STING Platform Architecture

## System Overview

STING (Secure Trusted Intelligence and Networking Guardian) is a microservices-based platform designed for enterprise-grade AI deployment with advanced knowledge management capabilities.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                           Frontend Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  React 18 + Material-UI + Tailwind CSS (Port 8443/3010)      │
│  ├── Dashboard & Analytics                                      │
│  ├── Chat Interface ("Bee" Assistant)                          │
│  ├── Honey Jar Management                                       │
│  ├── Teams Management                                           │
│  └── Knowledge Marketplace                                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTPS/WSS
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  Flask/Python API Server (Port 5050)                          │
│  ├── Authentication & Authorization                             │
│  ├── Chat API & Message Routing                                │
│  ├── Knowledge Management API                                   │
│  └── System Health & Monitoring                                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Auth Layer    │ │  Knowledge      │ │   AI/LLM        │
│   (Port 4433/4) │ │  Services       │ │   Services      │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ Ory Kratos      │ │ Knowledge API   │ │ LLM Gateway     │
│ ├── Identity    │ │ (Port 8090)     │ │ (Port 8086)     │
│ ├── Sessions    │ │ ├── Doc Proc.   │ │ ├── Phi-3       │
│ ├── WebAuthn    │ │ ├── Embeddings  │ │ ├── DeepSeek    │
│ └── OIDC        │ │ └── Search      │ │ ├── TinyLlama   │
└─────────────────┘ │                 │ │ └── Dynamic     │
                    │ Chroma Vector   │ │     Loading     │
                    │ DB (Port 8000)  │ └─────────────────┘
                    │ ├── Collections │
                    │ ├── Embeddings  │          │
                    │ └── Similarity  │          │
                    └─────────────────┘          │
                                                 │
┌─────────────────────────────────────────────────────────────────┐
│                   Beeacon Observability Stack                   │
├─────────────────────────────────────────────────────────────────┤
│  Grafana (Port 3000)         Loki (Port 3100)                 │
│  ├── Dashboards              ├── Log Aggregation               │
│  ├── Monitoring              ├── 7-day Retention               │
│  └── Alerts                  └── Query Interface               │
│                                                                 │
│  Promtail (Port 9080)        Log Forwarder                    │
│  ├── Log Collection          ├── Container Logs               │
│  ├── PII Sanitization        ├── Cross-platform Support       │
│  └── Vault Integration       └── Real-time Streaming          │
└─────────────────────────────────────────────────────────────────┘
                                                 │
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL (Port 5433)          Redis (Port 6379)             │
│  ├── User Management             ├── Session Storage            │
│  ├── Conversation History        ├── Cache Management          │
│  ├── Knowledge Metadata          └── Message Queuing           │
│  └── System Configuration                                       │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  HashiCorp Vault (Port 8200)     Docker Compose              │
│  ├── Secrets Management          ├── Service Orchestration     │
│  ├── API Keys & Tokens           ├── Health Monitoring         │
│  ├── Database Credentials        ├── Auto-restart Policies     │
│  └── Encryption Keys             └── Volume Management         │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Frontend Layer

**Technology Stack:**
- React 18 with functional components and hooks
- Material-UI for consistent design system
- Tailwind CSS for utility-first styling
- HTTPS-enabled development with self-signed certificates

**Key Features:**
- Real-time chat interface with streaming responses
- Knowledge management dashboard with search and filtering
- Teams management with bee-themed role hierarchy
- Marketplace for knowledge base distribution
- Responsive design for desktop and mobile

### 2. API Gateway

**Flask Application Structure:**
```
app/
├── api/
│   ├── auth/          # Authentication endpoints
│   ├── chat/          # Chatbot interaction
│   ├── knowledge/     # Knowledge management
│   └── health/        # System health checks
├── models/            # Database models
├── services/          # Business logic layer
└── utils/             # Shared utilities
```

**Core Responsibilities:**
- Request routing and validation
- Authentication and authorization
- Rate limiting and throttling
- API documentation (OpenAPI/Swagger)
- Error handling and logging

### 3. Authentication Layer (Ory Kratos)

**Authentication Methods:**
- Email/password with secure hashing
- WebAuthn for passwordless authentication
- Session management with secure cookies
- Multi-factor authentication support

**Security Features:**
- Account verification and recovery
- Password policies and strength validation
- Session hijacking protection
- CSRF protection

### 4. AI/LLM Services

**Model Management:**
```yaml
Model Lifecycle:
├── Dynamic Loading: Models loaded on-demand
├── Memory Management: Intelligent eviction policies
├── Priority System: Business-critical models stay loaded
└── Health Monitoring: Automatic restart on failures
```

**Supported Models:**
- **Phi-3 Medium (14B)**: Enterprise primary model
- **DeepSeek-1.5B**: Reasoning and code generation
- **TinyLlama (1.1B)**: Fast responses for simple queries
- **Extensible**: Plugin architecture for new models

**Hardware Acceleration:**
- Metal Performance Shaders (macOS)
- CUDA support (NVIDIA GPUs)
- CPU optimization with multi-threading

### 5. Knowledge Services

**Honey Jar System Architecture:**
```
Knowledge Flow:
Document → Processing → Embeddings → Vector Store → Search API
    ↓           ↓           ↓            ↓           ↓
  PDF,DOCX   Text Ext.  Sentence     Chroma DB   Semantic
   MD,TXT    Chunking   Transform.   Collections  Search
```

**Processing Pipeline:**
1. **Document Ingestion**: Multi-format support with validation
2. **Text Extraction**: Content parsing with metadata preservation
3. **Chunking Strategy**: Intelligent text segmentation
4. **Embedding Generation**: Sentence transformers for semantic vectors
5. **Storage**: Chroma DB with collection management
6. **Retrieval**: Similarity search with ranking

### 6. Beeacon Observability Stack

**Real-time Monitoring Architecture:**
```
Log Sources → Log Forwarder → Promtail → Pollen Filter → Loki → Grafana
     ↓             ↓           ↓           ↓         ↓       ↓
Container     Stream to    Collect &    PII        Store &  Dashboards
  Logs         Files       Process    Sanitize     Query    & Alerts
```

**Key Features:**
1. **Cross-Platform Log Collection**: Works on macOS Docker Desktop and Linux
2. **PII Sanitization Pipeline**: Automated detection and redaction of sensitive data
3. **Vault Integration**: Secure handling of secrets and credentials in logs
4. **Real-time Dashboards**: Live system health and performance monitoring
5. **7-day Log Retention**: Configurable retention with automatic cleanup
6. **Health Check Dependencies**: Ensures proper service startup order

**Components:**
- **Grafana (Port 3000)**: Interactive dashboards and alerting
- **Loki (Port 3100)**: Centralized log aggregation and storage
- **Promtail (Port 9080)**: Log collection agent with health checks
- **Log Forwarder**: Container log streaming service for cross-platform support
- **Pollen Filter**: PII sanitization and Vault-aware log processing

### 7. Data Layer

**PostgreSQL Schema:**
```sql
-- Core Tables
users              # User accounts and profiles
sessions           # Authentication sessions  
conversations      # Chat history and context
knowledge_bases    # Honey Jar metadata
documents          # Document references
embeddings         # Vector embedding metadata
marketplace        # Knowledge marketplace data
```

**Redis Usage:**
- Session storage and management
- Response caching for frequent queries
- Message queuing for async processing
- Rate limiting counters

### 7. Infrastructure

**Docker Compose Services:**
- **Health Checks**: Comprehensive monitoring for all services
- **Volume Management**: Persistent storage for data and models
- **Network Security**: Isolated networks with controlled access
- **Auto-restart**: Failure recovery with exponential backoff

**HashiCorp Vault Integration:**
- **Secret Management**: API keys, tokens, and credentials
- **Encryption**: Data at rest and in transit
- **Audit Logging**: Complete access tracking
- **Rotation**: Automated credential rotation

**Observability Infrastructure:**
- **Log Volumes**: Persistent storage for Loki, Grafana, and container logs
- **Cross-Platform Compatibility**: Unified approach for macOS and Linux environments
- **Centralized Configuration**: Utils container approach eliminates local config generation
- **Health Check Dependencies**: Ensures proper service startup order and health monitoring
- **PII Protection**: Automated sanitization of sensitive data in all log streams

## Security Architecture

### Multi-Layer Security Model

```
┌─────────────────────────────────────────┐
│           Application Security           │
├─────────────────────────────────────────┤
│ • Input validation & sanitization      │
│ • Output encoding & escaping           │
│ • CSRF protection                       │
│ • XSS prevention                        │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│           Transport Security             │
├─────────────────────────────────────────┤
│ • TLS 1.3 encryption                   │
│ • Certificate pinning                   │
│ • HSTS headers                          │
│ • Secure WebSocket connections          │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│           Data Security                  │
├─────────────────────────────────────────┤
│ • Encryption at rest (Vault)           │
│ • Database column encryption            │
│ • Secure key management                 │
│ • Data anonymization                    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         Infrastructure Security          │
├─────────────────────────────────────────┤
│ • Container isolation                   │
│ • Network segmentation                  │
│ • Secrets management                    │
│ • Audit logging                         │
└─────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling Strategy

**Stateless Services:**
- API Gateway: Multiple instances behind load balancer
- LLM Services: Model distribution across GPU nodes
- Knowledge Services: Distributed processing workers

**Stateful Services:**
- PostgreSQL: Read replicas and sharding
- Redis: Cluster mode with automatic failover
- Chroma DB: Distributed collections

**Resource Optimization:**
- Model sharing across instances
- Intelligent caching strategies
- Connection pooling
- Async processing queues

## Performance Metrics

### Response Time Targets

| Service | Target | Acceptable | Maximum |
|---------|--------|------------|---------|
| API Gateway | <100ms | <300ms | <1s |
| Chat Response | <2s | <5s | <10s |
| Knowledge Search | <500ms | <1s | <3s |
| Model Loading | <5s | <15s | <30s |

### Resource Utilization

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Frontend | 5-10% | 100MB | 50MB |
| API Gateway | 10-20% | 512MB | 1GB |
| LLM Service | 20-80% | 8-16GB | 500MB |
| Database | 5-15% | 1-2GB | 10-100GB |

## Monitoring and Observability

### Health Check Strategy

```yaml
Service Monitoring:
├── Application Health: Custom endpoints for business logic
├── Infrastructure Health: Container and resource monitoring  
├── Dependency Health: External service availability
└── End-to-End Health: Full user journey validation
```

### Logging Architecture

```
Application Logs → Structured JSON → Log Aggregation → Alerting
     ↓                   ↓              ↓             ↓
  Python          Centralized       ELK Stack    PagerDuty
  Logging         Collection        (Optional)   (Production)
```

### Key Metrics

- **Request Rate**: Requests per second by endpoint
- **Error Rate**: 4xx/5xx responses and application errors
- **Response Time**: P50, P95, P99 latency percentiles
- **Resource Usage**: CPU, memory, disk, and network utilization
- **Model Performance**: Inference time and throughput
- **User Engagement**: Session duration and feature usage

This architecture provides a solid foundation for enterprise deployment while maintaining the flexibility to scale and adapt to changing requirements.