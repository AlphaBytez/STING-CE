# Service Health Monitoring Guide

This guide provides detailed information about monitoring the health and status of all STING platform services.

## Table of Contents
- [Overview](#overview)
- [Health Check Endpoints](#health-check-endpoints)
- [Monitoring Commands](#monitoring-commands)
- [Service Dependencies](#service-dependencies)
- [Automated Health Checks](#automated-health-checks)
- [Troubleshooting Unhealthy Services](#troubleshooting-unhealthy-services)

## Overview

STING implements comprehensive health monitoring across all microservices. Each service exposes health endpoints that provide real-time status information.

### Health Check Types:
- **Liveness**: Is the service running?
- **Readiness**: Is the service ready to accept requests?
- **Dependencies**: Are required services available?

## Health Check Endpoints

### Core Services

| Service | Health Endpoint | Expected Response | Critical |
|---------|----------------|-------------------|----------|
| Flask API | `https://localhost:5050/health` | `{"status": "healthy"}` | ✅ Yes |
| Kratos Auth | `https://localhost:4434/admin/health/ready` | `{"status": "ready"}` | ✅ Yes |
| PostgreSQL | `docker exec sting-ce-db pg_isready` | `accepting connections` | ✅ Yes |
| Vault | `http://localhost:8200/v1/sys/health` | `{"initialized": true}` | ✅ Yes |

### AI & Knowledge Services

| Service | Health Endpoint | Expected Response | Critical |
|---------|----------------|-------------------|----------|
| Knowledge Service | `http://localhost:8090/health` | `{"status": "healthy", "service": "knowledge"}` | ✅ Yes |
| ChromaDB | `http://localhost:8000/api/v1/heartbeat` | `{"nanosecond heartbeat": ...}` | ✅ Yes |
| Chatbot | `http://localhost:8888/health` | `{"status": "healthy"}` | ❌ No |
| LLM Gateway | `http://localhost:8085/health` | `{"status": "healthy"}` | ❌ No |

### Supporting Services

| Service | Health Endpoint | Expected Response | Critical |
|---------|----------------|-------------------|----------|
| Redis | `docker exec sting-ce-redis redis-cli ping` | `PONG` | ❌ No |
| Messaging | `http://localhost:8889/health` | `{"status": "healthy"}` | ❌ No |
| Mailpit | N/A | Check container status | ❌ No |
| Frontend | Check container status | Running | ✅ Yes |

## Monitoring Commands

### Quick Health Check Script
```bash
#!/bin/bash
# Save as check_health.sh

echo "=== STING Service Health Check ==="
echo

# Core Services
echo "Flask API: $(curl -s https://localhost:5050/health 2>/dev/null || echo 'OFFLINE')"
echo "Kratos: $(curl -s https://localhost:4434/admin/health/ready 2>/dev/null || echo 'OFFLINE')"
echo "Vault: $(curl -s http://localhost:8200/v1/sys/health 2>/dev/null || echo 'OFFLINE')"
echo "Database: $(docker exec sting-ce-db pg_isready 2>&1 || echo 'OFFLINE')"
echo

# AI Services
echo "Knowledge: $(curl -s http://localhost:8090/health 2>/dev/null || echo 'OFFLINE')"
echo "ChromaDB: $(curl -s http://localhost:8000/api/v1/heartbeat 2>/dev/null | head -c 50)..."
echo "Chatbot: $(curl -s http://localhost:8888/health 2>/dev/null || echo 'OFFLINE')"
echo "LLM Gateway: $(curl -s http://localhost:8085/health 2>/dev/null || echo 'OFFLINE')"
echo

# Support Services
echo "Redis: $(docker exec sting-ce-redis redis-cli ping 2>&1 || echo 'OFFLINE')"
echo "Messaging: $(curl -s http://localhost:8889/health 2>/dev/null || echo 'OFFLINE')"
```

### Container Status Monitoring
```bash
# View all containers with health status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"

# Watch container status in real-time
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Get detailed health info for a specific service
docker inspect sting-ce-knowledge --format='{{json .State.Health}}' | jq
```

### Service Logs Monitoring
```bash
# Monitor multiple services simultaneously
docker compose logs -f app knowledge chatbot

# View logs with timestamps
docker logs --timestamps --tail 50 sting-ce-knowledge

# Search for errors across all services
docker compose logs | grep -i error
```

## Service Dependencies

Understanding service dependencies helps troubleshoot cascading failures:

```
┌─────────────────┐
│    Frontend     │
└────────┬────────┘
         │
┌────────▼────────┐
│   Flask API     │
├─────────────────┤
│ Depends on:     │
│ • PostgreSQL    │
│ • Vault         │
│ • Kratos        │
│ • Knowledge*    │
└────────┬────────┘
         │
┌────────▼────────┐     ┌─────────────┐
│   Knowledge     │────▶│  ChromaDB   │
└─────────────────┘     └─────────────┘
         │
┌────────▼────────┐     ┌─────────────┐
│    Chatbot      │────▶│ LLM Gateway │
├─────────────────┤     └─────────────┘
│ Depends on:     │
│ • Messaging     │
│ • Redis         │
└─────────────────┘
```

## Automated Health Checks

### Docker Compose Health Checks
Each service in `docker-compose.yml` includes health check configuration:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 30s
```

### Monitoring with Docker Events
```bash
# Monitor health check events
docker events --filter event=health_status

# Get health check history
docker inspect sting-ce-knowledge | jq '.[0].State.Health.Log'
```

### Creating Custom Health Monitors
```python
# health_monitor.py
import requests
import time
import json

SERVICES = {
    "flask_api": "https://localhost:5050/health",
    "knowledge": "http://localhost:8090/health",
    "chatbot": "http://localhost:8888/health",
    "chromadb": "http://localhost:8000/api/v1/heartbeat",
}

def check_services():
    results = {}
    for name, url in SERVICES.items():
        try:
            response = requests.get(url, timeout=5, verify=False)
            results[name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            results[name] = {
                "status": "offline",
                "error": str(e)
            }
    return results

# Run continuous monitoring
while True:
    status = check_services()
    print(json.dumps(status, indent=2))
    time.sleep(30)
```

## Troubleshooting Unhealthy Services

### Common Health Check Failures

#### 1. Knowledge Service Unhealthy
```bash
# Check if ChromaDB is running (dependency)
curl http://localhost:8000/api/v1/heartbeat

# View knowledge service logs
docker logs sting-ce-knowledge --tail 100

# Restart the service
docker compose restart knowledge
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL status
docker exec sting-ce-db pg_isready -U postgres

# View connection count
docker exec sting-ce-db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Reset connections
docker compose restart db app
```

#### 3. Redis Memory Issues
```bash
# Check Redis memory usage
docker exec sting-ce-redis redis-cli info memory

# Clear Redis cache if needed
docker exec sting-ce-redis redis-cli FLUSHALL

# Restart Redis
docker compose restart redis
```

#### 4. LLM Gateway Not Responding
```bash
# Check native LLM service (macOS)
./sting-llm status

# Check proxy configuration
docker logs sting-ce-llm-gateway-proxy

# Test direct connection
curl http://host.docker.internal:8086/health
```

### Health Check Best Practices

1. **Monitor Critical Services First**: Focus on database, authentication, and API services
2. **Set Appropriate Timeouts**: Adjust health check intervals based on service startup time
3. **Use Cascading Restarts**: Restart dependent services in order
4. **Log Health Events**: Keep history of health check failures for pattern analysis
5. **Alert on Repeated Failures**: Don't alert on single failures, wait for consistent issues

## Integration with Monitoring Systems

### Prometheus Metrics
```yaml
# Example prometheus configuration
scrape_configs:
  - job_name: 'sting-services'
    static_configs:
      - targets:
        - 'localhost:5050'  # Flask API metrics
        - 'localhost:8090'  # Knowledge service metrics
```

### Grafana Dashboard
Create dashboards to visualize:
- Service uptime percentages
- Response time trends
- Resource usage (CPU, memory)
- Error rates

### Alert Manager Rules
```yaml
# Example alert rule
groups:
  - name: sting_alerts
    rules:
      - alert: ServiceDown
        expr: up{job="sting-services"} == 0
        for: 5m
        annotations:
          summary: "Service {{ $labels.instance }} is down"
```

## Related Documentation

- [Debugging Guide](./DEBUGGING.md)
- [Troubleshooting Guide](../troubleshooting/README.md)
- [Docker Compose Configuration](../docker-compose.yml)
- [Service Architecture](../docs/architecture.md)