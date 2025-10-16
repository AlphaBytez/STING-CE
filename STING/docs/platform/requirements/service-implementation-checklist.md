# Service Implementation Checklist

This checklist ensures new STING services follow consistent patterns and integrate properly with the platform.

## Pre-Implementation Planning

- [ ] **Service Purpose**: Clear definition of service functionality
- [ ] **Port Assignment**: Assigned unique port (check `docker-compose.yml` for conflicts)
- [ ] **Dependencies**: Identified service dependencies (db, app, etc.)
- [ ] **Resource Requirements**: Memory/CPU limits based on service complexity

## Core Service Files

### 1. Service Directory Structure
- [ ] Create service directory in project root
- [ ] **Dockerfile**: Container build configuration
- [ ] **requirements.txt** (Python) or equivalent dependency file
- [ ] **app.py** or main application file
- [ ] **README.md**: Service-specific documentation

### 2. Health Check Implementation
- [ ] **Health Endpoint**: `/health` endpoint returning JSON status
- [ ] **Startup Validation**: Check dependencies before reporting healthy
- [ ] **Graceful Shutdown**: Handle SIGTERM for clean container stops

## Integration Requirements

### 1. Docker Compose Configuration
- [ ] **Service Definition**: Add service to `docker-compose.yml`
- [ ] **Container Naming**: Follow `sting-ce-service-name` pattern
- [ ] **Network Configuration**: Use `sting_local` network with aliases
- [ ] **Dependencies**: Proper `depends_on` with health check conditions
- [ ] **Resource Limits**: Memory and CPU limits defined
- [ ] **Volume Mounts**: Data persistence and log directories
- [ ] **Environment Configuration**: Use `env_file` directive

### 2. Service Management Integration

#### File Operations (`lib/file_operations.sh`)
- [ ] **Sync Rules**: Add service-specific sync case in `sync_service_files()`
```bash
service-name)
    mkdir -p "$INSTALL_DIR/service_directory"
    rsync -a "$project_dir/service_directory/" "$INSTALL_DIR/service_directory/" \
        --exclude='venv' --exclude='**/venv' --exclude='.venv' \
        --exclude='__pycache__' --exclude='**/__pycache__' --exclude='*.pyc' \
        --exclude='*.egg-info'
    log_message "Service synchronized successfully"
    ;;
```
- [ ] **Available Services List**: Add to warning message service list

#### Health Checks (`lib/services.sh`)
- [ ] **Health Check Logic**: Add case in `wait_for_service()` function
```bash
"service-name")
    if curl -s -f "http://localhost:PORT/health" > /dev/null 2>&1; then
        log_message "Service is fully operational"
        return 0
    fi
    ;;
```

### 3. Configuration System
- [ ] **Config Schema**: Add service configuration to `conf/config.yml`
- [ ] **Environment Generation**: Ensure config generates appropriate `.env` file
- [ ] **Port Configuration**: Service port properly configured and exposed

### 4. Installation Integration

#### Installation Cleanup (`lib/installation.sh`)
- [ ] **Container Stop/Kill Commands**: Add service to cleanup commands (lines 213-214)
```bash
# Add sting-ce-service-name to both stop and kill commands:
timeout 5s docker stop sting-ce-vault ... sting-ce-service-name 2>/dev/null || true
timeout 5s docker kill sting-ce-vault ... sting-ce-service-name 2>/dev/null || true
```
- [ ] **Build Phase**: Add to build commands in `lib/installation.sh`
- [ ] **Startup Phase**: Add to service startup sequence
- [ ] **Health Validation**: Include in health check validation

#### Validation Script Compatibility (`lib/configuration.sh`)
- [ ] **Hyphenated Service Names**: Ensure sed command uses `^` anchor (line 686)
```bash
# CORRECT - preserves hyphens in filenames:
sed 's/^[[:space:]]*-[[:space:]]*//'

# WRONG - strips all hyphens with spaces:
sed 's/[[:space:]]*-[[:space:]]*//'
```

## Service Standards

### 1. API Conventions
- [ ] **Health Endpoint**: `GET /health` returns `{"status": "healthy"}`
- [ ] **Error Handling**: Consistent error responses
- [ ] **Authentication**: Integration with STING auth if required
- [ ] **CORS Configuration**: Proper CORS headers for frontend integration

### 2. Logging Standards
- [ ] **Log Directory**: Mount `/var/log/service-name` volume
- [ ] **Log Format**: Structured logging (JSON preferred)
- [ ] **Log Levels**: Appropriate log levels (DEBUG, INFO, WARN, ERROR)
- [ ] **Sensitive Data**: No secrets or PII in logs

### 3. Security Requirements
- [ ] **Non-Root User**: Run as non-root user in container
- [ ] **Secrets Management**: Use environment variables for secrets
- [ ] **Input Validation**: Validate all API inputs
- [ ] **Rate Limiting**: Implement if service is externally accessible

## Database Integration (if required)

- [ ] **Database Models**: SQLAlchemy models with proper relationships
- [ ] **Migrations**: Database migration scripts
- [ ] **Connection Pooling**: Proper database connection management
- [ ] **Error Handling**: Database connection error handling

## Testing Requirements

- [ ] **Unit Tests**: Core functionality unit tests
- [ ] **Integration Tests**: Service integration tests
- [ ] **Health Check Tests**: Validate health endpoint functionality
- [ ] **Docker Tests**: Container build and startup tests

## Documentation Requirements

- [ ] **Service README**: Purpose, API, configuration
- [ ] **API Documentation**: Endpoint documentation
- [ ] **Configuration Guide**: Environment variables and settings
- [ ] **Troubleshooting Guide**: Common issues and solutions

## Service-Specific Implementations

### Public Bee (Nectar Bots) ✅
- [x] **Service Directory**: `public_bee/`
- [x] **Docker Configuration**: FastAPI with PostgreSQL integration
- [x] **File Sync Rules**: Added to `lib/file_operations.sh`
- [x] **Health Checks**: HTTP health endpoint integration
- [x] **API Endpoints**: Public chat API with authentication
- [x] **Database Models**: Bot management and usage tracking
- [x] **Admin Interface**: React component integration

## Validation Checklist

### Pre-Deployment Testing
- [ ] **Local Build**: Service builds successfully
- [ ] **Health Check**: Health endpoint responds correctly
- [ ] **Service Update**: `./manage_sting.sh update service-name` works
- [ ] **Log Verification**: Logs appear in expected locations
- [ ] **Resource Usage**: Memory/CPU usage within limits

### Production Readiness
- [ ] **Error Handling**: Graceful error responses
- [ ] **Resource Monitoring**: Metrics and monitoring integration
- [ ] **Backup Strategy**: Data persistence and backup procedures
- [ ] **Security Review**: Security assessment completed

## Common Patterns by Service Type

### Web API Services
- FastAPI/Flask application structure
- Database connection pooling
- Authentication middleware
- CORS configuration
- Request/response logging

### Background Workers
- Job queue integration
- Error retry logic
- Progress tracking
- Resource cleanup

### Data Processing Services
- Streaming data handling
- Batch processing capabilities
- Memory management
- Progress reporting

## Service Examples

### Minimal FastAPI Service
```python
from fastapi import FastAPI
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "example-service"}

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up...")

@app.on_event("shutdown") 
async def shutdown_event():
    logger.info("Service shutting down...")
```

### Docker Compose Service Template
```yaml
example-service:
  container_name: sting-ce-example-service
  build:
    context: ./example_service
    dockerfile: Dockerfile
  env_file:
    - ${INSTALL_DIR}/env/example-service.env
  ports:
    - "8093:8093"
  networks:
    sting_local:
      aliases:
        - example-service
  depends_on:
    db:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
  restart: unless-stopped
```