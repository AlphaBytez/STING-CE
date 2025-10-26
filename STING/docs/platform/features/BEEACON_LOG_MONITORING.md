# Beeacon Real-time Log Monitoring

## Overview

The Beeacon system provides comprehensive real-time log monitoring and analysis capabilities for STING-CE. Built on a modern observability stack, it aggregates logs from all services and provides intuitive interfaces for monitoring, searching, and alerting.

## Architecture

### Log Collection Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  STING Services │───▶│   Log Files     │───▶│    Promtail     │
│  (App, Kratos,  │    │ /var/log/sting/ │    │  (Collector)    │
│   Knowledge)    │    └─────────────────┘    └─────────────────┘
└─────────────────┘                                    │
                                                       ▼
┌─────────────────┐    ┌─────────────────────────────────────────┐
│ Docker Logs     │───▶│             Loki                        │
│ (Containers)    │    │        (Log Aggregation)                │
└─────────────────┘    └─────────────────────────────────────────┘
                                            │
                       ┌────────────────────┴────────────────────┐
                       ▼                                         ▼
            ┌─────────────────┐                      ┌─────────────────┐
            │    Grafana      │                      │  Beeacon UI     │
            │   (Analysis)    │                      │ (Real-time)     │
            └─────────────────┘                      └─────────────────┘
```

### Service Components

1. **Log Forwarder Container**: Streams Docker container logs to files
2. **Promtail**: Collects and labels log entries  
3. **Loki**: Stores and indexes log data
4. **Grafana**: Provides analysis dashboards
5. **Beeacon Frontend**: Real-time log viewer interface

## Configuration

### Log Forwarder Service

The log forwarder is defined in `docker-compose.yml`:

```yaml
log-forwarder:
  container_name: sting-ce-log-forwarder
  image: alpine:3.18
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - container_logs:/var/log/containers
  command: >
    sh -c '
      echo "Installing Docker client and setting up log forwarder..."
      apk add --no-cache docker-cli curl
      
      echo "Starting log forwarder for STING containers..."
      
      # Create log files
      mkdir -p /var/log/containers
      touch /var/log/containers/app.log
      touch /var/log/containers/knowledge.log
      touch /var/log/containers/chatbot.log
      touch /var/log/containers/kratos.log
      
      # Start log forwarding in background
      (docker logs -f sting-ce-app 2>&1 | while read line; do echo "$(date -Iseconds) [app] $line"; done >> /var/log/containers/app.log) &
      (docker logs -f sting-ce-knowledge 2>&1 | while read line; do echo "$(date -Iseconds) [knowledge] $line"; done >> /var/log/containers/knowledge.log) &
      (docker logs -f sting-ce-chatbot 2>&1 | while read line; do echo "$(date -Iseconds) [chatbot] $line"; done >> /var/log/containers/chatbot.log) &
      (docker logs -f sting-ce-kratos 2>&1 | while read line; do echo "$(date -Iseconds) [kratos] $line"; done >> /var/log/containers/kratos.log) &
      
      echo "Log forwarders started, keeping container alive..."
      while true; do sleep 60; done
    '
```

### Promtail Configuration

Located at `/observability/promtail/config/promtail.yml`:

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # STING centralized logs
  - job_name: sting-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: sting-logs
          __path__: /var/log/sting/*.log

  # Container logs forwarded by log-forwarder
  - job_name: container-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: container-logs
          __path__: /var/log/containers/*.log
    pipeline_stages:
      - regex:
          expression: '^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}) \[(?P<service>\w+)\] (?P<message>.*)$'
      - labels:
          service:
      - timestamp:
          source: timestamp
          format: RFC3339
```

### Loki Configuration

Located at `/observability/loki/config/loki.yml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 720h  # 30 days
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32
  max_concurrent_tail_requests: 20

compactor:
  retention_enabled: true
  retention_delete_delay: 2h
```

## Frontend Integration

### Beeacon Page Component

The real-time log viewer is accessible through the Beeacon page (`/dashboard/beeacon`):

```javascript
// Key features in the Beeacon interface:
const BeeaconPage = () => {
  const [logQuery, setLogQuery] = useState('');
  const [logResults, setLogResults] = useState([]);
  const [liveMode, setLiveMode] = useState(false);
  
  // Real-time log streaming
  const streamLogs = useCallback(() => {
    const eventSource = new EventSource('/api/logs/stream');
    eventSource.onmessage = (event) => {
      const logEntry = JSON.parse(event.data);
      setLogResults(prev => [...prev.slice(-100), logEntry]);
    };
    return eventSource;
  }, []);
  
  // Log search functionality
  const searchLogs = async (query) => {
    const response = await fetch(`/api/logs/query?q=${encodeURIComponent(query)}`);
    const results = await response.json();
    setLogResults(results.data);
  };
};
```

### Interactive Features

1. **Real-time Streaming**: Live log updates as they occur
2. **Search Interface**: Query logs by service, level, or content
3. **Filtering**: Filter by time range, service, log level
4. **Export**: Download log segments for analysis
5. **Alerting**: Set up alerts for specific log patterns

## Log Querying

### LogQL Query Examples

```logql
# All logs from the app service
{job="container-logs", service="app"}

# Error logs from all services
{job="sting-logs"} |= "ERROR"

# Authentication-related logs
{service="kratos"} |= "authentication"

# High-frequency queries (last 5 minutes)
{job="container-logs"} |= "error" [5m]

# Rate of errors per minute
rate({job="sting-logs"} |= "ERROR" [1m])
```

### API Endpoints

The log monitoring system exposes several API endpoints:

```bash
# Query logs
GET /api/logs/query?q={logql_query}&start={timestamp}&end={timestamp}

# Stream logs in real-time  
GET /api/logs/stream (Server-Sent Events)

# Get log statistics
GET /api/logs/stats?service={service_name}

# Export logs
GET /api/logs/export?format=csv&query={logql_query}
```

## Service Management

### Starting Log Monitoring

```bash
# Start observability stack with log monitoring
./manage_sting.sh start --profile observability

# Or start individual components
docker compose up -d loki promtail log-forwarder grafana
```

### Health Monitoring

```bash
# Check all log services
./manage_sting.sh status | grep -E "(loki|promtail|grafana|log-forwarder)"

# Check Promtail status
curl -s http://localhost:9080/ready

# Check Loki query capabilities
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="sting-logs"}' \
  --data-urlencode 'limit=5'
```

### Log Volume Management

```bash
# Check log storage usage
docker exec sting-ce-loki du -sh /loki/

# Clean old logs (respects retention policy)
curl -X POST "http://localhost:3100/loki/api/v1/delete" \
  -H "Content-Type: application/json" \
  -d '{"query": "{job=\"sting-logs\"}", "start": "2024-01-01T00:00:00Z", "end": "2024-01-31T00:00:00Z"}'
```

## Log Structure and Labels

### Standard Log Format

All STING services use structured logging:

```json
{
  "timestamp": "2024-08-22T10:30:45.123Z",
  "level": "INFO",
  "service": "app",
  "component": "auth",
  "message": "User authentication successful",
  "user_id": "user-123",
  "session_id": "session-456",
  "request_id": "req-789"
}
```

### Log Labels

Promtail automatically applies labels:

- `job`: Source job (sting-logs, container-logs)
- `service`: STING service name (app, kratos, knowledge, chatbot)  
- `level`: Log level (ERROR, WARN, INFO, DEBUG)
- `component`: Service component (auth, api, worker)

## Troubleshooting

### No Logs Appearing

**Symptoms:**
- Beeacon page shows no log data
- Grafana log dashboards are empty

**Diagnosis:**
```bash
# 1. Check Promtail is running and configured
./manage_sting.sh logs promtail

# 2. Verify log files exist
docker exec sting-ce-promtail ls -la /var/log/sting/

# 3. Test Loki connectivity
curl -G -s "http://localhost:3100/loki/api/v1/labels"
```

**Solutions:**
```bash
# Restart log collection pipeline
docker compose restart promtail log-forwarder

# Check file permissions
docker exec sting-ce-promtail chmod 644 /var/log/sting/*.log

# Verify Promtail configuration
docker exec sting-ce-promtail cat /etc/promtail/promtail.yml
```

### High Memory Usage

**Symptoms:**
- Loki container consuming excessive memory
- System becoming unresponsive

**Solutions:**
```bash
# Adjust retention period (reduce from 30 days)
# Edit observability/loki/config/loki.yml:
# retention_period: 168h  # 7 days instead of 720h

# Restart with new configuration
docker compose restart loki

# Monitor memory usage
docker stats sting-ce-loki
```

### Log Streaming Interruptions

**Symptoms:**
- Real-time log stream stops updating
- Connection errors in browser console

**Solutions:**
```bash
# Check log forwarder status
docker logs sting-ce-log-forwarder

# Restart log streaming services
docker compose restart log-forwarder promtail

# Verify disk space
df -h
```

## Performance Optimization

### Log Rotation

Implement log rotation to prevent disk space issues:

```bash
# Create logrotate configuration
cat > /etc/logrotate.d/sting << EOF
/var/log/sting/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker kill --signal=HUP sting-ce-promtail 2>/dev/null || true
    endscript
}
EOF
```

### Query Optimization

For better performance with large log volumes:

```logql
# Use specific time ranges
{job="sting-logs"} |= "error" [1h]

# Filter early in the query
{service="app"} |= "authentication" != "debug"

# Use aggregation for metrics
count_over_time({job="sting-logs"} |= "ERROR" [5m])
```

## Security Considerations

### Access Control

- **Internal Network**: Log services communicate on `sting_local` network only
- **Authentication**: Grafana protected by admin credentials
- **Data Privacy**: Logs remain on local infrastructure

### Log Sanitization

Sensitive data is automatically filtered:

```yaml
# Promtail pipeline stage for PII removal
pipeline_stages:
  - replace:
      expression: '(password=)[^&\s]+'
      replace: '${1}[REDACTED]'
  - replace:
      expression: '(token=)[^&\s]+'  
      replace: '${1}[REDACTED]'
```

## Integration with Other Systems

### Alert Management

Integrate with external systems:

```yaml
# Grafana alerting configuration
alerting:
  webhooks:
    - url: http://app:5050/api/alerts/webhook
      method: POST
      headers:
        Content-Type: application/json
```

### External Log Forwarding

Forward logs to external systems if needed:

```yaml
# Additional Promtail client for external forwarding
clients:
  - url: http://loki:3100/loki/api/v1/push
  - url: https://external-log-system/api/v1/push
    basic_auth:
      username: sting
      password: ${EXTERNAL_LOG_PASSWORD}
```

## Future Enhancements

### Planned Features

1. **ML-based Anomaly Detection**: Automatic detection of unusual log patterns
2. **Custom Dashboards**: User-configurable log analysis dashboards  
3. **Advanced Alerting**: Complex alert rules with correlation
4. **Log Analytics API**: Programmatic access to log insights

### Integration Roadmap

- **SIEM Integration**: Export to security information and event management systems
- **Metrics Correlation**: Link logs with performance metrics
- **Audit Trail**: Complete audit logging for compliance requirements

---

**Note**: The Beeacon log monitoring system provides production-ready log aggregation and real-time analysis capabilities. It's designed to scale with STING-CE deployments while maintaining privacy and security requirements.