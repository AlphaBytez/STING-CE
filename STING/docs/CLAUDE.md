# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

STING (Secure Trusted Intelligence and Networking Guardian) is a microservices-based platform for secure, private LLM deployment with advanced knowledge management capabilities. It features a React frontend, Flask backend, and multiple AI/LLM services orchestrated via Docker Compose.

**Core Value**: Enterprise-ready AI deployment with complete data sovereignty and innovative "Honey Jar" knowledge management system.

## Architecture

- **Frontend**: React 18 + Material-UI + Tailwind CSS (port 8443)
- **Backend API**: Flask/Python with PostgreSQL (port 5050 HTTPS)
- **Authentication**: Ory Kratos with passwords and WebAuthn support (ports 4433/4434)
- **LLM Services**: Modern Ollama (port 11434) + External AI (port 8091), Legacy gateway (port 8085/8086)
- **Knowledge System**: "Honey Jar" knowledge bases with vector search (port 8090)
- **Infrastructure**: Docker Compose + HashiCorp Vault for secrets
- **Chatbot**: "Bee" assistant with context management and tools

## Essential Commands

```bash
# Installation
./pre_install.sh
./install_sting.sh install --debug
./setup_hf_token.sh

# Service Management
./manage_sting.sh start          # Start all services
./manage_sting.sh stop           # Stop services
./manage_sting.sh restart        # Restart services
./manage_sting.sh status         # Check service health
./manage_sting.sh build          # Build Docker images
./manage_sting.sh logs [service] # View logs (omit service for all)
./manage_sting.sh update [service] # Update specific service (rebuilds and restarts)

# Development
./manage_sting.sh start -d       # Debug mode with verbose logging
cd frontend && npm start         # React dev server (port 8443)
cd frontend && npm run lint      # Lint frontend code
cd frontend && npm test          # Run frontend tests

# Model Management (Legacy)
./manage_sting.sh check-models   # Verify model downloads
./manage_sting.sh download-models # Download required models

# 🤖 Modern LLM Stack (Ollama-based - Recommended)
./manage_sting.sh install-ollama # Install Ollama with default models (phi3:mini, deepseek-r1)
./manage_sting.sh ollama-status  # Check Ollama installation and status
./manage_sting.sh llm-status     # Check all LLM services (Ollama, External AI, etc.)
./sting-llm start               # Start universal LLM stack (Ollama + External AI)
./sting-llm status              # Check modern LLM stack status
ollama list                     # List installed Ollama models
ollama pull phi3:mini           # Install additional models

# Legacy LLM Service (Backward Compatibility)
./sting-llm start --legacy      # Start legacy native service on port 8086
MODEL_NAME=phi3 ./sting-llm start  # Start with phi3 model (legacy mode)

# Knowledge Service (Honey Jar System)
./manage_sting.sh start knowledge        # Start knowledge service
./manage_sting.sh logs knowledge        # View knowledge service logs

# 🐝 Hive Diagnostics (Support Bundle System)
./manage_sting.sh buzz collect           # Create diagnostic honey jar
./manage_sting.sh buzz collect --auth-focus    # Focus on auth issues
./manage_sting.sh buzz collect --llm-focus     # Focus on LLM issues  
./manage_sting.sh buzz collect --ticket ABC123 # Tag with support ticket
./manage_sting.sh buzz list              # List existing bundles
./manage_sting.sh buzz clean             # Clean old bundles
./manage_sting.sh buzz hive-status       # Show diagnostic status

# 🐝 Cache Buzzer (Docker Cache Management)
./manage_sting.sh cache-buzz             # Moderate cache clear and rebuild
./manage_sting.sh cache-buzz --full      # Full cache clear (removes all containers/images)
./manage_sting.sh cache-buzz --validate  # Check container freshness
./manage_sting.sh cache-buzz app         # Target specific service
```

## 🍯 Honey Jar Knowledge System

STING includes a sophisticated knowledge management system called "Honey Jars" that enables semantic search and AI-powered knowledge retrieval.

### Architecture Overview

The Honey Jar system uses bee-themed terminology:
- **Nectar Processor**: Document ingestion and text extraction (PDF, DOCX, HTML, JSON, Markdown, TXT)
- **Honeycomb Manager**: Vector database interface using Chroma DB for embeddings storage
- **Pollination Engine**: Semantic search across knowledge bases with relevance scoring
- **Hive Manager**: Knowledge base administration and user permissions
- **Buzz Marketplace**: Distribution system for sharing and selling knowledge packages
- **Honey Combs**: Pre-configured data source templates for rapid connectivity (NEW)

### Key Features

- **Multi-format Support**: Automatic text extraction from 6+ document formats
- **Vector Search**: Semantic similarity search using sentence transformers
- **Background Processing**: Asynchronous document chunking and embedding generation
- **Role-based Access**: Public, private, and premium knowledge bases
- **Bee Integration**: Contextual knowledge retrieval enhances Bee's responses

### Service Endpoints

- **Knowledge API**: http://localhost:8090/
- **Chroma Vector DB**: http://localhost:8000/
- **Frontend UI**: https://localhost:8443/dashboard/hive

### Essential Operations

```bash
# Create a new Honey Jar (via API)
curl -X POST http://localhost:8090/honey-jars \
  -H "Content-Type: application/json" \
  -d '{"name": "My Knowledge Base", "description": "Internal docs", "type": "private"}'

# Upload documents (via API)
curl -X POST http://localhost:8090/honey-jars/{id}/documents \
  -F "file=@document.pdf" \
  -F "metadata={\"category\": \"documentation\"}"

# Search knowledge bases (via API)
curl -X POST http://localhost:8090/search \
  -H "Content-Type: application/json" \
  -d '{"query": "installation guide", "top_k": 5}'

# Get Bee context enhancement
curl -X POST http://localhost:8090/bee/context \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy STING?"}'
```

### Frontend Access

Navigate to **Honey Jars** tab in the dashboard (`/dashboard/honey-pot`) to:
- View and manage knowledge bases
- Upload documents via drag-and-drop interface
- Search across accessible Honey Jars
- Monitor processing statistics
- Configure permissions and sharing
- Query specific honey jars with Bee using the "Query with Bee" button
- Export honey jars in multiple formats (HJX, JSON, TAR)

### File Structure

```
knowledge_service/
├── app.py                    # Main FastAPI application
├── requirements.txt          # Python dependencies
├── semantic_search.py        # Semantic search engine with ChromaDB
├── core/
│   ├── nectar_processor.py   # Document processing pipeline
│   ├── honeycomb_manager.py  # Chroma DB vector interface
│   ├── pollination_engine.py # Search and retrieval engine
│   └── hive_manager.py       # Knowledge base management
├── auth/
│   └── knowledge_auth.py     # Authentication integration
└── models/
    └── honey_jar_models.py   # Pydantic data models
```

## 🏗️ Honey Combs - Data Source Connectivity

Honey Combs are reusable data source configuration templates that enable rapid, secure connectivity to databases, APIs, file systems, and streaming platforms.

### Key Concepts

- **Honey Combs**: Pre-configured connection templates (like hexagonal cells that produce honey)
- **Worker Bees**: Use Honey Combs to connect and extract data
- **Two Modes**:
  - **Continuous Flow**: Live data streaming into existing Honey Jars
  - **Snapshot Generation**: Create new Honey Jars from database dumps or API exports
- **Built-in Scrubbing**: Automatic PII detection and removal for compliance

### Supported Data Sources

#### Database Combs
- PostgreSQL, MySQL, MongoDB
- Oracle, SQL Server, Snowflake
- BigQuery, DynamoDB

#### API Combs
- REST APIs (with OAuth2, API Key, Bearer auth)
- GraphQL endpoints
- SOAP services
- WebSocket streams

#### File System Combs
- AWS S3, Google Cloud Storage, Azure Blob
- FTP/SFTP servers
- SharePoint, Google Drive, Dropbox
- Local file systems

#### Stream Combs
- Apache Kafka
- RabbitMQ
- AWS Kinesis
- Redis Streams

### Usage Example

```python
# Select a Honey Comb template
comb = HoneyCombLibrary.get_comb("postgresql_production")

# Configure scrubbing for GDPR compliance
comb.configure_scrubbing({
    "enabled": True,
    "profile": "gdpr_compliant",
    "custom_rules": [
        {"field": "email", "action": "hash"},
        {"field": "ssn", "action": "remove"}
    ]
})

# Create a Worker Bee to execute
worker_bee = WorkerBee(comb)

# Generate a new Honey Jar from database snapshot
honey_jar = await worker_bee.generate_honey_jar(
    filter={"created_at": {"$gte": "2024-01-01"}}
)
```

### Documentation

- **Technical Specification**: `docs/features/HONEY_COMBS_TECHNICAL_SPECIFICATION.md`
- **Connector Design**: `docs/features/HONEY_COMBS_CONNECTOR_DESIGN.md`
- **Integration Guide**: See Worker Bee Connector Framework docs

## 🐝 Hive Diagnostics System

STING includes a comprehensive diagnostic system called "Hive Diagnostics" that enables users to easily gather and share sanitized diagnostic bundles for support.

### Overview

The Hive Diagnostics system uses bee-themed terminology and creates "honey jars" - secure, sanitized bundles of diagnostic data:
- **Honey Collector**: Main bundle generation script (`lib/hive_diagnostics/honey_collector.sh`)
- **Pollen Filter**: Data sanitization engine (`lib/hive_diagnostics/pollen_filter.py`)
- **Worker Bee Logs**: Collects logs from all STING services
- **Nectar Collection**: Gathers diagnostic data from containers, services, and system

### Key Features

- **Automatic Sanitization**: Removes passwords, API keys, tokens, PII, certificates
- **Configurable Time Windows**: Default 24-48 hours, customizable ranges
- **Focus Areas**: Auth, LLM, performance, startup troubleshooting
- **Privacy-First**: Local-only generation, comprehensive data filtering
- **Marketing Ready**: "Buzzing for support" creates user-friendly experience

### Essential Operations

```bash
# Create diagnostic bundle
./manage_sting.sh buzz collect

# Focus on specific issues  
./manage_sting.sh buzz collect --auth-focus
./manage_sting.sh buzz collect --llm-focus --performance

# Extended time windows
./manage_sting.sh buzz collect --hours 48 --ticket SUPPORT-123

# Bundle management
./manage_sting.sh buzz list
./manage_sting.sh buzz clean --older-than 7d
./manage_sting.sh buzz filter-test
```

### File Structure

```
lib/hive_diagnostics/
├── honey_collector.sh        # Main collection script
├── pollen_filter.py         # Data sanitization engine
docs/support/
├── BUZZING_FOR_SUPPORT.md   # Complete user guide
└── BUZZ_QUICK_REFERENCE.md  # Quick command reference
```

### Bundle Contents

- Recent service logs (sanitized)
- Docker container status and health
- System resource usage metrics
- Configuration snapshots (secrets removed)
- Database connection info (no actual data)
- Network connectivity tests
- Error pattern analysis

### Privacy Protection

The Pollen Filter automatically removes:
- API keys, passwords, tokens, secrets
- Email addresses, phone numbers, SSNs
- Database connection strings with credentials
- Certificate data and private keys
- Configurable IP address filtering
- Custom sensitive data patterns

## Project Structure

```
STING/
├── app/                          # Flask backend application
│   ├── routes/                   # API route handlers
│   ├── models/                   # SQLAlchemy models
│   ├── services/                 # Business logic services
│   ├── middleware/               # Request/response middleware
│   ├── migrations/               # Database migrations
│   └── workers/                  # Background workers (report, profile sync)
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── utils/               # Utility functions
│   │   └── services/            # API service clients
│   └── public/                  # Static assets
├── knowledge_service/           # Honey Jar knowledge management
│   ├── core/                    # Core knowledge processing
│   ├── auth/                    # Authentication integration
│   └── models/                  # Data models
├── chatbot/                     # Bee AI assistant service
│   ├── bee_server.py           # Main chatbot server
│   ├── prompts/                # AI prompts and templates
│   └── tools/                  # Chatbot tool integrations
├── external_ai_service/        # Modern AI service (Ollama interface)
├── llm_service/                # Legacy LLM service (macOS Metal)
├── messaging_service/          # Inter-service messaging
├── vault/                      # HashiCorp Vault configuration
├── kratos/                     # Ory Kratos identity configuration
│   ├── identity.schema.*.json  # Identity schemas
│   ├── kratos.yml              # Main Kratos config
│   └── courier-templates/      # Email templates
├── observability/              # Monitoring stack
│   ├── grafana/                # Dashboards and config
│   ├── loki/                   # Log aggregation config
│   └── promtail/               # Log collection config
├── conf/                       # Configuration management
│   ├── config.yml              # Main configuration file
│   └── config_loader.py        # Config to env file generator
├── lib/                        # Shell library modules
│   ├── bootstrap.sh            # Initial setup
│   ├── services.sh             # Service management
│   ├── installation.sh         # Installation logic
│   ├── health.sh               # Health check functions
│   ├── cache_buzzer.sh         # Docker cache management
│   └── hive_diagnostics/       # Diagnostic bundle creation
├── docs/                       # Documentation
│   ├── CLAUDE.md               # This file
│   ├── architecture/           # Architecture docs
│   ├── features/               # Feature documentation
│   └── guides/                 # User guides
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Service orchestration
├── manage_sting.sh             # Main management script
├── install_sting.sh            # Installation script
└── pyproject.toml             # Python project configuration
```

## Configuration Structure

Main configuration in `/conf/config.yml` controls:
- Service ports and URLs
- Feature flags (knowledge, observability, etc.)
- Model selection and parameters
- Security settings
- Health check intervals
- Resource limits

Environment files are generated in `${INSTALL_DIR}/env/` from config.yml:
- `db.env` - PostgreSQL credentials
- `kratos.env` - Authentication settings
- `vault.env` - Secrets management
- `frontend.env` - React app configuration
- `app.env` - Flask application settings
- `chatbot.env` - Bee chatbot configuration
- `knowledge.env` - Knowledge service settings
- `observability.env` - Grafana, Loki, Promtail configuration
- `headscale.env` - Support tunnel configuration

### Testing Configuration Generation

To test configuration generation in the utils container:

```bash
# Start utils container for testing
COMPOSE_FILE=/opt/sting-ce/docker-compose.yml docker compose --profile installation up -d utils

# Test config generation manually
docker exec sting-ce-utils bash -c "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode bootstrap"

# Check generated files
docker exec sting-ce-utils ls -la /app/env/

# Copy generated files to install directory for inspection
docker cp sting-ce-utils:/app/env/observability.env /tmp/observability.env.test
cat /tmp/observability.env.test

# Regenerate environment files after config changes
./manage_sting.sh regenerate-env
```

## Development Workflow

1. **Making Changes**:
   - Frontend code: `frontend/src/`
   - Backend API: `app/` (Flask application with routes in `app/routes/`)
   - LLM services: `llm_service/` and `external_ai_service/`
   - Chatbot: `chatbot/` (Bee assistant service)
   - Knowledge Service: `knowledge_service/` (Honey Jar management)
   - Configuration: Update `conf/config.yml`, then run `./manage_sting.sh regenerate-env`

2. **Service Endpoints**:
   - Frontend: https://localhost:8443 (dev) or :3010 (prod)
   - API: https://localhost:5050/api/
   - Kratos Public: https://localhost:4433/
   - Kratos Admin: https://localhost:4434/
   - LLM Gateway: http://localhost:8085/ (proxy to :8086)
   - Ollama: http://localhost:11434/ (modern LLM stack)
   - External AI: http://localhost:8091/
   - Knowledge Service: http://localhost:8090/
   - Chatbot (Bee): http://localhost:8888/
   - Vault UI: http://localhost:8200/
   - Chroma DB: http://localhost:8000/
   - Grafana: http://localhost:3001/
   - Mailpit (dev): http://localhost:8025/

3. **Database Access**:
   - PostgreSQL on port 5433 (external mapping)
   - Credentials in `${INSTALL_DIR}/env/db.env`
   - Main DB: `sting_app` (user: `app_user`)
   - Kratos DB: `kratos` (user: `kratos_user`)
   - Messaging DB: `sting_messaging` (user: `app_user`)
   - Connection from host: `psql -h localhost -p 5433 -U postgres -d sting_app`

## Key Implementation Details

### Authentication & Security
- **Authentication Flow**: Frontend → Kratos (identity provider) → Backend API validation
- **Session Management**: Kratos sessions stored in PostgreSQL, validated via middleware
- **WebAuthn/Passkeys**: Supported via Kratos native WebAuthn (custom implementation archived)
- **Multi-Factor Auth**: TOTP, recovery codes, AAL2 (Authentication Assurance Level 2)
- **Secrets**: All sensitive data stored in HashiCorp Vault, accessed via hvac client
- **API Keys**: Managed via `app/models/api_key_models.py` for programmatic access

### LLM & AI Architecture
- **Modern Stack (Recommended)**: Ollama (port 11434) + External AI Service (port 8091)
- **Legacy Stack**: Native LLM service on macOS Metal (port 8086)
- **LLM Routing**: Chatbot (Bee) → External AI → Ollama → Models
- **Models**: phi3:mini, deepseek-r1 (configurable via Ollama)
- **Context Management**: Conversation history stored in PostgreSQL
- **Knowledge Integration**: Bee can query Honey Jars for contextual responses

### Knowledge System (Honey Jars)
- **Document Processing**: `knowledge_service/core/nectar_processor.py` handles PDF, DOCX, Markdown, etc.
- **Vector Storage**: ChromaDB for semantic embeddings
- **Search**: `knowledge_service/core/pollination_engine.py` for semantic search
- **Management**: `app/models/honey_jar_models.py` for database models

### Observability
- **Log Aggregation**: Loki collects logs from all services via Promtail
- **Monitoring**: Grafana dashboards at http://localhost:3001/
- **PII Sanitization**: Pollen Filter removes sensitive data from logs
- **Service Health**: All services expose `/health` endpoints
- **Diagnostics**: Buzz/Hive diagnostics system for support bundles

### Database Architecture
- **Multi-Database**: Separate databases for app, Kratos, messaging
- **User Separation**: app_user, kratos_user, postgres for security isolation
- **Migrations**: Kratos auto-migrates, app uses manual migrations in `app/migrations/`
- **Connection Pooling**: SQLAlchemy with configurable pool sizes

### Deployment Patterns
- **Platform Detection**: macOS vs Linux handling in `lib/platform_helper.sh`
- **Service Dependencies**: Strict startup order defined in docker-compose.yml
- **Health Checks**: All services have configurable health check intervals
- **Resource Limits**: Memory and CPU limits prevent resource exhaustion
- **Profiles**: Docker Compose profiles control optional services (dev, full, support-tunnels)

## Common Issues and Solutions

1. **Health check errors**: Ensure HEALTH_CHECK_INTERVAL environment variables have time units (e.g., "5s" not "5")
2. **Model loading failures**: Check HF_TOKEN is set and models are downloaded to `${INSTALL_DIR}/models`
3. **Database connection issues**: Verify `db.env` exists and PostgreSQL is healthy
4. **Kratos errors**: Check `kratos.env` and that migrations have run
5. **Memory/swap issues**: All services now have memory limits to prevent 40GB+ swap usage
6. **phi3 model not loading**: Service optimized for phi3 with 8-bit quantization and persistence
7. **Queue management**: Redis configured for job queuing - see `docs/QUEUING_ARCHITECTURE.md`
8. **Docker cache issues**: Use `./manage_sting.sh cache-buzz --validate` to check and `cache-buzz --full` to fix persistent cache problems - see `docs/CACHE_BUZZER_GUIDE.md`
9. **Service update failures**: Use `./manage_sting.sh update [service]` to rebuild and restart specific services - this handles proper container removal, image rebuilding, and service restart

### Configuration Persistence Issues

**CRITICAL**: Changes made in the installation directory (`${INSTALL_DIR}`) get overwritten during reinstall/updates.

**Always make configuration changes in the project directory (`/Volumes/EXT-SSD/DevWorld/STING/`) instead:**

5. **Chatbot not responding despite "healthy" status**:
   - **Cause**: Docker compose environment variables override env files
   - **Symptoms**: Health checks pass but chatbot gives generic responses, logs show "All LLM endpoints failed"
   - **Solution**: 
     ```bash
     # 1. Update project docker-compose.yml (NOT the installation copy)
     vim /Volumes/EXT-SSD/DevWorld/STING/docker-compose.yml
     
     # 2. Ensure chatbot environment has:
     - CHATBOT_MODEL=deepseek-1.5b
     - NATIVE_LLM_URL=http://host.docker.internal:8086
     
     # 3. Copy updated file and recreate container:
     cp docker-compose.yml ${INSTALL_DIR}/
     docker compose -f ${INSTALL_DIR}/docker-compose.yml stop chatbot
     docker compose -f ${INSTALL_DIR}/docker-compose.yml rm -f chatbot
     docker compose -f ${INSTALL_DIR}/docker-compose.yml up -d chatbot
     ```

6. **Native LLM service port conflicts during restart**:
   - **Issue**: Service starts on port 8085 (conflicts with nginx proxy) instead of 8086
   - **Files to check**: `lib/native_llm.sh` - ensure `NATIVE_LLM_PORT=8086`
   - **Default model**: Should load deepseek-1.5b, not tinyllama

7. **Docker crashes during STING restart**:
   - **Cause**: Resource contention between native LLM and Docker services
   - **Prevention**: Native LLM service now starts after Docker services are stable
   - **Solution**: Start native LLM manually: `MODEL_NAME=deepseek-1.5b ./sting-llm start`

## Testing

### Frontend Testing
- Unit/component tests: `cd frontend && npm test`
- Linting: `cd frontend && npm run lint`
- Build test: `cd frontend && npm run build`
- Test coverage: Jest-based test suite in `frontend/src/`

### Backend Testing
- Unit tests: Use pytest (tests in `app/tests/`)
- Integration tests: `./manage_sting.sh test`
- API testing: Use curl or tools like Postman/Insomnia
- Database tests: Test fixtures in `app/tests/fixtures/`

### Service Testing
- Email testing: Mailpit UI at http://localhost:8025 (development profile)
- LLM testing: Direct API calls to http://localhost:8091/v1/chat/completions
- Knowledge testing: Upload test documents via frontend or API
- Auth testing: Scripts in `kratos/` directory for flow testing

### Health Checks
- All services: `./manage_sting.sh status`
- Individual service: `curl http://localhost:[PORT]/health`
- Database: `./manage_sting.sh health db`
- Comprehensive diagnostics: `./manage_sting.sh buzz collect`

## Debugging

### Log Analysis
- Enable debug mode: `./manage_sting.sh start -d`
- View logs: `./manage_sting.sh logs [service]`
- Follow logs: `./manage_sting.sh logs [service] -f`
- Grafana logs: View aggregated logs at http://localhost:3001/
- Log locations: `${INSTALL_DIR}/logs/` and Docker container logs

### Container Inspection
- Shell access: `docker exec -it sting-ce-[service] /bin/sh` (or `/bin/bash`)
- Container status: `docker ps -a | grep sting-ce`
- Container health: `docker inspect sting-ce-[service] | jq '.[0].State.Health'`
- Resource usage: `docker stats sting-ce-[service]`

### Database Debugging
- Connect to DB: `psql -h localhost -p 5433 -U postgres -d sting_app`
- List tables: `\dt` (in psql)
- Check migrations: Query `alembic_version` table
- Kratos identities: `psql -h localhost -p 5433 -U postgres -d kratos -c "SELECT id, traits FROM identities;"`

### Service-Specific Debugging
- **Kratos**: Check admin API at https://localhost:4434/admin/health/ready
- **Knowledge Service**: Test with `curl http://localhost:8090/health`
- **LLM Services**: Check Ollama: `ollama list` and `curl http://localhost:11434/api/tags`
- **Vault**: Access UI at http://localhost:8200/ (root token in logs)
- **Redis**: Connect with `redis-cli -p 6379`

### Diagnostic Tools
- **Buzz System**: `./manage_sting.sh buzz collect` - Creates sanitized diagnostic bundle
- **Cache Issues**: `./manage_sting.sh cache-buzz --validate` - Check container freshness
- **Service Health**: Comprehensive health dashboard in Grafana
- **API Debug Routes**: `/api/debug/service-statuses` endpoint for service status

## 🏗️ Service Management Architecture & Patterns

### Service Startup Order & Dependencies

STING follows a **strict dependency chain** for service startup:
```
vault → db → kratos → app/frontend → messaging/chatbot → llm-services → knowledge-system
```

**Key Principles:**
- Each service waits for health checks before starting the next
- Critical services (vault, db, kratos, app) must be healthy before auxiliary services
- Managed via `build_and_start_services()` in `lib/installation.sh`
- Runtime control via `lib/services.sh`

### Adding New Services - Standard Pattern

#### 1. Configuration Structure (`conf/config.yml`)
```yaml
new_service:
  enabled: true
  port: 8091
  timeout: 30
  max_retries: 3
  dependencies: ["db", "app"]
  
docker:
  network: sting_local
  
monitoring:
  health_checks:
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

#### 2. Docker Compose Service Definition
```yaml
new-service:
  container_name: sting-ce-new-service
  build:
    context: ./new_service
    dockerfile: Dockerfile
  env_file:
    - ${INSTALL_DIR}/env/new-service.env
  environment:
    - SERVICE_PORT=8091
    - SERVICE_NAME=new-service
  volumes:
    - ./conf:/app/conf:ro
    - new_service_data:/app/data
    - new_service_logs:/var/log/new-service
  ports:
    - "8091:8091"
  networks:
    sting_local:
      aliases:
        - new-service
  depends_on:
    db:
      condition: service_healthy
    app:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8091/health"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 256M
  restart: unless-stopped
  # Use profiles to control startup timing
  profiles:
    - full
    - optional-services
```

#### 3. Health Check Integration (`lib/services.sh`)
Add custom health logic to `wait_for_service()` function:
```bash
case "$service" in
    new-service)
        if curl -s -f "http://localhost:8091/health" >/dev/null 2>&1; then
            log_message "Service $service is healthy"
            return 0
        fi
        ;;
esac
```

#### 4. Installation Integration (`lib/installation.sh`)
Add to service list in `build_and_start_services()`:
```bash
# Build phase
docker compose build --no-cache vault dev db app frontend kratos mailpit messaging redis new-service

# Startup phase  
docker compose up -d new-service
wait_for_service "new-service" || return 1
```

### Profile-Based Service Control

**Profile System**: Controls which services start in different scenarios
- `linux-only` / `macos-only` - Platform-specific services
- `knowledge-system` - Knowledge/AI services (chroma, knowledge)
- `full` - All optional services
- `dev-tools` - Development utilities

**Usage:**
```bash
# Start specific service group
docker compose --profile knowledge-system up -d

# Start all services
docker compose --profile full up -d
```

### Environment File Generation

**Process Flow:**
1. `config_loader.py` reads `conf/config.yml`
2. Generates `${INSTALL_DIR}/env/[service].env` files
3. `load_service_env()` loads variables into shell environment
4. Docker Compose uses `env_file:` directives

**Critical Environment Variables Pattern:**
```bash
# Database connectivity (all services need this)
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=sting_app
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# Service networking
SERVICE_NAME=new-service
SERVICE_PORT=8091
SERVICE_URL=http://new-service:8091

# Health check configuration
HEALTH_CHECK_INTERVAL=30s
HEALTH_CHECK_TIMEOUT=10s
HEALTH_CHECK_RETRIES=5
HEALTH_CHECK_START_PERIOD=60s
```

### Platform-Specific Service Handling

**macOS vs Linux Detection Pattern:**
```bash
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS: Use proxy/native services
    export LLM_GATEWAY_IMAGE="nginx:alpine"
    export NATIVE_LLM_ENABLED="true"
else
    # Linux: Use containerized services
    export LLM_GATEWAY_IMAGE=""  # Use build instead
    export NATIVE_LLM_ENABLED="false"
fi
```

### Health Check Standardization

**Service-Specific Health Check Patterns:**
- **Database**: `pg_isready -U postgres`
- **Web Services**: `curl -k -s "https://localhost:PORT/health"`
- **API Services**: `curl -f "http://localhost:PORT/api/health"`
- **Container-Only**: `docker compose ps service | grep -q "Up"`

**Health Check Configuration:**
- Timeout: 10s (web services), 3s (db)
- Retries: 30 (critical), 5 (auxiliary)
- Start Period: 30s-300s (service complexity dependent)
- Interval: 5s (critical), 30s (auxiliary)

### Resource Management

**Standard Resource Limits:**
```yaml
deploy:
  resources:
    limits:
      memory: 1G        # Service-specific
      cpus: '1.0'       # Usually 1.0 or 0.5
    reservations:
      memory: 256M      # Minimum guaranteed
```

**Memory Allocation Guidelines:**
- **Critical Services** (db, app): 1-2G limits
- **LLM Services**: 4-8G limits  
- **Auxiliary Services**: 512M-1G limits
- **Proxy/Nginx**: 256M limits

### Integration Checklist for New Services

**Required Files to Modify:**
1. ✅ `conf/config.yml` - Service configuration section
2. ✅ `docker-compose.yml` - Service definition with proper profiles
3. ✅ `lib/services.sh` - Custom health check logic
4. ✅ `lib/installation.sh` - Build and startup integration
5. ✅ Create service directory with Dockerfile
6. ✅ Add volumes to docker-compose (data, logs)

**Required Service Conventions:**
- ✅ Health endpoint at `/health` returning JSON
- ✅ Configuration via generated env files
- ✅ Logging to mounted volumes (`/var/log/service-name`)
- ✅ Graceful shutdown handling (SIGTERM)
- ✅ Memory/CPU resource limits defined
- ✅ Proper dependency declarations in `depends_on`
- ✅ Network aliases for service discovery
- ✅ Container naming: `sting-ce-service-name`

### Common Service Management Operations

```bash
# Individual service management
./manage_sting.sh start [service]
./manage_sting.sh stop [service]  
./manage_sting.sh restart [service]
./manage_sting.sh logs [service]
./manage_sting.sh update [service]   # Preferred for updates - rebuilds and restarts cleanly

# Profile-based management
./manage_sting.sh start-profile knowledge-system
./manage_sting.sh stop-profile optional-services

# Health and status
./manage_sting.sh status
./manage_sting.sh health [service]

# Configuration management
./manage_sting.sh regenerate-env
./manage_sting.sh reload-config
```

### Module Loading Pattern

**Dynamic Module Loading:**
```bash
# Load required functionality on-demand
load_required_module "services"
load_required_module "health"
load_required_module "docker"
load_required_module "config"
```

**This ensures:**
- Faster script startup
- Clear dependency management
- Modular functionality organization
- Better error isolation
## Critical Concepts & Workflows

### Installation Directory Pattern
STING uses a **dual-directory pattern**:
- **Source Directory**: `/path/to/STING/` (project repo, e.g., `/Volumes/EXT-SSD/DevWorld/STING/`)
- **Install Directory**: `${INSTALL_DIR}` (runtime, e.g., `~/.sting-ce` or `/opt/sting-ce`)

**Important**: Always make configuration changes in the **source directory**, not the install directory. The install directory gets overwritten during updates.

### Service Communication
Services communicate via Docker internal networking (`sting_local` network):
- Internal hostnames: `db`, `kratos`, `app`, `knowledge`, `chatbot`, etc.
- External access: `host.docker.internal` for accessing host services (e.g., Ollama)
- Port mapping: Internal ports differ from external (e.g., PostgreSQL is 5432 internal, 5433 external)

### Authentication Flow (Detailed)
1. User accesses frontend at https://localhost:8443
2. Frontend checks for Kratos session via `/api/auth/session`
3. If no session, redirect to Kratos login flow at https://localhost:4433
4. Kratos handles authentication (password, WebAuthn, TOTP)
5. On success, Kratos creates session and redirects to frontend
6. Frontend validates session with backend API
7. Backend middleware (`app/middleware/kratos_auth_middleware.py`) validates every request
8. Session stored in PostgreSQL `kratos` database

### Honey Jar Lifecycle
1. **Creation**: User creates Honey Jar via frontend or API
2. **Document Upload**: Files uploaded to knowledge service
3. **Processing**: Nectar processor extracts text and chunks content
4. **Embedding**: Sentence transformers generate vector embeddings
5. **Storage**: Embeddings stored in ChromaDB, metadata in PostgreSQL
6. **Search**: Pollination engine performs semantic search
7. **Integration**: Bee chatbot can query Honey Jars for context

### Configuration Changes
When updating configuration:
1. Edit `conf/config.yml` in source directory
2. Run `./manage_sting.sh regenerate-env` to update env files
3. Restart affected services: `./manage_sting.sh restart [service]`
4. For major changes: `./manage_sting.sh update [service]` (rebuilds container)

### Docker Compose Profiles
- **No profile**: Core services (vault, db, kratos, app, frontend)
- **development**: Adds Mailpit for email testing
- **full**: All services including observability stack
- **support-tunnels**: Headscale for remote support
- **installation**: Utils container for config generation

Activate profiles: `docker compose --profile development up -d`

## Known Issues

1. **Passkey Registration**: If you encounter "Failed to generate registration options", ensure the PasskeyRegistrationChallenge model has the required methods (create_challenge, get_valid_challenge).

2. **Docker Buildx Segmentation Fault**: If you encounter "Segmentation fault: 11" during builds:
   - The cache buzzer has been updated to use the default Docker builder
   - Run `docker buildx rm sting-builder` to remove problematic builders
   - The system will automatically fall back to the default builder

3. **Docker Image Naming**: Ensure COMPOSE_PROJECT_NAME=sting-ce is set in .env to get correct image names

4. **Middleware Not Working After Update**: If middleware changes (like password change flow) aren't working after an update:
   - Check if you used `--sync-only` flag: this only copies files but doesn't rebuild containers
   - Middleware and server-side code changes require a full rebuild: `msting update app`
   - Verify with: `./scripts/verify_enrollment_flow.sh`
   - For complete rebuild: `msting update app --no-cache`

## Authentication Fixes

### Passkey Creation Failure - Custom WebAuthn Disabled (January 2025)
**Problem**: Passkey creation was failing because the custom WebAuthn endpoints were disabled but the frontend was still trying to use them.

**Root Cause**: 
- The custom WebAuthn routes (`/api/webauthn/*`) were archived and commented out in `app/__init__.py`
- Frontend component `PasskeySettingsIntegrated` was still trying to call these endpoints
- The system was supposed to use Kratos native WebAuthn but the UI wasn't updated

**Solution**:
- Created `PasskeySettingsSimple.jsx` that shows existing passkeys from Kratos identity
- Added a button that opens Kratos settings page in a new tab for passkey management
- Updated `SecuritySettings.jsx` to use the simplified component
- This is a temporary solution until Kratos WebAuthn can be fully integrated into the UI

**Files Changed**:
- Created `/frontend/src/components/settings/PasskeySettingsSimple.jsx`
- Updated `/frontend/src/components/user/SecuritySettings.jsx` to import PasskeySettingsSimple
- Updated `/frontend/src/utils/kratosConfig.js` to include settings flow endpoints

## Development Conventions & Best Practices

### Code Organization
- **Backend Routes**: Follow pattern `app/routes/[feature]_routes.py`, register in `app/__init__.py`
- **Frontend Components**: Organize by feature in `frontend/src/components/[feature]/`
- **Models**: Define in `app/models/[feature]_models.py`, import in `app/models/__init__.py`
- **Services**: Business logic in `app/services/[feature]_service.py`
- **Middleware**: Request processing in `app/middleware/[feature]_middleware.py`

### Naming Conventions
- **Services**: Container names use `sting-ce-[service]` format
- **Environment Variables**: Use SCREAMING_SNAKE_CASE
- **Python**: Use snake_case for functions/variables, PascalCase for classes
- **JavaScript/React**: Use camelCase for functions/variables, PascalCase for components
- **Database Tables**: Use snake_case (SQLAlchemy automatically converts)
- **API Endpoints**: Use kebab-case in URLs (e.g., `/api/honey-jars`)

### Docker & Container Practices
- **Health Checks**: Every service must have a `/health` endpoint
- **Resource Limits**: Always define memory/CPU limits in docker-compose.yml
- **Logging**: Write logs to stdout/stderr for Docker log collection
- **Graceful Shutdown**: Handle SIGTERM signal properly
- **Environment Variables**: Use env_file directive, not hardcoded environment values
- **Volumes**: Use named volumes for persistent data, mount volumes for configuration

### Security Practices
- **Secrets**: Store in Vault, retrieve via hvac client, never commit to Git
- **API Keys**: Use `app/models/api_key_models.py`, hash and salt properly
- **Passwords**: Always use Kratos for user authentication, never roll your own
- **SQL Injection**: Use SQLAlchemy ORM, never raw SQL with string interpolation
- **XSS**: React sanitizes by default, be careful with `dangerouslySetInnerHTML`
- **CSRF**: Kratos handles CSRF tokens, ensure frontend includes them

### Testing Practices
- **Backend**: Write pytest tests in `app/tests/test_[feature].py`
- **Frontend**: Write Jest tests alongside components as `[Component].test.jsx`
- **Integration**: Test full workflows in `scripts/` directory
- **Health Checks**: Verify all services are healthy before running tests
- **Fixtures**: Use pytest fixtures for database setup/teardown

### Git Practices
- **Commits**: Use conventional commits (feat:, fix:, docs:, refactor:)
- **Branches**: Feature branches from main, use descriptive names
- **.gitignore**: Never commit `.env` files, secrets, or local configuration
- **Documentation**: Update CLAUDE.md and relevant docs with major changes

### Performance Considerations
- **Database**: Use connection pooling, create indexes for frequent queries
- **Caching**: Use Redis for session data and frequently accessed data
- **Vector Search**: ChromaDB handles embeddings, don't store in PostgreSQL
- **API Responses**: Paginate large result sets, use streaming for large files
- **Docker Images**: Use multi-stage builds, minimize layer count
- **LLM Responses**: Stream responses to user, don't buffer entire response

### Debugging Tips
- **Start Simple**: Use `./manage_sting.sh status` before deep debugging
- **Check Logs**: Always check service logs before assuming code issues
- **Isolate Services**: Test individual services with curl/httpie
- **Use Debug Routes**: `/api/debug/` endpoints provide service status
- **Buzz System**: Create diagnostic bundle for complex issues
- **Container Inspection**: Exec into containers to check file system state

### Common Patterns

#### Adding a New API Endpoint
1. Create route function in `app/routes/[feature]_routes.py`
2. Define request/response schemas (Pydantic or Flask-RESTX)
3. Add authentication middleware if needed
4. Register blueprint in `app/__init__.py`
5. Add health check if new service
6. Document in API docs (OpenAPI/Swagger)
7. Write tests in `app/tests/test_[feature].py`

#### Adding a New Frontend Page
1. Create component in `frontend/src/pages/[Feature]Page.jsx`
2. Add route in `frontend/src/App.js`
3. Create API service in `frontend/src/services/[feature]Service.js`
4. Add navigation link if needed
5. Handle authentication/authorization
6. Write tests in `[Feature]Page.test.jsx`

#### Adding a New Microservice
1. Create service directory with Dockerfile
2. Add service definition to `docker-compose.yml`
3. Define in `conf/config.yml`
4. Create env file generation in `conf/config_loader.py`
5. Add health check endpoint
6. Register in `lib/services.sh` for startup
7. Add to `lib/installation.sh` build sequence
8. Document in this file (CLAUDE.md)
