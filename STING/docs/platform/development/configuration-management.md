# STING Configuration Management Guide

## Overview

STING uses a centralized configuration system that allows administrators to customize their instance through a single `config.yml` file. This guide covers how to configure, manage, and maintain your STING installation.

## Table of Contents

1. [Configuration Architecture](#configuration-architecture)
2. [The config.yml File](#the-configyml-file)
3. [Environment Variable Generation](#environment-variable-generation)
4. [Service-Specific Configuration](#service-specific-configuration)
5. [Configuration Workflow](#configuration-workflow)
6. [Common Configuration Tasks](#common-configuration-tasks)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

## Configuration Architecture

STING's configuration follows a hierarchical approach:

```
config.yml → config_loader.py → env files → Docker services
```

1. **Primary Configuration**: `conf/config.yml` - The master configuration file
2. **Configuration Loader**: `conf/config_loader.py` - Processes config.yml and generates environment files
3. **Environment Files**: `${INSTALL_DIR}/env/*.env` - Service-specific environment variables
4. **Docker Services**: Services read their configuration from environment files

## The config.yml File

### Location and Setup

```bash
# Default template location
conf/config.yml.default

# Your configuration (created during installation)
conf/config.yml

# To create from template
cp conf/config.yml.default conf/config.yml
```

### Structure Overview

```yaml
# Core sections
licensing:          # License and support configuration
application:        # Main app settings (ports, SSL, etc.)
database:           # PostgreSQL configuration
security:           # Authentication and security settings
frontend:           # React app configuration
email_service:      # Email/SMTP settings
docker:             # Container orchestration
monitoring:         # Health checks and logging
kratos:             # Authentication service
llm_service:        # AI model configuration
chatbot:            # Bee assistant settings
knowledge_service:  # Honey jar system configuration
```

## Environment Variable Generation

### How It Works

1. **Read Configuration**:
   ```bash
   python conf/config_loader.py conf/config.yml --mode runtime
   ```

2. **Generate Environment Files**:
   - The config loader creates `.env` files in `${INSTALL_DIR}/env/`
   - Each service gets its own environment file (e.g., `app.env`, `frontend.env`)

3. **Apply Changes**:
   ```bash
   # Sync configuration
   ./manage_sting.sh sync-config
   
   # Regenerate environment files
   ./manage_sting.sh regenerate-env
   
   # Restart services to apply changes
   ./manage_sting.sh restart [service]
   ```

### Environment File Locations

```
${INSTALL_DIR}/env/
├── app.env          # Backend API configuration
├── db.env           # Database credentials
├── frontend.env     # React app settings
├── kratos.env       # Authentication service
├── knowledge.env    # Knowledge service (NEW)
├── llm-gateway.env  # LLM routing service
├── chatbot.env      # Bee assistant
├── messaging.env    # WebSocket service
├── profile.env      # User profile service
└── vault.env        # Secrets management
```

## Service-Specific Configuration

### Knowledge Service (Honey Jars)

The knowledge service configuration demonstrates the full power of config.yml:

```yaml
knowledge_service:
  enabled: true
  port: 8090
  
  # Authentication settings
  authentication:
    development_mode: false  # Set to true for dev/testing
    development_user:
      id: "dev-user"
      email: "dev@sting.local"
      role: "admin"
    kratos_public_url: "https://kratos:4433"
    kratos_admin_url: "https://kratos:4434"
  
  # Access control
  access_control:
    creation_roles:
      - "admin"
      - "support"
      - "moderator"
      - "editor"
    team_based_access: true
    passkey_protection:
      enabled: false
      sensitivity_levels: ["confidential", "restricted", "secret"]
  
  # Honey jar configuration
  honey_jars:
    max_per_user: 0  # 0 = unlimited
    max_document_size: 52428800  # 50MB
    allowed_document_types:
      - "text/plain"
      - "text/markdown"
      - "application/pdf"
```

### Authentication (Kratos)

```yaml
kratos:
  public_url: "https://localhost:4433"
  admin_url: "https://localhost:4434"
  
  selfservice:
    default_return_url: "https://localhost:8443"
    login:
      ui_url: "https://localhost:8443/login"
      lifespan: "1h"
    registration:
      ui_url: "https://localhost:8443/register"
      lifespan: "1h"
  
  methods:
    password:
      enabled: true
    webauthn:
      enabled: true
      rp_id: "localhost"
      display_name: "STING Authentication"
```

### LLM Service

```yaml
llm_service:
  enabled: true
  
  # Modern Ollama configuration
  ollama:
    enabled: true
    endpoint: "http://localhost:11434"
    default_model: "phi3:mini"
    models_to_install:
      - "phi3:mini"
      - "deepseek-r1:latest"
  
  # Performance tuning
  performance:
    profile: "auto"  # auto, speed_optimized, gpu_accelerated
    
  # Model lifecycle
  model_lifecycle:
    lazy_loading: true
    idle_timeout: 60  # minutes
    max_loaded_models: 2
    preload_on_startup: false
```

## Configuration Workflow

### Initial Setup

1. **Copy Template**:
   ```bash
   cp conf/config.yml.default conf/config.yml
   ```

2. **Edit Configuration**:
   ```bash
   vim conf/config.yml
   ```

3. **Generate Environment**:
   ```bash
   python conf/config_loader.py conf/config.yml --mode initialize
   ```

4. **Start Services**:
   ```bash
   ./manage_sting.sh start
   ```

### Making Changes

1. **Edit config.yml**:
   ```bash
   vim conf/config.yml
   ```

2. **Sync Configuration**:
   ```bash
   ./manage_sting.sh sync-config
   ```

3. **Restart Affected Services**:
   ```bash
   # Restart specific service
   ./manage_sting.sh restart knowledge
   
   # Or restart all
   ./manage_sting.sh restart
   ```

### Validation

```bash
# Check configuration syntax
python conf/config_loader.py conf/config.yml --validate

# View generated environment
./manage_sting.sh show-env [service]

# Test service with new config
./manage_sting.sh test [service]
```

## Common Configuration Tasks

### 1. Enable Development Mode

For testing without authentication:

```yaml
knowledge_service:
  authentication:
    development_mode: true
```

### 2. Configure Email

```yaml
email_service:
  provider: "smtp"
  smtp:
    host: "smtp.gmail.com"
    port: "587"
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from_address: "noreply@yourdomain.com"
```

### 3. Set Custom Domain

```yaml
application:
  ssl:
    domain: "sting.yourdomain.com"
    email: "admin@yourdomain.com"

kratos:
  selfservice:
    default_return_url: "https://sting.yourdomain.com"
```

### 4. Configure Resource Limits

```yaml
docker:
  resources:
    db:
      memory: "2G"
      cpus: "2.0"
    app:
      memory: "1G"
      cpus: "1.0"
```

### 5. Enable/Disable Features

```yaml
# Disable a service entirely
profile_service:
  enabled: false

# Enable specific features
chatbot:
  tools:
    enabled: true
    allowed_tools:
      - search
      - summarize
      - analyze
```

## Advanced Configuration

### Environment Variable Substitution

Use `${VARIABLE}` syntax to reference environment variables:

```yaml
database:
  host: "${DB_HOST:-db}"
  password: "${DB_PASSWORD}"
```

### Conditional Configuration

Use profiles for different environments:

```yaml
# Development overrides
development:
  application:
    debug: true
  llm_service:
    model_lifecycle:
      development_mode: true

# Production overrides  
production:
  application:
    debug: false
  security:
    strict_mode: true
```

### Secrets Management

Sensitive values can be stored in Vault:

```yaml
security:
  secrets_backend: "vault"
  vault:
    address: "http://vault:8200"
    token: "${VAULT_TOKEN}"
```

## Configuration Reference

### Required Environment Variables

These must be set before running STING:

```bash
# Installation directory
export INSTALL_DIR="/path/to/sting"

# Domain configuration
export DOMAIN_NAME="localhost"

# Email for SSL certificates
export CERTBOT_EMAIL="admin@example.com"
```

### Service Discovery

Services communicate using Docker network aliases:

```yaml
# Internal service URLs
app: "https://app:5050"
kratos: "https://kratos:4433"
knowledge: "http://knowledge:8090"
chroma: "http://chroma:8000"
```

### Health Check Configuration

Standard health check settings:

```yaml
monitoring:
  health_checks:
    enabled: true
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

## Troubleshooting

### Configuration Not Applied

1. **Check Sync Status**:
   ```bash
   ./manage_sting.sh sync-config
   ```

2. **Verify Environment Files**:
   ```bash
   ls -la ${INSTALL_DIR}/env/
   cat ${INSTALL_DIR}/env/knowledge.env
   ```

3. **Restart Services**:
   ```bash
   ./manage_sting.sh restart
   ```

### Validation Errors

```bash
# Validate configuration
python conf/config_loader.py conf/config.yml --validate

# Check for syntax errors
yamllint conf/config.yml
```

### Service Won't Start

1. **Check Logs**:
   ```bash
   ./manage_sting.sh logs [service]
   ```

2. **Verify Dependencies**:
   ```bash
   ./manage_sting.sh status
   ```

3. **Test Configuration**:
   ```bash
   docker compose config
   ```

### Environment Variable Issues

```bash
# Show all environment variables for a service
docker inspect sting-ce-knowledge | jq '.[0].Config.Env'

# Check if variable is set
docker exec sting-ce-knowledge env | grep KNOWLEDGE_
```

## Best Practices

1. **Version Control**: Always commit your `config.yml` changes
2. **Documentation**: Document custom configuration in comments
3. **Testing**: Test configuration changes in development first
4. **Backups**: Keep backups of working configurations
5. **Incremental Changes**: Make one change at a time
6. **Monitoring**: Watch logs after configuration changes

## Migration Guide

### From Environment Files to config.yml

If you have custom `.env` files:

1. **Identify Custom Values**:
   ```bash
   diff ${INSTALL_DIR}/env/app.env conf/app.env.default
   ```

2. **Add to config.yml**:
   ```yaml
   application:
     custom_setting: "your_value"
   ```

3. **Regenerate**:
   ```bash
   ./manage_sting.sh regenerate-env
   ```

### From Docker Compose Overrides

If using `docker-compose.override.yml`:

1. **Move Settings to config.yml**
2. **Remove Override File**
3. **Regenerate and Restart**

## Configuration Schema Reference

The complete configuration schema is defined in:
- `conf/config.yml.default` - Full example with all options
- `conf/config_loader.py` - Schema validation and processing

For the latest configuration options, always refer to `config.yml.default` in your STING version.