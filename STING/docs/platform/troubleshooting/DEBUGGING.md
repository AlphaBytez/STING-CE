# STING Platform Debugging Guide

This guide provides comprehensive information about debugging tools and techniques available in the STING platform.

## Table of Contents
- [Overview](#overview)
- [Debug Interface](#debug-interface)
- [Service Health Monitoring](#service-health-monitoring)
- [Backend Debug Endpoints](#backend-debug-endpoints)
- [Frontend Debug Components](#frontend-debug-components)
- [Docker Container Debugging](#docker-container-debugging)
- [Common Debugging Scenarios](#common-debugging-scenarios)

## Overview

STING provides a comprehensive set of debugging tools to help developers troubleshoot issues with authentication, services, and integrations. The platform includes both frontend and backend debugging capabilities.

### Key Features:
- Real-time service health monitoring
- Interactive API endpoint testing
- Authentication flow debugging
- Container status monitoring
- Knowledge service diagnostics

## Debug Interface

The main debug interface is accessible at `/debug` when running in development mode.

### Accessing the Debug Interface:
```bash
# Start the platform
docker compose up -d

# Navigate to:
https://localhost:8443/debug
```

### Available Debug Pages:
- **Main Debug Dashboard** (`/debug`) - Central hub for all debugging tools
- **Kratos API Testing** (`/debug/kratos`) - Test authentication endpoints
- **Verification Flow Testing** (`/debug/verification`) - Debug email verification
- **Service Health Dashboard** - Monitor all platform services

## Service Health Monitoring

STING includes health checks for all core services:

### Core Services:
| Service | Health Endpoint | Port | Purpose |
|---------|----------------|------|---------|
| Flask API | `https://localhost:5050/health` | 5050 | Main application API |
| Kratos Auth | `https://localhost:4434/admin/health/ready` | 4434 | Authentication service |
| Knowledge Service | `http://localhost:8090/health` | 8090 | Knowledge management |
| ChromaDB | `http://localhost:8000/api/v1/heartbeat` | 8000 | Vector database |
| Redis | `redis-cli ping` | 6379 | Cache and queue |
| Messaging | `http://localhost:8889/health` | 8889 | Real-time messaging |
| Chatbot | `http://localhost:8888/health` | 8888 | Bee AI assistant |
| LLM Gateway | `http://localhost:8085/health` | 8085 | LLM proxy service |

### Quick Health Check Commands:
```bash
# Check all services at once
curl -s http://localhost:5050/api/debug/service-statuses | jq

# Individual service checks
curl -s http://localhost:8090/health | jq  # Knowledge service
curl -s http://localhost:8889/health | jq  # Messaging service
curl -s http://localhost:8888/health | jq  # Chatbot service

# Docker container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Backend Debug Endpoints

The Flask application provides several debug endpoints (defined in `app/routes/debug_routes.py`):

### Available Endpoints:

#### 1. **Service Status Overview**
```bash
GET /api/debug/service-statuses
```
Returns health status for all connected services.

#### 2. **Knowledge Service Health**
```bash
GET /api/debug/knowledge-health
```
Checks knowledge service connectivity and returns diagnostic information.

#### 3. **Container Status**
```bash
GET /api/debug/containers
```
Lists all STING Docker containers with their health status.

#### 4. **Configuration Debug**
```bash
GET /api/debug/config
```
Shows current environment configuration (sanitized).

### Example Usage:
```python
import requests

# Get all service statuses
response = requests.get('https://localhost:5050/api/debug/service-statuses', verify=False)
print(response.json())

# Check specific service
response = requests.get('https://localhost:5050/api/debug/knowledge-health', verify=False)
print(response.json())
```

## Frontend Debug Components

### Main Debug Page (`DebugPage.jsx`)
Located at `/frontend/src/components/auth/DebugPage.jsx`

Features:
- Service health status dashboard
- Quick links to all authentication flows
- API endpoint testing interface
- Browser compatibility checks

### Kratos Debug Component (`KratosDebug.jsx`)
Interactive testing for Kratos authentication endpoints:
- Registration flow testing
- Login flow testing
- Session management
- Error flow inspection

### Verification Debug (`VerificationDebug.jsx`)
Tools for debugging email verification:
- Verification token inspection
- Email delivery status
- Mailpit integration testing

## Docker Container Debugging

### View Container Logs:
```bash
# View logs for a specific service
docker logs sting-ce-knowledge -f
docker logs sting-ce-app-1 -f
docker logs sting-ce-chatbot -f

# View logs with timestamps
docker logs --timestamps sting-ce-knowledge

# View last 100 lines
docker logs --tail 100 sting-ce-app-1
```

### Container Health Status:
```bash
# Check container health
docker inspect sting-ce-knowledge --format='{{.State.Health.Status}}'

# View detailed health check logs
docker inspect sting-ce-knowledge --format='{{json .State.Health}}' | jq
```

### Execute Commands in Containers:
```bash
# Check Python version in knowledge service
docker exec sting-ce-knowledge python --version

# Test internal connectivity
docker exec sting-ce-app-1 curl http://knowledge:8090/health
```

## Common Debugging Scenarios

### 1. File Download Issues

STING includes comprehensive diagnostics for file download and report generation problems.

#### File Download Diagnostic System

**Enhanced Logging Prefixes**:
- `[FILE_DOWNLOAD]` - File service operations
- `[REPORT_DOWNLOAD]` - Report download tracking
- `[PERMISSION_CHECK]` - Access control debugging
- `[FILE_DEBUG]` - Diagnostic endpoint logging

#### Quick Diagnosis Commands

```bash
# View file download logs in real-time
docker logs sting-ce-app -f | grep -E '\[(FILE_DOWNLOAD|REPORT_DOWNLOAD|PERMISSION_CHECK)\]'

# Check recent file download issues
docker logs sting-ce-app --since=1h | grep -E '\[(FILE_DOWNLOAD|REPORT_DOWNLOAD)\]'

# Test file access without downloading
curl -k -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
     https://localhost:5050/api/reports/debug/file/<FILE_ID>
```

#### File Download Flow Debugging

1. **Check Database Record**:
   ```bash
   # Diagnostic endpoint shows complete file info
   curl -k -H "X-API-Key: YOUR_API_KEY" \
        https://localhost:5050/api/reports/debug/file/<FILE_ID> | jq
   ```

   Look for:
   - `database_record_found: true`
   - `storage_path` has valid Vault path
   - `owner_id` matches requesting user
   - `file_size > 0`

2. **Verify Permissions**:
   ```bash
   # Check permission logs
   docker logs sting-ce-app | grep "\[PERMISSION_CHECK\]" | tail -5
   ```

   Should show:
   - `User X owns file Y - permission granted` OR
   - `Found explicit permission for user X on file Y: active=true`

3. **Test Vault Connectivity**:
   ```bash
   # Diagnostic endpoint tests Vault retrieval
   # Look for vault_test section in response
   curl -k -H "X-API-Key: YOUR_API_KEY" \
        https://localhost:5050/api/reports/debug/file/<FILE_ID> | jq '.debug_info.vault_test'
   ```

   Should show:
   - `response_received: true`
   - `has_data_key: true`
   - `data_size > 0`

4. **Monitor Encryption/Decryption**:
   ```bash
   # Check encryption processing
   docker logs sting-ce-app | grep -E '\[FILE_DOWNLOAD\].*encrypt' | tail -3
   ```

#### Common File Download Issues

**Issue**: `Report file not accessible`
```bash
# Check specific error details
curl -k -H "X-API-Key: YOUR_API_KEY" \
     https://localhost:5050/api/reports/<REPORT_ID>/download
```
Look for detailed error response with `file_id` and failure reason.

**Issue**: `Permission denied`
```bash
# Check ownership and permissions
docker logs sting-ce-app | grep -E "PERMISSION_CHECK.*<FILE_ID>" | tail -1
```
Shows exactly why permission was denied.

**Issue**: `Vault retrieval fails`
```bash
# Test Vault service health
docker logs sting-ce-vault | tail -20
curl -k https://localhost:8200/v1/sys/health
```

**Issue**: `File exists but returns 0 bytes`
```bash
# Check storage path and file integrity
docker logs sting-ce-app | grep -E "FILE_DOWNLOAD.*storage_path.*<FILE_ID>" | tail -1
```

#### File Download Diagnostic Endpoint

**Endpoint**: `/api/reports/debug/file/<file_id>`
**Purpose**: Test file access without actual download
**Authentication**: Requires API key or valid session

**Example Response**:
```json
{
  "success": true,
  "debug_info": {
    "file_id": "52df54f8-e7c9-4a4b-ae1e-8013c3a1a794",
    "user_id": "32",
    "database_record_found": true,
    "vault_client_available": true,
    "filename": "report_20250913.pdf",
    "storage_backend": "vault",
    "storage_path": "32/report/d9cca6e981e94b74",
    "owner_id": "32",
    "file_size": 2511,
    "is_deleted": false,
    "permission_granted": true,
    "vault_test": {
      "response_received": true,
      "response_type": "<class 'dict'>",
      "has_data_key": true,
      "data_type": "<class 'bytes'>",
      "data_size": 3985
    }
  }
}
```

#### File Download Success Flow

When working correctly, logs should show:
```
[PERMISSION_CHECK] User 32 owns file abc-123 - permission granted
[FILE_DOWNLOAD] File found: filename=report.pdf, storage_backend=vault, storage_path=32/report/d9cc...
[FILE_DOWNLOAD] Attempting Vault retrieval with path: 32/report/d9cc...
[FILE_DOWNLOAD] Vault response received. Type: <class 'dict'>, Keys: dict_keys(['data', 'size', 'hash'])
[FILE_DOWNLOAD] Raw data retrieved. Size: 3985 bytes, Type: <class 'bytes'>
[FILE_DOWNLOAD] File abc-123 is unencrypted, returning raw data
[REPORT_DOWNLOAD] File data retrieved successfully. Size: 3985 bytes
[REPORT_DOWNLOAD] Sending file: filename=report.pdf, mimetype=application/pdf
```

#### Troubleshooting Tips

1. **Always test with diagnostic endpoint first** - Shows exact failure point
2. **Check logs for specific file ID** - Use `grep "FILE_ID"` to trace single file
3. **Verify report completion** - Files only downloadable after `status: completed`
4. **Monitor Vault connectivity** - Many issues are storage backend related
5. **Test with different users** - Permission issues are user-specific
6. **Check file metadata** - Encryption status affects download process

### 2. Knowledge Service Not Starting
```bash
# Check if service is running
docker ps | grep knowledge

# View logs
docker logs sting-ce-knowledge

# Test health endpoint
curl http://localhost:8090/health

# Check ChromaDB dependency
curl http://localhost:8000/api/v1/heartbeat
```

### 2. Authentication Issues
- Navigate to `/debug/kratos` for interactive testing
- Check Kratos logs: `docker logs sting-ce-kratos-1`
- Verify sessions: `curl https://localhost:4433/sessions/whoami`

### 3. LLM Service Issues
```bash
# Check native LLM status
./sting-llm status

# View LLM logs
./sting-llm logs

# Test LLM gateway proxy
curl http://localhost:8085/health
```

### 4. Database Connection Issues
```bash
# Check PostgreSQL
docker exec sting-ce-db pg_isready

# View database logs
docker logs sting-ce-db

# Connect to database
docker exec -it sting-ce-db psql -U postgres -d sting_app
```

### 5. Redis/Caching Issues
```bash
# Test Redis connection
docker exec sting-ce-redis redis-cli ping

# Monitor Redis in real-time
docker exec -it sting-ce-redis redis-cli monitor
```

## Environment Variables for Debugging

Set these environment variables for enhanced debugging:

```bash
# Enable debug logging
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# Enable SQL query logging
export SQLALCHEMY_ECHO=true

# Knowledge service debug mode
export KNOWLEDGE_DEBUG=true

# Verbose Docker Compose output
export COMPOSE_VERBOSE=true
```

## Troubleshooting Tips

1. **Always check service health first** - Many issues are caused by unhealthy services
2. **Use the debug interface** - The `/debug` route provides visual tools for testing
3. **Check container logs** - Most errors are logged with detailed information
4. **Verify network connectivity** - Use `docker exec` to test internal connections
5. **Monitor resource usage** - Some services may fail due to memory constraints

## Related Documentation

- [Service Health Monitoring](./SERVICE_HEALTH_MONITORING.md)
- [Troubleshooting Guide](../troubleshooting/README.md)
- [Common Errors and Fixes](./COMMON_ERRORS_AND_FIXES.md)
- [Authentication Troubleshooting](../kratos/LOGIN_TROUBLESHOOTING.md)