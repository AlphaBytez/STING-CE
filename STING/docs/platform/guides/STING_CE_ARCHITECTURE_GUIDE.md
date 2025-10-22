# STING-CE Architecture & Installation Guide

## Overview

STING-CE (Community Edition) is the open-source version of STING Assistant - **Secure Trusted Intelligence and Networking Guardian Assistant**. This guide provides a comprehensive overview of the system architecture, installation process, and configuration management.

The system features **B. STING** (or "Bee"), a robotic bee assistant that provides secure information management, performance optimization suggestions, and bot-as-a-service capabilities.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Service Components](#service-components)
3. [Port Allocations](#port-allocations)
4. [Installation Process](#installation-process)
5. [Configuration Management](#configuration-management)
6. [Local LLM Integration](#local-llm-integration)
7. [Security Architecture](#security-architecture)
8. [Troubleshooting](#troubleshooting)

## System Architecture

STING-CE follows a microservices architecture with the following key principles:
- **Container-based deployment** using Docker Compose
- **Service isolation** for security and maintainability
- **Local LLM support** for privacy-conscious deployments
- **Modular authentication** with Ory Kratos
- **Secure secrets management** with HashiCorp Vault

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (React)                           │
│                         Port: 3010 (HTTP)                           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
┌────────────────────────────────┴────────────────────────────────────┐
│                         API Gateway (Flask)                          │
│                         Port: 5050 (HTTPS)                          │
└─────────┬──────────────┬──────────────┬──────────────┬─────────────┘
          │              │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌────┴────┐  ┌─────┴─────┐
    │   Kratos  │  │   Vault   │  │   LLM   │  │ Messaging │
    │  4433/34  │  │   8200    │  │Gateway  │  │  Service  │
    └───────────┘  └───────────┘  │  8086   │  └───────────┘
                                   └────┬────┘
                          ┌─────────────┼─────────────┐
                    ┌─────┴─────┐ ┌────┴────┐ ┌──────┴──────┐
                    │  LLaMA3   │ │  Phi-3  │ │   Zephyr    │
                    │  Service  │ │ Service │ │   Service   │
                    └───────────┘ └─────────┘ └─────────────┘
```

## Service Components

### Core Services

#### 1. **PostgreSQL Database** (`db`)
- **Purpose**: Primary data store for application data, user information, and Kratos identity management
- **Port**: 5433 (external), 5432 (internal)
- **Image**: postgres:16
- **Health Check**: pg_isready command
- **Initialization**: Custom SQL scripts in `/docker-entrypoint-initdb.d/`

#### 2. **HashiCorp Vault** (`vault`)
- **Purpose**: Secure secrets management and encryption key storage
- **Port**: 8200
- **Mode**: Development mode (for CE)
- **Features**: 
  - Dynamic secrets generation
  - Encryption as a service
  - Policy-based access control

#### 3. **Ory Kratos** (`kratos`)
- **Purpose**: Identity and user management system
- **Ports**: 
  - 4433 (Public API - HTTPS)
  - 4434 (Admin API - HTTPS)
- **Features**:
  - Password-based authentication
  - Passwordless/WebAuthn support
  - Account recovery flows
  - Email verification

#### 4. **Flask Application** (`app`)
- **Purpose**: Main API backend
- **Port**: 5050 (HTTPS)
- **Features**:
  - RESTful API endpoints
  - WebAuthn integration
  - Secure session management
  - Integration with all services

#### 5. **React Frontend** (`frontend`)
- **Purpose**: Web UI for STING-CE
- **Port**: 3010
- **Features**:
  - Modern React 18 application
  - Material-UI components
  - Kratos integration for auth
  - Bee chatbot interface

### LLM Services

#### 6. **LLM Gateway** (`llm-gateway`)
- **Purpose**: Unified interface for LLM services
- **Port**: 8086 (external), 8080 (internal)
- **Features**:
  - Load balancing across models
  - Request routing
  - Response caching
  - Rate limiting

#### 7. **LLaMA 3 Service** (`llama3-service`)
- **Model**: meta-llama/Llama-3.1-8B
- **Memory**: 8GB recommended
- **Purpose**: General-purpose conversation and analysis

#### 8. **Phi-3 Service** (`phi3-service`)
- **Model**: microsoft/Phi-3-medium-128k-instruct
- **Memory**: 4GB recommended
- **Purpose**: Efficient inference for common tasks

#### 9. **Zephyr Service** (`zephyr-service`)
- **Model**: HuggingFaceH4/zephyr-7b-beta
- **Memory**: 6GB recommended
- **Purpose**: Specialized technical assistance

### Supporting Services

#### 10. **Mailpit** (`mailpit`)
- **Purpose**: Development email capture
- **Ports**: 
  - 8025 (SMTP)
  - 8025 (API)
  - 5051 (Web UI)

#### 11. **Redis** (`redis`)
- **Purpose**: Caching and session storage
- **Port**: 6379
- **Image**: redis:7-alpine

#### 12. **Messaging Service** (`messaging`)
- **Purpose**: Internal message queue and notifications
- **Features**: Real-time messaging, queue management

#### 13. **Chatbot Service** (`chatbot`)
- **Purpose**: Bee assistant implementation
- **Port**: 8081
- **Features**: Context management, tool integration

## Port Allocations

| Service | External Port | Internal Port | Protocol | Purpose |
|---------|--------------|---------------|----------|---------|
| Frontend | 3010 | 8443 | HTTP | Web UI |
| App/API | 5050 | 5050 | HTTPS | Main API |
| Kratos Public | 4433 | 4433 | HTTPS | Auth endpoints |
| Kratos Admin | 4434 | 4434 | HTTPS | Admin API |
| Vault | 8200 | 8200 | HTTP | Secrets management |
| PostgreSQL | 5433 | 5432 | TCP | Database |
| Mailpit SMTP | 8025 | 25 | SMTP | Email capture |
| Mailpit API | 8025 | 8025 | HTTP | Email API |
| Mailpit UI | 5051 | 8080 | HTTP | Email UI |
| Redis | 6379 | 6379 | TCP | Cache |
| **Beeacon Observability Stack** |
| Grafana | 3000 | 3000 | HTTP | Monitoring dashboards |
| Loki | 3100 | 3100 | HTTP | Log aggregation |
| Promtail | N/A | 9080 | HTTP | Log collection agent |
| Log Forwarder | N/A | N/A | N/A | Container log streaming |
| **AI/LLM Services** |
| LLM Gateway | 8086 | 8080 | HTTP | LLM routing |
| Chatbot | 8081 | 8081 | HTTP | Bee assistant |

## Installation Process

### Prerequisites

1. **System Requirements**:
   - Docker Engine 20.10+
   - Docker Compose v2.0+
   - 16GB RAM minimum (32GB recommended for full LLM support)
   - 50GB free disk space

2. **Environment Setup**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-org/STING-CE.git
   cd STING-CE/STING
   
   # Set up Hugging Face token (for LLM models)
   export HF_TOKEN="your-hugging-face-token"
   ```

### Installation Order

The `manage_sting.sh` script handles the installation in the following order:

1. **Environment Initialization**
   - Create directory structure
   - Set up logging
   - Initialize environment files

2. **Base Image Build**
   - Build `sting/llm-base:latest` image first
   - This is required for all LLM services

3. **Core Services Build**
   - vault
   - dev (development utilities)
   - db (PostgreSQL)
   - app (Flask backend)
   - frontend (React)
   - kratos (authentication)
   - mailpit
   - messaging
   - redis

4. **LLM Services Build**
   - llama3-service
   - phi3-service
   - zephyr-service
   - llm-gateway
   - chatbot

5. **Beeacon Observability Services Build**
   - loki (log aggregation)
   - promtail (log collection)
   - grafana (dashboards)
   - log-forwarder (container log streaming)

6. **Service Startup Sequence**
   ```
   1. Vault (secrets management)
   2. Database (PostgreSQL)
   3. Development container (config generation)
   4. Kratos (authentication)
   5. Application backend
   6. Mailpit
   7. Frontend
   8. Messaging service
   9. Redis cache
   10. Beeacon Stack (observability profile)
       - Loki → Promtail → Grafana → Log Forwarder
   11. LLM services (optional)
   12. Chatbot (Bee)
   ```

### Installation Commands

```bash
# Full installation
./manage_sting.sh install

# Update specific service
./manage_sting.sh update frontend

# Start all services
./manage_sting.sh start

# Start with observability stack
./manage_sting.sh start --profile observability

# Start full system (includes LLM + observability)
./manage_sting.sh start --profile full

# Check status
./manage_sting.sh status

# Access monitoring dashboards
# Grafana: http://localhost:3000 (admin/admin initially)
# Loki: http://localhost:3100
# Beeacon Page: https://localhost:3010/beeacon (in STING UI)
```

## Configuration Management

### Main Configuration File: `config.yml`

The system uses a centralized YAML configuration file managed by Vault:

```yaml
# Example structure
app:
  flask:
    secret_key: vault-generated
    port: 5050
    debug: false

auth:
  kratos:
    public_url: https://localhost:4433
    admin_url: https://localhost:4434
  
database:
  postgresql:
    host: db
    port: 5432
    name: sting_app
    
llm:
  models:
    - name: llama3
      enabled: true
      memory_limit: 8G
    - name: phi3
      enabled: true
      memory_limit: 4G

# Beeacon Observability Configuration
observability:
  enabled: true
  profiles:
    - observability  # Grafana, Loki, Promtail only
    - full          # All services including LLM
  
  grafana:
    enabled: true
    port: 3000
    admin_user: vault-ref:sting/data/grafana/admin_user
    admin_password: vault-ref:sting/data/grafana/admin_password
    
  loki:
    enabled: true
    port: 3100
    retention_period: 168h  # 7 days
    max_line_size: 256KB
    
  promtail:
    enabled: true
    port: 9080
    pii_sanitization: true
    vault_integration: true
    log_paths:
      - /var/log/sting-app/*.log
      - /var/log/kratos/*.log
      - /var/log/vault/*.log
      - /var/log/containers/*.log
```

### Configuration Loading Process

1. **Vault Initialization**
   - Vault starts in dev mode
   - Root token is generated
   - Policies are applied

2. **Centralized Config Generation** ⭐ **Enhanced**
   - `utils` container runs `generate_config_via_utils()`
   - Eliminates all local config generation paths
   - Cross-platform compatibility (macOS Docker Desktop, Linux)
   - Reads base configuration from `conf/config.yml`
   - Generates service-specific env files including observability configs
   - Stores secrets in Vault with observability credentials

3. **Service Configuration**
   - Each service reads from `/app/conf/config.yml`
   - Environment-specific overrides applied
   - Secrets fetched from Vault at runtime
   - Observability services auto-configured with health dependencies

### Managing Configuration

```bash
# View current config
docker exec sting-ce-utils cat /app/conf/config.yml

# Update config (edit locally then restart utils)
vim conf/config.yml
./manage_sting.sh restart utils

# Rotate secrets (including observability credentials)
docker exec sting-ce-vault-1 vault write -f secret/rotate

# Check observability services
docker logs sting-ce-loki          # Log aggregation
docker logs sting-ce-promtail      # Log collection
docker logs sting-ce-grafana       # Dashboard service
docker logs sting-ce-log-forwarder # Container log streaming

# Access Beeacon monitoring
curl http://localhost:5050/api/beeacon/status  # System health
open http://localhost:3000                     # Grafana dashboards
```

## Local LLM Integration

### Model Management

STING-CE supports fully local LLM deployment for privacy and control:

1. **Model Storage**
   - Default location: `~/Downloads/llm_models` (macOS)
   - Linux: `/opt/models`
   - Set via `STING_MODELS_DIR` environment variable

2. **Model Download Process**
   - Automatic download during installation
   - Uses Hugging Face Hub with optional authentication
   - Supports resume on failure

3. **Hardware Detection**
   - Automatic CPU/GPU detection
   - Optimized settings based on available resources
   - Quantization options for memory-constrained systems

### LLM Gateway Architecture

```
Client Request
     │
     ▼
LLM Gateway (8086)
     │
     ├─── Load Balancer
     │         │
     ├─────────┼─────────┐
     ▼         ▼         ▼
  LLaMA3    Phi-3    Zephyr
```

### Model Selection

The gateway automatically routes requests based on:
- Model availability
- Current load
- Request type
- User preferences

## Security Architecture

### Authentication Flow

1. **User Registration/Login**
   - Frontend → Kratos Public API
   - Kratos validates credentials
   - Session cookie issued

2. **API Access**
   - Frontend includes session cookie
   - App backend validates with Kratos
   - Request processed if valid

3. **WebAuthn/Passkeys**
   - Managed by app backend
   - Credentials stored in PostgreSQL
   - Integrated with Kratos identity

### Secrets Management

- **Vault Integration**:
  - All secrets generated on first run
  - Automatic rotation supported
  - Policy-based access control

- **Environment Isolation**:
  - Each service has dedicated env file
  - Secrets never stored in git
  - Runtime injection only

### Network Security

- **Internal Network**: `sting_local`
- **HTTPS Enforcement**: Self-signed certs for dev
- **Port Isolation**: Services only expose necessary ports
- **Container Isolation**: Minimal privileges per service

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check for conflicts
   ./manage_sting.sh check-ports
   
   # Stop specific service
   docker compose -p sting-ce stop vault
   ```

2. **LLM Memory Issues**
   ```bash
   # Reduce model memory limits
   vim docker-compose.yml
   # Adjust mem_limit values
   ```

3. **Authentication Problems**
   ```bash
   # Reset Kratos
   ./manage_sting.sh reset-auth
   
   # Check Kratos logs
   docker logs sting-ce-kratos-1
   ```

4. **Beeacon Observability Issues** ⭐ **New**
   ```bash
   # Check observability stack health
   curl http://localhost:3100/ready      # Loki ready status
   curl http://localhost:3000/api/health # Grafana health
   curl http://localhost:5050/api/beeacon/status # System overview
   
   # Restart observability services
   docker compose -p sting-ce restart loki promtail grafana log-forwarder
   
   # Check log collection
   docker logs sting-ce-promtail | grep -i error
   docker logs sting-ce-log-forwarder
   
   # Verify PII sanitization
   docker exec sting-ce-promtail cat /tmp/positions.yaml
   ```

5. **Cross-Platform Log Collection Issues**
   ```bash
   # macOS Docker Desktop: Check log forwarder
   docker logs sting-ce-log-forwarder
   
   # Verify container log mounting
   docker exec sting-ce-promtail ls -la /var/log/containers/
   
   # Check Docker socket access
   docker exec sting-ce-log-forwarder docker ps
   ```

### Useful Commands

```bash
# View all logs
./manage_sting.sh logs

# Restart everything
./manage_sting.sh restart

# Backup data
./manage_sting.sh backup

# Clean installation
./manage_sting.sh clean
./manage_sting.sh install
```

## Development Workflow

### Making Changes

1. **Frontend Development**
   ```bash
   # Hot reload enabled
   ./manage_sting.sh update frontend
   ```

2. **Backend Changes**
   ```bash
   # Update and restart
   ./manage_sting.sh update app
   ```

3. **Configuration Updates**
   ```bash
   # Edit config
   vim conf/config.yml
   # Reload
   ./manage_sting.sh restart dev
   ```

### Adding New Services

1. Define in `docker-compose.yml`
2. Add to installation order in `manage_sting.sh`
3. Configure in `config.yml`
4. Add health checks
5. Document ports and purpose

## Performance Tuning

### LLM Optimization

- **CPU Systems**: Enable INT8 quantization
- **GPU Systems**: Use float16 precision
- **Memory Limited**: Use smaller models (Phi-3)

### Database Tuning

- PostgreSQL configured for containers
- Shared memory optimizations
- Connection pooling enabled

### Caching Strategy

- Redis for session storage
- LLM response caching in gateway
- Static asset caching in frontend

---

## Quick Reference

### Essential Paths
- Install directory: `~/.sting-ce` (macOS) or `/opt/sting-ce` (Linux)
- Logs: `{INSTALL_DIR}/logs`
- Config: `{INSTALL_DIR}/conf`
- Models: `~/Downloads/llm_models` or `$STING_MODELS_DIR`

### Key Commands
- Install: `./manage_sting.sh install`
- Start: `./manage_sting.sh start`
- Stop: `./manage_sting.sh stop`
- Update: `./manage_sting.sh update [service]`
- Status: `./manage_sting.sh status`
- Logs: `./manage_sting.sh logs [service]`

### Default Credentials
- Vault Token: Generated on install (see logs)
- PostgreSQL: postgres/postgres (local only)
- First user: Create via UI registration

---

*Last Updated: January 2025*
*Version: STING-CE 1.0*